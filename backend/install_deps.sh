#!/bin/bash

# Install vector database dependencies for RStudio AI Backend
echo "Installing vector database dependencies..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

echo "Vector database dependencies installed successfully!"
echo ""
echo "To start the backend with vector database support:"
echo "source venv/bin/activate && uvicorn main:app --host 127.0.0.1 --port 8001" 