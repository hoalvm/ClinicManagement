"""Tests for environment-backed backend configuration."""

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_database_url_preserves_reserved_password_characters() -> None:
    password = "p@ss#word%with:/reserved"

    settings = Settings(
        _env_file=None,
        db_host="sql.example.test",
        db_port=1444,
        db_name="ClinicManagementDB",
        db_user="clinic_app",
        db_password=password,
        db_driver="ODBC Driver 18 for SQL Server",
        db_encrypt="yes",
        db_trust_server_certificate="no",
    )

    url = settings.database_url

    assert url.drivername == "mssql+pyodbc"
    assert url.username == "clinic_app"
    assert url.password == password
    assert url.host == "sql.example.test"
    assert url.port == 1444
    assert url.database == "ClinicManagementDB"
    assert url.query == {
        "driver": "ODBC Driver 18 for SQL Server",
        "Encrypt": "yes",
        "TrustServerCertificate": "no",
    }


def test_settings_validate_network_ports() -> None:
    settings = Settings(_env_file=None, db_port=1433, api_port=8000)

    assert settings.db_port == 1433
    assert settings.api_port == 8000


def test_database_port_can_be_omitted_for_local_default_instance() -> None:
    settings = Settings(_env_file=None, db_port="none")

    assert settings.db_port is None
    assert settings.database_url.port is None


def test_settings_require_private_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "placeholder",
    [
        "replace_with_a_long_random_secret_before_running_the_application",
        "change_me_to_a_long_random_secret_value",
    ],
)
def test_settings_reject_documented_jwt_placeholders(placeholder: str) -> None:
    settings = Settings(_env_file=None, jwt_secret=placeholder)

    with pytest.raises(RuntimeError, match="JWT_SECRET must be a private random value"):
        _ = settings.jwt_secret_value
