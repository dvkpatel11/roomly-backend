from pydantic import BaseModel
from datetime import datetime

from app.models.enums import HouseholdRole


class HouseholdMembershipCreate(BaseModel):
    user_id: int
    household_id: int
    role: HouseholdRole = HouseholdRole.MEMBER


class HouseholdMembershipResponse(BaseModel):
    id: int
    user_id: int
    household_id: int
    role: str
    joined_at: datetime
    is_active: bool
