"""Registration, login, and current-user endpoints."""

from fastapi import APIRouter, status

from backend.app.api.deps import CurrentUser, DatabaseSession
from backend.app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from backend.app.services import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, session: DatabaseSession) -> RegisterResponse:
    return AuthService(session).register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: DatabaseSession) -> TokenResponse:
    return AuthService(session).login(payload)


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: CurrentUser) -> CurrentUserResponse:
    return AuthService.current_user_response(current_user)
