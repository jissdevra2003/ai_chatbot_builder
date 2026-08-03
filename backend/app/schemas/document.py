from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentStatusEnum


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chatbot_id: str
    org_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatusEnum
    chunk_count: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    chunk_index: int
    content: str
    char_count: int
