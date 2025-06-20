#!/bin/bash

# Quick API Test Script
BASE_URL="http://localhost:8000/api"

echo "🚀 Starting API tests..."

# Test 1: Login
echo "📝 Testing login..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@test.com",
    "password": "password123"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
else
    echo "✅ Login successful"
fi

# Test 2: Dashboard
echo "📊 Testing dashboard..."
DASHBOARD_RESPONSE=$(curl -s -X GET "$BASE_URL/dashboard/" \
  -H "Authorization: Bearer $TOKEN")

if echo "$DASHBOARD_RESPONSE" | grep -q "dashboard"; then
    echo "✅ Dashboard working"
else
    echo "❌ Dashboard failed"
    echo "Response: $DASHBOARD_RESPONSE"
fi

# Test 3: Expenses
echo "💰 Testing expenses..."
EXPENSES_RESPONSE=$(curl -s -X GET "$BASE_URL/expenses/" \
  -H "Authorization: Bearer $TOKEN")

if echo "$EXPENSES_RESPONSE" | grep -q "expenses"; then
    echo "✅ Expenses working"
else
    echo "❌ Expenses failed"
    echo "Response: $EXPENSES_RESPONSE"
fi

# Test 4: Tasks
echo "✅ Testing tasks..."
TASKS_RESPONSE=$(curl -s -X GET "$BASE_URL/tasks/" \
  -H "Authorization: Bearer $TOKEN")

if echo "$TASKS_RESPONSE" | grep -q "tasks"; then
    echo "✅ Tasks working"
else
    echo "❌ Tasks failed"
    echo "Response: $TASKS_RESPONSE"
fi

# Test 5: Create new expense
echo "🆕 Testing expense creation..."
CREATE_EXPENSE_RESPONSE=$(curl -s -X POST "$BASE_URL/expenses/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "API Test Expense",
    "amount": 50.00,
    "category": "groceries",
    "split_method": "equal_split",
    "notes": "Testing expense creation via API"
  }')

if echo "$CREATE_EXPENSE_RESPONSE" | grep -q "expense"; then
    echo "✅ Expense creation working"
else
    echo "❌ Expense creation failed"
    echo "Response: $CREATE_EXPENSE_RESPONSE"
fi

# Test 6: Notifications
echo "🔔 Testing notifications..."
NOTIFICATIONS_RESPONSE=$(curl -s -X GET "$BASE_URL/notifications/" \
  -H "Authorization: Bearer $TOKEN")

if echo "$NOTIFICATIONS_RESPONSE" | grep -q "notifications"; then
    echo "✅ Notifications working"
else
    echo "❌ Notifications failed"
    echo "Response: $NOTIFICATIONS_RESPONSE"
fi

echo "🎉 API tests completed!"
echo ""
echo "💡 Next steps:"
echo "  - Test individual endpoints using the curl commands"
echo "  - Check the API documentation at http://localhost:8000/docs"
echo "  - Try creating, updating, and deleting resources"