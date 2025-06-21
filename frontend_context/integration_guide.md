# Frontend Integration Guide

## Page to Context Mapping

### Dashboard Page

- **Context File:** `dashboard_context.md`
- **Key Endpoints:** Dashboard aggregation, household overview
- **Primary Models:** Household, User, Dashboard summary

### Calendar Page

- **Context File:** `calendar_context.md`
- **Key Endpoints:** Events, Bills, User schedules
- **Primary Models:** Event, Bill,
- **Frontend Toggles:** Schedule view | Events view

### Tasks Page

- **Context File:** `tasks_context.md`
- **Key Endpoints:** Task CRUD, assignments, completion
- **Primary Models:** Task

### Expenses Page

- **Context File:** `expenses_context.md`
- **Key Endpoints:** Expenses, Bills, payments
- **Primary Models:** Expense, Bill

### Communication Page

- **Context File:** `communication_context.md`
- **Key Endpoints:** Announcements, Polls, Notifications
- **Primary Models:** Announcement, Poll, Notification

### House Page

- **Context File:** `house_context.md`
- **Key Endpoints:** Guests, Shopping, Household settings
- **Primary Models:** Guest, ShoppingList, Household

### Shared Context

- **Context File:** `shared_context.md`
- **Key Endpoints:** Authentication, Approvals
- **Primary Models:** Enums, RSVP, EventApproval

## Next Steps for Frontend Developer

1. Review each context file for your assigned page
2. Extract TypeScript interfaces from Pydantic models
3. Identify required API endpoints and their signatures
4. Generate mock data matching the schema structures
5. Build components that align with backend data flow

## Mock Data Generation Tips

- Use the Pydantic models as your source of truth
- Pay attention to enum values and field constraints
- Maintain relationships between models (foreign keys)
- Include realistic test data that covers edge cases
