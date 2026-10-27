from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.dp import get_db
from app.deps import require_roles
from app.models import Employee, Role, User
from app.schemas import RoleUpdate, UserCreate

router = APIRouter(prefix="/api/admin", tags=["admin"])
admin = Depends(require_roles(Role.ADMIN))

@router.post("/users", status_code=201)
def create_user(data: UserCreate, _actor: User = admin, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already exists")
    user = User(email=email, password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.flush()
    employee = Employee(user_id=user.id, full_name=data.employee_name, department="Unassigned")
    db.add(employee)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role, "is_active": user.is_active}

@router.patch("/users/{user_id}/role")
def set_role(user_id: int, data: RoleUpdate, actor: User = admin,
             db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == actor.id and data.role != Role.ADMIN:
        raise HTTPException(400, "You cannot remove your own admin role")
    target.role = data.role
    db.commit()
    return {"id": target.id, "role": target.role}

@router.patch("/users/{user_id}/active")
def set_active(user_id: int, active: bool, actor: User = admin,
               db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == actor.id and not active:
        raise HTTPException(400, "You cannot deactivate your own account")
    if target.role == Role.ADMIN and target.is_active and not active:
        count = db.scalar(select(func.count()).select_from(User).where(
            User.role == Role.ADMIN, User.is_active.is_(True)))
        if count <= 1:
            raise HTTPException(400, "At least one active admin is required")
    target.is_active = active
    db.commit()
    return {"id": target.id, "is_active": target.is_active}
