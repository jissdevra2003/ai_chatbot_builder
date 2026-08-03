from typing import List, Tuple
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import RoleEnum
from app.schemas.chatbot import ChatbotCreate, ChatbotUpdate, ChatbotResponse
from app.services.chatbot_service import ChatbotService

router = APIRouter(prefix="/chatbots", tags=["Chatbots"])


@router.post("/", response_model=ChatbotResponse, status_code=201)
def create_chatbot(
    chatbot_in: ChatbotCreate,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Creates a new chatbot for the active organization. Requires OWNER or ADMIN role."""
    _, active_org, _ = auth_data
    return ChatbotService.create_chatbot(db, org_id=active_org.id, chatbot_in=chatbot_in)


@router.get("/", response_model=List[ChatbotResponse])
def list_chatbots(
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER)),
    db: Session = Depends(get_db)
):
    """Lists all chatbots in the active organization."""
    _, active_org, _ = auth_data
    return ChatbotService.list_chatbots(db, org_id=active_org.id)


@router.get("/{chatbot_id}", response_model=ChatbotResponse)
def get_chatbot(
    chatbot_id: str,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER)),
    db: Session = Depends(get_db)
):
    """Gets a chatbot by ID within the active organization."""
    _, active_org, _ = auth_data
    return ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id)


@router.patch("/{chatbot_id}", response_model=ChatbotResponse)
def update_chatbot(
    chatbot_id: str,
    update_in: ChatbotUpdate,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Updates chatbot configuration. Requires OWNER or ADMIN role."""
    _, active_org, _ = auth_data
    return ChatbotService.update_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id, update_in=update_in)


@router.delete("/{chatbot_id}", status_code=204)
def delete_chatbot(
    chatbot_id: str,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Deletes a chatbot and all its documents/vectors. Requires OWNER or ADMIN role."""
    _, active_org, _ = auth_data
    ChatbotService.delete_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id)
