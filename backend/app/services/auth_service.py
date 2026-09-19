"""Authentication and patient registration business logic."""

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.exceptions import (
    AppError,
    AuthenticationError,
    ConflictError,
    InternalServerError,
)
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.models import Patient, User
from backend.app.repositories import PatientRepository, UserRepository
from backend.app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

DUMMY_PASSWORD_HASH = hash_password("clinic-login-dummy-password")


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.patients = PatientRepository(session)

    def register(self, payload: RegisterRequest) -> RegisterResponse:
        if self.users.get_by_username(payload.username) is not None:
            raise ConflictError("Username is already registered.")

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            phone=payload.phone,
            email=str(payload.email) if payload.email is not None else None,
            role="PATIENT",
            is_active=True,
        )
        try:
            self.users.add(user)
            patient = Patient(
                user_id=user.user_id,
                date_of_birth=payload.date_of_birth,
                gender=payload.gender,
                address=payload.address,
            )
            self.patients.add(patient)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            if self.users.get_by_username(payload.username) is not None:
                raise ConflictError("Username is already registered.") from exc
            raise AppError("Unable to register patient.") from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Unable to register patient at this time.") from exc

        return RegisterResponse(
            user_id=user.user_id,
            patient_id=patient.patient_id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
        )

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.users.get_by_username(payload.username)
        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        password_valid = verify_password(payload.password, password_hash)
        if user is None or not user.is_active or user.role != "PATIENT" or not password_valid:
            raise AuthenticationError("Incorrect username or password.")
        return TokenResponse(access_token=create_access_token(user_id=user.user_id, role=user.role))

    @staticmethod
    def current_user_response(user: User) -> CurrentUserResponse:
        return CurrentUserResponse(
            user_id=user.user_id,
            patient_id=user.patient.patient_id if user.patient is not None else None,
            username=user.username,
            full_name=user.full_name,
            phone=user.phone,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        )
