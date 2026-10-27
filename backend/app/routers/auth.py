from app.schemas import RegisterIn, UserOut, LoginIn
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.schemas import RegisterIn, UserOut, LoginIn
from app.database import get_db
from app.models import User, UserRole
from app.auth import create_access_token
from app.dependencies import get_current_user
from datetime import date
from fastapi import status
from sqlalchemy.exc import IntegrityError
from app.models import Employee, Role
from app.schemas import RegisterIn
from app.auth import create_access_token, hash_password, verify_password
from app.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# REGISTER
@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterIn,
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(User).where(
            or_(
                User.username == data.username,
                User.email == str(data.email).lower(),
            )
        )
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    user = User(
        username=data.username,
        email=str(data.email).lower(),
        hashed_password=hash_password(data.password),
        role=UserRole.EMPLOYEE,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# JSON LOGIN
@router.post("/login")
def login(
    data: LoginIn,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            or_(
                User.username == data.username,
                User.email == data.username.lower(),
            )
        )
    )

    if user is None or not verify_password(
        data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        {
            "sub": user.username,
            "role": user.role.value,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# CURRENT USER
@router.get("/me", response_model=UserOut)
def me(
    user: User = Depends(get_current_user),
):
    return user


# FORM LOGIN FOR OAUTH2 SWAGGER FLOW
@router.post("/token")
def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            or_(
                User.username == username,
                User.email == username.lower(),
            )
        )
    )

    if user is None or not verify_password(
        password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        {
            "sub": user.username,
            "role": user.role.value,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
@router.get("/me", response_model=UserOut)
def me(
    user: User = Depends(get_current_user),
):
    return user
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    user = User(username=data.username, email=str(data.email).lower(),
                password_hash=hash_password(data.password), role=Role.EMPLOYEE,
                is_active=True)
    db.add(user)
    try:
        db.flush()
        db.add(Employee(user_id=user.id, full_name=data.full_name,
                        designation="Employee", department="Unassigned",
                        joining_date=date.today(), salary=0, status="ACTIVE"))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Username or email already exists")
    return {"id": user.id, "username": user.username, "role": user.role.value}
