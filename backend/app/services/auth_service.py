from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, RoleEnum
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password
from app.services.org_service import OrgService


class AuthService:
    @classmethod
    def get_user_by_email(cls, db: Session, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower())
        return db.execute(stmt).scalars().first()

    @classmethod
    def get_user_by_id(cls, db: Session, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return db.execute(stmt).scalars().first()

    @classmethod
    def register_user(cls, db: Session, user_in: UserCreate) -> Tuple[User, Organization, Membership]:
        """Registers a user, auto-creates an Organization, and creates an OWNER membership in ONE atomic transaction."""
        # 1. Check duplicate email
        existing_user = cls.get_user_by_email(db, user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        # 2. Atomic transaction block
        try:
            # Create User
            hashed_pwd = hash_password(user_in.password)
            user = User(
                email=user_in.email.lower(),
                hashed_password=hashed_pwd,
                full_name=user_in.full_name,
                is_active=True
            )
            db.add(user)
            db.flush()  # Populates user.id

            # Create default Organization
            org_name = user_in.org_name if user_in.org_name else f"{user_in.full_name}'s Workspace"
            org = OrgService.create_organization(db, name=org_name)

            # Create OWNER Membership
            membership = OrgService.create_membership(
                db,
                user_id=user.id,
                org_id=org.id,
                role=RoleEnum.OWNER
            )

            # Commit atomic transaction
            db.commit()
            db.refresh(user)
            db.refresh(org)
            db.refresh(membership)
            return user, org, membership

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete user registration: {str(e)}"
            )

    @classmethod
    def authenticate_user(cls, db: Session, email: str, password: str) -> Optional[User]:
        user = cls.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
