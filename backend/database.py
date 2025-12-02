"""
База данных SQLite для хранения задач, статистики и истории рассылок.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "bot.db"


def get_db_path() -> Path:
    """Возвращает путь к базе данных."""
    db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


@contextmanager
def get_db():
    """Контекстный менеджер для работы с базой данных."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Инициализирует базу данных, создает таблицы если их нет."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Таблица задач
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                promo_message TEXT NOT NULL,
                error TEXT,
                post_ids TEXT NOT NULL,
                sent INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                log TEXT
            )
        """)
        
        # Таблица статистики по постам
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_stats (
                post_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                reposts INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (post_id, group_id, date)
            )
        """)
        
        # Таблица информации о пользователях
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                photo_url TEXT,
                last_seen TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Таблица истории рассылок (детальная)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaign_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                comment_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                sent_at TEXT,
                error TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # Таблица информации о группе
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_info (
                group_id INTEGER PRIMARY KEY,
                name TEXT,
                screen_name TEXT,
                description TEXT,
                members_count INTEGER,
                photo_url TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Индексы для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_campaign_task ON campaign_history(task_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_campaign_user ON campaign_history(user_id)
        """)


def save_task(task_data: Dict[str, Any]) -> None:
    """Сохраняет или обновляет задачу в базе данных."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO tasks 
            (id, status, created_at, completed_at, promo_message, error, 
             post_ids, sent, failed, total, log)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_data["id"],
            task_data["status"],
            task_data.get("created_at", datetime.utcnow().isoformat()),
            task_data.get("completed_at"),
            task_data.get("promo_message", ""),
            task_data.get("error"),
            json.dumps(task_data.get("post_ids", [])),
            task_data.get("sent", 0),
            task_data.get("failed", 0),
            task_data.get("total", 0),
            json.dumps(task_data.get("log", [])),
        ))


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Получает задачу по ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_all_tasks(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Получает список всех задач."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tasks 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]


def update_task_status(task_id: str, status: str, **kwargs) -> None:
    """Обновляет статус задачи и другие поля."""
    updates = ["status = ?"]
    values = [status]
    
    if "completed_at" in kwargs:
        updates.append("completed_at = ?")
        values.append(kwargs["completed_at"])
    if "sent" in kwargs:
        updates.append("sent = ?")
        values.append(kwargs["sent"])
    if "failed" in kwargs:
        updates.append("failed = ?")
        values.append(kwargs["failed"])
    if "total" in kwargs:
        updates.append("total = ?")
        values.append(kwargs["total"])
    if "log" in kwargs:
        updates.append("log = ?")
        values.append(json.dumps(kwargs["log"]))
    if "error" in kwargs:
        updates.append("error = ?")
        values.append(kwargs["error"])
    
    values.append(task_id)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
            values
        )


def save_post_stats(group_id: int, post_id: int, stats: Dict[str, Any]) -> None:
    """Сохраняет статистику поста."""
    today = datetime.utcnow().date().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO post_stats 
            (post_id, group_id, date, views, likes, comments, reposts, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_id,
            group_id,
            today,
            stats.get("views", 0),
            stats.get("likes", 0),
            stats.get("comments", 0),
            stats.get("reposts", 0),
            datetime.utcnow().isoformat(),
        ))


def save_user_info(user_id: int, user_data: Dict[str, Any]) -> None:
    """Сохраняет информацию о пользователе."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, first_name, last_name, photo_url, last_seen, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            user_data.get("first_name"),
            user_data.get("last_name"),
            user_data.get("photo_url"),
            user_data.get("last_seen"),
            datetime.utcnow().isoformat(),
        ))


def save_group_info(group_id: int, group_data: Dict[str, Any]) -> None:
    """Сохраняет информацию о группе."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO group_info 
            (group_id, name, screen_name, description, members_count, photo_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            group_id,
            group_data.get("name"),
            group_data.get("screen_name"),
            group_data.get("description"),
            group_data.get("members_count"),
            group_data.get("photo_url"),
            datetime.utcnow().isoformat(),
        ))


def get_group_info(group_id: int) -> Optional[Dict[str, Any]]:
    """Получает информацию о группе."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM group_info WHERE group_id = ?", (group_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def save_campaign_entry(
    task_id: str, user_id: int, post_id: int, comment_id: int, 
    status: str, error: Optional[str] = None
) -> None:
    """Сохраняет запись об отправке сообщения пользователю."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO campaign_history 
            (task_id, user_id, post_id, comment_id, status, sent_at, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            user_id,
            post_id,
            comment_id,
            status,
            datetime.utcnow().isoformat() if status == "sent" else None,
            error,
        ))


def get_campaign_stats(task_id: str) -> Dict[str, Any]:
    """Получает статистику по кампании."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM campaign_history
            WHERE task_id = ?
        """, (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else {"total": 0, "sent": 0, "failed": 0}


# Инициализация базы при импорте
init_db()

