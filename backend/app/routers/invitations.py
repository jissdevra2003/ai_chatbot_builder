from typing import List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_org, require_roles
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import RoleEnum
from app.schemas.invitation import InvitationCreate, InvitationResponse, InvitationAccept
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/invitations", tags=["Invitations"])


@router.post("/", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    invitation_in: InvitationCreate,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Sends an invitation to a member or admin (Requires OWNER or ADMIN role)."""
    current_user, active_org, _ = auth_data
    return InvitationService.create_invitation(
        db,
        org_id=active_org.id,
        invited_by_user=current_user,
        invitation_in=invitation_in
    )


@router.get("/", response_model=List[InvitationResponse])
def list_invitations(
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Lists all pending/sent invitations for the active organization."""
    _, active_org, _ = auth_data
    return InvitationService.list_org_invitations(db, org_id=active_org.id)


@router.get("/{token}", response_model=InvitationResponse)
def get_invitation(token: str, db: Session = Depends(get_db)):
    """Retrieves invitation details by token (Public endpoint for invite acceptance preview)."""
    invitation = InvitationService.get_invitation_by_token(db, token)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation token not found or invalid."
        )
    return invitation


@router.post("/accept", status_code=status.HTTP_200_OK)
def accept_invitation(accept_in: InvitationAccept, db: Session = Depends(get_db)):
    """Accepts an invitation using token and joins the organization."""
    membership = InvitationService.accept_invitation(
        db,
        token=accept_in.token,
        password=accept_in.password,
        full_name=accept_in.full_name
    )
    return {
        "message": "Invitation accepted successfully!",
        "org_id": membership.org_id,
        "role": membership.role.value
    }
