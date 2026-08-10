from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str = Field(..., min_length=1, max_length=10000, description="User's message text")
    session_id: Optional[str] = Field(
        None, max_length=64,
        description="Session ID to continue an existing conversation. If not provided, a new conversation is created."
    )


class ChatSourceDocument(BaseModel):
    """A source document chunk that was used to generate the bot's response."""
    filename: str
    chunk_index: int
    relevance_score: float


class ChatResponse(BaseModel):
    """Response from the chat endpoint with bot's reply."""
    message: str
    session_id: str
    conversation_id: str
    sources: List[ChatSourceDocument] = []
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None


class MessageResponse(BaseModel):
    """A single message in a conversation."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    sources: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None
    created_at: datetime


class ConversationResponse(BaseModel):
    """A conversation summary."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    chatbot_id: str
    session_id: str
    title: Optional[str] = None
    is_active: bool
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    """A conversation with all its messages."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    chatbot_id: str
    session_id: str
    title: Optional[str] = None
    is_active: bool
    message_count: int
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
