from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.membership import RoleEnum
from app.schemas.user import UserResponse


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserMeResponse(BaseModel):
    user: UserResponse
    active_organization: OrgResponse
    role: RoleEnum
