"""Environment-backed settings for the desktop client."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    """Runtime settings shared by the frontend HTTP client."""

    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_scheme: str = Field(default="http", pattern=r"^https?$")
    api_timeout_seconds: float = Field(default=15.0, gt=0, le=120)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def api_base_url(self) -> str:
        return f"{self.api_scheme}://{self.api_host}:{self.api_port}"


@lru_cache
def get_frontend_settings() -> FrontendSettings:
    return FrontendSettings()
