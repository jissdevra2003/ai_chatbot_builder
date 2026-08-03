from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.membership import RoleEnum
from app.models.invitation import InvitationStatusEnum


class InvitationCreate(BaseModel):
    email: EmailStr
    role: RoleEnum = Field(..., description="Role to grant: ADMIN or MEMBER")


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    invited_by_id: str
    email: str
    role: RoleEnum
    token: str
    status: InvitationStatusEnum
    expires_at: datetime
    created_at: datetime



class InvitationAccept(BaseModel):
    token: str
    password: Optional[str] = Field(None, min_length=8, description="Password required if new user account")
    full_name: Optional[str] = Field(None, description="Full name required if new user account")
