

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LeavePolicy(Base):
    __tablename__ = "leave_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    leave_type: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    total_days_allowed: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "total_days_allowed >= 0",
            name="ck_leave_policy_days_nonnegative",
        ),
    )


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id"), nullable=False
    )
    leave_type: Mapped[str] = mapped_column(
        ForeignKey("leave_policies.leave_type"), nullable=False
    )
    remaining_days: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "leave_type",
            name="uq_leave_balance_employee_type",
        ),
        CheckConstraint(
            "remaining_days >= 0",
            name="ck_leave_balance_nonnegative",
        ),
    )