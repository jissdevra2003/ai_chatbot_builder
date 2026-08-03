from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.invitation import Invitation, InvitationStatusEnum
from app.models.membership import Membership, RoleEnum
from app.models.user import User
from app.schemas.invitation import InvitationCreate
from app.services.auth_service import AuthService
from app.services.org_service import OrgService
from app.core.security import hash_password


class InvitationService:
    @classmethod
    def create_invitation(
        cls,
        db: Session,
        org_id: str,
        invited_by_user: User,
        invitation_in: InvitationCreate
    ) -> Invitation:
        """Creates an invitation for an email with a role (ADMIN or MEMBER)."""
        # 1. Validation: Cannot invite someone as OWNER
        if invitation_in.role == RoleEnum.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot invite users with the OWNER role. Transfer ownership instead."
            )

        email_clean = invitation_in.email.lower()

        # 2. Check if target user is already a member of this organization
        existing_user = AuthService.get_user_by_email(db, email_clean)
        if existing_user:
            existing_membership = db.execute(
                select(Membership).where(
                    Membership.user_id == existing_user.id,
                    Membership.org_id == org_id
                )
            ).scalars().first()
            if existing_membership:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User '{email_clean}' is already a member of this organization."
                )

        # 3. Revoke any previous PENDING invitations for this email in this org
        pending_invites = db.execute(
            select(Invitation).where(
                Invitation.org_id == org_id,
                Invitation.email == email_clean,
                Invitation.status == InvitationStatusEnum.PENDING
            )
        ).scalars().all()

        for old_invite in pending_invites:
            old_invite.status = InvitationStatusEnum.REVOKED

        # 4. Create new invitation
        invitation = Invitation(
            org_id=org_id,
            invited_by_id=invited_by_user.id,
            email=email_clean,
            role=invitation_in.role,
            status=InvitationStatusEnum.PENDING
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        return invitation

    @classmethod
    def get_invitation_by_token(cls, db: Session, token: str) -> Optional[Invitation]:
        stmt = select(Invitation).where(Invitation.token == token)
        invitation = db.execute(stmt).scalars().first()
        if not invitation:
            return None

        # Check expiration safely handling naive/aware datetimes
        now = datetime.now(timezone.utc)
        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if invitation.status == InvitationStatusEnum.PENDING and expires_at < now:
            invitation.status = InvitationStatusEnum.EXPIRED
            db.commit()
            db.refresh(invitation)

        return invitation


    @classmethod
    def list_org_invitations(cls, db: Session, org_id: str) -> List[Invitation]:
        stmt = select(Invitation).where(Invitation.org_id == org_id).order_by(Invitation.created_at.desc())
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def accept_invitation(
        cls,
        db: Session,
        token: str,
        password: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> Membership:
        """Accepts an invitation. Creates a user if they don't exist, and adds membership."""
        invitation = cls.get_invitation_by_token(db, token)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation token not found."
            )

        if invitation.status != InvitationStatusEnum.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation cannot be accepted. Current status: {invitation.status.value}"
            )

        try:
            # 1. Get or create user
            user = AuthService.get_user_by_email(db, invitation.email)
            if not user:
                if not password or not full_name:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="New users must provide 'password' and 'full_name' to accept an invitation."
                    )
                user = User(
                    email=invitation.email.lower(),
                    hashed_password=hash_password(password),
                    full_name=full_name,
                    is_active=True
                )
                db.add(user)
                db.flush()

            # 2. Check if membership already exists (safety check)
            membership = db.execute(
                select(Membership).where(
                    Membership.user_id == user.id,
                    Membership.org_id == invitation.org_id
                )
            ).scalars().first()

            if not membership:
                membership = OrgService.create_membership(
                    db,
                    user_id=user.id,
                    org_id=invitation.org_id,
                    role=invitation.role
                )

            # 3. Mark invitation as accepted
            invitation.status = InvitationStatusEnum.ACCEPTED
            db.commit()
            db.refresh(membership)
            return membership

        except Exception as e:
            db.rollback()
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to accept invitation: {str(e)}"
            )
