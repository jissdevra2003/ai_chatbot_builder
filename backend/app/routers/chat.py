from typing import List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import RoleEnum
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
)
from app.services.chatbot_service import ChatbotService
from app.services.chat_service import ChatService

router = APIRouter(tags=["Chat"])


@router.post("/chatbots/{chatbot_id}/chat", response_model=ChatResponse)
def send_chat_message(
    chatbot_id: str,
    chat_request: ChatRequest,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(
        require_roles(RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER)
    ),
    db: Session = Depends(get_db),
):
    """
    Send a message to a chatbot and get an AI-generated reply.

    The chatbot uses RAG (Retrieval-Augmented Generation):
    1. Searches uploaded documents for relevant information
    2. Builds context from matching document chunks
    3. Sends context + conversation history to Gemini AI
    4. Returns the AI response with source citations

    Pass a `session_id` to continue an existing conversation.
    Omit it to start a new conversation.
    """
    _, active_org, _ = auth_data
    chatbot = ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id)

    return ChatService.send_message(
        db=db,
        chatbot=chatbot,
        message=chat_request.message,
        session_id=chat_request.session_id,
    )


@router.get("/chatbots/{chatbot_id}/conversations", response_model=List[ConversationResponse])
def list_conversations(
    chatbot_id: str,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(
        require_roles(RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER)
    ),
    db: Session = Depends(get_db),
):
    """Lists all conversations for a chatbot, newest first."""
    _, active_org, _ = auth_data
    # Verify chatbot belongs to this org
    ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=chatbot_id)
    return ChatService.list_conversations(db, chatbot_id=chatbot_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: str,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(
        require_roles(RoleEnum.OWNER, RoleEnum.ADMIN, RoleEnum.MEMBER)
    ),
    db: Session = Depends(get_db),
):
    """Gets a conversation with all its messages."""
    conversation = ChatService.get_conversation(db, conversation_id=conversation_id)

    # Verify the conversation's chatbot belongs to the user's org
    _, active_org, _ = auth_data
    ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=conversation.chatbot_id)

    messages = ChatService.get_conversation_messages(db, conversation_id=conversation_id)

    return ConversationDetailResponse(
        id=conversation.id,
        chatbot_id=conversation.chatbot_id,
        session_id=conversation.session_id,
        title=conversation.title,
        is_active=conversation.is_active,
        message_count=conversation.message_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(msg) for msg in messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(
        require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """Deletes a conversation and all its messages. Requires OWNER or ADMIN role."""
    conversation = ChatService.get_conversation(db, conversation_id=conversation_id)

    # Verify the conversation's chatbot belongs to the user's org
    _, active_org, _ = auth_data
    ChatbotService.get_chatbot(db, org_id=active_org.id, chatbot_id=conversation.chatbot_id)

    ChatService.delete_conversation(db, conversation_id=conversation_id)
