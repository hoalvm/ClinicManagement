"""Environment-backed application settings."""

from functools import lru_cache

from pydantic import Field
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
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")

    db_host: str = "localhost"
    db_port: int = Field(default=1433, ge=1, le=65535)
    db_name: str = "ClinicManagementDB"
    db_user: str = "clinic_app"
    db_password: str = "change_me"
    db_driver: str = "ODBC Driver 18 for SQL Server"
    db_encrypt: str = "yes"
    db_trust_server_certificate: str = "yes"

    jwt_secret: str = "replace_with_long_random_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1)

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)

    @property
    def database_url(self) -> URL:
        """Build a safely escaped SQLAlchemy URL for SQL Server/pyodbc."""

        return URL.create(
            drivername="mssql+pyodbc",
            username=self.db_user,
            password=self.db_password,
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

    return Settings()
