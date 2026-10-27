
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Employee, User
from app.schemas import EmployeeCreate, EmployeeRead
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..auth import require_roles
from ..database import get_db
from ..models import Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/employees", tags=["employees"])



@router.post(
    "/",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = getattr(current_user.role, "value", current_user.role)

    if role not in ("ADMIN", "HR", "EMPLOYEE"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    employee_fields = employee_data.model_dump()

    if role == "EMPLOYEE":
        existing_employee = (
            db.query(Employee)
            .filter(Employee.user_id == current_user.id)
            .first()
        )

        if existing_employee:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Your employee profile already exists",
            )

        employee_fields["user_id"] = current_user.id

    employee = Employee(**employee_fields)
    db.add(employee)

    try:
        db.commit()
        db.refresh(employee)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create employee record")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create employee record",
        ) from exc
    return employee



router = APIRouter(prefix="/documents", tags=["documents"])
STORAGE = Path("private_uploads")
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_BYTES = 10 * 1024 * 1024


@router.post("/{employee_id}")
async def upload_document(
    employee_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user=Depends(require_roles("HR", "Admin")),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Unsupported file type")

    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "File too large")

    STORAGE.mkdir(parents=True, exist_ok=True)
    key = f"{uuid4().hex}"
    (STORAGE / key).write_bytes(content)

    document = Document(
        employee_id=employee_id,
        file_name=Path(file.filename or "document").name,
        storage_key=key,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return {"id": document.id, "file_name": document.file_name}