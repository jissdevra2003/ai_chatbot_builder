import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Text, Integer, Float, ForeignKey, Enum as SQLEnum, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.chatbot import Chatbot
    from app.models.organization import Organization


class DocumentStatusEnum(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


# Statuses that indicate processing is still in progress
ACTIVE_STATUSES = {
    DocumentStatusEnum.QUEUED,
    DocumentStatusEnum.PROCESSING,
    DocumentStatusEnum.EXTRACTING,
    DocumentStatusEnum.CHUNKING,
    DocumentStatusEnum.EMBEDDING,
    DocumentStatusEnum.INDEXING,
}

TERMINAL_STATUSES = {
    DocumentStatusEnum.COMPLETED,
    DocumentStatusEnum.FAILED,
}


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    chatbot_id: Mapped[str] = mapped_column(String(36), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DocumentStatusEnum] = mapped_column(
        SQLEnum(DocumentStatusEnum, native_enum=False),
        default=DocumentStatusEnum.QUEUED,
        nullable=False
    )
    processing_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)

    # Relationships
    chatbot: Mapped["Chatbot"] = relationship("Chatbot", back_populates="documents")
    organization: Mapped["Organization"] = relationship("Organization")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    chatbot_id: Mapped[str] = mapped_column(String(36), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
    embedding = mapped_column(Vector(768), nullable=True)  # Gemini embedding-001 produces 768-dim vectors
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
        Index("ix_chunk_chatbot_org", "chatbot_id", "org_id"),
    )
