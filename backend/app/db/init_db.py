"""Database schema initialization for Microsoft SQL Server.

Can be run directly via:
    python -m backend.app.db.init_db [--reset]

Or imported to ensure the database and tables exist before seeding or running the API.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path

import pyodbc

from backend.app.core.config import get_settings


def _build_connection_string(database: str = "master") -> str:
    """Build a pyodbc connection string matching backend configuration."""
    settings = get_settings()
    server = settings.db_host
    if settings.db_port:
        server = f"{server},{settings.db_port}"

    parts = [
        f"Driver={{{settings.db_driver}}}",
        f"Server={server}",
        f"Database={database}",
        f"Encrypt={settings.db_encrypt}",
        f"TrustServerCertificate={settings.db_trust_server_certificate}",
    ]
    if str(settings.db_trusted_connection).strip().lower() in {"yes", "true", "1"}:
        parts.append("Trusted_Connection=yes")
    else:
        parts.append(f"UID={settings.db_user}")
        parts.append(f"PWD={settings.db_password.get_secret_value()}")

    return ";".join(parts) + ";"


def _find_sql_script() -> Path:
    """Locate the database/ClinicManagementDB.sql script."""
    # Try relative to repo root
    current = Path(__file__).resolve()
    for parent in [current.parent, current.parents[1], current.parents[2], current.parents[3]]:
        candidate = parent / "database" / "ClinicManagementDB.sql"
        if candidate.is_file():
            return candidate
    # Fallback to current working directory
    candidate = Path.cwd() / "database" / "ClinicManagementDB.sql"
    if candidate.is_file():
        return candidate
    raise FileNotFoundError("Could not find 'database/ClinicManagementDB.sql'.")


def _sql_batches(content: str) -> list[str]:
    return [batch.strip() for batch in re.split(r"(?mi)^\s*GO\s*$", content) if batch.strip()]


def _apply_migrations(db_name: str, verbose: bool) -> None:
    """Apply each numbered migration once, committing its DDL and marker together."""
    migration_dir = _find_sql_script().parent / "migrations"
    migration_files = sorted(migration_dir.glob("[0-9][0-9][0-9]_*.sql"))
    with closing(pyodbc.connect(_build_connection_string(database=db_name), autocommit=False)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "IF OBJECT_ID(N'dbo.SchemaMigrations', N'U') IS NULL "
            "CREATE TABLE dbo.SchemaMigrations ("
            "MigrationID NVARCHAR(100) NOT NULL PRIMARY KEY, "
            "AppliedAt DATETIME2 NOT NULL DEFAULT GETDATE())"
        )
        conn.commit()
        for migration_file in migration_files:
            cursor.execute(
                "SELECT 1 FROM dbo.SchemaMigrations WHERE MigrationID = ?",
                migration_file.stem,
            )
            if cursor.fetchone() is not None:
                continue
            try:
                for batch in _sql_batches(migration_file.read_text(encoding="utf-8")):
                    cursor.execute(batch)
                cursor.execute(
                    "INSERT INTO dbo.SchemaMigrations (MigrationID) VALUES (?)",
                    migration_file.stem,
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            if verbose:
                print(f"[OK] Applied migration {migration_file.stem} to '{db_name}'.")


def init_database(reset: bool = False, verbose: bool = True) -> bool:
    """Create the target SQL Server database and tables if they do not exist.

    Args:
        reset: If True, drop the database first if it already exists.
        verbose: If True, print progress messages.

    Returns:
        True if the database is initialized and ready.
    """
    settings = get_settings()
    if settings.app_mode == "production":
        raise RuntimeError(
            "Production schema changes require the explicit --provision-existing command "
            "with a DBA identity and an already created database."
        )
    db_name = settings.db_name
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", db_name):
        raise ValueError("DB_NAME must contain only letters, digits, and underscores")
    if reset and db_name != "ClinicManagementDemoDB":
        raise ValueError("--reset is allowed only for ClinicManagementDemoDB")
    master_conn_str = _build_connection_string(database="master")

    if verbose:
        print(f"Connecting to SQL Server ({settings.db_host})...")

    try:
        with closing(pyodbc.connect(master_conn_str, autocommit=True)) as master_conn:
            with master_conn.cursor() as cur:
                cur.execute("SELECT database_id FROM sys.databases WHERE name = ?", db_name)
                db_exists = cur.fetchone() is not None

                if db_exists and reset:
                    if verbose:
                        print(f"Resetting existing database '{db_name}'...")
                    cur.execute(
                        f"ALTER DATABASE [{db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
                        f"DROP DATABASE [{db_name}];"
                    )
                    db_exists = False

                if not db_exists:
                    if verbose:
                        print(f"Creating database '{db_name}'...")
                    cur.execute(f"CREATE DATABASE [{db_name}];")
                    if verbose:
                        print(f"[OK] Database '{db_name}' created.")
                else:
                    if verbose:
                        print(f"[OK] Database '{db_name}' already exists.")
    except pyodbc.Error as exc:
        if verbose:
            print(f"[ERROR] Failed to connect to SQL Server or manage database '{db_name}': {exc}", file=sys.stderr)
        raise

    # Connect to the target database and inspect/create tables
    target_conn_str = _build_connection_string(database=db_name)
    with closing(pyodbc.connect(target_conn_str, autocommit=True)) as target_conn:
        with target_conn.cursor() as cur:
            cur.execute(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
            )
            existing_tables = {row[0] for row in cur.fetchall()}

            # Key tables expected
            expected_tables = {
                "Users", "Patients", "Specialties", "Clinics", "Doctors",
                "DoctorSchedules", "Appointments", "MedicalRecords",
                "Prescriptions", "PrescriptionItems", "Invoices",
                "InvoiceItems", "Payments"
            }

            if expected_tables.issubset(existing_tables):
                if verbose:
                    print(f"[OK] All {len(expected_tables)} required tables are already present in '{db_name}'.")
            else:
                if existing_tables.intersection(expected_tables):
                    raise RuntimeError(
                        f"'{db_name}' contains an incomplete clinic schema; "
                        "refusing to run the full create script over existing tables"
                    )
                if verbose:
                    print(f"Applying schema from ClinicManagementDB.sql to '{db_name}'...")
                for batch in _sql_batches(_find_sql_script().read_text(encoding="utf-8")):
                    cleaned = re.sub(r"--.*$", "", batch, flags=re.MULTILINE).strip()
                    if not cleaned or re.match(
                        r"^(CREATE\s+DATABASE|USE)\s+", cleaned, re.IGNORECASE
                    ):
                        continue
                    cur.execute(batch)
                if verbose:
                    print(f"[OK] Schema applied successfully to '{db_name}'.")

    _apply_migrations(db_name, verbose)

    return True


def provision_existing_production_database(verbose: bool = True) -> bool:
    """Provision or migrate an existing production DB; never create or reset a DB.

    Run this maintenance command using a separate DBA identity during a service
    outage. The application SQL identity should have no DDL privilege.
    """

    settings = get_settings()
    if settings.app_mode != "production":
        raise ValueError("--provision-existing requires APP_MODE=production")
    db_name = settings.db_name
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", db_name):
        raise ValueError("DB_NAME must contain only letters, digits, and underscores")

    # A direct target connection proves the DBA created the intended database.
    # No connection to master and no CREATE/DROP DATABASE statement is issued.
    with closing(pyodbc.connect(_build_connection_string(database=db_name), autocommit=False)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE'"
        )
        existing = {row[0] for row in cursor.fetchall()}
        expected = {
            "Users", "Patients", "Specialties", "Clinics", "Doctors",
            "DoctorSchedules", "Appointments", "MedicalRecords",
            "Prescriptions", "PrescriptionItems", "Invoices",
            "InvoiceItems", "Payments",
        }
        if not expected.issubset(existing):
            if existing:
                raise RuntimeError(
                    "Production database is not empty and lacks the complete clinic schema; "
                    "restore or repair it under DBA review before migration."
                )
            for batch in _sql_batches(_find_sql_script().read_text(encoding="utf-8")):
                cleaned = re.sub(r"--.*$", "", batch, flags=re.MULTILINE).strip()
                if not cleaned or re.match(
                    r"^(CREATE\s+DATABASE|USE)\s+", cleaned, re.IGNORECASE
                ):
                    continue
                cursor.execute(batch)
            conn.commit()
            if verbose:
                print(f"[OK] Created schema in existing production database '{db_name}'.")
    _apply_migrations(db_name, verbose)
    return True


def ensure_database_initialized() -> bool:
    """Quietly ensure the database and required tables exist; initialize if missing."""
    if get_settings().app_mode == "production":
        raise RuntimeError("Production schema is managed by the explicit DBA migration command")
    try:
        return init_database(reset=False, verbose=False)
    except Exception:
        # Re-run with verbose output to provide actionable diagnostics
        return init_database(reset=False, verbose=True)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Initialize the ClinicManagement database schema in Microsoft SQL Server."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate ClinicManagementDemoDB only.",
    )
    parser.add_argument(
        "--provision-existing",
        action="store_true",
        help="Provision or migrate an already created production DB using a DBA identity.",
    )
    args = parser.parse_args(argv)

    try:
        if args.provision_existing and args.reset:
            parser.error("--provision-existing cannot be combined with --reset")
        if args.provision_existing:
            provision_existing_production_database(verbose=True)
        else:
            init_database(reset=args.reset, verbose=True)
        print("\nDatabase initialization completed successfully.")
    except Exception as exc:
        sys.exit(f"\n[FATAL] Database initialization failed: {exc}")


if __name__ == "__main__":
    main()
