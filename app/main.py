from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .utils.background_tasks import start_background_tasks, stop_background_tasks
import atexit

try:
    # Import routers with proper module paths
    from . import routers
    from .database import engine, Base

    # Create database tables
    Base.metadata.create_all(bind=engine)

    print("✅ All imports successful!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure all dependencies are installed")
    raise

# Initialize FastAPI app
app = FastAPI(
    title="Roomly API", description="Roommate Management System API", version="1.0.0"
)

# Add CORS middleware for Gradio frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7860", "http://127.0.0.1:7860"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Start background tasks when app starts"""
    print("🚀 Starting Roomly API with background notification system...")
    start_background_tasks()


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks when app shuts down"""
    print("⏹️ Stopping background tasks...")
    stop_background_tasks()


# Include routers
app.include_router(routers.auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(
    routers.dashboard.router, prefix="/api/dashboard", tags=["dashboard"]
)
app.include_router(routers.expenses.router, prefix="/api/expenses", tags=["expenses"])
app.include_router(routers.event.router, prefix="/api/event", tags=["event"])
app.include_router(routers.bills.router, prefix="/api/bills", tags=["bills"])
app.include_router(routers.tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(routers.guests.router, prefix="/api/guests", tags=["guests"])
app.include_router(
    routers.communications.router, prefix="/api/communications", tags=["communications"]
)
app.include_router(
    routers.notifications.router, prefix="/api/notifications", tags=["notifications"]
)
app.include_router(routers.shopping.router, prefix="/api/shopping", tags=["shopping"])
app.include_router(
    routers.households.router, prefix="/api/households", tags=["households"]
)

atexit.register(stop_background_tasks)


@app.get("/")
async def root():
    return {"message": "Welcome to Roomly API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "roomly-api", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
