# Add these imports to the top of main.py
from .utils.background_tasks import start_background_tasks, stop_background_tasks
import atexit

# Add this after creating the FastAPI app but before including routers
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

# Register shutdown handler for unexpected termination
atexit.register(stop_background_tasks)
