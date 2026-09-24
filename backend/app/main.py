from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from .database import get_db
from .auth import verify_password, create_access_token
from . import schemas
from .routers import users, doctors, specialties, clinics, schedules, statistics
from backend.app.api.routes import api_router

# Import models so SQLAlchemy can resolve all table mappings
import backend.app.models  # noqa: F401 – side-effect import

app = FastAPI(title="Clinic Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Use the new models package (snake_case attrs)
    from backend.app.models import User
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(401, "Sai tài khoản hoặc mật khẩu")
    if not user.is_active:
        raise HTTPException(403, "Tài khoản đã bị khóa")
    token = create_access_token({"sub": str(user.user_id), "username": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


app.include_router(users.router)
app.include_router(doctors.router)
app.include_router(specialties.router)
app.include_router(clinics.router)
app.include_router(schedules.router)
app.include_router(statistics.router)
app.include_router(api_router)