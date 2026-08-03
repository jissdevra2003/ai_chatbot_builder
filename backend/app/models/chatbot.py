import secrets
from typing import TYPE_CHECKING, List
from sqlalchemy import String, Text, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.document import Document


def generate_api_key() -> str:
    """Generates a unique public API key for chatbot widget embedding."""
    return f"cb_{secrets.token_urlsafe(32)}"


class Chatbot(Base, TimestampMixin):
    __tablename__ = "chatbots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="You are a helpful AI assistant.")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="gemini-2.0-flash")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    chunk_overlap: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, default=generate_api_key)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="chatbots")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="chatbot", cascade="all, delete-orphan")
