from contextlib import asynccontextmanager
from datetime import date, datetime, time
from app.routers.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Literal
from pwdlib import PasswordHash
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import Employee
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from .database import Base, engine, get_db, settings
from app.routers import shifts
from app.models.phase3 import (
    Shift,
    EmployeeShift,
    Document,
    PerformanceReview,
)

from app.database import get_db
from app.models import (
    User,
    Employee,
    Attendance,
    AttendanceStatus,
    LeavePolicy,
    LeaveBalance,
    LeaveRequest,
    Payroll,
)
from app.schemas import LoginIn
from app.schemas import UserCreate
from app.auth import verify_password, create_access_token
from fastapi import FastAPI
from .routers import shifts, documents, performance, analytics, notifications

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware




from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="WorkSphere HRMS", version="3.0.0")

app.include_router(shifts.router, prefix="/api")
# Configure CORS before the application starts serving requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "WorkSphere HRMS API is running",
        "status": "success",
        "phase": 3,
    }

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "WorkSphere HRMS",
    }

from app.routers import (
    auth,
    shifts,
    documents,
    performance,
    analytics,
    notifications,
)

app.include_router(shifts.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(performance.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(auth.router)
router = APIRouter(prefix="/auth", tags=["Authentication"])

from .schemas import (
    RegisterIn,
    LoginIn,
    UserCreate,
    UserOut,
    LeaveCreate,
)
from .database import Base, engine, get_db
from .models import (
    User, Employee, Attendance, LeavePolicy,
    LeaveBalance, LeaveRequest, Payroll
)

from .auth import (
    hash_password,
    verify_password,
    create_access_token,
)
from .dependencies import get_current_user, require_roles


class LeaveDecision(BaseModel):
    status: Literal["APPROVED", "REJECTED"]

def get_employee(db: Session, user_id: int):
    employee = db.query(Employee).filter(
        Employee.user_id == user_id
    ).first()

    if not employee:
        raise HTTPException(404, "Employee profile not found")

    return employee


@app.get("/")
def home():
    return {"message": "WorkSphere HRMS API is running"}

    
# ---------------- AUTHENTICATION ----------------



app.include_router(auth_router)
password_hash = PasswordHash.recommended()
users_db = {}

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr
    password: str = Field(min_length=8)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Register endpoint
@app.post("/auth/register")
def register(user: RegisterRequest):
    email = str(user.email).lower()

    if email in users_db:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    users_db[email] = {
        "username": user.username,
        "email": email,
        "hashed_password": password_hash.hash(user.password)
    }

    return {"message": "Registration successful"}


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    identifier = data.username.strip()

    # Find the registered user by username or email
    user = db.scalar(
        select(User).where(
            or_(
                User.username == identifier,
                User.email == identifier.lower()
            )
        )
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found. Please register first."
        )

    # Verify the password against the saved password hash
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    token = create_access_token({
    "sub": user.username,
    "role": (
        user.role.value
        if hasattr(user.role, "value")
        else str(user.role)
    ),
})
    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "username": user.username
    }



    
# ---------------- ADMIN: USERS ----------------
@app.post("/admin/users", response_model=UserOut)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("ADMIN")),
):
    existing = db.query(User).filter(
        (User.username == data.username)
        | (User.email == data.email)
    ).first()

    if existing:
        raise HTTPException(409, "Username or email already exists")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/admin/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    admin=Depends(require_roles("ADMIN")),
):
    return db.query(User).order_by(User.id).all()


@app.patch("/admin/users/{user_id}/role")
def change_role(
    user_id: int,
    new_role: str,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("ADMIN")),
):
    if new_role not in {"EMPLOYEE", "HR", "ADMIN"}:
        raise HTTPException(422, "Invalid role")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    user.role = new_role
    db.commit()

    return {
        "message": "Role updated; user must log in again",
        "user_id": user.id,
        "role": user.role,
    }


@app.patch("/admin/users/{user_id}/active")
def change_active_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("ADMIN")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = is_active
    db.commit()

    return {"user_id": user.id, "is_active": user.is_active}


@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("ADMIN")),
):
    if user_id == admin.id:
        raise HTTPException(400, "Cannot delete your own account")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Deactivate first; historical HR records must be preserved.
    user.is_active = False
    db.commit()

    return {"message": "User deactivated"}


# ---------------- EMPLOYEE PROFILE ----------------

@app.post("/employees")
def add_employee(
    user_id: int,
    full_name: str,
    department: str,
    designation: str,
    salary: float,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("HR", "ADMIN")),
):
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=404,
            detail="Active user not found",
        )

    existing = (
        db.query(Employee)
        .filter(Employee.user_id == user_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Employee profile already exists",
        )

    if salary <= 0:
        raise HTTPException(
            status_code=422,
            detail="Salary must be greater than zero",
        )

    employee = Employee(
        user_id=user_id,
        full_name=full_name,
        department=department,
        designation=designation,
        joining_date=date.today(),
        salary=salary,
    )

    db.add(employee)
    try:
        db.commit()
        db.refresh(employee)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create employee profile; check that this user does not already have one",
        )

    return employee


def get_employee(db: Session, user_id: int) -> Employee:
    employee = (
        db.query(Employee)
        .filter(Employee.user_id == user_id)
        .first()
    )

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee profile not found for this logged-in user",
        )

    return employee
# ---------------- ATTENDANCE ----------------#

@app.post("/attendance/check-in")
def check_in(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    employee = get_employee(db, user.id)

    # Use a naive local datetime to match SQLAlchemy DateTime columns
    # that do not set timezone=True.
    now = datetime.now()
    today = now.date()

    record = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee.id,
            Attendance.date == today,
        )
        .first()
    )

    if record is not None:
        raise HTTPException(
            status_code=409,
            detail="Attendance already recorded today",
        )

    is_late = now.time() > time(9, 15)

    record = Attendance(
        employee_id=employee.id,
        date=today,
        check_in=now,
        status=AttendanceStatus.PRESENT,
    )

    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Attendance already recorded today",
        )

    return {
        "message": "Check-in successful",
        "check_in": record.check_in.isoformat(),
        "status": getattr(record.status, "value", record.status),
        "late": is_late,
    }


@app.post("/attendance/check-out")
def check_out(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    employee = get_employee(db, user.id)
    today = date.today()

    record = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee.id,
            Attendance.date == today,
        )
        .first()
    )

    if record is None or record.check_in is None:
        raise HTTPException(
            status_code=404,
            detail="No check-in found for today",
        )

    if record.check_out is not None:
        raise HTTPException(
            status_code=409,
            detail="Already checked out today",
        )

    now = datetime.now()
    check_in_time = record.check_in

    # Accommodate existing timezone-aware values if any are stored.
    if check_in_time.tzinfo is not None:
        now = now.astimezone(check_in_time.tzinfo)
    else:
        now = now.replace(tzinfo=None)

    hours_worked = (now - check_in_time).total_seconds() / 3600

    record.check_out = now
    record.status = (
        AttendanceStatus.HALF_DAY
        if hours_worked < 4
        else AttendanceStatus.PRESENT
    )

    db.commit()
    db.refresh(record)

    return {
        "message": "Check-out successful",
        "check_out": record.check_out.isoformat(),
        "hours_worked": round(hours_worked, 2),
        "status": getattr(record.status, "value", record.status),
    }


@app.get("/attendance/me")
def my_attendance(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    employee = get_employee(db, user.id)

    return (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.id)
        .order_by(Attendance.date.desc())
        .all()
    )


@app.get("/attendance")
def attendance_records(
    db: Session = Depends(get_db),
    user=Depends(require_roles("HR", "ADMIN")),
):
    return (
        db.query(Attendance)
        .order_by(Attendance.date.desc())
        .all()
    )
# ---------------- LEAVE POLICIES ----------------

@app.post("/leave-policies")
def create_leave_policy(
    leave_type: str,
    total_days_allowed: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles("HR", "ADMIN")),
):
    if total_days_allowed < 0:
        raise HTTPException(422, "Days cannot be negative")

    policy = LeavePolicy(
        leave_type=leave_type,
        total_days_allowed=total_days_allowed,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@app.get("/leave-policies")
def list_leave_policies(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return db.query(LeavePolicy).order_by(
        LeavePolicy.leave_type
    ).all()


# ---------------- LEAVE APPLICATIONS ----------------

@app.post("/leaves")
def apply_leave(
    data: LeaveCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    employee = get_employee(db, user.id)

    policy = db.query(LeavePolicy).filter_by(
        leave_type=data.leave_type
    ).first()
    if not policy:
        raise HTTPException(422, "Unknown leave type")

    # Simple calendar-day calculation; weekends/holidays excluded
    # only after you implement a working-day calendar.
    days = (data.end_date - data.start_date).days + 1

    if data.start_date < date.today():
        raise HTTPException(422, "Past leave dates are not allowed")

    balance = db.query(LeaveBalance).filter_by(
        employee_id=employee.id,
        leave_type=data.leave_type,
    ).first()

    if not balance:
        balance = LeaveBalance(
            employee_id=employee.id,
            leave_type=data.leave_type,
            remaining_days=policy.total_days_allowed,
        )
        db.add(balance)
        db.flush()

    pending = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.status == "PENDING",
        LeaveRequest.start_date <= data.end_date,
        LeaveRequest.end_date >= data.start_date,
    ).first()

    if pending:
        raise HTTPException(409, "Overlapping pending leave exists")

    approved_days = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.leave_type == data.leave_type,
        LeaveRequest.status == "APPROVED",
    ).all()

    used_days = sum(item.days_requested for item in approved_days)

    pending_same_type = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.leave_type == data.leave_type,
        LeaveRequest.status == "PENDING",
    ).all()

    pending_days = sum(
        item.days_requested for item in pending_same_type
    )

    if days > balance.remaining_days - pending_days:
        raise HTTPException(400, "Insufficient leave balance")

    request = LeaveRequest(
        employee_id=employee.id,
        leave_type=data.leave_type,
        start_date=data.start_date,
        end_date=data.end_date,
        days_requested=days,
        reason=data.reason,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return request


@app.get("/leaves/me")
def my_leaves(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    employee = get_employee(db, user.id)

    return db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id
    ).order_by(LeaveRequest.id.desc()).all()


@app.get("/leave-balances/me")
def my_leave_balances(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    employee = get_employee(db, user.id)

    return db.query(LeaveBalance).filter_by(
        employee_id=employee.id
    ).all()


@app.get("/leaves")
def all_leave_requests(
    db: Session = Depends(get_db),
    user=Depends(require_roles("HR", "ADMIN")),
):
    return db.query(LeaveRequest).order_by(
        LeaveRequest.id.desc()
    ).all()


@app.patch("/leaves/{leave_id}/decision")
def decide_leave(
    leave_id: int,
    data: LeaveDecision,
    db: Session = Depends(get_db),
    user=Depends(require_roles("HR", "ADMIN")),
):
    leave = db.query(LeaveRequest).filter_by(
        id=leave_id
    ).with_for_update().first()

    if not leave:
        raise HTTPException(404, "Leave request not found")

    if leave.status != "PENDING":
        raise HTTPException(409, "Leave has already been reviewed")

    if data.status == "APPROVED":
        balance = db.query(LeaveBalance).filter_by(
            employee_id=leave.employee_id,
            leave_type=leave.leave_type,
        ).with_for_update().first()

        if not balance or balance.remaining_days < leave.days_requested:
            raise HTTPException(400, "Insufficient leave balance")

        balance.remaining_days -= leave.days_requested

    leave.status = data.status
    leave.reviewed_by = user.id
    db.commit()

    return {"message": "Leave decision saved", "status": leave.status}


# ---------------- PAYROLL ----------------

@app.get("/payroll/me")
def my_payroll(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    employee = get_employee(db, user.id)

    return (
        db.query(Payroll)
        .filter(Payroll.employee_id == employee.id)
        .order_by(Payroll.month.desc())
        .all()
    )


@app.get("/payroll")
def all_payroll(
    db: Session = Depends(get_db),
    user=Depends(require_roles("HR", "ADMIN")),
):
    return (
        db.query(Payroll)
        .order_by(Payroll.month.desc())
        .all()
    )


@app.post("/payroll/generate")
def generate_payroll(
    employee_id: int,
    payroll_month: str,
    basic_salary: float,
    allowances: float = 0,
    deductions: float = 0,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("HR", "ADMIN")),
):
    # Expect a month like 2026-09
    try:
        month_date = date.fromisoformat(f"{payroll_month}-01")
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="payroll_month must use YYYY-MM format, for example 2026-09",
        )

    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing = (
        db.query(Payroll)
        .filter(
            Payroll.employee_id == employee_id,
            Payroll.month == payroll_month,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Payroll already exists for this employee and month",
        )

    if basic_salary < 0 or allowances < 0 or deductions < 0:
        raise HTTPException(
            status_code=422,
            detail="Salary, allowances, and deductions cannot be negative",
        )

    net_salary = basic_salary + allowances - deductions
    if net_salary < 0:
        raise HTTPException(
            status_code=422,
            detail="Deductions cannot exceed salary plus allowances",
        )

    payroll = Payroll(
        employee_id=employee_id,
        month=payroll_month,
        basic_salary=basic_salary,
        allowances=allowances,
        deductions=deductions,
        net_salary=net_salary,
    )

    db.add(payroll)
    db.commit()
    db.refresh(payroll)
    return payroll


@app.post("/api/attendance/auto-mark")
def auto_mark(
    db: Session = Depends(get_db),
    _=Depends(require_roles("HR", "ADMIN")),
):
    today = date.today()

    # EmployeeShift represents each employee's current shift.
    assignments = db.execute(
        select(EmployeeShift, Shift)
        .join(Shift, EmployeeShift.shift_id == Shift.id)
    ).all()

    created = 0

    for assignment, _shift in assignments:
        existing = db.scalar(
            select(Attendance).where(
                Attendance.employee_id == assignment.employee_id,
                Attendance.work_date == today,
            )
        )

        if existing is None:
            db.add(
                Attendance(
                    employee_id=assignment.employee_id,
                    work_date=today,
                    status="absent",
                )
            )
            created += 1

    db.commit()
    return {"date": today, "marked_absent": created}



@app.get("/api/analytics")
def get_analytics():
    return {
        "attendance_trends": [],
        "leave_trends": [],
        "performance_insights": [],
        "department_reports": [],
    }


@app.get("/api/documents")
def get_documents():
    return []


@app.get("/api/leaves")
def get_leaves():
    return []


@app.get("/api/employees")
def get_employees():
    return []


@app.get("/api/performance")
def get_performance():
    return []
