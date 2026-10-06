from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.models import User

from .core.exceptions import AuthenticationError
from .core.security import decode_access_token, validate_access_session
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Không xác thực được"
    )
    try:
        payload = decode_access_token(token)
    except AuthenticationError:
        raise credentials_exception from None

    user = db.query(User).filter(User.user_id == payload.user_id).first()
    if user is None or not user.is_active or user.role != payload.role:
        raise credentials_exception
    if user.role == "DOCTOR" and (user.doctor is None or not user.doctor.is_active):
        raise credentials_exception
    try:
        validate_access_session(db, payload)
    except AuthenticationError:
        raise credentials_exception from None
    return user

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ ADMIN mới có quyền truy cập")
    return current_user
