"""Admin dashboard response models."""

from backend.app.schemas.common import APIModel, Money


class AdminStats(APIModel):
    total_appointments: int
    completed_appointments: int
    paid_revenue: Money
    today_appointments: int
    today_completed: int
    today_collected: Money
    unpaid_total: Money
