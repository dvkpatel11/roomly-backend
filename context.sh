#!/bin/bash

# Roomly Backend Context Extractor
# Extracts relevant backend context for each frontend page

OUTPUT_DIR="frontend_context"
mkdir -p "$OUTPUT_DIR"

echo "🏠 Extracting Roomly Backend Context for Frontend Pages..."

# Function to extract and format file content
extract_file() {
    local file_path="$1"
    local output_file="$2"
    
    if [ -f "$file_path" ]; then
        echo "## $file_path" >> "$output_file"
        echo '```python' >> "$output_file"
        cat "$file_path" >> "$output_file"
        echo '```' >> "$output_file"
        echo "" >> "$output_file"
    else
        echo "⚠️  Warning: $file_path not found"
    fi
}

# Dashboard Page Context
echo "📊 Extracting Dashboard context..."
DASHBOARD_OUTPUT="$OUTPUT_DIR/dashboard_context.md"
cat > "$DASHBOARD_OUTPUT" << 'EOF'
# Dashboard Page - Backend Context

## Overview
Dashboard aggregates household overview, financial summary, task status, and recent activity.

## Related Files:
EOF

extract_file "app/routers/dashboard.py" "$DASHBOARD_OUTPUT"
extract_file "app/schemas/dashboard.py" "$DASHBOARD_OUTPUT"
extract_file "app/models/household.py" "$DASHBOARD_OUTPUT"
extract_file "app/models/user.py" "$DASHBOARD_OUTPUT"

# Calendar Page Context
echo "📅 Extracting Calendar context..."
CALENDAR_OUTPUT="$OUTPUT_DIR/calendar_context.md"
cat > "$CALENDAR_OUTPUT" << 'EOF'
# Calendar Page - Backend Context

## Overview
Calendar handles scheduling, events, bill due dates, etc.
Frontend toggles: Schedule | Events

## Related Files:
EOF

extract_file "app/routers/event.py" "$CALENDAR_OUTPUT"
extract_file "app/routers/bills.py" "$CALENDAR_OUTPUT"
extract_file "app/schemas/event.py" "$CALENDAR_OUTPUT"
extract_file "app/schemas/bill.py" "$CALENDAR_OUTPUT"
extract_file "app/models/event.py" "$CALENDAR_OUTPUT"
extract_file "app/models/bill.py" "$CALENDAR_OUTPUT"
extract_file "app/models/user_schedule.py" "$CALENDAR_OUTPUT"

# Tasks Page Context
echo "✅ Extracting Tasks context..."
TASKS_OUTPUT="$OUTPUT_DIR/tasks_context.md"
cat > "$TASKS_OUTPUT" << 'EOF'
# Tasks Page - Backend Context

## Overview
Task management with assignments, completion tracking, and chore scheduling.

## Related Files:
EOF

extract_file "app/routers/tasks.py" "$TASKS_OUTPUT"
extract_file "app/schemas/task.py" "$TASKS_OUTPUT"
extract_file "app/models/task.py" "$TASKS_OUTPUT"

# Expenses Page Context
echo "💰 Extracting Expenses context..."
EXPENSES_OUTPUT="$OUTPUT_DIR/expenses_context.md"
cat > "$EXPENSES_OUTPUT" << 'EOF'
# Expenses Page - Backend Context

## Overview
Expense tracking, bill splitting, payment management, and financial reports.

## Related Files:
EOF

extract_file "app/routers/expenses.py" "$EXPENSES_OUTPUT"
extract_file "app/routers/bills.py" "$EXPENSES_OUTPUT"
extract_file "app/schemas/expense.py" "$EXPENSES_OUTPUT"
extract_file "app/schemas/bill.py" "$EXPENSES_OUTPUT"
extract_file "app/models/expense.py" "$EXPENSES_OUTPUT"
extract_file "app/models/bill.py" "$EXPENSES_OUTPUT"

# Communication Page Context
echo "💬 Extracting Communication context..."
COMMUNICATION_OUTPUT="$OUTPUT_DIR/communication_context.md"
cat > "$COMMUNICATION_OUTPUT" << 'EOF'
# Communication Page - Backend Context

## Overview
Announcements, polls, notifications, and household communication.

## Related Files:
EOF

extract_file "app/routers/communications.py" "$COMMUNICATION_OUTPUT"
extract_file "app/routers/notifications.py" "$COMMUNICATION_OUTPUT"
extract_file "app/schemas/announcement.py" "$COMMUNICATION_OUTPUT"
extract_file "app/schemas/poll.py" "$COMMUNICATION_OUTPUT"
extract_file "app/schemas/notification.py" "$COMMUNICATION_OUTPUT"
extract_file "app/models/announcement.py" "$COMMUNICATION_OUTPUT"
extract_file "app/models/poll.py" "$COMMUNICATION_OUTPUT"
extract_file "app/models/notification.py" "$COMMUNICATION_OUTPUT"

# House Page Context
echo "🏡 Extracting House context..."
HOUSE_OUTPUT="$OUTPUT_DIR/house_context.md"
cat > "$HOUSE_OUTPUT" << 'EOF'
# House Page - Backend Context

## Overview
Resource tracking (groceries, supplies), guest management, house rules, and settings.

## Related Files:
EOF

extract_file "app/routers/guests.py" "$HOUSE_OUTPUT"
extract_file "app/routers/shopping.py" "$HOUSE_OUTPUT"
extract_file "app/routers/households.py" "$HOUSE_OUTPUT"
extract_file "app/schemas/guest.py" "$HOUSE_OUTPUT"
extract_file "app/schemas/guest_approval.py" "$HOUSE_OUTPUT"
extract_file "app/schemas/shopping_list.py" "$HOUSE_OUTPUT"
extract_file "app/schemas/household.py" "$HOUSE_OUTPUT"
extract_file "app/models/guest.py" "$HOUSE_OUTPUT"
extract_file "app/models/guest_approval.py" "$HOUSE_OUTPUT"
extract_file "app/models/shopping_list.py" "$HOUSE_OUTPUT"
extract_file "app/models/household_membership.py" "$HOUSE_OUTPUT"


# Shared Context (used across multiple pages)
echo "🔄 Extracting Shared context..."
SHARED_OUTPUT="$OUTPUT_DIR/shared_context.md"
cat > "$SHARED_OUTPUT" << 'EOF'
# Shared Context - Backend Context

## Overview
Common models, enums, authentication, and utilities used across all pages.

## Related Files:
EOF

extract_file "app/routers/auth.py" "$SHARED_OUTPUT"
extract_file "app/models/enums.py" "$SHARED_OUTPUT"
extract_file "app/models/rsvp.py" "$SHARED_OUTPUT"
extract_file "app/models/event_approval.py" "$SHARED_OUTPUT"
extract_file "app/schemas/rsvp.py" "$SHARED_OUTPUT"
extract_file "app/schemas/event_approval.py" "$SHARED_OUTPUT"

# Generate Frontend Integration Guide
echo "📋 Generating integration guide..."
INTEGRATION_OUTPUT="$OUTPUT_DIR/integration_guide.md"
cat > "$INTEGRATION_OUTPUT" << 'EOF'
# Frontend Integration Guide

## Page to Context Mapping

### Dashboard Page
- **Context File:** `dashboard_context.md`
- **Key Endpoints:** Dashboard aggregation, household overview
- **Primary Models:** Household, User, Dashboard summary

### Calendar Page  
- **Context File:** `calendar_context.md`
- **Key Endpoints:** Events, Bills, User schedules
- **Primary Models:** Event, Bill, UserSchedule
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
EOF

echo "✅ Context extraction complete!"
echo "📁 Files generated in: $OUTPUT_DIR/"
echo ""
echo "Generated files:"
ls -la "$OUTPUT_DIR/"
echo ""
echo "🎯 Next: Share the relevant context file with your frontend AI developer for each page they're building."