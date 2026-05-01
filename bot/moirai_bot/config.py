"""Конфигурация бота: загружается из переменных окружения."""

from __future__ import annotations

from typing import Annotated

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки рантайма.

    Переменные окружения подаются через `docker compose env_file`,
    поэтому собственный `env_file` здесь не указываем.
    """

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    telegram_bot_token: str
    # NoDecode отключает JSON-парсинг complex-типа на уровне источника env,
    # чтобы строку "123,456" обработал валидатор ниже.
    telegram_allowed_user_ids: Annotated[list[int], NoDecode]
    telegram_proxy_url: str | None = None
    gdrive_folder_id: str
    gdrive_service_account_file: str
    state_dir: str = "/state"
    outputs_poll_interval_sec: int = 60

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chat_id(self) -> int:
        """Telegram chat для пересылки артефактов: первый из whitelist'а."""
        return self.telegram_allowed_user_ids[0]

    @field_validator("telegram_allowed_user_ids", mode="before")
    @classmethod
    def _split_user_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        return value

    @field_validator("telegram_allowed_user_ids", mode="after")
    @classmethod
    def _require_non_empty_user_ids(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError(
                "TELEGRAM_ALLOWED_USER_IDS must contain at least one numeric user id, "
                "e.g. TELEGRAM_ALLOWED_USER_IDS=123456789"
            )
        return value

    @field_validator("telegram_bot_token", mode="after")
    @classmethod
    def _require_non_empty_token(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("TELEGRAM_BOT_TOKEN must be set to a non-empty value")
        return value

    @field_validator("gdrive_folder_id", mode="after")
    @classmethod
    def _require_non_empty_folder_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("GDRIVE_FOLDER_ID must be set to a non-empty value")
        return value

    @field_validator("gdrive_service_account_file", mode="after")
    @classmethod
    def _require_non_empty_sa_file(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("GDRIVE_SERVICE_ACCOUNT_FILE must be set to a non-empty path")
        return value

    @field_validator("telegram_proxy_url", mode="before")
    @classmethod
    def _empty_proxy_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value
