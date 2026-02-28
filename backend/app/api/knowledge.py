import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.engine import get_session
from app.schemas.document import DocumentOut
from app.services.document_service import DocumentService

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")

def get_doc_service(session: AsyncSession = Depends(get_session)) -> DocumentService:
    return DocumentService(session)

@router.get("", response_model=List[DocumentOut])
async def list_documents(service: DocumentService = Depends(get_doc_service)):
    return await service.list_documents()

@router.post("", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_doc_service)
):
    try:
        doc = await service.upload_document(file, UPLOAD_DIR)
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{doc_id}")
async def delete_document(doc_id: str, service: DocumentService = Depends(get_doc_service)):
    success = await service.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted"}
