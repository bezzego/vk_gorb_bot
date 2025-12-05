import json
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel, Field, ValidationError

from config import (
    GROUP_ID,
    GROUP_TOKEN,
    POST_ID,
    PROMO_MESSAGE,
    REQUEST_DELAY,
    USER_TOKEN,
)

CONFIG_PATH = Path(__file__).parent.parent / "data" / "config.json"


class Community(BaseModel):
    name: str = Field("", description="Friendly community name")
    group_id: int = Field(..., description="VK group id without minus")
    user_token: str = Field("", description="User token used to read comments")
    group_token: str = Field("", description="Group token used to reply")


class BotConfig(BaseModel):
    # Legacy single community fields (kept for backward compatibility)
    user_token: str = Field("", description="User token used to read comments")
    group_token: str = Field("", description="Group token used to reply")
    group_id: int = Field(GROUP_ID, description="VK group id without minus")
    # New multi-community support
    communities: list[Community] = Field(default_factory=list, description="Communities list")
    active_group_id: int | None = Field(None, description="Group id currently selected")
    request_delay: float = Field(REQUEST_DELAY, ge=0.05, le=30.0)
    promo_message: str = Field(PROMO_MESSAGE, description="Reply text")
    post_ids: list[int] = Field(default_factory=list, description="Selected post ids")


DEFAULT_CONFIG = {
    "user_token": USER_TOKEN,
    "group_token": GROUP_TOKEN,
    "group_id": GROUP_ID,
    "communities": [],
    "active_group_id": GROUP_ID if GROUP_ID else None,
    "request_delay": REQUEST_DELAY,
    "promo_message": PROMO_MESSAGE,
    "post_ids": [POST_ID] if POST_ID else [],
}


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    """
    Pydantic v1/v2 compatibility helper.
    """
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _model_dump_json(model: BaseModel) -> str:
    if hasattr(model, "model_dump_json"):
        return model.model_dump_json(indent=2, ensure_ascii=False)
    return model.json(indent=2, ensure_ascii=False)


def _model_copy(model: BaseModel, update: Dict[str, Any]) -> BaseModel:
    if hasattr(model, "model_copy"):
        return model.model_copy(update=update)
    return model.copy(update=update)


def load_config() -> BotConfig:
    data: Dict[str, Any] = DEFAULT_CONFIG.copy()

    if CONFIG_PATH.exists():
        try:
            data.update(json.loads(CONFIG_PATH.read_text()))
        except json.JSONDecodeError:
            # Keep defaults if file is broken
            pass

    # migrate legacy single community into list
    if not data.get("communities"):
        if data.get("group_id") or data.get("user_token") or data.get("group_token"):
            data["communities"] = [
                {
                    "name": f"Группа {data.get('group_id') or ''}".strip(),
                    "group_id": data.get("group_id") or 0,
                    "user_token": data.get("user_token") or "",
                    "group_token": data.get("group_token") or "",
                }
            ]

    if not data.get("active_group_id") and data.get("communities"):
        first = data["communities"][0]
        data["active_group_id"] = first.get("group_id")

    try:
        cfg = BotConfig(**data)
    except ValidationError as exc:
        raise RuntimeError(f"Config invalid: {exc}") from exc

    # ensure legacy fields reflect active community
    active = get_active_community(cfg)
    if active:
        cfg.user_token = active.user_token
        cfg.group_token = active.group_token
        cfg.group_id = active.group_id

    return cfg


def save_config(cfg: BotConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(_model_dump_json(cfg))


def update_config(partial_data: Dict[str, Any]) -> BotConfig:
    cfg = load_config()
    updated = _model_copy(cfg, partial_data)
    save_config(updated)
    return updated


def config_to_dict(cfg: BotConfig) -> Dict[str, Any]:
    return _model_dump(cfg)


def get_active_community(cfg: BotConfig) -> Community | None:
    if not cfg.communities:
        return None
    active_id = cfg.active_group_id
    if active_id:
        for c in cfg.communities:
            if c.group_id == active_id:
                return c
    return cfg.communities[0]
