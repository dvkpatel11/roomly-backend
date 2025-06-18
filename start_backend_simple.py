#!/usr/bin/env python3
"""
Simple Backend Starter
Starts the FastAPI backend with proper imports
"""

import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure we're in the project root directory
    # (where this script is located)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Add project root to Python path
    sys.path.insert(0, script_dir)

    print(f"🚀 Starting Roomly API from: {script_dir}")
    print("📡 Server will be available at: http://localhost:8000")
    print("📄 API docs will be available at: http://localhost:8000/docs")

    # Start uvicorn with the app module
    uvicorn.run(
        "app.main:app",  # Note: app.main, not just main
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./app"],  # Only watch the app directory
    )
