from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from .database import get_db
from . import models, auth, schemas
from .routers import users, doctors, specialties, clinics, schedules, statistics

app = FastAPI(title="Clinic Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.Username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.PasswordHash):
        raise HTTPException(401, "Sai tài khoản hoặc mật khẩu")
    if not user.IsActive:
        raise HTTPException(403, "Tài khoản đã bị khóa")
    token = auth.create_access_token({"sub": user.Username, "role": user.Role})
    return {"access_token": token, "token_type": "bearer"}

app.include_router(users.router)
app.include_router(doctors.router)
app.include_router(specialties.router)
app.include_router(clinics.router)
app.include_router(schedules.router)
app.include_router(statistics.router)