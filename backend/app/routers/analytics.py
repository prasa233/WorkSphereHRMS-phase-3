from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models import Attendance, Employee, PerformanceReview
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query




router = APIRouter(prefix="/analytics", tags=["analytics"])


def validate_date_range(start_date: date, end_date: date):
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date",
        )


router.get("/attendance")
def attendance_analytics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    department: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date"
        )

    # Keep your existing attendance analytics database query here.
    # Use start_date, end_date, and department in that query.

    # Replace this temporary response with your actual query result.
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "department": department,
        "message": "Date parameters validated successfully"
    }


@router.get("/performance")
def performance_summary(
    review_period: str | None = None,
    department: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("HR", "ADMIN")),
):
    query = (
        select(
            Employee.department,
            func.count(PerformanceReview.id),
            func.avg(PerformanceReview.rating),
        )
        .join(Employee, Employee.id == PerformanceReview.employee_id)
        .group_by(Employee.department)
    )

    if review_period:
        query = query.where(
            PerformanceReview.review_period == review_period
        )

    if department:
        query = query.where(Employee.department == department)

    rows = db.execute(query).all()

    return {
        "review_period": review_period,
        "results": [
            {
                "department": row[0],
                "review_count": row[1],
                "average_rating": (
                    round(float(row[2]), 2) if row[2] is not None else None
                ),
            }
            for row in rows
        ],
    }