from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, Payroll, User, UserRole, Notification
from app.schemas import PayrollCreate, PayrollOut
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/api/payroll", tags=["Payroll"])


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.post("/generate", response_model=PayrollOut, status_code=201)
def generate_payroll(
    data: PayrollCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
):
    employee = db.get(Employee, data.employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")

    if employee.status.value != "ACTIVE":
        raise HTTPException(400, "Cannot generate payroll for an inactive employee")

    existing = db.scalar(
        select(Payroll).where(
            Payroll.employee_id == data.employee_id,
            Payroll.month == data.month,
        )
    )
    if existing:
        raise HTTPException(409, "Payroll already exists for this employee and month")

    net_salary = money(
        data.basic_salary + data.bonus - data.deductions
    )
    if net_salary < 0:
        raise HTTPException(422, "Deductions cannot exceed salary plus bonus")

    payroll = Payroll(
        employee_id=data.employee_id,
        basic_salary=data.basic_salary,
        deductions=data.deductions,
        bonus=data.bonus,
        net_salary=net_salary,
        month=data.month,
    )
    db.add(payroll)
    db.flush()

    db.add(Notification(
        user_id=employee.user_id,
        title="Payroll generated",
        message=f"Your payslip for {data.month} is available.",
    ))

    db.commit()
    db.refresh(payroll)
    return payroll


@router.get("/my-payslips", response_model=list[PayrollOut])
def my_payslips(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    employee = db.scalar(
        select(Employee).where(Employee.user_id == user.id)
    )
    if not employee:
        raise HTTPException(404, "Employee profile not found")

    return list(db.scalars(
        select(Payroll)
        .where(Payroll.employee_id == employee.id)
        .order_by(Payroll.month.desc())
    ).all())


@router.get("", response_model=list[PayrollOut])
def all_payroll(
    month: str | None = None,
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.HR, UserRole.ADMIN)),
):
    stmt = select(Payroll)

    if month:
        import re
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            raise HTTPException(422, "Month must use YYYY-MM format")
        stmt = stmt.where(Payroll.month == month)

    if employee_id is not None:
        stmt = stmt.where(Payroll.employee_id == employee_id)

    return list(db.scalars(stmt.order_by(Payroll.month.desc())).all())


@router.get("/{payroll_id}", response_model=PayrollOut)
def get_payslip(
    payroll_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payroll = db.get(Payroll, payroll_id)
    if not payroll:
        raise HTTPException(404, "Payslip not found")

    employee = db.get(Employee, payroll.employee_id)

    if user.role == UserRole.EMPLOYEE and employee.user_id != user.id:
        raise HTTPException(403, "Access denied")

    return payroll