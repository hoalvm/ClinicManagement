"""Current patient's dashboard endpoint."""

from fastapi import APIRouter

from backend.app.api.deps import CurrentPatient, DatabaseSession
from backend.app.schemas.dashboard import DashboardResponse
from backend.app.services import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/me", response_model=DashboardResponse)
def get_dashboard(current_patient: CurrentPatient, session: DatabaseSession) -> DashboardResponse:
    return DashboardService(session).get_dashboard(current_patient)
