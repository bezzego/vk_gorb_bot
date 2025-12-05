import asyncio
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Tuple

from vkbottle import API
from vkbottle.exception_factory import VKAPIError

from storage import BotConfig, get_active_community
from database import save_user_info

ProgressHandler = Callable[[Dict[str, object]], None]


def _safe_text_preview(text: str, limit: int = 80) -> str:
    clean = (text or "").replace("\n", " ").strip()
    return clean if len(clean) <= limit else f"{clean[:limit].rstrip()}…"


class VKService:
    def __init__(self, cfg: BotConfig) -> None:
        self.cfg = cfg
        community = get_active_community(cfg)
        if not community:
            raise RuntimeError("Не выбрано сообщество")
        self.owner_id = -abs(community.group_id)
        self.user_api = API(community.user_token)
        self.group_api = API(community.group_token)

    async def fetch_posts(self, limit: int = 20) -> List[Dict[str, object]]:
        try:
            resp = await self.user_api.request(
                "wall.get", {
                    "owner_id": self.owner_id, 
                    "count": limit,
                    "extended": 1  # Получаем расширенную информацию
                }
            )
        except VKAPIError as exc:
            raise RuntimeError(f"VK API error while loading posts: {exc}") from exc

        payload = resp.get("response", resp) if isinstance(resp, dict) else {}
        items = payload.get("items") if isinstance(payload, dict) else []
        posts = []
        for item in items or []:
            # Получаем просмотры если доступны
            views = item.get("views", {})
            views_count = views.get("count", 0) if isinstance(views, dict) else 0
            
            # Получаем информацию о вложениях
            attachments = item.get("attachments", [])
            has_photo = any(att.get("type") == "photo" for att in attachments)
            has_video = any(att.get("type") == "video" for att in attachments)
            
            posts.append(
                {
                    "id": item.get("id"),
                    "text": item.get("text") or "",
                    "preview": _safe_text_preview(item.get("text") or "", 120),
                    "date": datetime.fromtimestamp(item.get("date", 0)).isoformat()
                    if item.get("date")
                    else "",
                    "comments": (item.get("comments") or {}).get("count", 0),
                    "likes": (item.get("likes") or {}).get("count", 0),
                    "reposts": (item.get("reposts") or {}).get("count", 0),
                    "views": views_count,
                    "has_photo": has_photo,
                    "has_video": has_video,
                    "attachments_count": len(attachments),
                }
            )
        return posts

    async def get_group_info(self) -> Dict[str, object]:
        """Получает информацию о группе."""
        try:
            resp = await self.user_api.request(
                "groups.getById", {
                    "group_id": abs(self.owner_id),
                    "fields": "members_count,description,photo_200"
                }
            )
        except VKAPIError as exc:
            raise RuntimeError(f"VK API error while loading group info: {exc}") from exc

        payload = resp.get("response", resp) if isinstance(resp, dict) else {}
        if isinstance(payload, list) and len(payload) > 0:
            group = payload[0]
        elif isinstance(payload, dict):
            group = payload
        else:
            return {}

        return {
            "id": group.get("id"),
            "name": group.get("name", ""),
            "screen_name": group.get("screen_name", ""),
            "description": group.get("description", ""),
            "members_count": group.get("members_count", 0),
            "photo_url": group.get("photo_200", ""),
        }

    async def get_post_details(self, post_id: int) -> Dict[str, object]:
        """Получает детальную информацию о посте."""
        try:
            resp = await self.user_api.request(
                "wall.getById", {
                    "posts": f"{self.owner_id}_{post_id}",
                    "extended": 1
                }
            )
        except VKAPIError as exc:
            raise RuntimeError(f"VK API error while loading post details: {exc}") from exc

        payload = resp.get("response", resp) if isinstance(resp, dict) else {}
        items = payload.get("items") if isinstance(payload, dict) else []
        
        if not items or len(items) == 0:
            return {}
        
        item = items[0]
        views = item.get("views", {})
        views_count = views.get("count", 0) if isinstance(views, dict) else 0
        
        return {
            "id": item.get("id"),
            "text": item.get("text", ""),
            "date": datetime.fromtimestamp(item.get("date", 0)).isoformat()
            if item.get("date") else "",
            "comments": (item.get("comments") or {}).get("count", 0),
            "likes": (item.get("likes") or {}).get("count", 0),
            "reposts": (item.get("reposts") or {}).get("count", 0),
            "views": views_count,
            "attachments": item.get("attachments", []),
        }

    async def get_users_info(self, user_ids: List[int]) -> List[Dict[str, object]]:
        """Получает информацию о пользователях."""
        if not user_ids:
            return []
        
        try:
            # VK API позволяет запрашивать до 1000 пользователей за раз
            resp = await self.user_api.request(
                "users.get", {
                    "user_ids": ",".join(map(str, user_ids[:1000])),
                    "fields": "photo_100,last_seen"
                }
            )
        except VKAPIError as exc:
            raise RuntimeError(f"VK API error while loading users info: {exc}") from exc

        payload = resp.get("response", resp) if isinstance(resp, dict) else {}
        users = payload if isinstance(payload, list) else []
        
        result = []
        for user in users:
            last_seen = user.get("last_seen", {})
            last_seen_time = None
            if isinstance(last_seen, dict) and "time" in last_seen:
                last_seen_time = datetime.fromtimestamp(last_seen["time"]).isoformat()
            
            result.append({
                "id": user.get("id"),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "photo_url": user.get("photo_100", ""),
                "last_seen": last_seen_time,
            })
        
        return result

    async def get_unique_commentators(
        self, post_id: int, on_progress: ProgressHandler | None = None
    ) -> List[Tuple[int, int]]:
        offset = 0
        count = 100
        user_to_comment: Dict[int, int] = {}

        while True:
            try:
                resp = await self.user_api.request(
                    "wall.getComments",
                    {
                        "owner_id": self.owner_id,
                        "post_id": post_id,
                        "offset": offset,
                        "count": count,
                        "extended": 0,
                    },
                )
            except VKAPIError as exc:
                if on_progress:
                    on_progress(
                        {
                            "stage": "error",
                            "log": f"VK API error while reading comments on post {post_id}: {exc}",
                        }
                    )
                break

            payload = resp.get("response", resp) if isinstance(resp, dict) else {}
            items = payload.get("items") if isinstance(payload, dict) else []
            if not items:
                break

            for comment in items:
                user_id = comment.get("from_id")
                comment_id = comment.get("id")
                if user_id and user_id > 0 and comment_id is not None:
                    user_to_comment[user_id] = comment_id

            if on_progress:
                on_progress(
                    {
                        "stage": "collect",
                        "post_id": post_id,
                        "loaded": offset + len(items),
                        "unique": len(user_to_comment),
                    }
                )

            if len(items) < count:
                break

            offset += count
            await asyncio.sleep(self.cfg.request_delay)

        return list(user_to_comment.items())

    async def reply_to_comment(self, post_id: int, comment_id: int, message: str) -> bool:
        try:
            await self.group_api.wall.create_comment(
                owner_id=self.owner_id,
                post_id=post_id,
                reply_to_comment=comment_id,
                message=message,
            )
            return True
        except VKAPIError:
            return False
        except Exception:
            return False

    async def send_campaign(
        self,
        post_ids: Iterable[int],
        message: str,
        on_progress: ProgressHandler | None = None,
    ) -> Dict[str, int]:
        all_commentators: Dict[int, Tuple[int, int]] = {}

        for post_id in post_ids:
            if on_progress:
                on_progress({"stage": "collect", "log": f"Читаю комментарии поста {post_id}..."})

            commentators = await self.get_unique_commentators(post_id, on_progress=on_progress)

            for user_id, comment_id in commentators:
                if user_id not in all_commentators:
                    all_commentators[user_id] = (post_id, comment_id)

            if on_progress:
                on_progress(
                    {
                        "stage": "collect_done",
                        "log": f"Пост {post_id}: найдено участников {len(commentators)}",
                        "unique_total": len(all_commentators),
                    }
                )

        total = len(all_commentators)
        sent = 0
        failed = 0

        if on_progress:
            on_progress({"stage": "sending", "total": total})

        # Получаем информацию о пользователях батчами
        user_ids_list = list(all_commentators.keys())
        for i in range(0, len(user_ids_list), 100):
            batch = user_ids_list[i:i+100]
            try:
                users_info = await self.get_users_info(batch)
                # Сохраняем информацию о пользователях
                for user_info in users_info:
                    save_user_info(user_info["id"], user_info)
            except Exception:
                pass  # Игнорируем ошибки при получении информации о пользователях
        
        for idx, (user_id, (post_id, comment_id)) in enumerate(all_commentators.items(), start=1):
            ok = await self.reply_to_comment(post_id, comment_id, message)
            if ok:
                sent += 1
            else:
                failed += 1

            if on_progress:
                on_progress(
                    {
                        "stage": "progress",
                        "current": idx,
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "user_id": user_id,
                        "post_id": post_id,
                        "comment_id": comment_id,
                    }
                )

            await asyncio.sleep(self.cfg.request_delay)

        if on_progress:
            on_progress({"stage": "completed", "sent": sent, "failed": failed, "total": total})

        return {"sent": sent, "failed": failed, "total": total}
