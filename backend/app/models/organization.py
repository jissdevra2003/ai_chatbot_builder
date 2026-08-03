from typing import TYPE_CHECKING, List
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.invitation import Invitation
    from app.models.chatbot import Chatbot


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Relationships
    memberships: Mapped[List["Membership"]] = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")
    invitations: Mapped[List["Invitation"]] = relationship("Invitation", back_populates="organization", cascade="all, delete-orphan")
    chatbots: Mapped[List["Chatbot"]] = relationship("Chatbot", back_populates="organization", cascade="all, delete-orphan")


