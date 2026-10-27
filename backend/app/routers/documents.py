from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import Document, Employee, User


router = APIRouter(prefix="/documents", tags=["documents"])

STORAGE = Path("private_uploads")
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_BYTES = 10 * 1024 * 1024


def can_access_employee(user: User, employee_id: int, db: Session) -> bool:
    role = getattr(user.role, "value", user.role)
    if role in {"HR", "ADMIN"}:
        return True

    employee = db.scalar(
        select(Employee).where(
            Employee.user_id == user.id,
            Employee.id == employee_id,
        )
    )
    return employee is not None


@router.post("/{employee_id}", status_code=201)
async def upload_document(
    employee_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("HR", "ADMIN")),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    STORAGE.mkdir(parents=True, exist_ok=True)
    storage_key = uuid4().hex
    (STORAGE / storage_key).write_bytes(content)

    document = Document(
        employee_id=employee_id,
        file_name=Path(file.filename or "document").name,
        storage_key=storage_key,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return {"id": document.id, "file_name": document.file_name}


@router.get("/{employee_id}")
def list_documents(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not can_access_employee(user, employee_id, db):
        raise HTTPException(status_code=403, detail="Access denied")

    documents = db.scalars(
        select(Document)
        .where(Document.employee_id == employee_id)
        .order_by(Document.uploaded_at.desc())
    ).all()

    return [
        {
            "id": doc.id,
            "employee_id": doc.employee_id,
            "file_name": doc.file_name,
            "uploaded_at": doc.uploaded_at,
        }
        for doc in documents
    ]


@router.get("/file/{document_id}")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if not can_access_employee(user, document.employee_id, db):
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = STORAGE / document.storage_key
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=document.file_name,
        media_type="application/octet-stream",
    )