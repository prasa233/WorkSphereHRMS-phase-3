from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models import Employee, PerformanceReview
from app.schemas import PerformanceCreate, PerformanceRead


router = APIRouter(prefix="/performance", tags=["performance"])


@router.post("", response_model=PerformanceRead, status_code=201)
def create_review(
    data: PerformanceCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("HR", "ADMIN")),
):
    employee = db.get(Employee, data.employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    review = PerformanceReview(**data.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get(
    "/employee/{employee_id}",
    response_model=list[PerformanceRead],
)
def list_employee_reviews(
    employee_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("HR", "ADMIN")),
):
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    reviews = db.scalars(
        select(PerformanceReview)
        .where(PerformanceReview.employee_id == employee_id)
        .order_by(PerformanceReview.created_at.desc())
    ).all()

    return reviews