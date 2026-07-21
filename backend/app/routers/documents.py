from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.routers.auth import get_current_active_user
from app.models.document import WorkerDocument
from app.models.user import User

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("/worker/{worker_id}")
def get_worker_documents(worker_id: int, db: Session = Depends(get_db)):
    docs = db.query(WorkerDocument).filter(WorkerDocument.worker_id == worker_id, WorkerDocument.status == "Active").all()
    # Mock some default documents if none exist for demonstration
    if not docs:
        docs = [
            WorkerDocument(id=1, worker_id=worker_id, document_type="Offer Letter", file_name="Offer_Letter.pdf", file_url=""),
            WorkerDocument(id=2, worker_id=worker_id, document_type="Company Policies", file_name="Policies_2026.pdf", file_url=""),
        ]
    return docs

@router.get("/{doc_id}/download")
async def download_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(WorkerDocument).filter(WorkerDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # In a real scenario, this would serve a file or signed URL
    return {"message": "Download link generated", "url": doc.file_url, "file_name": doc.file_name}
