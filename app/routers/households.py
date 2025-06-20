from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..database import get_db
from ..services.household_service import HouseholdService
from ..schemas.household import (
    HouseholdCreate,
    HouseholdUpdate,
    HouseholdInvitation,
)
from ..dependencies.permissions import (
    require_household_member,
    require_household_admin,
)
from ..utils.router_helpers import (
    handle_service_errors,
    RouterResponse,
)
from ..models.user import User
from ..models.enums import HouseholdRole
from .auth import get_current_user

router = APIRouter(prefix="/households", tags=["households"])


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
@handle_service_errors
async def create_household(
    household_data: HouseholdCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new household with current user as admin"""
    household_service = HouseholdService(db)

    household = household_service.create_household(
        household_data=household_data, creator_id=current_user.id
    )

    return RouterResponse.created(
        data={"household": household}, message="Household created successfully"
    )


@router.get("/me", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_household(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get current user's household information"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    details = household_service.get_household_details(household_id)

    return RouterResponse.success(data={"household": details})


@router.get("/{household_id}", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_details(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not household_service.check_member_permissions(current_user.id, household_id):
        raise HTTPException(403, "Access denied")

    household_service = HouseholdService(db)
    details = household_service.get_household_details(household_id)
    return RouterResponse.success(data={"household": details})


@router.put("/me", response_model=Dict[str, Any])
@handle_service_errors
async def update_my_household(
    household_update: HouseholdUpdate,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Update current user's household settings (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    household = household_service.update_household_settings(
        household_id=household_id,
        settings_update=household_update,
        updated_by=current_user.id,
    )

    return RouterResponse.updated(
        data={"household": household}, message="Household updated successfully"
    )


@router.get("/me/members", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_household_members(
    include_stats: bool = Query(False, description="Include member statistics"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household members with optional statistics"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    members = household_service.get_household_members(household_id)

    return RouterResponse.success(
        data={
            "members": members,
            "total_count": len(members),
            "admin_count": len([m for m in members if m["role"] == "admin"]),
            "active_count": len([m for m in members if m["is_active"]]),
        }
    )


@router.post("/me/members", response_model=Dict[str, Any])
@handle_service_errors
async def add_member_to_my_household(
    member_data: Dict[str, Any] = Body(..., example={"user_id": 2, "role": "member"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Add user to household (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    user_id = member_data.get("user_id")
    role = member_data.get("role", "member")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required"
        )

    # Validate role
    if role not in [r.value for r in HouseholdRole]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in HouseholdRole]}",
        )

    result = household_service.add_member_to_household(
        household_id=household_id,
        user_id=user_id,
        role=role,
        added_by=current_user.id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to add member"
        )

    return RouterResponse.success(
        message=f"Member added successfully with role: {role}"
    )


@router.delete("/me/members/{user_id}", response_model=Dict[str, Any])
@handle_service_errors
async def remove_member_from_my_household(
    user_id: int,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Remove member from household (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    result = household_service.remove_member_from_household(
        household_id=household_id,
        user_id=user_id,
        removed_by=current_user.id,
    )

    return RouterResponse.success(data=result, message="Member removal completed")


@router.put("/me/members/{user_id}/role", response_model=Dict[str, Any])
@handle_service_errors
async def update_member_role(
    user_id: int,
    role_data: Dict[str, str] = Body(..., example={"role": "admin"}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Update member role (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    new_role = role_data.get("role")
    if not new_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="role is required"
        )

    # Validate role
    if new_role not in [r.value for r in HouseholdRole]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in HouseholdRole]}",
        )

    success = household_service.update_member_role(
        household_id=household_id,
        user_id=user_id,
        new_role=new_role,
        updated_by=current_user.id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update member role",
        )

    return RouterResponse.updated(message=f"Member role updated to {new_role}")


@router.get("/me/health-score", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_household_health_score(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get household health score"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    health_score = household_service.calculate_household_health_score(household_id)

    return RouterResponse.success(data={"health_score": health_score})


@router.get("/me/statistics", response_model=Dict[str, Any])
@handle_service_errors
async def get_my_household_statistics(
    months_back: int = Query(6, ge=1, le=24, description="Months of data to analyze"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get comprehensive household statistics"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    stats = household_service.get_household_statistics(household_id)

    return RouterResponse.success(
        data={
            "statistics": stats,
            "period_months": months_back,
            "household_id": household_id,
        }
    )


@router.post("/me/invite", response_model=Dict[str, Any])
@handle_service_errors
async def invite_member_to_household(
    invitation: HouseholdInvitation,
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Send invitation to join household (admin only)"""
    current_user, household_id = user_household

    # TODO: Integrate with email service to send actual invitation
    # For now, return success message

    return RouterResponse.success(
        data={
            "invitation": {
                "email": invitation.email,
                "role": invitation.role,
                "invited_by": current_user.name,
                "household_id": household_id,
            }
        },
        message=f"Invitation sent to {invitation.email}",
    )


@router.post("/join", response_model=Dict[str, Any])
@handle_service_errors
async def join_household_by_invitation(
    join_data: Dict[str, Any] = Body(
        ..., example={"invitation_code": "abc123", "household_id": 1}
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join household using invitation code"""
    household_service = HouseholdService(db)

    invitation_code = join_data.get("invitation_code")
    household_id = join_data.get("household_id")

    if not invitation_code or not household_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invitation_code and household_id are required",
        )

    # TODO: Validate invitation code
    # For now, just add user as member

    success = household_service.add_member_to_household(
        household_id=household_id,
        user_id=current_user.id,
        role="member",
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to join household"
        )

    return RouterResponse.success(message="Successfully joined household")


@router.post("/me/leave", response_model=Dict[str, Any])
@handle_service_errors
async def leave_my_household(
    confirm: bool = Body(False, description="Confirmation flag"),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Leave current household"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must confirm leaving by setting confirm=true",
        )

    result = household_service.remove_member_from_household(
        household_id=household_id,
        user_id=current_user.id,
        removed_by=current_user.id,  # Self-removal
    )

    return RouterResponse.success(data=result, message="Successfully left household")


@router.post("/me/transfer-ownership", response_model=Dict[str, Any])
@handle_service_errors
async def transfer_household_ownership(
    transfer_data: Dict[str, int] = Body(..., example={"new_admin_id": 2}),
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_admin),
):
    """Transfer household ownership to another member (admin only)"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    new_admin_id = transfer_data.get("new_admin_id")
    if not new_admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="new_admin_id is required"
        )

    success = household_service.transfer_household_ownership(
        household_id=household_id,
        current_admin_id=current_user.id,
        new_admin_id=new_admin_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to transfer ownership",
        )

    return RouterResponse.success(
        message="Household ownership transferred successfully"
    )


@router.get("/config/roles", response_model=Dict[str, Any])
async def get_household_roles():
    """Get available household roles"""
    roles = [
        {"value": role.value, "label": role.value.title()} for role in HouseholdRole
    ]

    return RouterResponse.success(data={"roles": roles})


@router.get("/me/summary", response_model=Dict[str, Any])
@handle_service_errors
async def get_household_summary(
    db: Session = Depends(get_db),
    user_household: tuple[User, int] = Depends(require_household_member),
):
    """Get quick household summary for dashboard"""
    current_user, household_id = user_household
    household_service = HouseholdService(db)

    # Get basic household info
    details = household_service.get_household_details(household_id)
    health_score = household_service.calculate_household_health_score(household_id)

    summary = {
        "household": {
            "id": details["id"],
            "name": details["name"],
            "member_count": details["member_count"],
            "user_role": next(
                (m["role"] for m in details["members"] if m["id"] == current_user.id),
                "member",
            ),
        },
        "health_score": health_score["overall_score"],
        "quick_stats": {
            "active_members": details["member_count"],
            "health_score": health_score["overall_score"],
            "improvement_suggestions": health_score["improvement_suggestions"][
                :2
            ],  # Top 2
        },
    }

    return RouterResponse.success(data=summary)
