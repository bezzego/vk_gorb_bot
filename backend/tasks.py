import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from storage import BotConfig
from vk_service import VKService
from database import (
    save_task, update_task_status, save_campaign_entry,
    save_post_stats, save_user_info, save_group_info
)


@dataclass
class TaskState:
    id: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    promo_message: str = ""
    error: str = ""
    post_ids: List[int] = field(default_factory=list)
    sent: int = 0
    failed: int = 0
    total: int = 0
    log: List[str] = field(default_factory=list)

    def add_log(self, text: str) -> None:
        self.log.append(text)
        if len(self.log) > 80:
            self.log = self.log[-80:]

    def snapshot(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "status": self.status,
            "promo_message": self.promo_message,
            "error": self.error,
            "post_ids": self.post_ids,
            "sent": self.sent,
            "failed": self.failed,
            "total": self.total,
            "log": self.log,
            "created_at": self.created_at,
        }


class TaskManager:
    def __init__(self) -> None:
        self.tasks: Dict[str, TaskState] = {}

    def get(self, task_id: str) -> TaskState | None:
        return self.tasks.get(task_id)

    def create_campaign(self, cfg: BotConfig, post_ids: List[int], message: str) -> TaskState:
        task_id = uuid.uuid4().hex[:8]
        state = TaskState(id=task_id, post_ids=post_ids, promo_message=message)
        self.tasks[task_id] = state
        
        # Сохраняем задачу в базу данных
        save_task(state.snapshot())
        
        asyncio.create_task(self._run_campaign(state, cfg))
        return state

    async def _run_campaign(self, state: TaskState, cfg: BotConfig) -> None:
        client = VKService(cfg)
        state.status = "collecting"
        state.add_log("Старт задачи, читаю комментарии выбранных постов...")

        def on_progress(event: Dict[str, object]) -> None:
            stage = event.get("stage")
            if event.get("log"):
                state.add_log(str(event["log"]))

            if stage == "collect":
                state.status = "collecting"
                update_task_status(state.id, "collecting", log=state.log)
            if stage == "collect_done":
                state.status = "collecting"
                update_task_status(state.id, "collecting", log=state.log)
            if stage == "sending":
                state.status = "sending"
                state.total = int(event.get("total", 0))
                update_task_status(state.id, "sending", total=state.total, log=state.log)
            if stage == "progress":
                state.status = "sending"
                prev_sent = state.sent
                state.sent = int(event.get("sent", state.sent))
                state.failed = int(event.get("failed", state.failed))
                state.total = int(event.get("total", state.total))
                
                # Сохраняем запись о попытке отправки
                user_id = event.get("user_id")
                post_id = event.get("post_id")
                comment_id = event.get("comment_id", 0)
                if user_id and post_id:
                    # Определяем статус отправки
                    send_status = "sent" if state.sent > prev_sent else "failed"
                    save_campaign_entry(
                        state.id, int(user_id), int(post_id), 
                        int(comment_id) if comment_id else 0, send_status
                    )
                
                # Обновляем задачу в БД
                update_task_status(
                    state.id, state.status,
                    sent=state.sent, failed=state.failed, 
                    total=state.total, log=state.log
                )
            if stage == "error":
                state.status = "failed"
                update_task_status(state.id, "failed", error=str(event.get("log", "")), log=state.log)
            if stage == "completed":
                state.status = "completed"
                state.sent = int(event.get("sent", state.sent))
                state.failed = int(event.get("failed", state.failed))
                state.total = int(event.get("total", state.total))
                
                # Обновляем задачу в БД
                update_task_status(
                    state.id, "completed",
                    completed_at=datetime.utcnow().isoformat(),
                    sent=state.sent, failed=state.failed, 
                    total=state.total, log=state.log
                )

        try:
            # Сохраняем статистику постов перед началом
            for post_id in state.post_ids:
                try:
                    post_details = await client.get_post_details(post_id)
                    if post_details:
                        save_post_stats(
                            cfg.group_id, post_id,
                            {
                                "views": post_details.get("views", 0),
                                "likes": post_details.get("likes", 0),
                                "comments": post_details.get("comments", 0),
                                "reposts": post_details.get("reposts", 0),
                            }
                        )
                except Exception:
                    pass  # Игнорируем ошибки при сохранении статистики
            
            result = await client.send_campaign(
                state.post_ids, state.promo_message, on_progress=on_progress
            )
            state.status = "completed"
            state.sent = result["sent"]
            state.failed = result["failed"]
            state.total = result["total"]
            state.add_log("Задача завершена.")
            
            # Финальное обновление в БД
            update_task_status(
                state.id, "completed",
                completed_at=datetime.utcnow().isoformat(),
                sent=state.sent, failed=state.failed, 
                total=state.total, log=state.log
            )
        except Exception as exc:
            state.status = "failed"
            state.error = f"Ошибка: {exc}"
            state.add_log(state.error)
            update_task_status(
                state.id, "failed",
                error=state.error, log=state.log
            )
        finally:
            await client.close()


tasks = TaskManager()
