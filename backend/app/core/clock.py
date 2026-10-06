"""Clinic-local clock helpers shared by validation, queries, and seed data."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


def clinic_now() -> datetime:
    settings = get_settings()
    clinic_zone = ZoneInfo(settings.clinic_timezone)
    if settings.app_mode == "demo" and settings.clinic_demo_now is not None:
        return settings.clinic_demo_now.astimezone(clinic_zone)
    return datetime.now(clinic_zone)


def clinic_today() -> date:
    return clinic_now().date()


def clinic_naive_now() -> datetime:
    """Return clinic-local wall time for the existing SQL Server DATETIME2 columns."""

    return clinic_now().replace(tzinfo=None)
