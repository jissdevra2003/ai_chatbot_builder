from typing import TYPE_CHECKING, List
from sqlalchemy import String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.chatbot import Chatbot
    from app.models.message import Message


class Conversation(Base, TimestampMixin):
    """Represents a single chat session/thread between a user and a chatbot."""
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    chatbot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    chatbot: Mapped["Chatbot"] = relationship("Chatbot")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
