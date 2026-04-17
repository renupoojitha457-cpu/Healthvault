from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas, auth_utils

router = APIRouter()


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=auth_utils.hash_password(payload.password),
        phone=payload.phone,
        dob=payload.dob,
        blood_group=payload.blood_group,
        gender=payload.gender,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = auth_utils.create_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not auth_utils.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = auth_utils.create_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
    }


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth_utils.get_current_user)):
    return current_user


@router.put("/me", response_model=schemas.UserOut)
def update_profile(
    payload: schemas.RegisterRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db)
):
    current_user.name = payload.name
    current_user.phone = payload.phone
    current_user.dob = payload.dob
    current_user.blood_group = payload.blood_group
    current_user.gender = payload.gender
    db.commit()
    db.refresh(current_user)
    return current_user