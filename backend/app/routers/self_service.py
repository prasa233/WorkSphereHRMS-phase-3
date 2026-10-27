from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.permissions import CurrentUser
from app.models.employee import Employee

router = APIRouter(prefix="/self-service", tags=["Self Service"])


@router.get("/profile")
def get_my_profile(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    employee = (
        db.query(Employee)
        .filter(Employee.user_id == current_user.id)
        .first()
    )

    if employee is None:
        raise HTTPException(404, "Employee profile not found")

    return {
        "id": employee.id,
        "name": employee.name,
    }
from sqlalchemy import UniqueConstraint

__table_args__ = (
    UniqueConstraint(
        "employee_id",
        "attendance_date",
        name="uq_attendance_employee_date",
    ),
)