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


class BotConfig(BaseModel):
    user_token: str = Field("", description="User token used to read comments")
    group_token: str = Field("", description="Group token used to reply")
    group_id: int = Field(GROUP_ID, description="VK group id without minus")
    request_delay: float = Field(REQUEST_DELAY, ge=0.05, le=30.0)
    promo_message: str = Field(PROMO_MESSAGE, description="Reply text")
    post_ids: list[int] = Field(default_factory=list, description="Selected post ids")


DEFAULT_CONFIG = {
    "user_token": USER_TOKEN,
    "group_token": GROUP_TOKEN,
    "group_id": GROUP_ID,
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

    try:
        return BotConfig(**data)
    except ValidationError as exc:
        raise RuntimeError(f"Config invalid: {exc}") from exc


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
