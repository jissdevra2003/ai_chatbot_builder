import re
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.organization import Organization
from app.models.membership import Membership, RoleEnum


class OrgService:
    @staticmethod
    def generate_slug(name: str) -> str:
        """Generates a clean URL slug from organization name."""
        clean_name = re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().lower()
        slug = re.sub(r'[\s-]+', '-', clean_name)
        if not slug:
            slug = "workspace"
        unique_suffix = str(uuid.uuid4())[:8]
        return f"{slug}-{unique_suffix}"

    @classmethod
    def create_organization(cls, db: Session, name: str) -> Organization:
        """Creates a new organization record."""
        slug = cls.generate_slug(name)
        org = Organization(name=name, slug=slug)
        db.add(org)
        # flush to obtain org.id without committing transaction
        db.flush()
        return org

    @classmethod
    def create_membership(cls, db: Session, user_id: str, org_id: str, role: RoleEnum = RoleEnum.MEMBER) -> Membership:
        """Creates a user membership in an organization."""
        membership = Membership(user_id=user_id, org_id=org_id, role=role)
        db.add(membership)
        db.flush()
        return membership

    @classmethod
    def get_user_active_membership(cls, db: Session, user_id: str) -> Optional[Membership]:
        """Gets the user's primary/active membership including organization."""
        stmt = select(Membership).where(Membership.user_id == user_id)
        result = db.execute(stmt).scalars().first()
        return result
