from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from app.models.user import User, UserRole
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import User, UserRole
from app.models.leave import LeaveBalance, LeavePolicy

# Backward-compatible alias used by existing routerss
from app.models.phase3 import (
    Shift,
    EmployeeShift,
    Document,
    PerformanceReview,
)


# ---------------- MODULE 1: USERS ----------------
class UserRole(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    HR = "HR"
    ADMIN = "ADMIN"


# Backward-compatible alias for Phase 2 RBAC
Role = UserRole


# ---------------- MODULE 2: EMPLOYEES ----------------

class EmployeeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(150))
    designation: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100), index=True)
    joining_date: Mapped[date] = mapped_column(Date)
    salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[EmployeeStatus] = mapped_column(
        SAEnum(EmployeeStatus), default=EmployeeStatus.ACTIVE
    )

    user: Mapped["User"] = relationship(back_populates="employee")
    attendance: Mapped[list["Attendance"]] = relationship(
        back_populates="employee"
    )
    leaves: Mapped[list["Leave"]] = relationship(
        back_populates="employee"
    )
    payrolls: Mapped[list["Payroll"]] = relationship(
        back_populates="employee"
    )


# ---------------- MODULE 3: ATTENDANCE ----------------

class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    HALF_DAY = "HALF_DAY"


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "date",
            name="uq_attendance_employee_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), index=True
    )
    check_in: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    check_out: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus),
        default=AttendanceStatus.PRESENT,
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="attendance"
    )


# ---------------- MODULE 4: LEAVES ----------------

class LeaveType(str, Enum):
    SICK = "SICK"
    CASUAL = "CASUAL"
    PAID = "PAID"


class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Leave(Base):
    __tablename__ = "leaves"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), index=True
    )
    leave_type: Mapped[LeaveType] = mapped_column(SAEnum(LeaveType))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[LeaveStatus] = mapped_column(
        SAEnum(LeaveStatus), default=LeaveStatus.PENDING
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="leaves"
    )
LeaveRequest = Leave

# ---------------- MODULE 5: PAYROLL ----------------

class Payroll(Base):
    __tablename__ = "payroll"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "month",
            name="uq_payroll_employee_month",
        ),
    )
    allowances = Column(Float, nullable=False, default=0)
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), index=True
    )
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    bonus: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    month: Mapped[str] = mapped_column(String(7), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="payrolls"
    )


# ---------------- MODULE 7: NOTIFICATIONS ----------------

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(
        back_populates="notifications"
    )
