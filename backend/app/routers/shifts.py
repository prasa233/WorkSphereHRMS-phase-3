

from fastapi import HTTPException
from ..models import Shift
from ..schemas import ShiftCreate, ShiftRead
from ..dependencies import require_roles
from ..schemas import AssignShift, ShiftCreate, ShiftRead
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import require_roles
from ..models import Employee, EmployeeShift, Shift
from ..schemas import AssignShift

router = APIRouter(prefix="/shifts", tags=["shifts"])


# Create a shift

@router.post("", response_model=ShiftRead)
def create_shift(
    data: ShiftCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("HR", "Admin")),
):
    # Check whether the shift name already exists
    existing_shift = db.query(Shift).filter(
        Shift.name == data.name
    ).first()

    if existing_shift:
        raise HTTPException(
            status_code=409,
            detail=f"A shift named '{data.name}' already exists. Please use a different name."
        )

    # Create the shift
    shift = Shift(**data.model_dump())

    try:
        db.add(shift)
        db.commit()
        db.refresh(shift)
        return shift

    except Exception:
        db.rollback()
        raise


# List all shifts
@router.get("", response_model=list[ShiftRead])
def list_shifts(
    db: Session = Depends(get_db),
    _user=Depends(require_roles("HR", "Admin")),
):
    return db.query(Shift).order_by(Shift.name).all()


# Assign an existing shift to an employee

@router.put("/assign")
def assign_shift(
    data: AssignShift,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("HR", "Admin")),
):
    # Check that the employee exists
    employee = (
        db.query(Employee)
        .filter(Employee.id == data.employee_id)
        .first()
    )

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail=f"Employee ID {data.employee_id} does not exist."
        )

    # Check that the shift exists
    shift = (
        db.query(Shift)
        .filter(Shift.id == data.shift_id)
        .first()
    )

    if shift is None:
        raise HTTPException(
            status_code=404,
            detail=f"Shift ID {data.shift_id} does not exist."
        )

    # Find the employee's current shift assignment
    assignment = (
        db.query(EmployeeShift)
        .filter(EmployeeShift.employee_id == data.employee_id)
        .first()
    )

    try:
        if assignment:
            # Employee already has a shift: update it
            assignment.shift_id = data.shift_id
            message = "Employee shift updated successfully"
        else:
            # No existing assignment: create one
            assignment = EmployeeShift(
                employee_id=data.employee_id,
                shift_id=data.shift_id
            )
            db.add(assignment)
            message = "Shift assigned successfully"

        db.commit()
        db.refresh(assignment)

        return {
            "message": message,
            "id": assignment.id,
            "employee_id": assignment.employee_id,
            "shift_id": assignment.shift_id
        }

    except Exception:
        db.rollback()
        raise
