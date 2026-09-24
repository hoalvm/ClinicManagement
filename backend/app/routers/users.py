from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, auth
from ..database import get_db
from ..deps import require_admin
from backend.app.models import User

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    users = db.query(User).all()
    return [
        {
            "UserID": u.user_id, "Username": u.username, "FullName": u.full_name,
            "Phone": u.phone, "Email": u.email, "Role": u.role,
            "IsActive": u.is_active, "CreatedAt": u.created_at,
        }
        for u in users
    ]

@router.post("/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if db.query(User).filter(User.username == user.Username).first():
        raise HTTPException(400, "Username đã tồn tại")

    if user.Role == "DOCTOR":
        raise HTTPException(
            400,
            "Vui lòng tạo tài khoản Bác sĩ tại mục 'Quản lý Bác sĩ' để thiết lập chuyên khoa và phòng khám.",
        )

    new_user = User(
        username=user.Username,
        password_hash=auth.hash_password(user.Password),
        full_name=user.FullName,
        phone=user.Phone,
        email=user.Email,
        role=user.Role,
    )
    db.add(new_user)
    db.flush()

    if user.Role == "PATIENT":
        from backend.app.models import Patient
        patient = Patient(user_id=new_user.user_id)
        db.add(patient)

    db.commit()
    db.refresh(new_user)
    return {
        "UserID": new_user.user_id, "Username": new_user.username, "FullName": new_user.full_name,
        "Phone": new_user.phone, "Email": new_user.email, "Role": new_user.role,
        "IsActive": new_user.is_active, "CreatedAt": new_user.created_at,
    }

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, data: schemas.UserUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(404, "Không tìm thấy user")
    mapping = {
        "Username": "username", "FullName": "full_name", "Phone": "phone",
        "Email": "email", "Role": "role", "IsActive": "is_active",
    }
    for field, value in data.dict(exclude_unset=True).items():
        setattr(user, mapping.get(field, field), value)
    db.commit()
    db.refresh(user)
    return {
        "UserID": user.user_id, "Username": user.username, "FullName": user.full_name,
        "Phone": user.phone, "Email": user.email, "Role": user.role,
        "IsActive": user.is_active, "CreatedAt": user.created_at,
    }

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(404, "Không tìm thấy user")
    user.is_active = False
    db.commit()
    return {"message": "Đã vô hiệu hóa tài khoản"}