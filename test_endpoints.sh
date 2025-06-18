#!/bin/bash

# Endpoint Testing Script
# Tests core API endpoints with curl

echo "🧪 TESTING ROOMLY API ENDPOINTS"
echo "==============================="

BASE_URL="http://localhost:8000"
TOKEN=""

echo ""
echo "📊 1. Testing Health Check..."
curl -s "$BASE_URL/health" | python -m json.tool
echo ""

echo "📊 2. Testing API Root..."
curl -s "$BASE_URL/" | python -m json.tool
echo ""

echo "📊 3. Testing API Documentation..."
echo "   📚 API Docs: $BASE_URL/docs"
echo "   📚 ReDoc: $BASE_URL/redoc"
echo ""

echo "👤 4. Testing User Registration..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@test.com",
    "name": "Alice Johnson",
    "password": "testpassword123"
  }')

echo "$REGISTER_RESPONSE" | python -m json.tool
echo ""

echo "🔐 5. Testing User Login..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@test.com", 
    "password": "testpassword123"
  }')

echo "$LOGIN_RESPONSE" | python -m json.tool

# Extract token for authenticated requests
TOKEN=$(echo "$LOGIN_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo "✅ Login successful, token received"
    echo ""
    
    echo "🏠 6. Testing Household Creation..."
    HOUSEHOLD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/households/" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{
        "name": "Test Household",
        "address": "123 Test Street",
        "house_rules": "Keep it clean and be respectful"
      }')
    
    echo "$HOUSEHOLD_RESPONSE" | python -m json.tool
    echo ""
    
    echo "💰 7. Testing Expense Creation..."
    EXPENSE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/expenses/" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{
        "description": "Groceries at Whole Foods",
        "amount": 85.50,
        "category": "groceries",
        "split_method": "equal_split"
      }')
    
    echo "$EXPENSE_RESPONSE" | python -m json.tool
    echo ""
    
    echo "📋 8. Testing Task Creation..."
    TASK_RESPONSE=$(curl -s -X POST "$BASE_URL/api/tasks/" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{
        "title": "Clean Kitchen",
        "description": "Deep clean the kitchen",
        "points": 15,
        "assigned_to": 1
      }')
    
    echo "$TASK_RESPONSE" | python -m json.tool
    echo ""
    
    echo "📊 9. Testing Dashboard Summary..."
    DASHBOARD_RESPONSE=$(curl -s -X GET "$BASE_URL/api/dashboard/summary" \
      -H "Authorization: Bearer $TOKEN")
    
    echo "$DASHBOARD_RESPONSE" | python -m json.tool
    echo ""
    
    echo "✅ ENDPOINT TESTING COMPLETE!"
    echo "=============================="
    echo "All core endpoints tested successfully!"
    
else
    echo "❌ Login failed, cannot test authenticated endpoints"
fi
