from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.dp import get_db
from app.deps import require_roles
from app.models import (Attendance, Employee, LeaveBalance, LeavePolicy,
                        LeaveRequest, LeaveStatus, Role, User)

router = APIRouter(prefix="/api/hr", tags=["hr"])
hr_user = Depends(require_roles(Role.HR, Role.ADMIN))

@router.get("/attendance")
def all_attendance(_user: User = hr_user, db: Session = Depends(get_db)):
    return db.scalars(select(Attendance).order_by(Attendance.work_date.desc())).all()

@router.get("/leaves")
def pending_leaves(_user: User = hr_user, db: Session = Depends(get_db)):
    return db.scalars(select(LeaveRequest).where(LeaveRequest.status == LeaveStatus.PENDING)
                      .order_by(LeaveRequest.start_date)).all()

@router.post("/leaves/{leave_id}/decision")
def decide_leave(leave_id: int, approved: bool,
                 reviewer: User = hr_user, db: Session = Depends(get_db)):
    request = db.scalar(select(LeaveRequest).where(LeaveRequest.id == leave_id).with_for_update())
    if not request:
        raise HTTPException(404, "Leave request not found")
    if request.status != LeaveStatus.PENDING:
        raise HTTPException(409, "Leave request has already been reviewed")
    balance = db.scalar(select(LeaveBalance).where(
        LeaveBalance.employee_id == request.employee_id,
        LeaveBalance.leave_type == request.leave_type).with_for_update())
    if approved and (not balance or balance.remaining_days < request.days):
        raise HTTPException(409, "Insufficient leave balance")
    if approved:
        balance.remaining_days -= request.days
        request.status = LeaveStatus.APPROVED
    else:
        request.status = LeaveStatus.REJECTED
    request.reviewed_by = reviewer.id
    request.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": request.id, "status": request.status}


