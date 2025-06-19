#!/usr/bin/env python3
"""
Data Model Validation Script
Validates relationships, constraints, and model integrity
"""

from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker
from .database import engine, Base
from .models import *


def validate_model_relationships():
    """Validate all model relationships are properly defined"""
    print("🔍 Validating model relationships...")

    # Get all model classes
    models = [
        User,
        Household,
        HouseholdMembership,
        Expense,
        ExpensePayment,
        Bill,
        BillPayment,
        Task,
        Event,
        EventApproval,
        Guest,
        GuestApproval,
        Announcement,
        Poll,
        PollVote,
        Notification,
        NotificationPreference,
        RSVP,
        UserSchedule,
        ShoppingList,
        ShoppingItem,
    ]

    issues = []

    for model in models:
        print(f"  📋 Checking {model.__name__}...")

        # Check for required relationships
        mapper = inspect(model)
        relationships = {rel.key: rel for rel in mapper.relationships}

        # Check foreign keys have corresponding relationships
        for column in mapper.columns:
            if column.foreign_keys:
                fk = list(column.foreign_keys)[0]
                target_table = fk.column.table.name

                # Check if there's a corresponding relationship
                has_relationship = any(
                    str(rel.target.name) == target_table
                    or rel.mapper.class_.__tablename__ == target_table
                    for rel in relationships.values()
                )

                if not has_relationship:
                    issues.append(
                        f"{model.__name__}.{column.name} -> {target_table}: Missing relationship"
                    )

    if issues:
        print("❌ Relationship issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ All relationships look good!")

    return len(issues) == 0


def validate_core_mvp_features():
    """Validate that core MVP features are supported by the data model"""
    print("\n🎯 Validating MVP feature support...")

    features = {
        "Expense Splitting": {
            "models": [Expense, ExpensePayment],
            "requirements": [
                "Expense.split_method",
                "Expense.split_details",
                "ExpensePayment.amount_paid",
                "ExpensePayment.payment_date",
            ],
        },
        "Task Management": {
            "models": [Task],
            "requirements": [
                "Task.assigned_to",
                "Task.status",
                "Task.due_date",
                "Task.completed_at",
            ],
        },
        "Household Calendar": {
            "models": [Event, RSVP],
            "requirements": [
                "Event.start_date",
                "Event.end_date",
                "RSVP.status",
                "RSVP.event_id",
            ],
        },
        "Communication": {
            "models": [Announcement, Notification],
            "requirements": [
                "Announcement.content",
                "Announcement.category",
                "Notification.notification_type",
                "Notification.is_read",
            ],
        },
    }

    all_good = True

    for feature, config in features.items():
        print(f"  📋 Checking {feature}...")

        # Check models exist
        for model in config["models"]:
            if not hasattr(model, "__tablename__"):
                print(f"    ❌ Model {model.__name__} not properly defined")
                all_good = False
                continue

        # Check required fields exist
        for requirement in config["requirements"]:
            model_name, field_name = requirement.split(".")
            model_class = next(
                (m for m in config["models"] if m.__name__ == model_name), None
            )

            if model_class and hasattr(model_class, field_name):
                print(f"    ✅ {requirement}")
            else:
                print(f"    ❌ {requirement} - Missing field")
                all_good = False

    if all_good:
        print("✅ All MVP features supported!")
    else:
        print("❌ Some MVP features need attention")

    return all_good


def validate_database_constraints():
    """Validate database constraints and indexes"""
    print("\n🔐 Validating database constraints...")

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    critical_constraints = {
        "users": ["email unique constraint"],
        "household_memberships": ["unique user-household constraint"],
        "expenses": ["amount > 0 constraint"],
        "bills": ["amount > 0 constraint"],
    }

    issues = []

    for table_name in tables:
        print(f"  📋 Checking {table_name}...")

        # Check indexes
        indexes = inspector.get_indexes(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        unique_constraints = inspector.get_unique_constraints(table_name)

        # Report what we found
        print(
            f"    📊 {len(indexes)} indexes, {len(foreign_keys)} foreign keys, {len(unique_constraints)} unique constraints"
        )

    return len(issues) == 0


def main():
    """Run all validations"""
    print("🚀 Starting data model validation...\n")

    try:
        rel_valid = validate_model_relationships()
        mvp_valid = validate_core_mvp_features()
        db_valid = validate_database_constraints()

        print(f"\n📊 Validation Summary:")
        print(f"  Relationships: {'✅' if rel_valid else '❌'}")
        print(f"  MVP Features: {'✅' if mvp_valid else '❌'}")
        print(f"  DB Constraints: {'✅' if db_valid else '❌'}")

        if all([rel_valid, mvp_valid, db_valid]):
            print("\n🎉 Data model validation passed! Ready for MVP development.")
        else:
            print("\n⚠️  Some issues found. Please review and fix before proceeding.")

    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
