import enum
import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.membership import RoleEnum

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization


class InvitationStatusEnum(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def default_expiration() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


class Invitation(Base, TimestampMixin):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[RoleEnum] = mapped_column(SQLEnum(RoleEnum, native_enum=False), default=RoleEnum.MEMBER, nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False, default=generate_invite_token)
    status: Mapped[InvitationStatusEnum] = mapped_column(SQLEnum(InvitationStatusEnum, native_enum=False), default=InvitationStatusEnum.PENDING, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=default_expiration, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="invitations")
    invited_by: Mapped["User"] = relationship("User")
