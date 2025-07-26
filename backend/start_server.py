#!/usr/bin/env python3
"""
Startup script for the RStudio AI Backend
"""
import os
import uvicorn
from main import app

if __name__ == "__main__":
    # Check if Gemini API key is set
    if not os.getenv("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY environment variable not set.")
        print("Please set it before starting the server:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        print()
    
    print("Starting RStudio AI Backend...")
    print("Server will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    ) 