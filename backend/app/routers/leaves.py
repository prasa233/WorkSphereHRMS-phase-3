from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .schemas.leave import LeaveCreate
from app.database import get_db
from app.models import (
    Employee, Leave, LeaveStatus, Notification, User, UserRole
)
from app.schemas import LeaveCreate, LeaveReview, LeaveOut
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/api/leaves", tags=["Leaves"])


@router.post("", response_model=LeaveOut, status_code=201)
def apply_leave(
    data: LeaveCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    employee = db.scalar(
        select(Employee).where(Employee.user_id == user.id)
    )
    if not employee:
        raise HTTPException(404, "Employee profile not found")

    if employee.status.value != "ACTIVE":
        raise HTTPException(403, "Inactive employees cannot apply for leave")

    if data.start_date < datetime.now(timezone.utc).date():
        raise HTTPException(422, "Leave start date cannot be in the past")

    overlapping = db.scalar(
        select(Leave).where(
            Leave.employee_id == employee.id,
            Leave.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
            Leave.start_date <= data.end_date,
            Leave.end_date >= data.start_date,
        )
    )
    if overlapping:
        raise HTTPException(409, "Leave overlaps an existing pending or approved request")

    leave = Leave(
        employee_id=employee.id,
        leave_type=data.leave_type,
        start_date=data.start_date,
        end_date=data.end_date,
        reason=data.reason,
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


@router.get("/my-history", response_model=list[LeaveOut])
def my_leave_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    employee = db.scalar(
        select(Employee).where(Employee.user_id == user.id)
    )
    if not employee:
        raise HTTPException(404, "Employee profile not found")

    return list(db.scalars(
        select(Leave)
        .where(Leave.employee_id == employee.id)
        .order_by(Leave.created_at.desc())
    ).all())


@router.get("", response_model=list[LeaveOut])
def list_all_leaves(
    status_filter: LeaveStatus | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
):
    stmt = select(Leave)
    if status_filter:
        stmt = stmt.where(Leave.status == status_filter)
    return list(db.scalars(stmt.order_by(Leave.created_at.desc())).all())


@router.patch("/{leave_id}/review", response_model=LeaveOut)
def review_leave(
    leave_id: int,
    data: LeaveReview,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
):
    leave = db.get(Leave, leave_id)
    if not leave:
        raise HTTPException(404, "Leave request not found")
    if leave.status != LeaveStatus.PENDING:
        raise HTTPException(409, "Leave request has already been reviewed")

    if data.status == LeaveStatus.APPROVED:
        conflict = db.scalar(
            select(Leave).where(
                Leave.employee_id == leave.employee_id,
                Leave.id != leave.id,
                Leave.status == LeaveStatus.APPROVED,
                Leave.start_date <= leave.end_date,
                Leave.end_date >= leave.start_date,
            )
        )
        if conflict:
            raise HTTPException(409, "Leave conflicts with another approved request")

    leave.status = data.status
    leave.reviewed_by = actor.id
    leave.reviewed_at = datetime.now(timezone.utc)

    notification = Notification(
        user_id=leave.employee.user_id,
        title=f"Leave {data.status.value.lower()}",
        message=(
            f"Your leave request from {leave.start_date} "
            f"to {leave.end_date} was {data.status.value.lower()}."
        ),
    )
    db.add(notification)
    db.commit()
    db.refresh(leave)
    return leave