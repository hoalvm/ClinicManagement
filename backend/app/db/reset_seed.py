"""Explicitly rebuild the synthetic project database from schema and seed."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from contextlib import closing

import pyodbc

from backend.app.core.config import get_settings
from backend.app.db.init_db import _build_connection_string, init_database
from backend.app.db.seed import PROJECT_DB_NAME, SEED_VERSION, seed_database
from backend.app.db.session import SessionLocal, engine


def validate_reset_settings() -> None:
    settings = get_settings()
    if settings.app_mode != "demo" or settings.db_name != PROJECT_DB_NAME:
        raise RuntimeError(
            f"Reset requires APP_MODE=demo and DB_NAME={PROJECT_DB_NAME}. No database was changed."
        )


def _validate_existing_database() -> None:
    """Refuse unexpected provenance or unrelated populated schemas."""
    with closing(pyodbc.connect(_build_connection_string(PROJECT_DB_NAME))) as connection:
        cursor = connection.cursor()
        if cursor.execute("SELECT DB_NAME()").fetchval() != PROJECT_DB_NAME:
            raise RuntimeError("Connected to an unexpected database. No database was changed.")
        if cursor.execute("SELECT OBJECT_ID(N'dbo.ProductionProvenance', N'U')").fetchval():
            origin = cursor.execute(
                "SELECT Origin FROM dbo.ProductionProvenance WHERE ProvenanceID = 1"
            ).fetchval()
            if origin not in (None, "EMPTY_DATABASE"):
                raise RuntimeError("Unexpected database provenance. Reset refused.")
        marker = None
        if cursor.execute("SELECT OBJECT_ID(N'dbo.SchemaMigrations', N'U')").fetchval():
            marker = cursor.execute(
                "SELECT COUNT(*) FROM dbo.SchemaMigrations WHERE MigrationID = ?",
                SEED_VERSION,
            ).fetchval()
        if marker == 1:
            return
        if cursor.execute("SELECT OBJECT_ID(N'dbo.Users', N'U')").fetchval():
            if cursor.execute("SELECT COUNT(*) FROM dbo.Users").fetchval():
                raise RuntimeError("Database has users without the project seed marker. Reset refused.")


def reset_project_seed() -> None:
    """Drop only the designated project DB, then run the same path as init_db."""
    # ODBC's process-wide pool otherwise keeps the validation connection alive
    # after close(), and SQL Server refuses DROP DATABASE as still in use.
    pyodbc.pooling = False
    validate_reset_settings()
    with closing(pyodbc.connect(_build_connection_string("master"), autocommit=True)) as master:
        cursor = master.cursor()
        exists = cursor.execute("SELECT DB_ID(?)", PROJECT_DB_NAME).fetchval() is not None
        if exists:
            _validate_existing_database()
            # Do not disconnect a running backend. SQL Server refuses DROP while
            # another session is using the database, leaving its data intact.
            engine.dispose()
            cursor.execute(f"DROP DATABASE [{PROJECT_DB_NAME}]")

    init_database(reset=False, verbose=True)
    with SessionLocal() as session:
        if not seed_database(session):
            raise RuntimeError("The new database was not empty; project seed was not applied.")
    print("Project database reset to the initial synthetic seed.")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Reset the synthetic ClinicManagementDB.")
    parser.add_argument("--reset", action="store_true", help="Delete all current project records.")
    args = parser.parse_args(argv)
    if not args.reset:
        parser.error("pass --reset to explicitly replace the project database")
    try:
        reset_project_seed()
    except RuntimeError as exc:
        raise SystemExit(f"Project reset failed: {exc}") from None
    except pyodbc.Error:
        raise SystemExit(
            "Project reset failed while accessing SQL Server. "
            "Stop backend/frontend and retry; if schema creation was interrupted, rerun this command."
        ) from None
    except Exception as exc:
        raise SystemExit(
            f"Project reset failed ({type(exc).__name__}). "
            "If database creation was interrupted, rerun this command or init_db.ps1."
        ) from None


if __name__ == "__main__":
    main()
