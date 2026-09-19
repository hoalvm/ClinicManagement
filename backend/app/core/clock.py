"""Clinic-local clock helpers shared by validation, queries, and seed data."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from backend.app.core.config import get_settings


def clinic_now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().clinic_timezone))


def clinic_today() -> date:
    return clinic_now().date()
