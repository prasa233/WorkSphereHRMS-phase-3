from datetime import datetime, date, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Attendance, AttendanceStatus, Employee, User, UserRole
)
from app.schemas import AttendanceOut
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


def get_employee_for_user(db: Session, user: User) -> Employee:
    employee = db.scalar(
        select(Employee).where(Employee.user_id == user.id)
    )
    if not employee:
        raise HTTPException(404, "Employee profile not found")
    return employee


def working_hours(record: Attendance) -> float | None:
    if not record.check_in or not record.check_out:
        return None
    start = record.check_in
    end = record.check_out

    # SQLite may return naive datetimes; interpret them as UTC.
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    return round((end - start).total_seconds() / 3600, 2)


@router.post("/check-in", response_model=AttendanceOut)
def check_in(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    employee = get_employee_for_user(db, user)
    if employee.status.value != "ACTIVE":
        raise HTTPException(403, "Inactive employees cannot check in")

    now = datetime.now(timezone.utc)
    today = now.date()

    record = db.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee.id,
            Attendance.date == today,
        )
    )

    if record and record.check_in:
        raise HTTPException(409, "Already checked in today")

    if record:
        record.check_in = now
        record.status = AttendanceStatus.PRESENT
    else:
        record = Attendance(
            employee_id=employee.id,
            date=today,
            check_in=now,
            status=AttendanceStatus.PRESENT,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


@router.post("/check-out", response_model=AttendanceOut)
def check_out(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    employee = get_employee_for_user(db, user)
    today = datetime.now(timezone.utc).date()

    record = db.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee.id,
            Attendance.date == today,
        )
    )

    if not record or not record.check_in:
        raise HTTPException(400, "You must check in before checking out")
    if record.check_out:
        raise HTTPException(409, "Already checked out")

    now = datetime.now(timezone.utc)
    record.check_out = now

    duration = (now - record.check_in.replace(
        tzinfo=timezone.utc
    ) if record.check_in.tzinfo is None else now - record.check_in).total_seconds() / 3600

    record.status = (
        AttendanceStatus.HALF_DAY if duration < 4
        else AttendanceStatus.PRESENT
    )

    db.commit()
    db.refresh(record)
    return record


@router.get("/my-history", response_model=list[AttendanceOut])
def my_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    employee = get_employee_for_user(db, user)
    stmt = select(Attendance).where(
        Attendance.employee_id == employee.id
    ).order_by(Attendance.date.desc())
    return list(db.scalars(stmt).all())


@router.get("/hours/{attendance_id}")
def attendance_hours(
    attendance_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = db.get(Attendance, attendance_id)
    if not record:
        raise HTTPException(404, "Attendance record not found")

    employee = db.get(Employee, record.employee_id)
    if user.role == UserRole.EMPLOYEE and employee.user_id != user.id:
        raise HTTPException(403, "Access denied")

    return {
        "attendance_id": record.id,
        "working_hours": working_hours(record),
    }


@router.get("", response_model=list[AttendanceOut])
def all_attendance(
    employee_id: int | None = None,
    attendance_date: date | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
):
    stmt = select(Attendance)

    if employee_id is not None:
        stmt = stmt.where(Attendance.employee_id == employee_id)
    if attendance_date is not None:
        stmt = stmt.where(Attendance.date == attendance_date)

    return list(db.scalars(stmt.order_by(Attendance.date.desc())).all())


@router.post("/mark-absence", response_model=AttendanceOut)
def mark_absence(
    employee_id: int,
    attendance_date: date,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
):
    if attendance_date > datetime.now(timezone.utc).date():
        raise HTTPException(422, "Cannot mark a future date as absent")

    if not db.get(Employee, employee_id):
        raise HTTPException(404, "Employee not found")

    record = db.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.date == attendance_date,
        )
    )
    if record:
        raise HTTPException(409, "Attendance already exists for this date")

    record = Attendance(
        employee_id=employee_id,
        date=attendance_date,
        status=AttendanceStatus.ABSENT,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record