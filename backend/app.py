import json
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator

from storage import (
    BotConfig,
    config_to_dict,
    get_active_community,
    load_config,
    save_config,
    update_config,
)
from tasks import TaskState, tasks
from vk_service import VKService
from database import (
    get_all_tasks, get_task as get_task_db, get_group_info,
    save_group_info, get_campaign_stats
)

app = FastAPI(title="VK Admin Panel", version="1.0.0")

# Определяем пути относительно корня проекта
BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "front" / "templates"
STATIC_DIR = BASE_DIR / "front" / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class CommunityPayload(BaseModel):
    name: str | None = ""
    group_id: int
    user_token: str
    group_token: str


class ConfigPayload(BaseModel):
    communities: list[CommunityPayload]
    active_group_id: int | None = None
    request_delay: float = Field(ge=0.05, le=30.0)
    promo_message: str

    @validator("promo_message")
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("promo_message cannot be empty")
        return v


class SendPayload(BaseModel):
    post_ids: list[int]
    message: str | None = None

    @validator("post_ids")
    def validate_posts(cls, v: list[int]) -> list[int]:
        unique = list(dict.fromkeys(v))
        if not unique:
            raise ValueError("Нужно выбрать хотя бы один пост")
        return unique


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    cfg = load_config()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "config": cfg,
            "config_dict": config_to_dict(cfg),
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    cfg = load_config()
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "config": cfg,
            "config_dict": config_to_dict(cfg),
        },
    )


@app.get("/api/config")
async def get_config():
    cfg = load_config()
    return config_to_dict(cfg)


@app.post("/api/config")
async def save_config_api(payload: ConfigPayload):
    payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()

    if not payload_dict.get("communities"):
        raise HTTPException(status_code=400, detail="Нужно добавить хотя бы одно сообщество")

    if not payload_dict.get("active_group_id"):
        payload_dict["active_group_id"] = payload_dict["communities"][0]["group_id"]

    cfg = update_config(payload_dict)
    return {"ok": True, "config": config_to_dict(cfg)}


class ActiveGroupPayload(BaseModel):
    group_id: int


@app.post("/api/config/active")
async def set_active_group(payload: ActiveGroupPayload):
    cfg = load_config()
    if not any(c.group_id == payload.group_id for c in cfg.communities):
        raise HTTPException(status_code=400, detail="Сообщество не найдено")
    cfg.active_group_id = payload.group_id
    # обновляем legacy поля для совместимости
    active = get_active_community(cfg)
    if active:
        cfg.group_id = active.group_id
        cfg.user_token = active.user_token
        cfg.group_token = active.group_token
    save_config(cfg)
    return config_to_dict(cfg)


@app.get("/api/posts")
async def get_posts(limit: int = 100):
    cfg = load_config()
    if not get_active_community(cfg):
        raise HTTPException(status_code=400, detail="Не выбрано сообщество")
    client = VKService(cfg)
    safe_limit = max(1, min(limit, 100))
    try:
        posts = await client.fetch_posts(limit=safe_limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"items": posts}


@app.post("/api/send")
async def start_campaign(payload: SendPayload):
    cfg = load_config()
    promo_message = (payload.message or cfg.promo_message).strip()
    active = get_active_community(cfg)

    if not active or not active.user_token or not active.group_token:
        raise HTTPException(status_code=400, detail="Сначала сохраните токены и группу")

    if not promo_message:
        raise HTTPException(status_code=400, detail="Текст сообщения пустой")

    # keep latest message as default for next sessions
    if promo_message != cfg.promo_message:
        copy_fn = getattr(cfg, "model_copy", cfg.copy)
        cfg = copy_fn(update={"promo_message": promo_message})
        save_config(cfg)

    state: TaskState = tasks.create_campaign(cfg, payload.post_ids, promo_message)
    return {"task_id": state.id, "status": state.status}


@app.get("/api/tasks")
async def list_tasks(limit: int = 50, offset: int = 0):
    # Получаем задачи из памяти и из БД
    memory_tasks = {task.id: task.snapshot() for task in tasks.tasks.values()}
    db_tasks = get_all_tasks(limit=limit, offset=offset)
    
    # Объединяем, приоритет у задач в памяти (активные)
    result = []
    for db_task in db_tasks:
        task_id = db_task["id"]
        if task_id in memory_tasks:
            # Используем актуальную версию из памяти
            result.append(memory_tasks[task_id])
        else:
            # Преобразуем данные из БД
            result.append({
                "id": db_task["id"],
                "status": db_task["status"],
                "promo_message": db_task["promo_message"],
                "error": db_task.get("error"),
                "post_ids": json.loads(db_task.get("post_ids", "[]")),
                "sent": db_task.get("sent", 0),
                "failed": db_task.get("failed", 0),
                "total": db_task.get("total", 0),
                "log": json.loads(db_task.get("log", "[]")),
                "created_at": db_task.get("created_at"),
            })
    
    return {"items": result}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    # Сначала проверяем активные задачи в памяти
    state = tasks.get(task_id)
    if state:
        return state.snapshot()
    
    # Если нет в памяти, ищем в БД
    db_task = get_task_db(task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    import json
    return {
        "id": db_task["id"],
        "status": db_task["status"],
        "promo_message": db_task["promo_message"],
        "error": db_task.get("error"),
        "post_ids": json.loads(db_task.get("post_ids", "[]")),
        "sent": db_task.get("sent", 0),
        "failed": db_task.get("failed", 0),
        "total": db_task.get("total", 0),
        "log": json.loads(db_task.get("log", "[]")),
        "created_at": db_task.get("created_at"),
    }


@app.get("/api/group/info")
async def get_group_info_api():
    """Получает информацию о группе."""
    cfg = load_config()
    active = get_active_community(cfg)
    if not active or not active.user_token or not active.group_id:
        raise HTTPException(status_code=400, detail="Токены не настроены")
    
    # Проверяем кэш в БД
    cached_info = get_group_info(active.group_id)
    
    # Если кэш свежий (менее часа), возвращаем его
    if cached_info:
        from datetime import datetime, timedelta
        updated_at = datetime.fromisoformat(cached_info["updated_at"])
        if datetime.utcnow() - updated_at < timedelta(hours=1):
            return cached_info
    
    # Получаем свежую информацию из VK API
    try:
        client = VKService(cfg)
        group_data = await client.get_group_info()
        if group_data:
            save_group_info(active.group_id, group_data)
            return group_data
        else:
            return cached_info or {}
    except Exception as exc:
        # Если ошибка, возвращаем кэш если есть
        if cached_info:
            return cached_info
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/posts/{post_id}")
async def get_post_details_api(post_id: int):
    """Получает детальную информацию о посте."""
    cfg = load_config()
    active = get_active_community(cfg)
    if not active or not active.user_token:
        raise HTTPException(status_code=400, detail="Токены не настроены")
    
    try:
        client = VKService(cfg)
        post_details = await client.get_post_details(post_id)
        return post_details
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/stats/campaign/{task_id}")
async def get_campaign_stats_api(task_id: str):
    """Получает детальную статистику по кампании."""
    stats = get_campaign_stats(task_id)
    return stats


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["../front", "."])
