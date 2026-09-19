"""Authentication and ownership dependencies shared by API routes."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.exceptions import AuthenticationError, AuthorizationError
from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models import Patient, User
from backend.app.repositories import PatientRepository, UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authentication credentials were not provided.")
    token_payload = decode_access_token(credentials.credentials)
    user = UserRepository(session).get_by_id(token_payload.user_id)
    if user is None or not user.is_active or user.role != token_payload.role:
        raise AuthenticationError()
    return user


def get_current_patient(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> Patient:
    if current_user.role != "PATIENT":
        raise AuthorizationError("A patient account is required.")
    patient = current_user.patient
    if patient is None:
        patient = PatientRepository(session).get_by_user_id(current_user.user_id)
    if patient is None:
        raise AuthorizationError("The patient profile is unavailable.")
    return patient


DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentPatient = Annotated[Patient, Depends(get_current_patient)]
