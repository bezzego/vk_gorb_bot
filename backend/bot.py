# bot.py
import asyncio
from typing import Dict

from storage import load_config
from vk_service import VKService


def console_progress(event: Dict[str, object]) -> None:
    stage = event.get("stage")
    if event.get("log"):
        print(event["log"])

    if stage == "collect":
        loaded = event.get("loaded", 0)
        unique = event.get("unique", 0)
        post_id = event.get("post_id")
        print(f"[*] Пост {post_id}: загружено {loaded}, уникальных {unique}")
    if stage == "progress":
        current = event.get("current", 0)
        total = event.get("total", 0)
        sent = event.get("sent", 0)
        failed = event.get("failed", 0)
        post_id = event.get("post_id")
        user_id = event.get("user_id")
        print(
            f"[*] {current}/{total} — post={post_id}, user={user_id} (sent={sent}, failed={failed})"
        )
    if stage == "completed":
        print(
            f"[+] Завершено. Отправлено: {event.get('sent', 0)}, ошибок: {event.get('failed', 0)}"
        )


async def send_promos_to_all():
    cfg = load_config()
    post_ids = cfg.post_ids or []
    if not post_ids:
        raise RuntimeError("Не заданы посты для рассылки. Укажите post_ids в config.json или config.py")

    client = VKService(cfg)
    print("[*] Старт рассылки...")
    await client.send_campaign(post_ids=post_ids, message=cfg.promo_message, on_progress=console_progress)


if __name__ == "__main__":
    asyncio.run(send_promos_to_all())
