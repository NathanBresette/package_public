
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Change to backend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Import and run the server
from main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8888)

