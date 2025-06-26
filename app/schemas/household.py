from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.enums import HouseholdRole


class HouseholdBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=300)
    house_rules: Optional[str] = Field(None, max_length=2000)


class HouseholdCreate(HouseholdBase):
    pass


class HouseholdUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=300)
    house_rules: Optional[str] = Field(None, max_length=2000)


class HouseholdMember(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    joined_at: datetime
    role: HouseholdRole = "member"


class HouseholdSettings(BaseModel):
    guest_policy: Dict[str, Any] = {
        "max_overnight_guests": 2,
        "max_consecutive_nights": 3,
        "approval_required": True,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "08:00",
    }
    notification_settings: Dict[str, Any] = {
        "bill_reminder_days": 3,
        "task_overdue_hours": 24,
        "event_reminder_hours": 24,
    }
    task_settings: Dict[str, Any] = {
        "rotation_enabled": True,
        "photo_proof_required": False,
    }


class HouseholdResponse(HouseholdBase):
    id: int
    created_at: datetime
    member_count: int
    admin_count: int
    members: List[HouseholdMember]
    settings: HouseholdSettings

    class Config:
        from_attributes = True


class HouseholdInvitation(BaseModel):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    role: str = "member"
    personal_message: Optional[str] = Field(None, max_length=300)
