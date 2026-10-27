from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.dp import get_db
from app.deps import current_user, require_roles
from app.models import LeaveRequest, LeaveStatus
from app.models import (Attendance, Employee, LeaveBalance, LeavePolicy,
                        LeaveRequest, LeaveStatus, Payroll, Role, User)
from app.schemas import LeaveCreate, PayrollOut
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from app.core.config import settings


router = APIRouter(prefix="/api/me", tags=["employee portal"])

def my_employee(user: User, db: Session) -> Employee:
    employee = db.scalar(select(Employee).where(Employee.user_id == user.id))
    if not employee:
        raise HTTPException(404, "Employee profile not found")
    return employee

@router.get("/profile")
def profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    emp = my_employee(user, db)
    return {"id": emp.id, "full_name": emp.full_name,
            "department": emp.department, "email": user.email}

@router.get("/attendance")
def attendance(user: User = Depends(current_user), db: Session = Depends(get_db)):
    emp = my_employee(user, db)
    return db.scalars(select(Attendance).where(Attendance.employee_id == emp.id)
                      .order_by(Attendance.work_date.desc())).all()

@router.get("/leave-balances")
def balances(user: User = Depends(current_user), db: Session = Depends(get_db)):
    emp = my_employee(user, db)
    return db.scalars(select(LeaveBalance).where(LeaveBalance.employee_id == emp.id)).all()

@router.get("/leave-policies")
def policies(_user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(LeavePolicy).where(LeavePolicy.active.is_(True))).all()

@router.post("/leaves", status_code=201)
def apply_leave(data: LeaveCreate, user: User = Depends(require_roles(Role.EMPLOYEE)),
                db: Session = Depends(get_db)):
    emp = my_employee(user, db)
    policy = db.scalar(select(LeavePolicy).where(
        LeavePolicy.leave_type == data.leave_type, LeavePolicy.active.is_(True)))
    balance = db.scalar(select(LeaveBalance).where(
        LeaveBalance.employee_id == emp.id, LeaveBalance.leave_type == data.leave_type))
    days = (data.end_date - data.start_date).days + 1 # replace with business-day calendar if required
    if not policy or not balance:
        raise HTTPException(400, "No active policy or balance for this leave type")
    if days > balance.remaining_days:
        raise HTTPException(400, "Requested leave exceeds remaining balance")
    request = LeaveRequest(employee_id=emp.id, leave_type=data.leave_type,
        start_date=data.start_date, end_date=data.end_date, days=days,
        reason=data.reason, status=LeaveStatus.PENDING)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request

@router.get("/leaves")
def my_leaves(user: User = Depends(current_user), db: Session = Depends(get_db)):
    emp = my_employee(user, db)
    return db.scalars(select(LeaveRequest).where(LeaveRequest.employee_id == emp.id)
                      .order_by(LeaveRequest.start_date.desc())).all()

@router.get("/payroll", response_model=list[PayrollOut])
def my_payroll(user: User = Depends(current_user), db: Session = Depends(get_db)):
    emp = my_employee(user, db)
    return db.scalars(select(Payroll).where(Payroll.employee_id == emp.id)
                      .order_by(Payroll.period_year.desc(), Payroll.period_month.desc())).all()
@router.post("/attendance/check-in", status_code=201)
def check_in(user: User = Depends(require_roles(Role.EMPLOYEE)), db: Session = Depends(get_db)):
    emp = my_employee(user, db)
    now_utc = datetime.now(timezone.utc)
    local_now = now_utc.astimezone(ZoneInfo(settings.workplace_timezone))
    cutoff_hour, cutoff_minute = map(int, settings.late_after.split(":"))
    cutoff = time(cutoff_hour, cutoff_minute)
    status = "LATE" if local_now.time() > cutoff else "PRESENT"
    row = Attendance(employee_id=emp.id, work_date=local_now.date(),
                     check_in=now_utc, status=status)
    db.add(row)
    try:
        db.commit()  # unique constraint prevents concurrent duplicate check-ins
    except Exception:
        db.rollback()
        raise HTTPException(409, "You have already checked in today")
    db.refresh(row)
    return row
