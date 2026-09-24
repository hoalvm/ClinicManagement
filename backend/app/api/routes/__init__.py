"""Versioned API router composition."""

from fastapi import APIRouter

from backend.app.api.routes import (
    appointments,
    auth,
    catalog,
    dashboard,
    invoices,
    medical_records,
    patients,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(appointments.router)
api_router.include_router(catalog.router)
api_router.include_router(medical_records.router)
api_router.include_router(invoices.router)
api_router.include_router(dashboard.router)

__all__ = ["api_router"]
