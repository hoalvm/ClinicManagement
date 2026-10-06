"""Environment-backed settings for the desktop client."""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    """Runtime settings shared by the frontend HTTP client."""

    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_scheme: str = Field(default="http", pattern=r"^https?$")
    api_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    app_mode: Literal["normal", "demo", "production"] = "normal"
    api_public_base_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_production_https(self) -> "FrontendSettings":
        if self.app_mode == "production":
            parsed = urlsplit(self.api_public_base_url or "")
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                raise ValueError("Production desktop clients require HTTPS API_PUBLIC_BASE_URL")
        return self

    @property
    def api_base_url(self) -> str:
        if self.app_mode == "production":
            return str(self.api_public_base_url).rstrip("/")
        return f"{self.api_scheme}://{self.api_host}:{self.api_port}"


@lru_cache
def get_frontend_settings() -> FrontendSettings:
    return FrontendSettings()
