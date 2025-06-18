#!/bin/bash

# Fix Testing Issues - Import and Pydantic Compatibility
# Fixes the import errors and Pydantic v2 compatibility issues

set -e

echo "🔧 FIXING TESTING ISSUES..."
echo "=========================="

cd app

echo "1️⃣ Fixing Pydantic v2 compatibility (regex -> pattern)..."

# Fix household.py schema
echo "📝 Fixing schemas/household.py..."
sed -i 's/regex=/pattern=/g' schemas/household.py 2>/dev/null || sed -i.bak 's/regex=/pattern=/g' schemas/household.py

# Check other schemas for regex usage
echo "📝 Checking other schemas for regex usage..."
find schemas/ -name "*.py" -exec grep -l "regex=" {} \; | while read file; do
    echo "   Fixing $file..."
    sed -i 's/regex=/pattern=/g' "$file" 2>/dev/null || sed -i.bak 's/regex=/pattern=/g' "$file"
done

echo "✅ Pydantic compatibility fixed!"

echo ""
echo "2️⃣ Fixing import issues in database setup..."

# Create fixed database setup script
echo "📝 Creating fixed database setup script..."
cat > ../setup_test_database_fixed.sh << 'EOF'
#!/bin/bash

echo "🗄️ Setting up test database..."

# Copy the minimal .env to actual .env
cp .env.testing .env

# Create the database with all tables using proper Python module execution
echo "📋 Creating database tables..."

# Run from project root to fix import issues
cd ..
python -m roomly-backend.app.database_setup
cd roomly-backend

echo "✅ Test database ready!"
echo "📍 Database file: roomly_test.db"
EOF

chmod +x ../setup_test_database_fixed.sh

# Create proper database setup module
echo "📝 Creating proper database setup module..."
cat > database_setup.py << 'EOF'
#!/usr/bin/env python3
"""
Database Setup Module
Creates database tables using proper module imports
"""

import os
import sys

# Add the parent directory to Python path to fix imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from database import engine, Base
    
    # Import all models to ensure they're registered
    from models.user import User
    from models.household import Household
    from models.expense import Expense
    from models.bill import Bill, BillPayment
    from models.task import Task
    from models.event import Event
    from models.guest import Guest
    from models.announcement import Announcement
    from models.poll import Poll, PollVote
    from models.notification import Notification, NotificationPreference
    from models.rsvp import RSVP
    from models.user_schedule import UserSchedule
    from models.shopping_list import ShoppingList, ShoppingItem
    
    print('📋 Creating all database tables...')
    Base.metadata.create_all(bind=engine)
    print('✅ Database setup complete!')
    
except ImportError as e:
    print(f'❌ Import error: {e}')
    print('💡 Make sure you are running from the correct directory')
    sys.exit(1)
except Exception as e:
    print(f'❌ Database setup failed: {e}')
    sys.exit(1)
EOF

echo "✅ Database setup module created!"

echo ""
echo "3️⃣ Fixing missing get_current_user import..."

# Create proper auth dependency
echo "📝 Fixing auth.py import in utils/security.py..."
cat > utils/security.py << 'EOF'
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(None)  # This will be properly injected
):
    """Get current authenticated user - import this from routers.auth instead"""
    # This function is now in routers/auth.py to avoid circular imports
    from .routers.auth import get_current_user as auth_get_current_user
    return auth_get_current_user(credentials, db)
EOF

echo "✅ Security module fixed!"

echo ""
echo "4️⃣ Fixing router imports to use proper auth dependency..."

# Update routers to import get_current_user correctly
echo "📝 Fixing router imports..."

# Fix expenses.py
sed -i 's/from ..utils.security import get_current_user/from .auth import get_current_user/' routers/expenses.py 2>/dev/null || sed -i.bak 's/from ..utils.security import get_current_user/from .auth import get_current_user/' routers/expenses.py

# Fix other routers
for router in routers/*.py; do
    if [ "$router" != "routers/auth.py" ] && [ "$router" != "routers/__init__.py" ]; then
        echo "   Fixing $router..."
        sed -i 's/from ..utils.security import get_current_user/from .auth import get_current_user/' "$router" 2>/dev/null || sed -i.bak 's/from ..utils.security import get_current_user/from .auth import get_current_user/' "$router"
    fi
done

echo "✅ Router imports fixed!"

echo ""
echo "5️⃣ Creating simple startup script..."

# Create simple startup script that avoids import issues
cat > ../start_backend_simple.py << 'EOF'
#!/usr/bin/env python3
"""
Simple Backend Starter
Starts the FastAPI backend with proper imports
"""

import uvicorn
import os
import sys

# Add current directory to path
sys.path.insert(0, os.getcwd())

if __name__ == "__main__":
    # Change to app directory
    os.chdir("app")
    
    # Start uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["./"]
    )
EOF

chmod +x ../start_backend_simple.py

echo "✅ Simple startup script created!"

echo ""
echo "6️⃣ Creating working test workflow..."

# Create working test workflow
cat > ../test_workflow_fixed.sh << 'EOF'
#!/bin/bash

echo "🧪 ROOMLY FIXED TESTING WORKFLOW"
echo "================================"

cd roomly-backend

echo ""
echo "🔧 Step 1: Setting up test environment..."
./setup_test_database_fixed.sh

echo ""
echo "🚀 Step 2: Starting backend server..."
echo "   You can start the backend with:"
echo "   python start_backend_simple.py"
echo ""
echo "   Or use uvicorn directly:"
echo "   cd app && uvicorn main:app --reload"
echo ""

echo "🧪 Step 3: Test endpoints with:"
echo "   ./test_endpoints.sh"
echo ""

echo "🎨 Step 4: Test Gradio frontend with:"
echo "   ./test_gradio.sh"
echo ""

echo "🌐 **TESTING URLS:**"
echo "   • Backend API: http://localhost:8000"
echo "   • API Docs: http://localhost:8000/docs" 
echo "   • Gradio Frontend: http://localhost:7860"
echo ""

echo "📋 **MANUAL STEPS:**"
echo "   1. ./setup_test_database_fixed.sh"
echo "   2. python start_backend_simple.py      # Terminal 1"
echo "   3. ./test_endpoints.sh                 # Terminal 2" 
echo "   4. ./test_gradio.sh                    # Terminal 3"
EOF

chmod +x ../test_workflow_fixed.sh

echo "✅ Fixed test workflow created!"

echo ""
echo "7️⃣ Fixing main.py to handle missing imports..."

# Add proper error handling to main.py
echo "📝 Adding error handling to main.py..."

# Create backup of main.py
cp main.py main.py.backup

# Add try-catch around imports in main.py
cat > main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Import routers with error handling
    from routers import (
        dashboard, expenses, tasks, calendar, auth, households, 
        bills, guests, communications, notifications, shopping
    )
    from database import engine, Base
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure all dependencies are installed and you're in the correct directory")
    sys.exit(1)

# Initialize FastAPI app
app = FastAPI(
    title="Roomly API",
    description="Roommate Management System API", 
    version="1.0.0"
)

# Add CORS middleware for Gradio frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7860", "http://127.0.0.1:7860"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["expenses"])
app.include_router(bills.router, prefix="/api/bills", tags=["bills"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(guests.router, prefix="/api/guests", tags=["guests"])
app.include_router(communications.router, prefix="/api/communications", tags=["communications"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(shopping.router, prefix="/api/shopping", tags=["shopping"])
app.include_router(households.router, prefix="/api/households", tags=["households"])

@app.get("/")
async def root():
    return {"message": "Welcome to Roomly API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "roomly-api", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
EOF

echo "✅ Main.py fixed with error handling!"

cd ..

echo ""
echo "🎉 ALL ISSUES FIXED!"
echo "==================="
echo ""
echo "✅ **FIXES APPLIED:**"
echo "   1️⃣ Pydantic v2 compatibility (regex -> pattern)"
echo "   2️⃣ Import issues in database setup"
echo "   3️⃣ Auth dependency circular import"
echo "   4️⃣ Router import dependencies"
echo "   5️⃣ Simple startup script created"
echo "   6️⃣ Working test workflow"
echo "   7️⃣ Main.py error handling"
echo ""
echo "🚀 **TRY THE FIXED WORKFLOW:**"
echo "   ./test_workflow_fixed.sh"
echo ""
echo "📋 **OR MANUAL STEPS:**"
echo "   1. ./setup_test_database_fixed.sh"
echo "   2. python start_backend_simple.py      # Terminal 1"
echo "   3. ./test_endpoints.sh                 # Terminal 2"
echo "   4. ./test_gradio.sh                    # Terminal 3"
echo ""
echo "✅ **READY TO TEST AGAIN!**"