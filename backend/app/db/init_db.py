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


def init_database(reset: bool = False, verbose: bool = True) -> bool:
    """Create the target SQL Server database and tables if they do not exist.

    Args:
        reset: If True, drop the database first if it already exists.
        verbose: If True, print progress messages.

    Returns:
        True if the database is initialized and ready.
    """
    settings = get_settings()
    db_name = settings.db_name
    master_conn_str = _build_connection_string(database="master")

    if verbose:
        print(f"Connecting to SQL Server ({settings.db_host})...")

    try:
        with pyodbc.connect(master_conn_str, autocommit=True) as master_conn:
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
    with pyodbc.connect(target_conn_str, autocommit=True) as target_conn:
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
                return True

            if verbose:
                print(f"Applying schema from ClinicManagementDB.sql to '{db_name}'...")

            sql_file = _find_sql_script()
            content = sql_file.read_text(encoding="utf-8")
            batches = [b.strip() for b in re.split(r"(?mi)^\s*GO\s*$", content) if b.strip()]

            for batch in batches:
                cleaned = re.sub(r"--.*$", "", batch, flags=re.MULTILINE).strip()
                if not cleaned:
                    continue
                # Skip CREATE DATABASE and USE statements because we are already connected to target DB
                if re.match(r"^(CREATE\s+DATABASE|USE)\s+", cleaned, re.IGNORECASE):
                    continue
                cur.execute(batch)

            # Verify tables after execution
            cur.execute(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
            )
            created_tables = [row[0] for row in cur.fetchall()]
            if verbose:
                print(f"[OK] Schema applied successfully ({len(created_tables)} tables created).")

    return True


def ensure_database_initialized() -> bool:
    """Quietly ensure the database and required tables exist; initialize if missing."""
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
        help="Drop and recreate the database if it already exists.",
    )
    args = parser.parse_args(argv)

    try:
        init_database(reset=args.reset, verbose=True)
        print("\nDatabase initialization completed successfully.")
    except Exception as exc:
        sys.exit(f"\n[FATAL] Database initialization failed: {exc}")


if __name__ == "__main__":
    main()
