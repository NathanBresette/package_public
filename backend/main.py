# Force rebuild: Fix WORKDIR and PYTHONPATH
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import os
from typing import Optional, List, Dict, AsyncGenerator
import json
from memory_only_context import memory_context
from context_summarizer import ContextSummarizer
from response_cache import SmartResponseCache
from conversation_memory import ConversationMemory
from stripe_billing import report_token_usage, calculate_token_cost
# from security_config import get_cors_config, ADMIN_ACCESS_CODE, get_security_headers
from config import get_user_manager
user_manager = get_user_manager()
import psutil
import gc
from datetime import datetime, timedelta
import stripe
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
import hashlib
import time
from psycopg2.extras import RealDictCursor
import jwt
from contextlib import asynccontextmanager
import re
import html


app = FastAPI(title="RStudio AI Backend", version="1.3.0")

# Initialize memory-only context, context summarizer, response cache, and conversation memory
context_summarizer = ContextSummarizer()
response_cache = SmartResponseCache(max_cache_size=200, cache_ttl_hours=4)  # Conservative settings for memory
conversation_memory = ConversationMemory()



# CORS middleware - allow all origins for RStudio add-in compatibility
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Security middleware for CSP headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Content Security Policy - strict CSP to prevent XSS
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://js.stripe.com https://checkout.stripe.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' http://localhost:* https://localhost:* http://127.0.0.1:* https://127.0.0.1:* https://api.stripe.com https://rgent.onrender.com https: http:; "
        "frame-src https://js.stripe.com https://checkout.stripe.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "upgrade-insecure-requests;"
    )
    
    response.headers["Content-Security-Policy"] = csp_policy
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response

# Pydantic models for request/response
class AccessCodeRequest(BaseModel):
    access_code: str

class ChatRequest(BaseModel):
    access_code: str
    prompt: str
    context_data: Optional[Dict] = None
    context_type: Optional[str] = "general"
    conversation_id: Optional[str] = None
    new_conversation: Optional[bool] = False

class ContextRequest(BaseModel):
    access_code: str
    context_data: Dict
    context_type: str = "general"

class ChatResponse(BaseModel):
    response: str
    retrieved_context: Optional[List[Dict]] = None
    context_summary: Optional[Dict] = None
    conversation_id: Optional[str] = None

class ContextResponse(BaseModel):
    success: bool
    message: str
    context_id: Optional[str] = None

class CreateUserRequest(BaseModel):
    access_code: str
    stripe_customer_id: str = ""
    daily_limit: int = 100
    monthly_budget: float = 10.0

class UpdateUserRequest(BaseModel):
    daily_limit: Optional[int] = None
    monthly_budget: Optional[float] = None
    rate_limit: Optional[int] = None
    notes: Optional[str] = None

class AdminActionRequest(BaseModel):
    admin_access_code: str

# Stripe Payment Models
class CreateCheckoutSessionRequest(BaseModel):
    plan_type: str  # 'free', 'pro', 'enterprise'
    plan_name: str
    price: int  # Price in cents
    requests: int
    customer_email: Optional[str] = None

class LookupKeyRequest(BaseModel):
    lookup_key: str  # For Pro plans: 'pro_haiku_monthly_base_v3' or 'pro_sonnet_monthly_base_v3'
    customer_email: Optional[str] = None

class PaymentSuccessRequest(BaseModel):
    session_id: str
    customer_email: str
    plan_type: str



class CreateAccountRequest(BaseModel):
    email: str
    plan_type: str

class CustomerPortalRequest(BaseModel):
    email: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# Configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    print("✅ Stripe configured successfully")
else:
    print("⚠️  STRIPE_SECRET_KEY not set. Payment features will be disabled.")

print("🚀 RStudio AI Backend v1.3.0 starting up...")

if not CLAUDE_API_KEY:
    print("Warning: CLAUDE_API_KEY not set. Set it as an environment variable.")
else:
    print(f"DEBUG: CLAUDE_API_KEY is set (length: {len(CLAUDE_API_KEY)})")
    print(f"DEBUG: CLAUDE_API_KEY preview: {CLAUDE_API_KEY[:10]}...")

def validate_access_code(access_code: str) -> bool:
    """Validate the access code using user manager"""
    is_valid, message = user_manager.validate_access(access_code)
    return is_valid

def track_usage(access_code: str, usage_info: dict = None):
    """Track usage for an access code using user manager"""
    if usage_info:
        print(f"DEBUG: Tracking usage for {access_code}")
        print(f"DEBUG: Usage info: {usage_info}")
        user_manager.record_usage(access_code, usage_info)

def get_usage_stats(access_code: str = None):
    """Get usage statistics using user manager"""
    if access_code:
        return user_manager.get_user_stats(access_code)
    return user_manager.get_all_users_summary()

def is_admin(admin_access_code: str) -> bool:
    """Check if the provided access code is an admin code"""
    # For now, use a simple admin code check
    # In production, this should be more secure
    ADMIN_ACCESS_CODE = os.getenv("ADMIN_ACCESS_CODE", "admin123")
    return admin_access_code == ADMIN_ACCESS_CODE

async def call_claude_api(prompt: str) -> tuple[str, dict]:
    """Call the Claude API with the given prompt"""
    if not CLAUDE_API_KEY:
        # Return a mock response for testing
        mock_response = f"""🤖 **Mock AI Response**

**Full Enhanced Prompt Received:**
```
{prompt}
```

This is a mock response since no Claude API key is configured. In production, this would be a real AI response from Anthropic's Claude API.

**To get real responses:**
1. Get a Claude API key from https://console.anthropic.com/
2. Set it as an environment variable: `export CLAUDE_API_KEY="your-key-here"`
3. Restart the backend server

**Features you can test:**
- ✅ Access code validation
- ✅ Context capture from RStudio
- ✅ UI interaction
- ✅ Code insertion into RStudio editor"""
        
        # Mock token usage for testing
        mock_usage = {
            "input_tokens": len(prompt.split()) * 1.3,
            "output_tokens": len(mock_response.split()) * 1.3,
            "total_tokens": len(prompt.split()) * 1.3 + len(mock_response.split()) * 1.3
        }
        
        return mock_response, mock_usage
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 2048,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    url = CLAUDE_API_URL
    print(f"DEBUG: call_claude_api - URL: {url}")
    print(f"DEBUG: call_claude_api - Data: {data}")
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"DEBUG: call_claude_api - Making request...")
            response = await client.post(url, headers=headers, json=data, timeout=60.0)
            print(f"DEBUG: call_claude_api - Response status: {response.status_code}")
            print(f"DEBUG: call_claude_api - Response headers: {dict(response.headers)}")
            response.raise_for_status()
            
            result = response.json()
            
            # Extract token usage from Claude API response
            usage_info = {}
            if "usage" in result:
                usage_info = {
                    "input_tokens": result["usage"].get("input_tokens", 0),
                    "output_tokens": result["usage"].get("output_tokens", 0),
                    "total_tokens": result["usage"].get("total_tokens", 0)
                }
            
            # Extract the response text from Claude API response
            if "content" in result and len(result["content"]) > 0:
                response_text = result["content"][0]["text"]
                return response_text, usage_info
            
            return "No response generated", usage_info
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error calling Claude API: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {e.response.text}")

async def stream_claude_api(prompt: str) -> AsyncGenerator[str, None]:
    """Stream response from Claude API with real-time chunks and retry logic for rate limits"""
    if not CLAUDE_API_KEY:
        print("DEBUG: No CLAUDE_API_KEY found, using mock response")
        # Return a mock streaming response for testing
        mock_response = f"""🤖 **Mock AI Response (Streaming)**

**Full Enhanced Prompt Received:**
```
{prompt}
```

This is a mock streaming response since no Claude API key is configured. In production, this would be a real AI response from Anthropic's Claude API streamed in real-time.

**Benefits of Streaming:**
- ✅ Real-time response delivery
- ✅ Lower memory usage (no buffering)
- ✅ Better user experience
- ✅ Immediate feedback

**Memory Optimization:**
- Traditional: Buffer entire response (200MB+ for long responses)
- Streaming: Only buffer current chunk (10-20MB max)
- Savings: 80-95% memory reduction
"""
        
        # Simulate streaming by yielding chunks
        words = mock_response.split()
        chunk_size = 5  # Words per chunk
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            yield chunk + " "
            # Simulate processing delay
            import asyncio
            await asyncio.sleep(0.1)
        
        return
    else:
        print(f"DEBUG: CLAUDE_API_KEY found (length: {len(CLAUDE_API_KEY)})")
    
    # Retry logic for rate limiting
    max_retries = 3
    base_delay = 1.0  # Start with 1 second delay
    
    for attempt in range(max_retries):
        try:
            # Debug: Log the prompt being sent
            print(f"DEBUG: Sending prompt to Claude API (attempt {attempt + 1}/{max_retries}, length: {len(prompt)})")
            print(f"DEBUG: Prompt preview: {prompt[:200]}...")
            
            # Prepare the request payload for Claude streaming
            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 2048,
                "temperature": 0.7,
                "stream": True,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            print(f"DEBUG: Payload structure: {json.dumps(payload, indent=2)[:500]}...")
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01"
            }
            
            # Make streaming request to Claude API
            url = CLAUDE_API_URL
            print(f"DEBUG: Making request to Claude API: {url}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:  # 60 second timeout
                try:
                    async with client.stream("POST", url, json=payload, headers=headers) as response:
                        print(f"DEBUG: Claude API response status: {response.status_code}")
                        print(f"DEBUG: Claude API response headers: {dict(response.headers)}")
                        print(f"DEBUG: Response content-type: {response.headers.get('content-type', 'unknown')}")
                        
                        # Handle rate limiting with retry
                        if response.status_code == 429:
                            retry_after = response.headers.get('Retry-After', base_delay * (2 ** attempt))
                            delay = float(retry_after) if retry_after.isdigit() else base_delay * (2 ** attempt)
                            
                            if attempt < max_retries - 1:
                                print(f"DEBUG: Rate limited (429), retrying in {delay} seconds...")
                                yield f"Rate limited by Claude API. Retrying in {delay:.1f} seconds... "
                                import asyncio
                                await asyncio.sleep(delay)
                                continue
                            else:
                                yield f"Rate limited by Claude API after {max_retries} attempts. Please try again later."
                                return
                        
                        response.raise_for_status()
                        
                        # Check if response is actually streaming
                        content_type = response.headers.get('content-type', '')
                        if 'text/event-stream' not in content_type:
                            print(f"DEBUG: Response is not streaming, content-type: {content_type}")
                            print(f"DEBUG: Response status: {response.status_code}")
                            print(f"DEBUG: Response headers: {dict(response.headers)}")
                            
                            # Try to read the response to see what error we're getting
                            try:
                                # For streaming responses, we need to read the content differently
                                error_response = await response.aread()
                                error_text = error_response.decode('utf-8')
                                print(f"DEBUG: Non-streaming response content: {error_text}")
                                print(f"DEBUG: Full error response length: {len(error_text)}")
                                yield f"Error: Expected streaming response but got: {content_type}. Response: {error_text}"
                            except Exception as e:
                                yield f"Error: Expected streaming response but got: {content_type}. Could not read response: {str(e)}"
                            return
                        
                        # Process Server-Sent Events (SSE) from Claude API
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[len("data: "):])
                                    # Claude's SSE format is different from Gemini
                                    if data.get("type") == "content_block_delta":
                                        text_chunk = data.get("delta", {}).get("text", "")
                                        if text_chunk:
                                            print(f"DEBUG: Yielding text chunk: {text_chunk[:50]}...")
                                            yield text_chunk
                                except Exception as e:
                                    print(f"Error parsing line: {e}")
                                    continue
                        
                        # If we get here, the request was successful
                        return
                        
                except httpx.RequestError as e:
                    error_msg = f"Request error to Claude API: {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    print(f"DEBUG: Request error type: {type(e)}")
                    print(f"DEBUG: Request error details: {e}")
                    
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"DEBUG: Request error, retrying in {delay} seconds...")
                        yield f"Connection error. Retrying in {delay:.1f} seconds... "
                        import asyncio
                        await asyncio.sleep(delay)
                        continue
                    else:
                        yield error_msg
                        return
        
        except httpx.HTTPStatusError as e:
            error_msg = f"Error streaming from Claude API: {e.response.status_code} {e.response.reason_phrase}"
            print(error_msg)
            print(f"Response headers: {dict(e.response.headers)}")
            print(f"Request URL: {e.request.url}")
            print(f"Request headers: {dict(e.request.headers)}")
            
            # Handle rate limiting with retry
            if e.response.status_code == 429:
                retry_after = e.response.headers.get('Retry-After', base_delay * (2 ** attempt))
                delay = float(retry_after) if retry_after.isdigit() else base_delay * (2 ** attempt)
                
                if attempt < max_retries - 1:
                    print(f"DEBUG: Rate limited (429), retrying in {delay} seconds...")
                    yield f"Rate limited by Claude API. Retrying in {delay:.1f} seconds... "
                    import asyncio
                    await asyncio.sleep(delay)
                    continue
                else:
                    yield f"Rate limited by Claude API after {max_retries} attempts. Please try again later."
                    return
            
            # Don't call e.response.text() as it can lock the stream
            yield error_msg
            return
        
        except Exception as e:
            error_msg = f"Error streaming from Claude API: {str(e)}"
            print(error_msg)
            
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"DEBUG: General error, retrying in {delay} seconds...")
                yield f"Unexpected error. Retrying in {delay:.1f} seconds... "
                import asyncio
                await asyncio.sleep(delay)
                continue
            else:
                yield error_msg
                return
    
    # If we get here, all retries failed
    yield "All retry attempts failed. Please try again later."
    print("DEBUG: Stream function completed - all retries failed")

@app.post("/validate")
async def validate_access(request: AccessCodeRequest):
    """Validate an access code"""
    is_valid, message = user_manager.validate_access(request.access_code)
    if is_valid:
        return {"valid": True, "message": "Access granted"}
    else:
        raise HTTPException(status_code=401, detail=message)

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """Chat with AI using RAG-enhanced prompt with context summarization, smart caching, and conversation memory"""
    # Validate access code
    is_valid, message = user_manager.validate_access(request.access_code)
    if not is_valid:
        raise HTTPException(status_code=401, detail=message)
    
    # Sanitize user input to prevent XSS
    sanitized_prompt = sanitize_input(request.prompt)
    if not sanitized_prompt:
        raise HTTPException(status_code=400, detail="Invalid prompt")
    
    # Handle conversation memory
    conversation_id = request.conversation_id
    
    # Start new conversation if requested or if no conversation exists
    if request.new_conversation or not conversation_id:
        conversation_id = conversation_memory.start_conversation(request.access_code)
        if not conversation_id:
            raise HTTPException(status_code=500, detail="Failed to start conversation")
    
    # Get conversation history for context
    conversation_context = conversation_memory.format_conversation_context(conversation_id, max_messages=5)
    
    # Debug: Log the request structure
    print(f"DEBUG: Request context_data type: {type(request.context_data)}")
    if request.context_data:
        print(f"DEBUG: Context data keys: {list(request.context_data.keys()) if isinstance(request.context_data, dict) else 'Not a dict'}")
        for key, value in request.context_data.items() if isinstance(request.context_data, dict) else []:
            print(f"DEBUG: {key}: {type(value)} = {str(value)[:100]}...")
    
    try:
        # Check for cached response first (but only if no conversation history to avoid stale responses)
        if not conversation_context.strip():
            cached_response = response_cache.get(request.prompt, request.context_data)
            if cached_response:
                # Return cached response with metadata
                return ChatResponse(
                    response=cached_response['response'],
                    retrieved_context=[],
                    context_summary={"cached_response": True, "cache_age": cached_response['cache_age']}
                )
        
        # Create context summary for storage and processing
        context_summary = None
        if request.context_data:
            context_summary = context_summarizer.summarize_context(request.context_data)
            
            # Store summarized context instead of full context
            # context_id = sqlite_rag.store_context(
            #     request.access_code, 
            #     context_summary,  # Store summary instead of full context
            #     request.context_type
            # )
        
        # Retrieve relevant context from memory-only processing (no persistent data)
        retrieved_contexts = memory_context.get_session_contexts(request.access_code)
        
        # Get context summary for response
        context_summary_response = memory_context.get_user_context_summary(request.access_code)
        
        # Build enhanced prompt with summarized context
        enhanced_prompt = sanitized_prompt
        
        # Include summarized current context if provided
        current_context_text = ""
        if context_summary:
            current_context_text = "\n\n=== CURRENT ENVIRONMENT SUMMARY ===\n"
            # Ensure context_summary is a dictionary
            if isinstance(context_summary, dict):
                for key, value in context_summary.items():
                    if key != "timestamp":
                        current_context_text += f"\n{key}:\n{value}\n"
            else:
                # If it's a string, just include it directly
                current_context_text += f"\n{context_summary}\n"
        
        # Add retrieved historical context if available (truncated)
        retrieved_context_text = ""
        if retrieved_contexts:
            retrieved_context_text = "\n\n=== RELEVANT HISTORICAL CONTEXT ===\n"
            for i, ctx in enumerate(retrieved_contexts, 1):
                retrieved_context_text += f"\n--- Context {i} ({ctx['type']}) ---\n"
                if isinstance(ctx['content'], dict):
                    # Format context data nicely (truncated)
                    for key, value in ctx['content'].items():
                        if key != "text":
                            if isinstance(value, str) and len(value) > 500:
                                value = value[:500] + "... [truncated]"
                            retrieved_context_text += f"{key}: {value}\n"
                    if "text" in ctx['content']:
                        text = ctx['content']['text']
                        if isinstance(text, str) and len(text) > 1000:
                            text = text[:1000] + "... [truncated]"
                        retrieved_context_text += f"Content: {text}\n"
                else:
                    content = ctx['content']
                    if isinstance(content, str) and len(content) > 1000:
                        content = content[:1000] + "... [truncated]"
                    retrieved_context_text += f"Content: {content}\n"
        
        # Combine all context including conversation history
        context_parts = []
        if current_context_text:
            context_parts.append(current_context_text)
        if retrieved_context_text:
            context_parts.append(retrieved_context_text)
        if conversation_context:
            context_parts.append(conversation_context)
        
        if context_parts:
            enhanced_prompt = "\n".join(context_parts) + "\n\n=== USER QUERY ===\n" + request.prompt
        
        # Call Claude API with enhanced prompt
        response, usage_info = await call_claude_api(enhanced_prompt)
        
        # Store messages in conversation memory
        conversation_memory.add_message(conversation_id, "user", request.prompt, request.context_data, request.context_type)
        conversation_memory.add_message(conversation_id, "assistant", response, request.context_data, request.context_type)
        
        # Cache the response if appropriate (only for non-conversational queries)
        if request.context_data and not conversation_context.strip():
            response_cache.set(request.prompt, request.context_data, response)
        
        # Calculate cost (approximate - adjust based on actual Gemini pricing)
        cost_per_1k_tokens = 0.001  # Adjust this based on actual pricing
        total_tokens = usage_info.get('total_tokens', 0)
        cost = (total_tokens / 1000) * cost_per_1k_tokens
        
        # Track usage with cost
        track_usage(request.access_code, {
            "request_type": "chat",
            "total_tokens": total_tokens,
            "input_tokens": usage_info.get('input_tokens', 0),
            "output_tokens": usage_info.get('output_tokens', 0),
            "cost": cost,
            "prompt_length": len(request.prompt),
            "response_length": len(response),
            "success": True,
            "context_summarized": context_summary is not None,
            "cached": False
        })
        
        # Report token usage to Stripe for billing (if customer has subscription)
        try:
            # Get user to find Stripe customer ID
            user = user_manager.get_user_by_access_code(request.access_code)
            if user and user.stripe_customer_id:
                input_tokens = usage_info.get('input_tokens', 0)
                output_tokens = usage_info.get('output_tokens', 0)
                
                # Report usage to Stripe
                report_token_usage(
                    user.stripe_customer_id,
                    input_tokens,
                    output_tokens
                )
        except Exception as e:
            print(f"Error reporting token usage to Stripe: {e}")
            # Don't fail the request if billing fails
        
        # Get context summary for response
        # context_summary_response = sqlite_rag.get_user_context_summary(request.access_code)
        
        # Force garbage collection after processing
        gc.collect()
        
        return ChatResponse(
            response=response,
            retrieved_context=retrieved_contexts,
            context_summary=context_summary_response,
            conversation_id=conversation_id
        )
    except Exception as e:
        # Force garbage collection on error
        gc.collect()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
async def chat_with_ai_stream(request: ChatRequest):
    """Stream chat with AI using RAG-enhanced prompt with real-time responses and conversation memory"""
    # Validate access code
    is_valid, message = user_manager.validate_access(request.access_code)
    if not is_valid:
        raise HTTPException(status_code=401, detail=message)
    
    # Handle conversation memory
    conversation_id = request.conversation_id
    
    # Start new conversation if requested or if no conversation exists
    if request.new_conversation or not conversation_id:
        conversation_id = conversation_memory.start_conversation(request.access_code)
        if not conversation_id:
            raise HTTPException(status_code=500, detail="Failed to start conversation")
    
    # Get conversation history for context
    conversation_context = conversation_memory.format_conversation_context(conversation_id, max_messages=5)
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        print(f"DEBUG: Starting stream generation for conversation {conversation_id}")
        try:
            # Check for cached response first (but only if no conversation history to avoid stale responses)
            if not conversation_context.strip():
                cached_response = response_cache.get(request.prompt, request.context_data)
                if cached_response:
                    # Return cached response as a single chunk
                    yield f"data: {json.dumps({'chunk': cached_response['response'], 'cached': True, 'done': True, 'conversation_id': conversation_id})}\n\n"
                    return
            
            # Create context summary for storage and processing
            context_summary = None
            if request.context_data:
                context_summary = context_summarizer.summarize_context(request.context_data)
                
                # Store summarized context instead of full context
                # context_id = sqlite_rag.store_context(
                #     request.access_code, 
                #     context_summary,  # Store summary instead of full context
                #     request.context_type
                # )
            
            # Retrieve relevant context from memory-only processing (no persistent data)
            retrieved_contexts = memory_context.get_session_contexts(request.access_code)
            
            # Build enhanced prompt with summarized context
            enhanced_prompt = request.prompt
            
            # Include summarized current context if provided
            current_context_text = ""
            if context_summary:
                current_context_text = "\n\n=== CURRENT ENVIRONMENT SUMMARY ===\n"
                for key, value in context_summary.items():
                    if key != "timestamp":
                        current_context_text += f"\n{key}:\n{value}\n"
            
            # Add retrieved historical context if available (truncated)
            retrieved_context_text = ""
            if retrieved_contexts:
                retrieved_context_text = "\n\n=== RELEVANT HISTORICAL CONTEXT ===\n"
                for i, ctx in enumerate(retrieved_contexts, 1):
                    retrieved_context_text += f"\n--- Context {i} ({ctx['type']}) ---\n"
                    if isinstance(ctx['content'], dict):
                        # Format context data nicely (truncated)
                        for key, value in ctx['content'].items():
                            if key != "text":
                                if isinstance(value, str) and len(value) > 500:
                                    value = value[:500] + "... [truncated]"
                                retrieved_context_text += f"{key}: {value}\n"
                        if "text" in ctx['content']:
                            text = ctx['content']['text']
                            if isinstance(text, str) and len(text) > 1000:
                                text = text[:1000] + "... [truncated]"
                            retrieved_context_text += f"Content: {text}\n"
                    else:
                        content = ctx['content']
                        if isinstance(content, str) and len(content) > 1000:
                            content = content[:1000] + "... [truncated]"
                        retrieved_context_text += f"Content: {content}\n"
            
            # Combine all context including conversation history
            context_parts = []
            if current_context_text:
                context_parts.append(current_context_text)
            if retrieved_context_text:
                context_parts.append(retrieved_context_text)
            if conversation_context:
                context_parts.append(conversation_context)
            
            if context_parts:
                enhanced_prompt = "\n".join(context_parts) + "\n\n=== USER QUERY ===\n" + request.prompt
            
            # Stream response from Gemini API
            print(f"DEBUG: About to start streaming from Gemini API - UPDATED")
            full_response = ""
            total_tokens = 0
            input_tokens = len(enhanced_prompt.split()) * 1.3  # Approximate input token count
            output_tokens = 0
            
            async for chunk in stream_claude_api(enhanced_prompt):
                full_response += chunk
                output_tokens += len(chunk.split())  # Approximate token count
                
                # Send chunk to client immediately
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'chunk': '', 'done': True, 'total_tokens': input_tokens + output_tokens, 'conversation_id': conversation_id})}\n\n"
            
            # Store messages in conversation memory
            conversation_memory.add_message(conversation_id, "user", request.prompt, request.context_data, request.context_type)
            conversation_memory.add_message(conversation_id, "assistant", full_response, request.context_data, request.context_type)
            
            # Cache the response if appropriate (only for non-conversational queries)
            if request.context_data and not conversation_context.strip():
                response_cache.set(request.prompt, request.context_data, full_response)
            
            # Calculate cost (approximate - adjust based on actual Gemini pricing)
            cost_per_1k_tokens = 0.001  # Adjust this based on actual pricing
            total_tokens = input_tokens + output_tokens
            cost = (total_tokens / 1000) * cost_per_1k_tokens
            
            # Track usage with cost
            usage_data = {
                "request_type": "chat_stream",
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "prompt_length": len(request.prompt),
                "response_length": len(full_response),
                "success": True,
                "context_summarized": context_summary is not None,
                "cached": False,
                "streamed": True
            }
            print(f"DEBUG: Streaming - Tracking usage for {request.access_code}")
            print(f"DEBUG: Streaming - Usage data: {usage_data}")
            track_usage(request.access_code, usage_data)
            
            # Force garbage collection after processing
            gc.collect()
            
        except Exception as e:
            # Send error as chunk
            error_msg = f"Error: {str(e)}"
            yield f"data: {json.dumps({'chunk': error_msg, 'error': True, 'done': True})}\n\n"
            # Force garbage collection on error
            gc.collect()
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )

@app.get("/health")
async def health_check():
    """Health check endpoint with memory info"""
    # Get memory usage
    memory = psutil.virtual_memory()
    memory_info = {
        "total_gb": round(memory.total / (1024**3), 2),
        "available_gb": round(memory.available / (1024**3), 2),
        "used_gb": round(memory.used / (1024**3), 2),
        "percent_used": memory.percent
    }
    
    return {
        "status": "healthy",
        "memory": memory_info,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/cache/stats")
async def get_cache_stats():
    """Get response cache statistics"""
    try:
        return response_cache.get_cache_stats()
    except Exception as e:
        return {"error": str(e)}

@app.post("/cache/clear")
async def clear_cache():
    """Clear the response cache"""
    try:
        response_cache.clear_cache()
        return {"success": True, "message": "Cache cleared successfully"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/memory")
async def memory_status():
    """Get detailed memory status"""
    try:
        # Get system memory info
        memory = psutil.virtual_memory()
        memory_info = {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent_used": memory.percent,
            "free_gb": round(memory.free / (1024**3), 2)
        }
        
        # Get process memory info
        process = psutil.Process()
        process_memory = process.memory_info()
        process_info = {
            "rss_gb": round(process_memory.rss / (1024**3), 2),
            "vms_gb": round(process_memory.vms / (1024**3), 2)
        }
        
        # Get vector database stats
        # try:
        #     db_stats = sqlite_rag.get_database_stats()
        #     total_contexts = db_stats.get("total_contexts", "Error getting count")
        # except:
        #     total_contexts = "Error getting count"
        
        # Get cache stats
        cache_stats = response_cache.get_cache_stats()
        
        return {
            "system_memory": memory_info,
            "process_memory": process_info,
            # "sqlite_db_stats": db_stats if 'db_stats' in locals() else {"error": "Could not get database stats"},
            "cache_stats": cache_stats,
            # "memory_limits": {
            #     "max_contexts_per_user": sqlite_rag.max_contexts_per_user,
            #     "max_total_contexts": sqlite_rag.max_total_contexts,
            #     "max_context_age_days": sqlite_rag.max_context_age_days
            # }
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/cleanup")
async def cleanup_memory():
    """Force memory cleanup"""
    try:
        # Force garbage collection
        collected = gc.collect()
        
        # Clean up old SQLite database data
        # sqlite_rag._cleanup_old_data()
        
        # Get memory status after cleanup
        memory = psutil.virtual_memory()
        
        return {
            "success": True,
            "garbage_collected": collected,
            "memory_after_cleanup": {
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent
            }
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/usage")
async def get_usage(access_code: str):
    """Get usage statistics for a specific user"""
    is_valid, message = user_manager.validate_access(access_code)
    if not is_valid:
        raise HTTPException(status_code=401, detail=message)
    
    stats = get_usage_stats(access_code)
    print(f"DEBUG: /usage endpoint returning stats: {stats}")
    return stats

@app.get("/usage/{access_code}")
async def get_user_usage(access_code: str):
    """Get usage statistics for a specific access code"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    return get_usage_stats(access_code)

@app.post("/context/store", response_model=ContextResponse)
async def store_context(request: ContextRequest):
    """Store context data using memory-only processing - NO persistent storage"""
    try:
        # Process context in memory only - NO persistent storage
        context_hash = memory_context.process_context(
            request.access_code,
            request.context_data,
            request.context_type
        )
        
        if context_hash:
            return ContextResponse(
                success=True,
                message="Context processed in memory (no persistent storage)",
                context_id=context_hash
            )
        else:
            return ContextResponse(
                success=False,
                message="Failed to process context"
            )
    except Exception as e:
        return ContextResponse(
            success=False,
            message=f"Context processing error: {str(e)}"
        )

@app.get("/context/summary/{access_code}")
async def get_context_summary(access_code: str):
    """Get user context summary using memory-only processing"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    try:
        summary = memory_context.get_user_context_summary(access_code)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/context/clear/{access_code}")
async def clear_user_context(access_code: str):
    """Clear user context using memory-only processing"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    try:
        memory_context.clear_session(access_code)
        return {"success": True, "message": "Context cleared from memory"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context/analytics/{access_code}")
async def get_user_analytics(access_code: str):
    """Get user context analytics using memory-only processing"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    try:
        analytics = memory_context.get_session_stats(access_code)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context/search/{access_code}")
async def search_user_context(access_code: str, q: str, context_type: str = None):
    """Search user context using memory-only processing"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    try:
        # For memory-only context, return session info instead of search results
        session_stats = memory_context.get_session_stats(access_code)
        return {
            "access_code": access_code,
            "search_term": q,
            "context_type_filter": context_type,
            "message": "Memory-only context processing - no persistent search available",
            "session_stats": session_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Conversation management endpoints
@app.get("/conversations/{access_code}")
async def get_user_conversations(access_code: str):
    """Get all conversations for a user"""
    try:
        # Validate access code
        is_valid, message = user_manager.validate_access(access_code)
        if not is_valid:
            raise HTTPException(status_code=401, detail=message)
        
        conversations = conversation_memory.get_user_conversations(access_code)
        return {"conversations": conversations}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{access_code}/active")
async def get_active_conversation(access_code: str):
    """Get the active conversation for a user"""
    try:
        # Validate access code
        is_valid, message = user_manager.validate_access(access_code)
        if not is_valid:
            raise HTTPException(status_code=401, detail=message)
        
        conversation_id = conversation_memory.get_active_conversation(access_code)
        if conversation_id:
            history = conversation_memory.get_conversation_history(conversation_id)
            return {"conversation_id": conversation_id, "history": history}
        else:
            return {"conversation_id": None, "history": []}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, access_code: str):
    """Delete a conversation"""
    try:
        # Validate access code
        is_valid, message = user_manager.validate_access(access_code)
        if not is_valid:
            raise HTTPException(status_code=401, detail=message)
        
        success = conversation_memory.delete_conversation(conversation_id)
        if success:
            return {"success": True, "message": "Conversation deleted"}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversations/{conversation_id}/clear")
async def clear_conversation(conversation_id: str, access_code: str):
    """Clear all messages from a conversation"""
    try:
        # Validate access code
        is_valid, message = user_manager.validate_access(access_code)
        if not is_valid:
            raise HTTPException(status_code=401, detail=message)
        
        success = conversation_memory.clear_conversation(conversation_id)
        if success:
            return {"success": True, "message": "Conversation cleared"}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/list")
async def list_users(admin_access_code: str):
    """List all users with their context summaries (Admin only)"""
    # Admin access code validation
    if not is_admin(admin_access_code):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    try:
        users = user_manager.get_all_users_summary()
        return {"users": users, "total_users": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/create")
async def create_user(request: CreateUserRequest, admin_request: AdminActionRequest):
    """Create a new user (Admin only)"""
    if not is_admin(admin_request.admin_access_code):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    try:
        success = user_manager.create_user(
            access_code=request.access_code,
            stripe_customer_id=request.stripe_customer_id,
            daily_limit=request.daily_limit,
            monthly_budget=request.monthly_budget
        )
        
        if success:
            return {"success": True, "message": f"User {request.access_code} created successfully"}
        else:
            return {"success": False, "message": "User already exists"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/users/{access_code}")
async def update_user(access_code: str, request: UpdateUserRequest, admin_request: AdminActionRequest):
    """Update user settings (Admin only)"""
    if not is_admin(admin_request.admin_access_code):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    try:
        updates = {k: v for k, v in request.dict().items() if v is not None}
        success = user_manager.update_user(access_code, updates)
        
        if success:
            return {"success": True, "message": f"User {access_code} updated successfully"}
        else:
            return {"success": False, "message": "User not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/{access_code}/disable")
async def disable_user(access_code: str, admin_request: AdminActionRequest):
    """Disable user access (Admin only)"""
    if not is_admin(admin_request.admin_access_code):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    try:
        success = user_manager.disable_user(access_code)
        
        if success:
            return {"success": True, "message": f"User {access_code} disabled successfully"}
        else:
            return {"success": False, "message": "User not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/{access_code}/enable")
async def enable_user(access_code: str, admin_request: AdminActionRequest):
    """Enable user access (Admin only)"""
    if not is_admin(admin_request.admin_access_code):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    try:
        success = user_manager.enable_user(access_code)
        
        if success:
            return {"success": True, "message": f"User {access_code} enabled successfully"}
        else:
            return {"success": False, "message": "User not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/users/{access_code}")
async def delete_user(access_code: str, admin_request: AdminActionRequest):
    """Delete user and all their data (Admin only)"""
    if not is_admin(admin_request.admin_access_code):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    try:
        success = user_manager.delete_user(access_code)
        
        if success:
            return {"success": True, "message": f"User {access_code} deleted successfully"}
        else:
            return {"success": False, "message": "User not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/analytics")
async def get_admin_analytics(admin_access_code: str, days: int = 30):
    """Get system-wide analytics (Admin only)"""
    if not is_admin(admin_access_code):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    try:
        analytics = user_manager.get_usage_analytics(days=days)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream/test")
async def test_streaming():
    """Test streaming endpoint"""
    async def generate_test_stream() -> AsyncGenerator[str, None]:
        test_data = [
            "This is a test of streaming responses.",
            "Each chunk is sent immediately to the client.",
            "This provides real-time feedback to users.",
            "Memory usage stays low because we don't buffer the entire response.",
            "Streaming is much more efficient than traditional buffering.",
            "Test complete!"
        ]
        
        for i, chunk in enumerate(test_data):
            yield f"data: {json.dumps({'chunk': chunk, 'chunk_number': i + 1, 'done': False})}\n\n"
            import asyncio
            await asyncio.sleep(0.5)  # Simulate processing delay
        
        yield f"data: {json.dumps({'chunk': '', 'done': True, 'total_chunks': len(test_data)})}\n\n"
    
    return StreamingResponse(
        generate_test_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.get("/api/test")
async def test_api_key():
    """Test if Claude API key is working with basic request"""
    print(f"DEBUG: API test called, CLAUDE_API_KEY length: {len(CLAUDE_API_KEY) if CLAUDE_API_KEY else 0}")
    
    if not CLAUDE_API_KEY:
        return {"status": "error", "message": "No CLAUDE_API_KEY configured"}
    
    try:
        # Test with a simple non-streaming request
        test_prompt = "Say hello in one word"
        print(f"DEBUG: Testing basic API call with prompt: {test_prompt}")
        response, _ = await call_claude_api(test_prompt)
        print(f"DEBUG: Basic API call returned: {response[:50]}...")
        return {
            "status": "success", 
            "message": "API key is working",
            "response": response[:100] + "..." if len(response) > 100 else response
        }
    except Exception as e:
        print(f"DEBUG: Basic API test failed: {str(e)}")
        return {"status": "error", "message": f"API test failed: {str(e)}"}

@app.get("/api/test/stream")
async def test_streaming_api():
    """Test streaming API specifically"""
    print(f"DEBUG: Streaming API test called, GEMINI_API_KEY length: {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0}")
    
    if not GEMINI_API_KEY:
        return {"status": "error", "message": "No GEMINI_API_KEY configured"}
    
    async def test_stream():
        try:
            test_prompt = "Say hello in one word"
            print(f"DEBUG: Testing streaming with prompt: {test_prompt}")
            
            async for chunk in stream_gemini_api(test_prompt):
                print(f"DEBUG: Got streaming chunk: {chunk[:50]}...")
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
            
            yield f"data: {json.dumps({'chunk': '', 'done': True})}\n\n"
            
        except Exception as e:
            error_msg = f"Streaming test failed: {str(e)}"
            print(f"DEBUG: {error_msg}")
            yield f"data: {json.dumps({'chunk': error_msg, 'error': True, 'done': True})}\n\n"
    
    return StreamingResponse(
        test_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )

# Stripe Payment Endpoints
@app.post("/api/create-checkout-session")
async def create_checkout_session(request: CreateCheckoutSessionRequest):
    """Create a Stripe checkout session for payment"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # For free plan, generate access code immediately
        if request.plan_type == "free":
            access_code = user_manager.generate_access_code()
            user_manager.create_user(
                access_code=access_code,
                stripe_customer_id="",  # Free users don't have Stripe customer ID initially
                daily_limit=50,
                monthly_budget=0.0
            )
            return {
                "success": True,
                "access_code": access_code,
                "plan_type": "free",
                "message": "Free plan activated successfully"
            }
        
        # For paid plans, create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': request.plan_name,
                        'description': f'RgentAI {request.plan_name} Plan - {request.requests} requests per month'
                    },
                    'unit_amount': request.price,
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://rgentai.com/success.html?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://rgentai.com/plans?cancelled=true',
            metadata={
                'plan_type': request.plan_type,
                'requests': str(request.requests),
                'customer_email': request.customer_email or ''
            }
        )
        
        return {"id": checkout_session.id}
        
    except Exception as e:
        print(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment setup failed: {str(e)}")

@app.post("/api/create-stripe-checkout")
async def create_stripe_checkout(request: LookupKeyRequest):
    """Create a Stripe checkout session using lookup keys (for Pro plans)"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Get the price from lookup key
        prices = stripe.Price.list(
            lookup_keys=[request.lookup_key],
            expand=['data.product']
        )
        
        if not prices.data:
            raise HTTPException(status_code=400, detail=f"Price not found for lookup key: {request.lookup_key}")
        
        # Check if this is a free trial
        is_free_trial = request.lookup_key == 'free_trial_monthly_v3'
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                'price': prices.data[0].id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://rgentai.com/success.html?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://rgentai.com/plans?cancelled=true',
            metadata={
                'lookup_key': request.lookup_key,
                'customer_email': request.customer_email or ''
            },
            # For free trial, add trial period
            subscription_data={
                'trial_period_days': 7 if is_free_trial else None,
                'metadata': {
                    'plan_type': 'free_trial' if is_free_trial else 'paid'
                }
            } if is_free_trial else None
        )
        
        return {"url": checkout_session.url}
        
    except Exception as e:
        print(f"Error creating Stripe checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment setup failed: {str(e)}")

@app.post("/api/create-customer-portal-session")
async def create_customer_portal_session(request: CustomerPortalRequest):
    """Create Stripe Customer Portal session for account management"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Find Stripe customer by email
        customers = stripe.Customer.list(email=request.email, limit=1)
        
        if not customers.data:
            raise HTTPException(status_code=404, detail="No account found with this email address")
        
        customer = customers.data[0]
        
        # Create customer portal session
        session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url="https://rgentai.com"  # Return to your homepage
        )
        
        return {
            "success": True,
            "url": session.url,
            "message": "Redirecting to account management"
        }
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Portal creation error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Customer portal error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create customer portal session")



@app.post("/api/create-account")
async def create_account(request: CreateAccountRequest, response: Response):
    """Create a new account with Stripe customer management and secure session cookies"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Create Stripe customer - metadata will be set by Stripe webhooks/products
        customer = stripe.Customer.create(
            email=request.email
            # No metadata here - let Stripe handle it based on products/subscriptions
        )
        
        # Generate access code
        access_code = user_manager.generate_access_code()
        
        # Determine plan settings based on plan_type (subscription + pay-per-token model)
        if request.plan_type == 'free_trial':
            daily_limit = 25  # 25 requests for free trial
            monthly_budget = 0.0  # No budget for free trial

        elif request.plan_type == 'pro_haiku':
            daily_limit = 10000  # Very high limit - users pay per token
            monthly_budget = 100.0  # Higher budget for token usage
        elif request.plan_type == 'pro_sonnet':
            daily_limit = 10000  # Very high limit - users pay per token
            monthly_budget = 200.0  # Higher budget for token usage
        else:  # pro
            daily_limit = 5000  # High limit for pay-per-token
            monthly_budget = 50.0
        
        # Store access code in Stripe customer metadata
        stripe.Customer.modify(
            customer.id,
            metadata={'access_code': access_code}
        )
        
        # Create user with Stripe customer ID - NO PII stored
        success = user_manager.create_user(
            access_code=access_code,
            stripe_customer_id=customer.id,
            daily_limit=daily_limit,
            monthly_budget=monthly_budget
        )
        
        if not success:
            # Clean up Stripe customer if user creation failed
            stripe.Customer.delete(customer.id)
            raise HTTPException(status_code=500, detail="Failed to create user account")
        
        # Create session token
        user_data = {
            "access_code": access_code,
            "email": request.email,
            "plan_type": request.plan_type,
            "stripe_customer_id": customer.id
        }
        session_token = create_session_token(user_data)
        
        # Send welcome email with access code and account info
        await send_welcome_email(request.email, access_code, request.plan_type, customer.id)
        
        # Return success with access code, user object, and JWT token
        return {
            "success": True,
            "user": {
                "access_code": access_code,
                "plan_type": request.plan_type,
                "stripe_customer_id": customer.id,
                "email": request.email
            },
            "access_code": access_code,
            "plan_type": request.plan_type,
            "stripe_customer_id": customer.id,
            "message": "Account created successfully! Check your email for your access code.",
            "token": session_token  # JWT token for frontend storage
        }
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Payment error: {str(e)}")
    except Exception as e:
        print(f"Account creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Account creation failed: {str(e)}")

@app.post("/api/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events - PII-free user management"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        # Get webhook secret from environment
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        # Handle the event
        if event['type'] == 'customer.created':
            # Set default metadata for new customers
            customer = event['data']['object']
            print(f"🆕 New customer created: {customer.email}")
            
            # Set default metadata for free trial
            stripe.Customer.modify(
                customer.id,
                metadata={
                    'plan_type': 'free_trial',
                    'created_at': datetime.now().isoformat(),
                    'trial_requests_remaining': '25'
                }
            )
            print(f"✅ Set default metadata for customer: {customer.id}")
            
        elif event['type'] == 'customer.subscription.created':
            # Update customer metadata when subscription is created
            subscription = event['data']['object']
            customer_id = subscription.customer
            
            # Get plan type from subscription
            lookup_key = subscription.metadata.get('lookup_key', '')
            if 'haiku' in lookup_key:
                plan_type = 'pro_haiku'
            elif 'sonnet' in lookup_key:
                plan_type = 'pro_sonnet'
            else:
                plan_type = 'pro'
            
            # Update customer metadata
            stripe.Customer.modify(
                customer_id,
                metadata={
                    'plan_type': plan_type,
                    'subscription_id': subscription.id,
                    'updated_at': datetime.now().isoformat()
                }
            )
            print(f"✅ Updated customer metadata for subscription: {subscription.id}")
            
        elif event['type'] == 'checkout.session.completed':
            # Handle successful checkout
            session = event['data']['object']
            customer_id = session.customer
            
            # Get plan type from session metadata
            plan_type = session.metadata.get('plan_type', 'free_trial')
            
            # Update customer metadata
            stripe.Customer.modify(
                customer_id,
                metadata={
                    'plan_type': plan_type,
                    'checkout_session_id': session.id,
                    'updated_at': datetime.now().isoformat()
                }
            )
            print(f"✅ Updated customer metadata for checkout: {session.id}")
            
        elif event['type'] == 'invoice.paid':
            # Handle successful payment via invoice
            invoice = event['data']['object']
            
            # Get subscription details
            subscription_id = invoice.get('subscription')
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                customer_id = subscription.customer
                
                # Generate access code for successful payment
                access_code = user_manager.generate_access_code()
                
                # Determine plan type from subscription metadata or lookup key
                lookup_key = subscription.metadata.get('lookup_key', '')
                if lookup_key:
                    # New lookup key approach (pay-per-token model)
                    if 'free_trial' in lookup_key:
                        plan_type = 'free_trial'
                        daily_limit = 25  # 25 requests for free trial
                        monthly_budget = 0.0  # No budget for free trial
                    elif 'haiku' in lookup_key:
                        plan_type = 'pro_haiku'
                        daily_limit = 10000  # Very high limit - users pay per token
                        monthly_budget = 100.0  # Higher budget for token usage
                    elif 'sonnet' in lookup_key:
                        plan_type = 'pro_sonnet'
                        daily_limit = 10000  # Very high limit - users pay per token
                        monthly_budget = 200.0  # Higher budget for token usage
                    else:
                        plan_type = 'pro'
                        daily_limit = 5000  # High limit for pay-per-token
                        monthly_budget = 50.0
                else:
                    # Legacy approach
                    plan_type = subscription.metadata.get('plan_type', 'pro')
                    daily_limit = 500
                    monthly_budget = 10.0
                
                # Create user with Stripe customer ID - NO PII stored
                success = user_manager.create_user(
                    access_code=access_code,
                    stripe_customer_id=customer_id,
                    daily_limit=daily_limit,
                    monthly_budget=monthly_budget
                )
                
                if success:
                    print(f"✅ Payment successful! Access code generated: {access_code} for plan: {plan_type}")
                    print(f"🔗 Linked to Stripe customer: {customer_id}")
                else:
                    print(f"❌ Failed to create user for customer: {customer_id}")
            
        elif event['type'] == 'payment_intent.succeeded':
            # Handle successful payment via payment intent
            payment_intent = event['data']['object']
            
            # Only process if this is for a subscription
            if payment_intent.metadata.get('subscription_id'):
                subscription_id = payment_intent.metadata.get('subscription_id')
                subscription = stripe.Subscription.retrieve(subscription_id)
                customer_id = subscription.customer
                
                # Generate access code for successful payment
                access_code = user_manager.generate_access_code()
                
                # Determine plan type from subscription metadata
                lookup_key = subscription.metadata.get('lookup_key', '')
                if lookup_key:
                    if 'haiku' in lookup_key:
                        plan_type = 'pro_haiku'
                        daily_limit = 1000
                        monthly_budget = 10.0
                    elif 'sonnet' in lookup_key:
                        plan_type = 'pro_sonnet'
                        daily_limit = 1000
                        monthly_budget = 10.0
                    else:
                        plan_type = 'pro'
                        daily_limit = 500
                        monthly_budget = 10.0
                else:
                    plan_type = subscription.metadata.get('plan_type', 'pro')
                    daily_limit = 500
                    monthly_budget = 10.0
                
                # Create user with Stripe customer ID - NO PII stored
                success = user_manager.create_user(
                    access_code=access_code,
                    stripe_customer_id=customer_id,
                    daily_limit=daily_limit,
                    monthly_budget=monthly_budget
                )
                
                if success:
                    print(f"✅ Payment successful! Access code generated: {access_code} for plan: {plan_type}")
                    print(f"🔗 Linked to Stripe customer: {customer_id}")
                else:
                    print(f"❌ Failed to create user for customer: {customer_id}")
            
        elif event['type'] == 'checkout.session.completed':
            # Keep existing checkout.session.completed logic for backward compatibility
            session = event['data']['object']
            customer_id = session.customer
            
            # Generate access code for successful payment
            access_code = user_manager.generate_access_code()
            
            # Determine plan type from metadata or lookup key
            lookup_key = session.metadata.get('lookup_key', '')
            if lookup_key:
                # New lookup key approach
                if 'haiku' in lookup_key:
                    plan_type = 'pro_haiku'
                    daily_limit = 1000  # Higher limit for Pro users
                    monthly_budget = 10.0
                elif 'sonnet' in lookup_key:
                    plan_type = 'pro_sonnet'
                    daily_limit = 1000  # Higher limit for Pro users
                    monthly_budget = 10.0
                else:
                    plan_type = 'pro'
                    daily_limit = 500
                    monthly_budget = 10.0
            else:
                # Legacy approach
                plan_type = session.metadata.get('plan_type', 'pro')
                requests = int(session.metadata.get('requests', 500))
                daily_limit = requests
                monthly_budget = 10.0 if plan_type == 'pro' else 99.0
            
            # Create user with Stripe customer ID - NO PII stored
            success = user_manager.create_user(
                access_code=access_code,
                stripe_customer_id=customer_id,
                daily_limit=daily_limit,
                monthly_budget=monthly_budget
            )
            
            if success:
                print(f"✅ Payment successful! Access code generated: {access_code} for plan: {plan_type}")
                print(f"🔗 Linked to Stripe customer: {customer_id}")
                
                # Store access code in Stripe customer metadata
                stripe.Customer.modify(
                    customer_id,
                    metadata={'access_code': access_code}
                )
                
                # Get customer email and send welcome email
                customer = stripe.Customer.retrieve(customer_id)
                if customer.email:
                    await send_welcome_email(customer.email, access_code, plan_type, customer_id)
                    print(f"📧 Welcome email sent to: {customer.email}")
                else:
                    print(f"⚠️ No email found for customer: {customer_id}")
            else:
                print(f"❌ Failed to create user for customer: {customer_id}")
            
        elif event['type'] == 'customer.subscription.deleted':
            # Handle subscription cancellation
            subscription = event['data']['object']
            customer_id = subscription.customer
            
            # Find user by Stripe customer ID and update billing status
            user = user_manager.get_user_by_stripe_customer_id(customer_id)
            if user:
                user_manager.update_user_billing_status(user.access_code, 'cancelled')
                print(f"📋 Subscription cancelled for customer: {customer_id}")
            else:
                print(f"⚠️ No user found for cancelled subscription: {customer_id}")
            
        elif event['type'] == 'customer.subscription.updated':
            # Handle subscription updates
            subscription = event['data']['object']
            customer_id = subscription.customer
            
            # Update user billing status based on subscription status
            user = user_manager.get_user_by_stripe_customer_id(customer_id)
            if user:
                status = subscription.status
                user_manager.update_user_billing_status(user.access_code, status)
                print(f"📋 Subscription updated for customer: {customer_id} - Status: {status}")
            else:
                print(f"⚠️ No user found for updated subscription: {customer_id}")
            
        return {"status": "success"}
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

@app.get("/api/payment-status/{session_id}")
async def get_payment_status(session_id: str):
    """Check payment status for a session"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "session_id": session_id,
            "status": session.payment_status,
            "customer_email": session.customer_details.email if session.customer_details else None
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")

@app.get("/api/session-access-code/{session_id}")
async def get_session_access_code(session_id: str):
    """Get access code for a completed checkout session"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status != 'paid':
            raise HTTPException(status_code=400, detail="Payment not completed")
        
        customer_id = session.customer
        if not customer_id:
            raise HTTPException(status_code=404, detail="No customer found for session")
        
        # Get customer and access code from metadata
        customer = stripe.Customer.retrieve(customer_id)
        access_code = customer.metadata.get('access_code')
        
        if not access_code:
            # Fallback: check if user exists in our database
            print(f"Access code not found in Stripe metadata, checking database for customer {customer_id}")
            user = user_manager.get_user_by_stripe_customer_id(customer_id)
            if user:
                access_code = user['access_code']
                print(f"Found access code in database: {access_code}")
            else:
                raise HTTPException(status_code=404, detail="Access code not found - webhook may still be processing")
        
        return {
            "access_code": access_code,
            "customer_email": customer.email,
            "plan_type": customer.metadata.get('plan_type', 'unknown')
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving access code: {str(e)}")

# Password management removed - Stripe handles user authentication
# @app.post("/api/forgot-password") - REMOVED
# @app.post("/api/reset-password") - REMOVED


        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Subscription error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Renew subscription error: {e}")
        raise HTTPException(status_code=500, detail="Failed to renew subscription")

@app.get("/debug/stripe")
async def debug_stripe_config():
    """Debug endpoint to check Stripe configuration"""
    try:
        stripe_secret = os.getenv("STRIPE_SECRET_KEY")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        claude_key = os.getenv("CLAUDE_API_KEY")
        
        debug_info = {
            "stripe_secret_key_set": stripe_secret is not None,
            "stripe_secret_key_preview": stripe_secret[:10] + "..." if stripe_secret else None,
            "webhook_secret_set": webhook_secret is not None,
            "webhook_secret_preview": webhook_secret[:10] + "..." if webhook_secret else None,
            "claude_key_set": claude_key is not None,
            "claude_key_preview": claude_key[:10] + "..." if claude_key else None,
        }
        
        # Test Stripe connection if secret is set
        if stripe_secret:
            try:
                # Set the API key
                stripe.api_key = stripe_secret
                
                # Test with a simple API call
                try:
                    customers = stripe.Customer.list(limit=1)
                    debug_info["stripe_connection"] = "✅ Success"
                except stripe.error.AuthenticationError:
                    debug_info["stripe_connection"] = "❌ Authentication failed - check your secret key"
                except stripe.error.APIConnectionError:
                    debug_info["stripe_connection"] = "❌ Connection failed - check your internet"
                except Exception as e:
                    debug_info["stripe_connection"] = f"❌ API Error: {str(e)}"
                    
            except Exception as e:
                debug_info["stripe_connection"] = f"❌ Setup Error: {str(e)}"
        else:
            debug_info["stripe_connection"] = "❌ No secret key"
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/stripe-products")
async def debug_stripe_products():
    """Debug endpoint to check Stripe products and prices"""
    try:
        stripe_secret = os.getenv("STRIPE_SECRET_KEY")
        if not stripe_secret:
            return {"error": "STRIPE_SECRET_KEY not set"}
        
        stripe.api_key = stripe_secret
        
        debug_info = {
            "products": [],
            "prices": [],
            "required_lookup_keys": {}
        }
        
        # Get all products
        products = stripe.Product.list(limit=10)
        for product in products.data:
            debug_info["products"].append({
                "name": product.name,
                "id": product.id,
                "active": product.active,
                "metadata": product.metadata
            })
        
        # Get all prices
        prices = stripe.Price.list(limit=20)
        for price in prices.data:
            debug_info["prices"].append({
                "nickname": price.nickname,
                "id": price.id,
                "product": price.product,
                "active": price.active,
                "unit_amount": price.unit_amount,
                "currency": price.currency,
                "recurring": price.recurring,
                "lookup_key": price.lookup_key,
                "metadata": price.metadata
            })
        
        # Check for specific lookup keys we need
        required_keys = [
            'free_trial_monthly_v3',
            'pro_haiku_monthly_base_v3', 
            'pro_haiku_input_tokens_v3',
            'pro_haiku_output_tokens_v3',
            'pro_sonnet_monthly_base_v3',
            'pro_sonnet_input_tokens_v3', 
            'pro_sonnet_output_tokens_v3'
        ]
        
        # Get all prices to check lookup keys
        all_prices = stripe.Price.list(limit=200)  # Increased limit
        
        # Add detailed debugging info
        debug_info["total_prices_found"] = len(all_prices.data)
        debug_info["prices_with_lookup_keys"] = []
        
        for price in all_prices.data:
            if price.lookup_key:
                debug_info["prices_with_lookup_keys"].append({
                    "id": price.id,
                    "lookup_key": price.lookup_key,
                    "active": price.active,
                    "nickname": price.nickname,
                    "unit_amount": price.unit_amount
                })
        
        lookup_keys_found = [price.lookup_key for price in all_prices.data if price.lookup_key]
        debug_info["all_lookup_keys"] = lookup_keys_found
        
        for key in required_keys:
            if key in lookup_keys_found:
                # Find the price with this lookup key
                price = next((p for p in all_prices.data if p.lookup_key == key), None)
                if price:
                    debug_info["required_lookup_keys"][key] = {
                        "found": True,
                        "id": price.id,
                        "active": price.active,
                        "lookup_key": price.lookup_key
                    }
                else:
                    debug_info["required_lookup_keys"][key] = {
                        "found": False,
                        "error": "Lookup key exists but price not found"
                    }
            else:
                debug_info["required_lookup_keys"][key] = {
                    "found": False,
                    "error": "Lookup key not found"
                }
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/logout")
async def logout(request: Request):
    """Logout user by blacklisting JWT token"""
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        # Add token to blacklist
        token_blacklist.add(token)
        print(f"Token blacklisted: {token[:20]}...")
    
    return {"success": True, "message": "Logged out successfully"}

@app.get("/api/session")
async def get_session(request: Request):
    """Get current session information from Bearer token"""
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid token")
    
    token = auth_header.split(" ")[1]
    user = verify_session_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {
        "success": True,
        "user": {
            "access_code": user.get("user_id"),
            "email": user.get("email"),
            "plan_type": user.get("plan_type"),
            "stripe_customer_id": user.get("stripe_customer_id")
        }
    }

@app.post("/debug/test-checkout")
async def test_checkout_creation(request: LookupKeyRequest):
    """Debug endpoint to test checkout session creation"""
    try:
        stripe_secret = os.getenv("STRIPE_SECRET_KEY")
        if not stripe_secret:
            return {"error": "STRIPE_SECRET_KEY not set"}
        
        stripe.api_key = stripe_secret
        
        debug_info = {
            "request": {
                "lookup_key": request.lookup_key,
                "customer_email": request.customer_email
            },
            "steps": {}
        }
        
        # Step 1: Get the price from lookup key
        try:
            prices = stripe.Price.list(
                lookup_keys=[request.lookup_key],
                expand=['data.product']
            )
            debug_info["steps"]["price_lookup"] = {
                "success": True,
                "prices_found": len(prices.data),
                "price_details": []
            }
            
            for price in prices.data:
                debug_info["steps"]["price_lookup"]["price_details"].append({
                    "id": price.id,
                    "lookup_key": price.lookup_key,
                    "active": price.active,
                    "unit_amount": price.unit_amount,
                    "currency": price.currency,
                    "recurring": price.recurring,
                    "product_id": price.product.id if hasattr(price.product, 'id') else None
                })
                
        except Exception as e:
            debug_info["steps"]["price_lookup"] = {
                "success": False,
                "error": str(e)
            }
            return debug_info
        
        if not prices.data:
            debug_info["steps"]["price_lookup"]["error"] = f"No price found for lookup key: {request.lookup_key}"
            return debug_info
        
        # Step 2: Create checkout session
        try:
            checkout_session = stripe.checkout.Session.create(
                line_items=[{
                    'price': prices.data[0].id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url='https://rgentai.com/success.html?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='https://rgentai.com/plans?cancelled=true',
                metadata={
                    'lookup_key': request.lookup_key,
                    'customer_email': request.customer_email or ''
                }
            )
            
            debug_info["steps"]["checkout_creation"] = {
                "success": True,
                "session_id": checkout_session.id,
                "url": checkout_session.url
            }
            
        except Exception as e:
            debug_info["steps"]["checkout_creation"] = {
                "success": False,
                "error": str(e)
            }
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e)}

# Session management
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
SESSION_EXPIRY_HOURS = 24

# Token blacklist for logout (in production, use Redis or database)
token_blacklist = set()

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not text:
        return ""
    
    # Remove any HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # HTML escape special characters
    text = html.escape(text)
    
    # Remove any remaining potentially dangerous characters
    text = re.sub(r'[<>"\']', '', text)
    
    return text.strip()

def create_session_token(user_data: dict) -> str:
    """Create a JWT session token with security features"""
    now = datetime.utcnow()
    payload = {
        "user_id": user_data.get("access_code"),
        "email": user_data.get("email"),
        "plan_type": user_data.get("plan_type"),
        "stripe_customer_id": user_data.get("stripe_customer_id"),
        "iat": now,  # Issued at
        "exp": now + timedelta(hours=SESSION_EXPIRY_HOURS),  # Expiration
        "jti": str(uuid.uuid4()),  # JWT ID for token revocation
        "iss": "rgent-ai",  # Issuer
        "aud": "rgent-ai-frontend"  # Audience
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_session_token(token: str) -> Optional[dict]:
    """Verify and decode JWT session token with security checks"""
    # Check if token is blacklisted
    if token in token_blacklist:
        print("JWT token is blacklisted")
        return None
        
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=["HS256"],
            issuer="rgent-ai",
            audience="rgent-ai-frontend"
        )
        return payload
    except jwt.ExpiredSignatureError:
        print("JWT token expired")
        return None
    except jwt.InvalidIssuerError:
        print("JWT token has invalid issuer")
        return None
    except jwt.InvalidAudienceError:
        print("JWT token has invalid audience")
        return None
    except jwt.InvalidTokenError:
        print("JWT token is invalid")
        return None

def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from session cookie"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    return verify_session_token(session_token)

async def send_welcome_email(email: str, access_code: str, plan_type: str, stripe_customer_id: str):
    """Send welcome email with access code and account management links"""
    try:
        # Create customer portal session URL
        portal_url = f"https://rgentaipaymentfrontend-99wx5gg8n-nathanbresettes-projects.vercel.app/customer-portal.html"
        recovery_url = f"https://rgentaipaymentfrontend-99wx5gg8n-nathanbresettes-projects.vercel.app/access-code-recovery.html"
        
        # Email content
        subject = "Welcome to RgentAI! Your Access Code & Account Info"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .access-code {{ background: #e9ecef; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 18px; text-align: center; margin: 20px 0; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 5px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to RgentAI!</h1>
                    <p>Your account has been created successfully</p>
                </div>
                
                <div class="content">
                    <h2>Your Access Code</h2>
                    <p>Use this access code in your R package to start using RgentAI:</p>
                    <div class="access-code">{access_code}</div>
                    
                    <div class="warning">
                        <strong>⚠️ Important:</strong> Keep this access code secure. You can always recover it later if needed.
                    </div>
                    
                    <h2>📊 Usage Tracking</h2>
                    <p>Monitor your usage and costs directly in your R package. No need to log into a dashboard!</p>
                    
                    <h2>🔧 Account Management</h2>
                    <p>Manage your subscription, billing, and access code:</p>
                    
                    <a href="{recovery_url}" class="button">🔑 Recover Access Code</a>
                    <a href="{portal_url}" class="button">⚙️ Customer Portal</a>
                    
                    <h2>📚 Getting Started</h2>
                    <p>Follow these 4 simple commands to install RgentAI:</p>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 14px; margin: 15px 0;">
                        <div style="color: #008000;"># 1. Install devtools (if not already installed)</div>
                        <div>install.packages("devtools")</div>
                        <div style="color: #008000;"># 2. Install RgentAI package</div>
                        <div>devtools::install_github("NathanBresette/Rgent-AI", force = TRUE)</div>
                        <div style="color: #008000;"># 3. Load the library</div>
                        <div>library(rstudioai)</div>
                        <div style="color: #008000;"># 4. Launch the AI assistant</div>
                        <div>ai_addin_viewer()</div>
                    </div>
                    <p><strong>That's it!</strong> Your AI assistant is now built right into RStudio.</p>
                    
                    <h2>🔧 Troubleshooting</h2>
                    <p>Having issues? Check our <a href="https://rgentaipaymentfrontend-99wx5gg8n-nathanbresettes-projects.vercel.app/installation.html" style="color: #667eea;">installation guide</a> for help with:</p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>GitHub access issues</li>
                        <li>Function not found errors</li>
                        <li>Viewer tab not appearing</li>
                        <li>System requirements</li>
                    </ul>
                    
                    <h2>💳 Plan Details</h2>
                    <p><strong>Plan:</strong> {plan_type.replace('_', ' ').title()}</p>
                    <p><strong>Customer ID:</strong> {stripe_customer_id}</p>
                </div>
                
                <div class="footer">
                    <p>Need help? Contact us at support@rgentai.com</p>
                    <p>© 2024 RgentAI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Try to send via AWS SES if configured
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        if aws_access_key and aws_secret_key:
            try:
                import boto3
                from botocore.exceptions import ClientError
                
                # Create SES client
                ses_client = boto3.client(
                    'ses',
                    region_name=aws_region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
                
                # Send email
                response = ses_client.send_email(
                    Source='noreply@rgentai.com',  # Update with your verified sender
                    Destination={
                        'ToAddresses': [email]
                    },
                    Message={
                        'Subject': {
                            'Data': subject,
                            'Charset': 'UTF-8'
                        },
                        'Body': {
                            'Html': {
                                'Data': html_content,
                                'Charset': 'UTF-8'
                            }
                        }
                    }
                )
                
                print(f"📧 Welcome email sent via AWS SES to {email} (Message ID: {response['MessageId']})")
                return True
                
            except ClientError as e:
                print(f"AWS SES error: {e.response['Error']['Message']}")
                # Fall back to logging
            except Exception as e:
                print(f"AWS SES error: {e}")
                # Fall back to logging
        
        # Fallback: just log the email (for development/testing)
        print(f"📧 Welcome email would be sent to {email}")
        print(f"📧 Access code: {access_code}")
        print(f"📧 Plan: {plan_type}")
        print(f"📧 Customer ID: {stripe_customer_id}")
        print(f"📧 To enable real emails, set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION environment variables")
        
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        # Don't fail the account creation if email fails

@app.post("/api/recover-access-code")
async def recover_access_code(request: CustomerPortalRequest):
    """Recover access code via email - PII-free approach"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Find Stripe customer by email
        customers = stripe.Customer.list(email=request.email, limit=1)
        
        if not customers.data:
            raise HTTPException(status_code=404, detail="No account found with this email")
        
        customer = customers.data[0]
        access_code = customer.metadata.get('access_code')
        
        if not access_code:
            raise HTTPException(status_code=404, detail="Access code not found for this account")
        
        # Get usage stats from user manager
        usage_stats = user_manager.get_user_stats(access_code)
        
        # Send email with access code and usage stats
        # Note: In production, you'd use a proper email service
        # For now, we'll return the info (you can integrate with SendGrid, etc.)
        
        return {
            "success": True,
            "message": "Access code sent to your email",
            "access_code": access_code,
            "usage_stats": usage_stats,
            "email_sent": True  # In production, this would be based on actual email send
        }
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        print(f"Access code recovery error: {e}")
        raise HTTPException(status_code=500, detail=f"Access code recovery failed: {str(e)}")

@app.post("/api/cancel-subscription")
async def cancel_subscription(request: CustomerPortalRequest):
    """Cancel user subscription - PII-free approach"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Find Stripe customer by email
        customers = stripe.Customer.list(email=request.email, limit=1)
        
        if not customers.data:
            raise HTTPException(status_code=404, detail="No account found with this email")
        
        customer = customers.data[0]
        
        # Get active subscriptions for this customer
        subscriptions = stripe.Subscription.list(customer=customer.id, status='active', limit=1)
        
        if not subscriptions.data:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        subscription = subscriptions.data[0]
        
        # Cancel the subscription at period end
        cancelled_subscription = stripe.Subscription.modify(
            subscription.id,
            cancel_at_period_end=True
        )
        
        # Update user status in database
        access_code = customer.metadata.get('access_code')
        if access_code:
            user_manager.update_user_status(access_code, is_active=False, billing_status='cancelled')
        
        return {
            "success": True,
            "message": "Subscription cancelled successfully",
            "subscription_id": subscription.id,
            "cancelled_at": cancelled_subscription.cancel_at,
            "current_period_end": subscription.current_period_end
        }
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        print(f"Subscription cancellation error: {e}")
        raise HTTPException(status_code=500, detail=f"Subscription cancellation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 