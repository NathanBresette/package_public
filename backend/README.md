# RStudio AI Backend

A FastAPI backend that provides secure access to the Gemini API for RStudio users.

## Features

- Access code validation
- Secure proxy to Gemini API
- CORS support for RStudio integration
- Health check endpoint

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your Gemini API key:**
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key-here"
   ```

3. **Configure access codes:**
   Edit `main.py` and add your access codes to the `VALID_ACCESS_CODES` dictionary:
   ```python
   VALID_ACCESS_CODES = {
       "YOUR_CODE_1": "user1",
       "YOUR_CODE_2": "user2",
   }
   ```

## Running the Server

```bash
python start_server.py
```

Or directly with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

- `POST /validate` - Validate access code
- `POST /chat` - Send chat request to Gemini
- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger UI)

## Security Notes

- In production, set specific CORS origins instead of `allow_origins=["*"]`
- Store access codes securely (database, environment variables)
- Add rate limiting for production use
- Use HTTPS in production

## Testing

You can test the API using curl:

```bash
# Validate access code
curl -X POST "http://localhost:8000/validate" \
     -H "Content-Type: application/json" \
     -d '{"access_code": "DEMO123"}'

# Send chat request
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"access_code": "DEMO123", "prompt": "Hello, how are you?"}'
``` 