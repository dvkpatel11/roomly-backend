# from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func
# from ..database import Base


# class User(Base):
#     __tablename__ = "users"

#     id = Column(Integer, primary_key=True, index=True)
#     email = Column(String, unique=True, index=True, nullable=False)
#     name = Column(String, nullable=False)
#     hashed_password = Column(String, nullable=False)
#     is_active = Column(Boolean, default=True)
#     phone = Column(String, index=True)  # Added index for better query performance
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())

#     # Add unique constraint for phone numbers (excluding NULL values)
#     __table_args__ = (
#         UniqueConstraint(
#             "phone", name="uq_user_phone", sqlite_on_conflict="ABORT"
#         ),  # For SQLite
#     )

#     # Relationships - Use household_memberships instead of direct household relationship
#     household_memberships = relationship("HouseholdMembership", back_populates="user")

#     # Expenses
#     created_expenses = relationship(
#         "Expense",
#         back_populates="created_by_user",
#         foreign_keys="Expense.created_by",
#         cascade="all, delete-orphan",
#     )
#     expense_payments = relationship("ExpensePayment", back_populates="user")

#     # Bills
#     created_bills = relationship(
#         "Bill", back_populates="created_by_user", foreign_keys="Bill.created_by"
#     )
#     bill_payments = relationship(
#         "BillPayment", back_populates="paid_by_user", foreign_keys="BillPayment.paid_by"
#     )

#     # Tasks
#     assigned_tasks = relationship(
#         "Task", back_populates="assigned_user", foreign_keys="Task.assigned_to"
#     )
#     created_tasks = relationship(
#         "Task", back_populates="created_by_user", foreign_keys="Task.created_by"
#     )

#     # Events
#     created_events = relationship(
#         "Event", back_populates="creator", foreign_keys="Event.created_by"
#     )
#     event_rsvps = relationship("RSVP", back_populates="user")

#     # Guests
#     hosted_guests = relationship(
#         "Guest", back_populates="host", foreign_keys="Guest.hosted_by"
#     )
#     approved_guests = relationship(
#         "Guest", back_populates="approver", foreign_keys="Guest.approved_by"
#     )

#     # Communications
#     announcements = relationship("Announcement", back_populates="author")
#     created_polls = relationship("Poll", back_populates="creator")
#     poll_votes = relationship("PollVote", back_populates="user")

#     # Notifications
#     notifications = relationship("Notification", back_populates="user")
#     notification_preferences = relationship(
#         "NotificationPreference", back_populates="user"
#     )

#     # Shopping
#     created_shopping_lists = relationship(
#         "ShoppingList", back_populates="creator", foreign_keys="ShoppingList.created_by"
#     )
#     assigned_shopping_lists = relationship(
#         "ShoppingList",
#         back_populates="shopper",
#         foreign_keys="ShoppingList.assigned_shopper",
#     )
#     requested_shopping_items = relationship("ShoppingItem", back_populates="requester")

#     # Helper methods
#     def get_active_household(self):
#         """Get the user's currently active household"""
#         active_membership = next(
#             (m for m in self.household_memberships if m.is_active), None
#         )
#         return active_membership.household if active_membership else None

#     def get_household_role(self, household_id: int):
#         """Get user's role in a specific household"""
#         membership = next(
#             (
#                 m
#                 for m in self.household_memberships
#                 if m.household_id == household_id and m.is_active
#             ),
#             None,
#         )
#         return membership.role if membership else None

from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)

    supabase_id = Column(String, unique=True, index=True, nullable=False)

    # User profile
    phone = Column(String, index=True)
    avatar_url = Column(String)  # Profile picture from Supabase or uploaded
    bio = Column(String, nullable=True)  # Optional user bio

    # User status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)  # Sync with Supabase
    last_login = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Constraints
    __table_args__ = (
        UniqueConstraint("phone", name="uq_user_phone"),
        UniqueConstraint("supabase_id", name="uq_user_supabase_id"),
        UniqueConstraint("email", name="uq_user_email"),
    )

    household_memberships = relationship("HouseholdMembership", back_populates="user")
    created_expenses = relationship(
        "Expense",
        back_populates="created_by_user",
        foreign_keys="Expense.created_by",
        cascade="all, delete-orphan",
    )
    expense_payments = relationship("ExpensePayment", back_populates="user")
    created_bills = relationship(
        "Bill", back_populates="created_by_user", foreign_keys="Bill.created_by"
    )
    bill_payments = relationship(
        "BillPayment", back_populates="paid_by_user", foreign_keys="BillPayment.paid_by"
    )
    assigned_tasks = relationship(
        "Task", back_populates="assigned_user", foreign_keys="Task.assigned_to"
    )
    created_tasks = relationship(
        "Task", back_populates="created_by_user", foreign_keys="Task.created_by"
    )
    created_events = relationship(
        "Event", back_populates="creator", foreign_keys="Event.created_by"
    )
    event_rsvps = relationship("RSVP", back_populates="user")
    hosted_guests = relationship(
        "Guest", back_populates="host", foreign_keys="Guest.hosted_by"
    )
    approved_guests = relationship(
        "Guest", back_populates="approver", foreign_keys="Guest.approved_by"
    )
    announcements = relationship("Announcement", back_populates="author")
    created_polls = relationship("Poll", back_populates="creator")
    poll_votes = relationship("PollVote", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    notification_preferences = relationship(
        "NotificationPreference", back_populates="user", uselist=False
    )
    created_shopping_lists = relationship(
        "ShoppingList", back_populates="creator", foreign_keys="ShoppingList.created_by"
    )
    assigned_shopping_lists = relationship(
        "ShoppingList",
        back_populates="shopper",
        foreign_keys="ShoppingList.assigned_shopper",
    )
    requested_shopping_items = relationship("ShoppingItem", back_populates="requester")

    # Helper methods
    def get_active_household(self):
        """Get the user's currently active household"""
        active_membership = next(
            (m for m in self.household_memberships if m.is_active), None
        )
        return active_membership.household if active_membership else None

    def get_household_role(self, household_id: int):
        """Get user's role in a specific household"""
        membership = next(
            (
                m
                for m in self.household_memberships
                if m.household_id == household_id and m.is_active
            ),
            None,
        )
        return membership.role if membership else None

    def is_household_admin(self, household_id: int = None) -> bool:
        """Check if user is admin of specified household or any household"""
        if household_id:
            return self.get_household_role(household_id) == "admin"
        return any(m.role == "admin" for m in self.household_memberships if m.is_active)

    def update_last_login(self, db_session):
        """Update last login timestamp"""
        self.last_login = func.now()
        db_session.commit()

    @classmethod
    def create_from_supabase(cls, supabase_user, db_session):
        """Create new user from Supabase auth user"""
        # Extract user metadata from Supabase
        user_metadata = supabase_user.user_metadata or {}

        user = cls(
            email=supabase_user.email,
            name=user_metadata.get("full_name")
            or user_metadata.get("name")
            or supabase_user.email.split("@")[0],
            supabase_id=supabase_user.id,
            phone=user_metadata.get("phone"),
            avatar_url=user_metadata.get("avatar_url"),
            email_verified=supabase_user.email_confirmed_at is not None,
            is_active=True,
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create default notification preferences
        from ..models.notification import NotificationPreference

        NotificationPreference.create_default_preferences(user.id, db_session)

        return user

    @classmethod
    def get_or_create_from_supabase(cls, supabase_user, db_session):
        """Get existing user or create new one from Supabase"""
        user = db_session.query(cls).filter(cls.supabase_id == supabase_user.id).first()

        if user:
            # Update email verification status if changed
            email_verified = supabase_user.email_confirmed_at is not None
            if user.email_verified != email_verified:
                user.email_verified = email_verified
                db_session.commit()
            return user

        return cls.create_from_supabase(supabase_user, db_session)

    @classmethod
    def find_by_supabase_id(cls, db_session, supabase_id: str):
        """Find user by Supabase ID"""
        return (
            db_session.query(cls)
            .filter(cls.supabase_id == supabase_id, cls.is_active == True)
            .first()
        )

    @classmethod
    def find_by_email(cls, db_session, email: str):
        """Find active user by email"""
        return (
            db_session.query(cls)
            .filter(cls.email == email, cls.is_active == True)
            .first()
        )

    def sync_with_supabase(self, supabase_user, db_session):
        """Sync user data with Supabase user metadata"""
        user_metadata = supabase_user.user_metadata or {}

        # Update fields that might have changed in Supabase
        self.email = supabase_user.email
        self.email_verified = supabase_user.email_confirmed_at is not None

        # Update metadata if provided
        if user_metadata.get("full_name"):
            self.name = user_metadata["full_name"]
        if user_metadata.get("phone"):
            self.phone = user_metadata["phone"]
        if user_metadata.get("avatar_url"):
            self.avatar_url = user_metadata["avatar_url"]

        self.updated_at = func.now()
        db_session.commit()

    def soft_delete(self, db_session):
        """Soft delete user (keep data but deactivate)"""
        self.is_active = False
        self.updated_at = func.now()

        # Deactivate all household memberships
        for membership in self.household_memberships:
            membership.is_active = False

        db_session.commit()

    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "phone": self.phone,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
            "active_household": (
                self.get_active_household().id if self.get_active_household() else None
            ),
        }
