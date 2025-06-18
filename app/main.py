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
