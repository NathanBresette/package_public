FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Debug: Show what's in the build context before copying
RUN echo "=== DEBUG: Build context before COPY ===" && pwd && ls -la

# Copy everything first to see what's in the build context
COPY . .

# Debug: List everything in build context to verify
RUN echo "=== DEBUG: ls -R /app ===" && ls -R /app

# Debug: Check if sqlite_rag.py exists
RUN echo "=== DEBUG: Check sqlite_rag.py ===" && ls -la /app/backend/sqlite_rag.py || echo "sqlite_rag.py not found!"

# Debug: Check Python path and try to import
RUN echo "=== DEBUG: Python path test ===" && python3 -c "import sys; print('Python path:', sys.path)" && python3 -c "import sqlite_rag; print('sqlite_rag imported successfully')" || echo "sqlite_rag import failed"

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install gunicorn uvicorn[standard]

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV PORT=8001
ENV DEPLOYMENT_MODE=production

# Change to backend directory
WORKDIR /app/backend

# Debug: Test import from backend directory
RUN echo "=== DEBUG: Testing import from /app/backend ===" && python3 -c "import sqlite_rag; print('sqlite_rag imported successfully from /app/backend')" || echo "sqlite_rag import failed from /app/backend"

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start the application
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8001"] 