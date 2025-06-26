from typing import TypeVar, Type, List, Dict, Any, Callable
from abc import ABC, abstractmethod
from fastapi import APIRouter, Depends, status, Query, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..dependencies import require_household_member, require_household_admin
from ..schemas.common import (
    SuccessResponse,
    PaginatedResponse,
    ResponseFactory,
    PaginationParams,
)
from ..models.user import User

T = TypeVar("T", bound=BaseModel)
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


class BaseService(ABC):
    """Abstract base service interface"""

    @abstractmethod
    def get_by_id(self, household_id: int, entity_id: int) -> Any:
        pass

    @abstractmethod
    def get_all(self, household_id: int, **filters) -> List[Any]:
        pass

    @abstractmethod
    def create(self, household_id: int, user_id: int, data: BaseModel) -> Any:
        pass

    @abstractmethod
    def update(
        self, household_id: int, entity_id: int, data: BaseModel, user_id: int
    ) -> Any:
        pass

    @abstractmethod
    def delete(self, household_id: int, entity_id: int, user_id: int) -> None:
        pass


class CRUDRouterBuilder:
    """Builder pattern for creating CRUD routers - fixes typing issues"""

    def __init__(self, entity_name: str):
        self.entity_name = entity_name
        self.entity_name_lower = entity_name.lower()
        self.router = APIRouter()
        self.require_admin_create = False
        self.require_admin_update = False
        self.require_admin_delete = False
        self.enable_pagination = True

    def with_admin_permissions(self, create=False, update=False, delete=False):
        """Configure admin requirements"""
        self.require_admin_create = create
        self.require_admin_update = update
        self.require_admin_delete = delete
        return self

    def with_pagination(self, enabled=True):
        """Configure pagination"""
        self.enable_pagination = enabled
        return self

    def build_router(
        self,
        service_factory: Callable[[Session], BaseService],
        create_schema: Type[CreateT],
        update_schema: Type[UpdateT],
        response_schema: Type[ResponseT],
    ) -> APIRouter:
        """Build the complete CRUD router"""
        create_dep = (
            require_household_admin
            if self.require_admin_create
            else require_household_member
        )
        update_dep = (
            require_household_admin
            if self.require_admin_update
            else require_household_member
        )
        delete_dep = (
            require_household_admin
            if self.require_admin_delete
            else require_household_member
        )

        @self.router.get(
            "",
            response_model=(
                PaginatedResponse[response_schema]
                if self.enable_pagination
                else SuccessResponse[List[response_schema]]
            ),
            summary=f"List {self.entity_name}s",
        )
        def list_entities(
            pagination: PaginationParams = (
                Depends() if self.enable_pagination else None
            ),
            active_only: bool = Query(True),
            user_household: tuple[User, int] = Depends(require_household_member),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = service_factory(db)
            try:
                entities = service.get_all(
                    household_id=household_id, active_only=active_only
                )
                if self.enable_pagination:
                    total = len(entities)
                    start = pagination.offset
                    end = start + pagination.limit
                    page_entities = entities[start:end]
                    from ..schemas.common import PaginationInfo

                    pagination_info = PaginationInfo(
                        current_page=pagination.page,
                        page_size=pagination.page_size,
                        total_items=total,
                        total_pages=(total + pagination.page_size - 1)
                        // pagination.page_size,
                        has_next=end < total,
                        has_previous=pagination.page > 1,
                    )
                    return ResponseFactory.paginated(
                        data=page_entities,
                        pagination=pagination_info,
                        message=f"{self.entity_name}s retrieved successfully",
                    )
                else:
                    return ResponseFactory.success(
                        data=entities,
                        message=f"{self.entity_name}s retrieved successfully",
                    )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.get(
            "/{entity_id}",
            response_model=SuccessResponse[response_schema],
            summary=f"Get {self.entity_name}",
        )
        def get_entity(
            entity_id: int,
            user_household: tuple[User, int] = Depends(require_household_member),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = service_factory(db)
            try:
                entity = service.get_by_id(household_id, entity_id)
                if not entity:
                    raise HTTPException(
                        status_code=404, detail=f"{self.entity_name} not found"
                    )
                return ResponseFactory.success(
                    data=entity, message=f"{self.entity_name} retrieved successfully"
                )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.post(
            "",
            response_model=SuccessResponse[response_schema],
            status_code=status.HTTP_201_CREATED,
            summary=f"Create {self.entity_name}",
        )
        def create_entity(
            entity_data: Any,
            background_tasks: BackgroundTasks,
            user_household: tuple[User, int] = Depends(create_dep),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = service_factory(db)
            try:
                entity = service.create(
                    household_id=household_id, user_id=current_user.id, data=entity_data
                )
                background_tasks.add_task(
                    self._notify_entity_change, "created", entity, household_id
                )
                return ResponseFactory.created(
                    data=entity, message=f"{self.entity_name} created successfully"
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.put(
            "/{entity_id}",
            response_model=SuccessResponse[response_schema],
            summary=f"Update {self.entity_name}",
        )
        def update_entity(
            entity_id: int,
            entity_data: Any,
            background_tasks: BackgroundTasks,
            user_household: tuple[User, int] = Depends(update_dep),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = service_factory(db)
            try:
                entity = service.update(
                    household_id=household_id,
                    entity_id=entity_id,
                    data=entity_data,
                    user_id=current_user.id,
                )
                background_tasks.add_task(
                    self._notify_entity_change, "updated", entity, household_id
                )
                return ResponseFactory.success(
                    data=entity, message=f"{self.entity_name} updated successfully"
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.delete(
            "/{entity_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary=f"Delete {self.entity_name}",
        )
        def delete_entity(
            entity_id: int,
            background_tasks: BackgroundTasks,
            user_household: tuple[User, int] = Depends(delete_dep),
            db: Session = Depends(get_db),
        ):
            current_user, household_id = user_household
            service = service_factory(db)
            try:
                service.delete(
                    household_id=household_id,
                    entity_id=entity_id,
                    user_id=current_user.id,
                )
                background_tasks.add_task(
                    self._notify_entity_change,
                    "deleted",
                    {"id": entity_id},
                    household_id,
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        return self.router

    def _notify_entity_change(self, action: str, entity_data: Any, household_id: int):
        """Background task for notifications"""
        print(f"{self.entity_name} {action}: {entity_data} in household {household_id}")


class CustomEndpointMixin:
    """Mixin for adding custom endpoints to CRUD routers"""

    def add_custom_endpoint(self, router: APIRouter, path: str, methods: List[str]):
        """Add custom endpoints to existing router"""

        def decorator(func):
            for method in methods:
                getattr(router, method.lower())(path)(func)
            return func

        return decorator


class ConfigRouterBuilder:
    """Builder for configuration/enum endpoints"""

    def __init__(self, prefix: str, tags: List[str]):
        self.router = APIRouter(prefix=prefix, tags=tags)

    def add_enum_config(
        self, enum_class: Type, endpoint_name: str, description: str = None
    ):
        """Add enum configuration endpoint"""

        @self.router.get(
            f"/{endpoint_name}",
            response_model=SuccessResponse[List[Dict[str, str]]],
            summary=f"Get {endpoint_name} options",
            description=description or f"Get available {endpoint_name} options",
        )
        def get_enum_options():
            options = [
                {
                    "value": item.value,
                    "label": item.value.replace("_", " ").title(),
                    "description": description,
                }
                for item in enum_class
            ]
            return ResponseFactory.success(
                data=options, message=f"{endpoint_name} options retrieved successfully"
            )

        return self

    def build(self) -> APIRouter:
        return self.router


class RouterFactory:
    """Factory for creating different types of routers"""

    @staticmethod
    def create_crud_router(
        entity_name: str,
        service_factory: Callable[[Session], BaseService],
        create_schema: Type[CreateT],
        update_schema: Type[UpdateT],
        response_schema: Type[ResponseT],
        **options,
    ) -> APIRouter:
        """Factory method for CRUD routers"""
        builder = CRUDRouterBuilder(entity_name)
        if options.get("admin_create"):
            builder.require_admin_create = True
        if options.get("admin_update"):
            builder.require_admin_update = True
        if options.get("admin_delete"):
            builder.require_admin_delete = True
        if "pagination" in options:
            builder.enable_pagination = options["pagination"]
        return builder.build_router(
            service_factory=service_factory,
            create_schema=create_schema,
            update_schema=update_schema,
            response_schema=response_schema,
        )

    @staticmethod
    def create_config_router(prefix: str, tags: List[str]) -> ConfigRouterBuilder:
        """Factory method for config routers"""
        return ConfigRouterBuilder(prefix, tags)
