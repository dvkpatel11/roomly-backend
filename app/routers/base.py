from typing import TypeVar, Generic, Type, List, Optional, Dict, Any, Callable
from abc import ABC, abstractmethod
from fastapi import APIRouter, Depends, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..dependencies import require_household_member, require_household_admin
from ..schemas.common import (
    SuccessResponse,
    PaginatedResponse,
    ResponseFactory,
    PaginationParams,
    ConfigResponse,
    ConfigOption,
)
from ..models.user import User
from ..utils.constants import ResponseMessages
from ..utils.router_helpers import handle_service_errors

# Type variables for generic patterns
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)
ResponseSchemaT = TypeVar("ResponseSchemaT", bound=BaseModel)
ServiceT = TypeVar("ServiceT")


class BaseRouterV2(ABC):
    """Abstract base class for all V2 routers"""

    def __init__(self, prefix: str, tags: List[str]):
        self.router = APIRouter(prefix=prefix, tags=tags)
        self._register_endpoints()

    @abstractmethod
    def _register_endpoints(self):
        """Register all endpoints for this router"""
        pass


class HouseholdCRUDRouter(
    BaseRouterV2, Generic[CreateSchemaT, UpdateSchemaT, ResponseSchemaT, ServiceT]
):
    """
    Generic CRUD router for household-scoped entities
    Eliminates 90% of repetitive router code
    """

    def __init__(
        self,
        entity_name: str,
        service_class: Type[ServiceT],
        create_schema: Type[CreateSchemaT],
        update_schema: Type[UpdateSchemaT],
        response_schema: Type[ResponseSchemaT],
        prefix: str = None,
        tags: List[str] = None,
        # Customization options
        require_admin_for_create: bool = False,
        require_admin_for_update: bool = False,
        require_admin_for_delete: bool = False,
        enable_pagination: bool = True,
        enable_filtering: bool = True,
        custom_endpoints: List[Callable] = None,
    ):
        self.entity_name = entity_name
        self.entity_name_lower = entity_name.lower()
        self.service_class = service_class
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema

        # Permission settings
        self.require_admin_for_create = require_admin_for_create
        self.require_admin_for_update = require_admin_for_update
        self.require_admin_for_delete = require_admin_for_delete

        # Feature flags
        self.enable_pagination = enable_pagination
        self.enable_filtering = enable_filtering

        # Custom endpoints to register
        self.custom_endpoints = custom_endpoints or []

        super().__init__(
            prefix=prefix or f"/{self.entity_name_lower}s",
            tags=tags or [self.entity_name_lower],
        )

    def _get_create_dependency(self):
        """Get appropriate dependency for create operations"""
        return (
            require_household_admin
            if self.require_admin_for_create
            else require_household_member
        )

    def _get_update_dependency(self):
        """Get appropriate dependency for update operations"""
        return (
            require_household_admin
            if self.require_admin_for_update
            else require_household_member
        )

    def _get_delete_dependency(self):
        """Get appropriate dependency for delete operations"""
        return (
            require_household_admin
            if self.require_admin_for_delete
            else require_household_member
        )

    def _register_endpoints(self):
        """Register all standard CRUD endpoints"""
        self._register_list_endpoint()
        self._register_get_endpoint()
        self._register_create_endpoint()
        self._register_update_endpoint()
        self._register_delete_endpoint()

        # Register custom endpoints
        for endpoint_func in self.custom_endpoints:
            endpoint_func(self.router)

    def _register_list_endpoint(self):
        """Register GET / endpoint with pagination and filtering"""

        if self.enable_pagination:
            response_model = PaginatedResponse[self.response_schema]
        else:
            response_model = SuccessResponse[List[self.response_schema]]

        @self.router.get(
            "",
            response_model=response_model,
            summary=f"List {self.entity_name}s",
            description=f"Get all {self.entity_name_lower}s for the household with optional filtering",
        )
        @handle_service_errors
        async def list_entities(
            pagination: PaginationParams = (
                Depends() if self.enable_pagination else None
            ),
            # Common filter parameters
            active_only: bool = Query(True, description="Show only active items"),
            created_by: Optional[int] = Query(None, description="Filter by creator"),
            # Dependencies
            user_household: tuple[User, int] = Depends(require_household_member),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = self.service_class(db)

            if self.enable_pagination:
                entities, pagination_meta = await service.get_entities_paginated(
                    household_id=household_id,
                    pagination=pagination,
                    active_only=active_only,
                    created_by=created_by,
                )

                return ResponseFactory.paginated(
                    data=entities,
                    pagination=pagination_meta,
                    message=f"{self.entity_name}s retrieved successfully",
                )
            else:
                entities = await service.get_entities(
                    household_id=household_id,
                    active_only=active_only,
                    created_by=created_by,
                )

                return ResponseFactory.success(
                    data=entities, message=f"{self.entity_name}s retrieved successfully"
                )

    def _register_get_endpoint(self):
        """Register GET /{id} endpoint"""

        @self.router.get(
            "/{entity_id}",
            response_model=SuccessResponse[self.response_schema],
            summary=f"Get {self.entity_name}",
            description=f"Get a specific {self.entity_name_lower} by ID",
        )
        @handle_service_errors
        async def get_entity(
            entity_id: int,
            user_household: tuple[User, int] = Depends(require_household_member),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = self.service_class(db)

            entity = await service.get_entity(household_id, entity_id)

            return ResponseFactory.success(
                data=entity, message=f"{self.entity_name} retrieved successfully"
            )

    def _register_create_endpoint(self):
        """Register POST / endpoint"""

        @self.router.post(
            "",
            response_model=SuccessResponse[self.response_schema],
            status_code=status.HTTP_201_CREATED,
            summary=f"Create {self.entity_name}",
            description=f"Create a new {self.entity_name_lower}",
        )
        @handle_service_errors
        async def create_entity(
            entity_data: self.create_schema,
            background_tasks: BackgroundTasks,
            user_household: tuple[User, int] = Depends(self._get_create_dependency()),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = self.service_class(db)

            entity = await service.create_entity(
                household_id=household_id,
                user_id=current_user.id,
                entity_data=entity_data,
            )

            # Add real-time broadcast
            background_tasks.add_task(
                self._broadcast_entity_event, "created", entity, household_id
            )

            return ResponseFactory.created(
                data=entity,
                message=getattr(
                    ResponseMessages,
                    f"{self.entity_name.upper()}_CREATED",
                    f"{self.entity_name} created successfully",
                ),
            )

    def _register_update_endpoint(self):
        """Register PUT /{id} endpoint"""

        @self.router.put(
            "/{entity_id}",
            response_model=SuccessResponse[self.response_schema],
            summary=f"Update {self.entity_name}",
            description=f"Update an existing {self.entity_name_lower}",
        )
        @handle_service_errors
        async def update_entity(
            entity_id: int,
            entity_data: self.update_schema,
            background_tasks: BackgroundTasks,
            user_household: tuple[User, int] = Depends(self._get_update_dependency()),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = self.service_class(db)

            entity = await service.update_entity(
                household_id, entity_id, entity_data, current_user.id
            )

            # Add real-time broadcast
            background_tasks.add_task(
                self._broadcast_entity_event, "updated", entity, household_id
            )

            return ResponseFactory.success(
                data=entity,
                message=getattr(
                    ResponseMessages,
                    f"{self.entity_name.upper()}_UPDATED",
                    f"{self.entity_name} updated successfully",
                ),
            )

    def _register_delete_endpoint(self):
        """Register DELETE /{id} endpoint"""

        @self.router.delete(
            "/{entity_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary=f"Delete {self.entity_name}",
            description=f"Delete a {self.entity_name_lower}",
        )
        @handle_service_errors
        async def delete_entity(
            entity_id: int,
            background_tasks: BackgroundTasks,
            user_household: tuple[User, int] = Depends(self._get_delete_dependency()),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = self.service_class(db)

            await service.delete_entity(household_id, entity_id, current_user.id)

            # Add real-time broadcast
            background_tasks.add_task(
                self._broadcast_entity_event, "deleted", {"id": entity_id}, household_id
            )

    async def _broadcast_entity_event(
        self, action: str, entity_data: Any, household_id: int
    ):
        """Broadcast entity changes for real-time updates"""
        # TODO: Implement WebSocket broadcasting
        # For now, this is a placeholder for future real-time features
        event = {
            "type": f"{self.entity_name_lower}_{action}",
            "data": entity_data,
            "household_id": household_id,
            "timestamp": "2024-01-01T00:00:00Z",  # Will use actual timestamp
        }
        # await broadcast_to_household(household_id, event)
        pass


class ConfigRouter(BaseRouterV2):
    """Router for configuration endpoints using enums"""

    def __init__(self, entity_name: str, prefix: str = None):
        self.entity_name = entity_name
        self.entity_name_lower = entity_name.lower()

        super().__init__(
            prefix=prefix or f"/{self.entity_name_lower}/config",
            tags=[f"{self.entity_name_lower}-config"],
        )

    def _register_endpoints(self):
        """Register config endpoints - will be customized per entity"""
        pass

    def add_enum_endpoint(
        self,
        enum_class: Type,
        endpoint_name: str,
        category_name: str,
        description_map: Dict[str, str] = None,
    ):
        """Add a configuration endpoint for an enum"""

        @self.router.get(
            f"/{endpoint_name}",
            response_model=SuccessResponse[ConfigResponse],
            summary=f"Get {category_name}",
            description=f"Get available {category_name.lower()} options",
        )
        async def get_enum_config():
            options = []
            for enum_value in enum_class:
                description = None
                if description_map:
                    description = description_map.get(enum_value.value)

                options.append(
                    ConfigOption(
                        value=enum_value.value,
                        label=enum_value.value.replace("_", " ").title(),
                        description=description,
                    )
                )

            return ResponseFactory.success(
                data=ConfigResponse(
                    options=options, total_count=len(options), category=category_name
                )
            )


class RealTimeRouter(BaseRouterV2):
    """Router for real-time WebSocket endpoints"""

    def __init__(self):
        super().__init__(prefix="/realtime", tags=["realtime"])

    def _register_endpoints(self):
        """Register WebSocket endpoints"""

        @self.router.websocket("/household/{household_id}")
        async def household_websocket(
            websocket,  # WebSocket type
            household_id: int,
            # TODO: Add authentication for WebSocket
        ):
            """WebSocket endpoint for real-time household updates"""
            # TODO: Implement WebSocket connection management
            pass
