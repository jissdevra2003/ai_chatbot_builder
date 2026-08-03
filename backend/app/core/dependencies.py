from typing import Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, RoleEnum
from app.services.auth_service import AuthService
from app.services.org_service import OrgService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    user = AuthService.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return user


def get_current_org(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Tuple[Organization, RoleEnum]:
    membership: Membership = OrgService.get_user_active_membership(db, user_id=current_user.id)
    if not membership or not membership.organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to an active organization"
        )
    return membership.organization, membership.role


def require_roles(*allowed_roles: RoleEnum):
    def role_checker(
        current_user: User = Depends(get_current_user),
        org_context: Tuple[Organization, RoleEnum] = Depends(get_current_org)
    ) -> Tuple[User, Organization, RoleEnum]:
        org, role = org_context
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Role '{role.value}' is not authorized for this operation."
            )
        return current_user, org, role
    return role_checker

