from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ChatbotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: str = Field(default="You are a helpful AI assistant.")
    model_name: str = Field(default="gemini-2.0-flash", max_length=100)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class ChatbotUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_name: Optional[str] = Field(default=None, max_length=100)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    chunk_size: Optional[int] = Field(default=None, ge=100, le=5000)
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=1000)


class ChatbotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    name: str
    description: Optional[str]
    system_prompt: str
    model_name: str
    temperature: float
    chunk_size: int
    chunk_overlap: int
    api_key: str
    created_at: datetime
    updated_at: datetime
