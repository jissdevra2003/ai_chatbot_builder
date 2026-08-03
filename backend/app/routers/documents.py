from typing import List, Tuple
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import RoleEnum
from app.schemas.document import DocumentResponse, DocumentChunkResponse
from app.services.chatbot_service import ChatbotService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/chatbots/{chatbot_id}/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=201)
def upload_document(
    chatbot_id: str,
    file: UploadFile = File(...),
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Uploads a document to a chatbot's knowledge base. Triggers parse → chunk → embed pipeline."""
    _, active_org, _ = auth_data
    # Verify chatbot belongs to this org
    ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id)
    return DocumentService.upload_document(db, org_id=active_org.id, chatbot_id=chatbot_id, file=file)


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    chatbot_id: str,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER)),
    db: Session = Depends(get_db)
):
    """Lists all documents in a chatbot's knowledge base with processing status."""
    _, active_org, _ = auth_data
    ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id)
    return DocumentService.list_documents(db, org_id=active_org.id, chatbot_id=chatbot_id)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    chatbot_id: str,
    document_id: str,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER)),
    db: Session = Depends(get_db)
):
    """Gets a single document's details and processing status."""
    _, active_org, _ = auth_data
    ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id)
    return DocumentService.get_document(db, org_id=active_org.id, document_id=document_id)


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkResponse])
def get_document_chunks(
    chatbot_id: str,
    document_id: str,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Gets all text chunks of a processed document."""
    _, active_org, _ = auth_data
    ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id)
    DocumentService.get_document(db, org_id=active_org.id, document_id=document_id)
    return DocumentService.get_document_chunks(db, document_id=document_id)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    chatbot_id: str,
    document_id: str,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Deletes a document and purges its vectors from the store."""
    _, active_org, _ = auth_data
    ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id)
    DocumentService.delete_document(db, org_id=active_org.id, chatbot_id=chatbot_id, document_id=document_id)
