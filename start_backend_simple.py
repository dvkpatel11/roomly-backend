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
