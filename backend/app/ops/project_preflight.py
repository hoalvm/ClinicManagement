"""Read-only startup check for the persistent synthetic-data project database."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import get_settings
from backend.app.db.seed import PROJECT_DB_NAME, SEED_VERSION
from backend.app.db.session import engine


def main() -> None:
    settings = get_settings()
    if settings.app_mode != "demo" or settings.db_name != PROJECT_DB_NAME:
        raise SystemExit("Expected the persistent synthetic-data project database.")
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT DB_NAME() ")).scalar_one() != PROJECT_DB_NAME:
                raise SystemExit("Connected to an unexpected database.")
            seeded = connection.execute(
                text("SELECT 1 FROM dbo.SchemaMigrations WHERE MigrationID = :version"),
                {"version": SEED_VERSION},
            ).scalar_one_or_none()
    except SQLAlchemyError:
        raise SystemExit("Project database is unavailable; run script/init_db.ps1 first.") from None
    if seeded != 1:
        raise SystemExit("Project seed is missing; run script/init_db.ps1 first.")


if __name__ == "__main__":
    main()
