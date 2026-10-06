"""Registration, login, and current-user endpoints."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.app.api.deps import CurrentUser, DatabaseSession
from backend.app.core.config import get_settings
from backend.app.core.exceptions import AuthenticationError
from backend.app.core.login_throttle import login_throttle
from backend.app.core.security import logout_access_token
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
    if get_settings().app_mode == "production":
        raise HTTPException(403, "Patient enrollment requires identity verification at reception.")
    return AuthService(session).register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: DatabaseSession, request: Request) -> TokenResponse:
    login_throttle.check(request, payload.username)
    try:
        token = AuthService(session).login(payload)
    except AuthenticationError:
        login_throttle.failed(request, payload.username)
        raise
    login_throttle.succeeded(request, payload.username)
    return token


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: CurrentUser) -> CurrentUserResponse:
    return AuthService.current_user_response(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, current_user: CurrentUser, session: DatabaseSession) -> Response:
    token = request.headers["authorization"].split(" ", 1)[1]
    logout_access_token(session, token, actor_role=current_user.role)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
