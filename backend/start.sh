#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Check if Gemini API key is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "Warning: GEMINI_API_KEY environment variable not set."
    echo "The server will run with mock responses for testing."
    echo ""
fi

echo "Starting RStudio AI Backend..."
echo "Server will be available at: http://127.0.0.1:8000"
echo "API Documentation: http://127.0.0.1:8000/docs"
echo ""

# Start the server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload 