from typing import Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token
from app.core.dependencies import get_current_user, get_current_org, require_roles
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import RoleEnum
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.schemas.organization import UserMeResponse, OrgResponse, OrgUpdate
from app.schemas.token import Token
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user and auto-creates their default organization in a single transaction."""
    user, org, membership = AuthService.register_user(db, user_in)
    return user


@router.post("/login", response_model=Token)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    """Logs in with email and password, returning a JWT access token."""
    user = AuthService.authenticate_user(db, email=login_in.email, password=login_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login/token", response_model=Token, include_in_schema=False)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Support OAuth2PasswordRequestForm for Swagger UI compliance."""
    user = AuthService.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserMeResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    org_context: tuple[Organization, RoleEnum] = Depends(get_current_org)
):
    """Returns current user identity, active tenant organization, and membership role."""
    active_org, role = org_context
    return UserMeResponse(
        user=UserResponse.model_validate(current_user),
        active_organization=OrgResponse.model_validate(active_org),
        role=role
    )


@router.patch("/organization", response_model=OrgResponse)
def update_organization(
    org_in: OrgUpdate,
    auth_data: Tuple[User, Organization, RoleEnum] = Depends(require_roles(RoleEnum.OWNER, RoleEnum.ADMIN)),
    db: Session = Depends(get_db)
):
    """Updates active organization details (Requires OWNER or ADMIN role)."""
    _, active_org, _ = auth_data
    if not org_in.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name cannot be empty."
        )
    active_org.name = org_in.name.strip()
    db.commit()
    db.refresh(active_org)
    return active_org
