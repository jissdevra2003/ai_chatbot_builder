import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, Integer, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, generate_uuid

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class MessageRoleEnum(str, enum.Enum):
    USER = "user"
    BOT = "bot"
    SYSTEM = "system"


class Message(Base):
    """Represents a single message in a conversation (sent by user or bot)."""
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRoleEnum] = mapped_column(
        SQLEnum(MessageRoleEnum, native_enum=False), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
