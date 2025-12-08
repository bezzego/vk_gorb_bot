import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from storage import BotConfig
from vk_service import VKService


@dataclass
class WatchState:
    id: str
    post_id: int
    message: str
    status: str = "running"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    replied: int = 0
    errors: int = 0
    last_seen_comment: int = 0
    log: List[str] = field(default_factory=list)

    def add_log(self, text: str) -> None:
        self.log.append(text)
        if len(self.log) > 50:
            self.log = self.log[-50:]

    def snapshot(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "post_id": self.post_id,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at,
            "replied": self.replied,
            "errors": self.errors,
            "last_seen_comment": self.last_seen_comment,
            "log": self.log,
        }


class WatchManager:
    def __init__(self) -> None:
        self.watchers: Dict[str, WatchState] = {}

    def list(self) -> List[Dict[str, object]]:
        return [w.snapshot() for w in self.watchers.values()]

    def start(self, cfg: BotConfig, post_id: int, message: str) -> WatchState:
        watch_id = uuid.uuid4().hex[:8]
        state = WatchState(id=watch_id, post_id=post_id, message=message)
        self.watchers[watch_id] = state
        asyncio.create_task(self._run(state, cfg))
        return state

    def stop(self, watch_id: str) -> bool:
        state = self.watchers.get(watch_id)
        if not state:
            return False
        state.status = "stopped"
        state.add_log("Остановка по запросу пользователя.")
        return True

    async def _run(self, state: WatchState, cfg: BotConfig) -> None:
        client = VKService(cfg)
        state.add_log("Старт автоответа, считываю последние комментарии...")

        # первичное считывание, чтобы не отвечать на старые
        try:
            comments = await client.fetch_comments(state.post_id, limit=50)
            if comments:
                state.last_seen_comment = max(c["id"] for c in comments)
                state.add_log(f"Пропустил {len(comments)} старых комментариев.")
        except Exception as exc:
            state.add_log(f"Ошибка при начальном чтении: {exc}")

        try:
            while state.status == "running":
                try:
                    comments = await client.fetch_comments(state.post_id, limit=30)
                except Exception as exc:
                    state.errors += 1
                    state.add_log(f"Ошибка чтения: {exc}")
                    await asyncio.sleep(cfg.request_delay or 0.5)
                    continue

                new_processed = False
                for c in comments or []:
                    cid = c["id"]
                    if state.last_seen_comment and cid <= state.last_seen_comment:
                        continue
                    state.last_seen_comment = max(state.last_seen_comment, cid)
                    ok = await client.reply_to_comment(state.post_id, cid, state.message)
                    if ok:
                        state.replied += 1
                        state.add_log(f"Ответил на комментарий {cid}")
                    else:
                        state.errors += 1
                        state.add_log(f"Не удалось ответить на {cid}")
                    new_processed = True
                    await asyncio.sleep(cfg.request_delay or 0.35)

                # более частый опрос, чтобы отвечать почти сразу
                await asyncio.sleep(1 if new_processed else 2)
        finally:
            state.status = "stopped"
            state.add_log("Автоответ остановлен.")
            await client.close()


watchers = WatchManager()
