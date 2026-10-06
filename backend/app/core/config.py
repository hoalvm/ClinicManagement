"""Environment-backed application settings."""

from datetime import datetime
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
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
    db_trusted_connection: str = "no"

    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1)
    appointment_grace_minutes: int = Field(default=15, ge=0, le=120)

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    clinic_timezone: str = "Asia/Ho_Chi_Minh"
    app_mode: Literal["normal", "demo", "production"] = "normal"
    clinic_demo_now: datetime | None = None
    api_public_base_url: str | None = None
    cors_origins: str = ""

    @model_validator(mode="after")
    def validate_demo_clock(self) -> "Settings":
        if self.app_mode == "demo":
            if self.db_name not in {"ClinicManagementDB", "ClinicManagementDemoDB"}:
                raise ValueError("Sample-data mode requires a designated clinic project database")
            if self.api_host not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Demo mode requires a loopback API_HOST")
            if self.clinic_demo_now is not None and self.clinic_demo_now.utcoffset() is None:
                raise ValueError("CLINIC_DEMO_NOW must include a timezone offset")
        elif self.clinic_demo_now is not None:
            raise ValueError("CLINIC_DEMO_NOW is available only in demo mode")
        if self.app_mode == "production":
            if self.jwt_algorithm != "HS256":
                raise ValueError("Production JWT_ALGORITHM must be HS256")
            if self.db_name == "ClinicManagementDemoDB":
                raise ValueError("Production cannot use ClinicManagementDemoDB")
            if self.api_host not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Production API_HOST must be loopback behind an HTTPS reverse proxy")
            if not self.api_public_base_url or urlsplit(self.api_public_base_url).scheme != "https":
                raise ValueError("Production API_PUBLIC_BASE_URL must be an HTTPS URL")
            public_url = urlsplit(self.api_public_base_url)
            if not public_url.hostname or public_url.username or public_url.password or public_url.path not in {"", "/"} or public_url.query or public_url.fragment:
                raise ValueError("Production API_PUBLIC_BASE_URL must be an HTTPS origin")
            if self.db_encrypt.strip().lower() not in {"yes", "mandatory", "strict"}:
                raise ValueError("Production requires encrypted SQL Server connections")
            if self.db_trust_server_certificate.strip().lower() not in {"no", "false", "0"}:
                raise ValueError("Production requires SQL Server certificate validation")
            if self.db_trusted_connection.strip().lower() not in {"yes", "true", "1"}:
                if self.db_user.strip().lower() in {"sa", "admin", "root"}:
                    raise ValueError("Production requires a dedicated least-privilege DB_USER")
                password = self.db_password.get_secret_value()
                if len(password) < 16 or password.lower().startswith(("change_me", "replace_with")):
                    raise ValueError("Production DB_PASSWORD must be a private value of at least 16 characters")
            secret = self.jwt_secret.get_secret_value().strip()
            if len(secret) < 48 or secret.lower().startswith(("replace_with", "change_me")):
                raise ValueError("Production JWT_SECRET must be a private random value of at least 48 characters")
            if any(not origin.startswith("https://") for origin in self.allowed_cors_origins):
                raise ValueError("Production CORS_ORIGINS must contain HTTPS origins only")
        return self

    @property
    def allowed_cors_origins(self) -> list[str]:
        """Browser origins; the desktop client does not need CORS."""

        origins = [item.strip().rstrip("/") for item in self.cors_origins.split(",") if item.strip()]
        for origin in origins:
            parsed = urlsplit(origin)
            if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or parsed.username or parsed.password:
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        return origins

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

        query = {
            "driver": self.db_driver,
            "Encrypt": self.db_encrypt,
            "TrustServerCertificate": self.db_trust_server_certificate,
        }
        if str(self.db_trusted_connection).strip().lower() in {"yes", "true", "1"}:
            query["trusted_connection"] = "yes"
            return URL.create(
                drivername="mssql+pyodbc",
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                query=query,
            )

        return URL.create(
            drivername="mssql+pyodbc",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query=query,
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings object."""

    settings = Settings()
    # Validate at startup, outside Pydantic's error formatting, so an invalid
    # secret can never be echoed in a ValidationError.
    _ = settings.jwt_secret_value
    return settings
