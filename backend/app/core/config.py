"""Environment-backed application settings."""

from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Runtime settings loaded from ``.env`` and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Clinic Management API"
    app_version: str = "1.0.0"

    db_host: str = "localhost"
    db_port: int | None = Field(default=1433, ge=1, le=65535)
    db_name: str = "ClinicManagementDB"
    db_user: str = "clinic_app"
    db_password: SecretStr = SecretStr("change_me")
    db_driver: str = "ODBC Driver 18 for SQL Server"
    db_encrypt: str = "yes"
    db_trust_server_certificate: str = "yes"

    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1)

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    clinic_timezone: str = "Asia/Bangkok"

    @field_validator("db_port", mode="before")
    @classmethod
    def allow_local_default_instance(cls, value: object) -> object:
        """Allow ``DB_PORT=none`` for local Shared Memory/named-instance access."""

        if isinstance(value, str) and value.strip().lower() in {"", "none", "null"}:
            return None
        return value

    @property
    def jwt_secret_value(self) -> str:
        """Return a usable key or fail without echoing the configured secret."""

        normalized = self.jwt_secret.get_secret_value().strip()
        if len(normalized) < 32 or normalized.lower().startswith(("replace_with", "change_me")):
            raise RuntimeError(
                "JWT_SECRET must be a private random value of at least 32 characters"
            )
        return normalized

    @field_validator("clinic_timezone")
    @classmethod
    def validate_clinic_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("CLINIC_TIMEZONE must be a valid IANA timezone") from exc
        return value

    @property
    def database_url(self) -> URL:
        """Build a safely escaped SQLAlchemy URL for SQL Server/pyodbc."""

        return URL.create(
            drivername="mssql+pyodbc",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={
                "driver": self.db_driver,
                "Encrypt": self.db_encrypt,
                "TrustServerCertificate": self.db_trust_server_certificate,
            },
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings object."""

    settings = Settings()
    # Validate at startup, outside Pydantic's error formatting, so an invalid
    # secret can never be echoed in a ValidationError.
    _ = settings.jwt_secret_value
    return settings
