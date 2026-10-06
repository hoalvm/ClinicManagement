"""Read-only database checks required before serving real patient data."""

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import get_settings
from backend.app.db.session import engine

REQUIRED_TABLES = {
    "Users",
    "Patients",
    "Doctors",
    "Appointments",
    "MedicalRecords",
    "Prescriptions",
    "Invoices",
    "Payments",
    "AuthSessions",
    "AuditEvents",
    "SchemaMigrations",
    "StaffClinicAssignments",
    "DoctorScheduleExceptions",
    "ChargeCatalog",
    "ProductionProvenance",
}

REQUIRED_MIGRATIONS = {
    "001_demo_workflow",
    "002_walkin_flag",
    "003_production_billing_and_scope",
    "004_append_only_audit",
    "005_clinical_context_gate",
    "006_production_provenance",
    "007_late_clinical_entry",
}

REQUIRED_COLUMNS = {
    ("Appointments", "SpecialtyID"),
    ("Appointments", "NoShowAt"),
    ("Appointments", "NoShowReasonCode"),
    ("Appointments", "ClinicalContextLoadedAt"),
    ("Appointments", "ClinicalContextLoadedByUserID"),
    ("Patients", "IsWalkIn"),
    ("InvoiceItems", "ChargeID"),
    ("Payments", "AmountReceived"),
    ("Payments", "ChangeDue"),
    ("Payments", "RecordedByUserID"),
    ("Payments", "ExternalReference"),
    ("Payments", "VerifiedAt"),
    ("MedicalRecords", "LateEntryReason"),
}


def validate_production_database(connection: Connection, expected_name: str) -> None:
    """Reject missing controls, sample records, or privileged app identities."""

    actual_name = connection.execute(text("SELECT DB_NAME() ")).scalar_one()
    if actual_name != expected_name:
        raise RuntimeError("Production connection is using a different database")

    tables = set(
        connection.execute(
            text(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_SCHEMA = 'dbo' AND TABLE_TYPE = 'BASE TABLE'"
            )
        ).scalars()
    )
    missing = REQUIRED_TABLES - tables
    if missing:
        raise RuntimeError(
            "Production database is missing required schema: " + ", ".join(sorted(missing))
        )

    applied = set(
        connection.execute(text("SELECT MigrationID FROM dbo.SchemaMigrations")).scalars()
    )
    missing_migrations = REQUIRED_MIGRATIONS - applied
    if missing_migrations:
        raise RuntimeError(
            "Production database is missing migrations: "
            + ", ".join(sorted(missing_migrations))
        )

    columns = set(
        connection.execute(
            text(
                "SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = 'dbo'"
            )
        ).all()
    )
    missing_columns = REQUIRED_COLUMNS - columns
    if missing_columns:
        raise RuntimeError(
            "Production database is missing required columns: "
            + ", ".join(f"{table}.{column}" for table, column in sorted(missing_columns))
        )

    append_only_trigger = connection.execute(
        text(
            "SELECT COUNT(*) FROM sys.triggers WHERE parent_id = OBJECT_ID('dbo.AuditEvents') "
            "AND name = 'TR_AuditEvents_AppendOnly' AND is_disabled = 0"
        )
    ).scalar_one()
    if append_only_trigger != 1:
        raise RuntimeError("Production audit append-only trigger is missing or disabled")

    unique_indexes = set(
        connection.execute(
            text(
                "SELECT OBJECT_NAME(object_id), name FROM sys.indexes WHERE is_unique = 1 "
                "AND is_disabled = 0 AND name IN "
                "('UX_ChargeCatalog_ActiveConsultation', 'UX_Payments_TransferReference', "
                "'UX_Appointments_ClinicDateQueue')"
            )
        ).all()
    )
    required_indexes = {
        ("ChargeCatalog", "UX_ChargeCatalog_ActiveConsultation"),
        ("Payments", "UX_Payments_TransferReference"),
        ("Appointments", "UX_Appointments_ClinicDateQueue"),
    }
    if not required_indexes.issubset(unique_indexes):
        raise RuntimeError("Production database is missing unique billing or queue indexes")

    provenance = connection.execute(
        text("SELECT Origin FROM dbo.ProductionProvenance WHERE ProvenanceID = 1")
    ).scalar_one_or_none()
    if provenance != "EMPTY_DATABASE":
        raise RuntimeError(
            "Production database was not provisioned empty; migrate verified data into a clean database"
        )

    demo_marker = connection.execute(
        text(
            "SELECT COUNT(*) FROM dbo.SchemaMigrations "
            "WHERE MigrationID LIKE 'demo-seed-%' "
            "OR MigrationID LIKE 'project-synthetic-seed-%'"
        )
    ).scalar_one()
    if demo_marker:
        raise RuntimeError("Production database contains the demo seed marker; use a clean verified database")

    sample_doctors = connection.execute(
        text(
            "SELECT COUNT(*) FROM dbo.Doctors AS d "
            "JOIN dbo.Users AS u ON u.UserID = d.UserID "
            "WHERE u.Username IN ('doctor01', 'doctor02', 'doctor03', 'doctor04', 'doctor05') "
            "OR UPPER(d.LicenseNumber) LIKE 'DEMO%'"
        )
    ).scalar_one()
    if sample_doctors:
        raise RuntimeError("Production database contains sample doctor identities; use verified staff records")

    unresolved_specialties = connection.execute(
        text("SELECT COUNT(*) FROM dbo.Appointments WHERE SpecialtyID IS NULL")
    ).scalar_one()
    if unresolved_specialties:
        raise RuntimeError(
            "Production appointments have unverified historical specialties; reconcile from source evidence"
        )

    active_admins = connection.execute(
        text("SELECT COUNT(*) FROM dbo.Users WHERE Role = 'ADMIN' AND IsActive = 1")
    ).scalar_one()
    if active_admins < 1:
        raise RuntimeError("Production database has no active administrator; run verified first-admin bootstrap")

    privileges = connection.execute(
        text(
            "SELECT IS_SRVROLEMEMBER('sysadmin'), IS_MEMBER('db_owner'), "
            "HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'ALTER')"
        )
    ).one()
    if any(value == 1 for value in privileges):
        raise RuntimeError("Production application SQL identity has schema or server administrator rights")

    audit_privileges = connection.execute(
        text(
            "SELECT HAS_PERMS_BY_NAME('dbo.AuditEvents', 'OBJECT', 'UPDATE'), "
            "HAS_PERMS_BY_NAME('dbo.AuditEvents', 'OBJECT', 'DELETE'), "
            "HAS_PERMS_BY_NAME('dbo.ProductionProvenance', 'OBJECT', 'INSERT'), "
            "HAS_PERMS_BY_NAME('dbo.ProductionProvenance', 'OBJECT', 'UPDATE'), "
            "HAS_PERMS_BY_NAME('dbo.ProductionProvenance', 'OBJECT', 'DELETE')"
        )
    ).one()
    if any(value == 1 for value in audit_privileges):
        raise RuntimeError("Production application SQL identity can alter audit or provenance controls")

    required_permissions = connection.execute(
        text(
            "SELECT HAS_PERMS_BY_NAME('dbo.AuthSessions', 'OBJECT', 'SELECT'), "
            "HAS_PERMS_BY_NAME('dbo.AuthSessions', 'OBJECT', 'INSERT'), "
            "HAS_PERMS_BY_NAME('dbo.AuthSessions', 'OBJECT', 'UPDATE'), "
            "HAS_PERMS_BY_NAME('dbo.AuditEvents', 'OBJECT', 'INSERT'), "
            "HAS_PERMS_BY_NAME('dbo.SchemaMigrations', 'OBJECT', 'SELECT'), "
            "HAS_PERMS_BY_NAME('dbo.ProductionProvenance', 'OBJECT', 'SELECT')"
        )
    ).one()
    if any(value != 1 for value in required_permissions):
        raise RuntimeError("Production application SQL identity lacks session, audit or schema-read permissions")


def run_production_preflight() -> None:
    settings = get_settings()
    if settings.app_mode != "production":
        raise RuntimeError("Production preflight requires APP_MODE=production")
    try:
        with engine.connect() as connection:
            validate_production_database(connection, settings.db_name)
    except SQLAlchemyError:
        raise RuntimeError("Production SQL Server connection or schema check failed") from None


if __name__ == "__main__":
    run_production_preflight()
    print("Production database preflight: passed")
