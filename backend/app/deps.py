from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.models import User

from .auth import decode_access_token
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Không xác thực được"
    )
    try:
        payload = decode_access_token(token)
        sub_val = payload.get("sub")
        username = payload.get("username")
        if not sub_val and not username:
            raise credentials_exception
    except Exception:
        # Do not expose token parsing details through the authentication error.
        raise credentials_exception from None

    if username:
        user = db.query(User).filter(User.username == username).first()
    elif sub_val and str(sub_val).isdigit():
        user = db.query(User).filter(User.user_id == int(sub_val)).first()
    else:
        user = db.query(User).filter(User.username == str(sub_val)).first()

    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ ADMIN mới có quyền truy cập")
    return current_user
