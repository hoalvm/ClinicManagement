"""Persistence operations for users."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: int) -> User | None:
        statement = select(User).options(joinedload(User.patient)).where(User.user_id == user_id)
        return self.session.execute(statement).unique().scalar_one_or_none()

    def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username)
        return self.session.execute(statement).scalar_one_or_none()

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user
