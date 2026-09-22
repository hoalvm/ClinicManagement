from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, auth
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return db.query(models.User).all()

@router.post("/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if db.query(models.User).filter(models.User.Username == user.Username).first():
        raise HTTPException(400, "Username đã tồn tại")
    new_user = models.User(
        Username=user.Username,
        PasswordHash=auth.hash_password(user.Password),
        FullName=user.FullName,
        Phone=user.Phone,
        Email=user.Email,
        Role=user.Role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, data: schemas.UserUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.query(models.User).filter(models.User.UserID == user_id).first()
    if not user:
        raise HTTPException(404, "Không tìm thấy user")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.query(models.User).filter(models.User.UserID == user_id).first()
    if not user:
        raise HTTPException(404, "Không tìm thấy user")
    user.IsActive = False
    db.commit()
    return {"message": "Đã vô hiệu hóa tài khoản"}