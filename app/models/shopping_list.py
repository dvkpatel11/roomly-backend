from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class ShoppingList(Base):
    __tablename__ = "shopping_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Grocery List")
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Shopping trip details
    store_name = Column(String)
    planned_date = Column(DateTime)
    total_estimated_cost = Column(Float)
    total_actual_cost = Column(Float)
    
    # Foreign Keys
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_shopper = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    household = relationship("Household", back_populates="shopping_lists")
    creator = relationship("User", back_populates="created_shopping_lists", foreign_keys=[created_by])
    shopper = relationship("User", back_populates="assigned_shopping_lists", foreign_keys=[assigned_shopper])
    items = relationship("ShoppingItem", back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingItem(Base):
    __tablename__ = "shopping_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    quantity = Column(String, default="1")  # "2 lbs", "1 gallon", "3 items"
    category = Column(String)  # produce, dairy, meat, etc.
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    notes = Column(Text)
    
    # Status
    is_purchased = Column(Boolean, default=False)
    is_urgent = Column(Boolean, default=False)
    
    # Foreign Keys
    shopping_list_id = Column(Integer, ForeignKey("shopping_lists.id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    purchased_at = Column(DateTime)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    shopping_list = relationship("ShoppingList", back_populates="items")
    requester = relationship("User", back_populates="requested_shopping_items", foreign_keys=[requested_by])
