from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Employee, EmployeeStatus, Attendance, AttendanceStatus,
    Leave, LeaveStatus, Payroll, User, UserRole
)
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
):
    today = datetime.now(timezone.utc).date()
    month = today.strftime("%Y-%m")

    total_employees = db.scalar(
        select(func.count(Employee.id)).where(
            Employee.status == EmployeeStatus.ACTIVE
        )
    ) or 0

    present_today = db.scalar(
        select(func.count(Attendance.id)).where(
            Attendance.date == today,
            Attendance.status == AttendanceStatus.PRESENT,
        )
    ) or 0

    absent_today = db.scalar(
        select(func.count(Attendance.id)).where(
            Attendance.date == today,
            Attendance.status == AttendanceStatus.ABSENT,
        )
    ) or 0

    half_day_today = db.scalar(
        select(func.count(Attendance.id)).where(
            Attendance.date == today,
            Attendance.status == AttendanceStatus.HALF_DAY,
        )
    ) or 0

    pending_leaves = db.scalar(
        select(func.count(Leave.id)).where(
            Leave.status == LeaveStatus.PENDING
        )
    ) or 0

    payroll_total = db.scalar(
        select(func.coalesce(func.sum(Payroll.net_salary), 0)).where(
            Payroll.month == month
        )
    ) or 0

    return {
        "total_employees": total_employees,
        "attendance": {
            "date": str(today),
            "present": present_today,
            "absent": absent_today,
            "half_day": half_day_today,
        },
        "pending_leaves": pending_leaves,
        "payroll": {
            "month": month,
            "total_net_salary": payroll_total,
        },
    }


@router.get("/employee")
def employee_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    employee = db.scalar(
        select(Employee).where(Employee.user_id == user.id)
    )

    if not employee:
        return {"employee_profile": None}

    pending_leaves = db.scalar(
        select(func.count(Leave.id)).where(
            Leave.employee_id == employee.id,
            Leave.status == LeaveStatus.PENDING,
        )
    ) or 0

    latest_payroll = db.scalar(
        select(Payroll)
        .where(Payroll.employee_id == employee.id)
        .order_by(Payroll.month.desc())
        .limit(1)
    )

    return {
        "employee_id": employee.id,
        "full_name": employee.full_name,
        "department": employee.department,
        "designation": employee.designation,
        "pending_leaves": pending_leaves,
        "latest_payroll": (
            {
                "month": latest_payroll.month,
                "net_salary": latest_payroll.net_salary,
            }
            if latest_payroll else None
        ),
    }