# app/routers/__init__.py

# Import all router modules to make them available
from . import auth
from . import dashboard
from . import expenses
from . import bills
from . import tasks
from . import calendar
from . import guests
from . import communications
from . import notifications
from . import shopping
from . import households

__all__ = [
    "auth",
    "dashboard",
    "expenses",
    "bills",
    "tasks",
    "calendar",
    "guests",
    "communications",
    "notifications",
    "shopping",
    "households",
]
