# Force rebuild: Fix WORKDIR and PYTHONPATH
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import os
from typing import Optional, List, Dict, AsyncGenerator
import json
from sqlite_rag import SQLiteRAG
from context_summarizer import ContextSummarizer
from response_cache import SmartResponseCache
from conversation_memory import ConversationMemory
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

app = FastAPI(title="RStudio AI Backend", version="1.3.0")

# Initialize SQLite RAG, context summarizer, response cache, and conversation memory
sqlite_rag = SQLiteRAG()
context_summarizer = ContextSummarizer()
response_cache = SmartResponseCache(max_cache_size=200, cache_ttl_hours=4)  # Conservative settings for memory
conversation_memory = ConversationMemory()

# CORS middleware with default config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    user_name: str
    email: str = ""
    daily_limit: int = 100
    monthly_budget: float = 10.0

class UpdateUserRequest(BaseModel):
    user_name: Optional[str] = None
    email: Optional[str] = None
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
    lookup_key: str  # For Pro plans: 'pro_haiku_monthly_base' or 'pro_sonnet_monthly_base'
    customer_email: Optional[str] = None

class PaymentSuccessRequest(BaseModel):
    session_id: str
    customer_email: str
    plan_type: str

class SignInRequest(BaseModel):
    email: str
    password: str

class CreateAccountRequest(BaseModel):
    email: str
    password: str
    plan_type: str

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
        # Get user stats to return user information
        user_stats = user_manager.get_user_stats(request.access_code)
        user_name = user_stats.get('user_name', 'Unknown') if user_stats else 'Unknown'
        return {"valid": True, "user": user_name}
    else:
        raise HTTPException(status_code=401, detail=message)

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """Chat with AI using RAG-enhanced prompt with context summarization, smart caching, and conversation memory"""
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
                    context_summary={"cached_response": True, "cache_age_hours": cached_response['cache_age']}
                )
        
        # Create context summary for storage and processing
        context_summary = None
        if request.context_data:
            context_summary = context_summarizer.summarize_context(request.context_data)
            
            # Store summarized context instead of full context
            context_id = sqlite_rag.store_context(
                request.access_code, 
                context_summary,  # Store summary instead of full context
                request.context_type
            )
        
        # Retrieve relevant context from vector database (reduced from 3 to 2)
        retrieved_contexts = sqlite_rag.retrieve_relevant_context(
            request.access_code, 
            request.prompt, 
            n_results=2  # Reduced from 3 to save memory
        )
        
        # Build enhanced prompt with summarized context
        enhanced_prompt = request.prompt
        
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
        
        # Call Gemini API with enhanced prompt
        response, usage_info = await call_gemini_api(enhanced_prompt)
        
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
        
        # Get context summary for response
        context_summary_response = sqlite_rag.get_user_context_summary(request.access_code)
        
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
                context_id = sqlite_rag.store_context(
                    request.access_code, 
                    context_summary,  # Store summary instead of full context
                    request.context_type
                )
            
            # Retrieve relevant context from vector database (reduced from 3 to 2)
            retrieved_contexts = sqlite_rag.retrieve_relevant_context(
                request.access_code, 
                request.prompt, 
                n_results=2  # Reduced from 3 to save memory
            )
            
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
            input_tokens = 0
            output_tokens = 0
            
            async for chunk in stream_claude_api(enhanced_prompt):
                full_response += chunk
                output_tokens += len(chunk.split())  # Approximate token count
                
                # Send chunk to client immediately
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'chunk': '', 'done': True, 'total_tokens': total_tokens, 'conversation_id': conversation_id})}\n\n"
            
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
            track_usage(request.access_code, {
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
            })
            
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
        try:
            db_stats = sqlite_rag.get_database_stats()
            total_contexts = db_stats.get("total_contexts", "Error getting count")
        except:
            total_contexts = "Error getting count"
        
        # Get cache stats
        cache_stats = response_cache.get_cache_stats()
        
        return {
            "system_memory": memory_info,
            "process_memory": process_info,
            "sqlite_db_stats": db_stats if 'db_stats' in locals() else {"error": "Could not get database stats"},
            "cache_stats": cache_stats,
            "memory_limits": {
                "max_contexts_per_user": sqlite_rag.max_contexts_per_user,
                "max_total_contexts": sqlite_rag.max_total_contexts,
                "max_context_age_days": sqlite_rag.max_context_age_days
            }
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
        sqlite_rag._cleanup_old_data()
        
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
    
    return get_usage_stats(access_code)

@app.get("/usage/{access_code}")
async def get_user_usage(access_code: str):
    """Get usage statistics for a specific access code"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    return get_usage_stats(access_code)

@app.post("/context/store", response_model=ContextResponse)
async def store_context(request: ContextRequest):
    """Store context data in vector database"""
    if not validate_access_code(request.access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    try:
        context_id = sqlite_rag.store_context(
            request.access_code,
            request.context_data,
            request.context_type
        )
        
        if context_id:
            return ContextResponse(
                success=True,
                message="Context stored successfully",
                context_id=context_id
            )
        else:
            return ContextResponse(
                success=False,
                message="Failed to store context"
            )
    except Exception as e:
        return ContextResponse(
            success=False,
            message=f"Error storing context: {str(e)}"
        )

@app.get("/context/summary/{access_code}")
async def get_context_summary(access_code: str):
    """Get context summary for a user"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    try:
        summary = sqlite_rag.get_user_context_summary(access_code)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/context/clear/{access_code}")
async def clear_user_context(access_code: str):
    """Clear all context for a user"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    try:
        success = sqlite_rag.clear_user_context(access_code)
        if success:
            return {"success": True, "message": "Context cleared successfully"}
        else:
            return {"success": False, "message": "Failed to clear context"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context/analytics/{access_code}")
async def get_user_analytics(access_code: str):
    """Get detailed analytics for a user's context"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    try:
        analytics = sqlite_rag.get_user_context_analytics(access_code)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context/search/{access_code}")
async def search_user_context(access_code: str, q: str, context_type: str = None):
    """Search user's context"""
    if not validate_access_code(access_code):
        raise HTTPException(status_code=401, detail="Invalid access code")
    
    try:
        results = sqlite_rag.search_user_context(access_code, q, context_type)
        return {
            "access_code": access_code,
            "search_term": q,
            "context_type_filter": context_type,
            "results": results,
            "total_results": len(results)
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
            user_name=request.user_name,
            email=request.email,
            daily_limit=request.daily_limit,
            monthly_budget=request.monthly_budget
        )
        
        if success:
            return {"success": True, "message": f"User {request.user_name} created successfully"}
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
                user_name="Free User",
                email=request.customer_email or "free@example.com",
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
            success_url='https://rgentai.com/dashboard?session_id={CHECKOUT_SESSION_ID}',
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
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            line_items=[{
                'price': prices.data[0].id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://rgentaipaymentfrontend-ik29jvzcv-nathanbresettes-projects.vercel.app/dashboard?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://rgentaipaymentfrontend-ik29jvzcv-nathanbresettes-projects.vercel.app/plans?cancelled=true',
            metadata={
                'lookup_key': request.lookup_key,
                'customer_email': request.customer_email or ''
            }
        )
        
        return {"id": checkout_session.id}
        
    except Exception as e:
        print(f"Error creating Stripe checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment setup failed: {str(e)}")

@app.post("/api/signin")
async def signin(request: SignInRequest):
    """Sign in using Stripe customer management - NO PII stored locally"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Find Stripe customer by email
        customers = stripe.Customer.list(email=request.email, limit=1)
        
        if not customers.data:
            raise HTTPException(status_code=401, detail="Account not found")
        
        customer = customers.data[0]
        
        # Find user by Stripe customer ID
        user = user_manager.get_user_by_stripe_customer_id(customer.id)
        
        if not user:
            raise HTTPException(status_code=401, detail="User account not found")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Account is disabled")
        
        # Return user data (no password verification needed - Stripe handles authentication)
        return {
            "success": True,
            "access_code": user.access_code,
            "plan_type": customer.metadata.get('plan_type', 'pro'),
            "stripe_customer_id": customer.id,
            "billing_status": user.billing_status,
            "message": "Sign in successful"
        }
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Authentication error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Sign in error: {e}")
        raise HTTPException(status_code=500, detail="Sign in failed")

@app.post("/api/create-account")
async def create_account(request: CreateAccountRequest):
    """Create a new account with Stripe customer management - NO PII stored locally"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Create Stripe customer for PII management
        customer = stripe.Customer.create(
            email=request.email,
            metadata={
                'plan_type': request.plan_type,
                'created_at': datetime.now().isoformat()
            }
        )
        
        # Generate access code
        access_code = user_manager.generate_access_code()
        
        # Determine plan limits
        if request.plan_type == 'free':
            daily_limit = 50
            monthly_budget = 5.0
        elif request.plan_type == 'pro_haiku':
            daily_limit = 1000
            monthly_budget = 10.0
        elif request.plan_type == 'pro_sonnet':
            daily_limit = 1000
            monthly_budget = 10.0
        else:  # pro
            daily_limit = 500
            monthly_budget = 10.0
        
        # Create user with Stripe customer ID - NO PII stored locally
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
        
        # Return success with access code
        return {
            "success": True,
            "access_code": access_code,
            "plan_type": request.plan_type,
            "stripe_customer_id": customer.id,
            "message": "Account created successfully"
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
        if event['type'] == 'invoice.paid':
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

# Password management removed - Stripe handles user authentication
# @app.post("/api/forgot-password") - REMOVED
# @app.post("/api/reset-password") - REMOVED

@app.post("/api/cancel-subscription")
async def cancel_subscription(request: SignInRequest):
    """Cancel subscription using Stripe customer management"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Find Stripe customer by email
        customers = stripe.Customer.list(email=request.email, limit=1)
        
        if not customers.data:
            raise HTTPException(status_code=401, detail="Account not found")
        
        customer = customers.data[0]
        
        # Find user by Stripe customer ID
        user = user_manager.get_user_by_stripe_customer_id(customer.id)
        
        if not user:
            raise HTTPException(status_code=401, detail="User account not found")
        
        # Cancel subscription in Stripe
        subscriptions = stripe.Subscription.list(customer=customer.id, status='active', limit=1)
        
        if not subscriptions.data:
            raise HTTPException(status_code=400, detail="No active subscription found")
        
        subscription = subscriptions.data[0]
        
        # Cancel at period end (user keeps access until billing period ends)
        cancelled_subscription = stripe.Subscription.modify(
            subscription.id,
            cancel_at_period_end=True
        )
        
        # Update local billing status
        user_manager.update_user_billing_status(user.access_code, 'cancelling')
        
        return {
            "success": True,
            "message": "Subscription cancelled. You'll have access until the end of your billing period.",
            "cancel_at": cancelled_subscription.cancel_at
        }
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Subscription error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Cancel subscription error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")

@app.post("/api/renew-subscription")
async def renew_subscription(request: SignInRequest):
    """Renew subscription using Stripe customer management"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        # Find Stripe customer by email
        customers = stripe.Customer.list(email=request.email, limit=1)
        
        if not customers.data:
            raise HTTPException(status_code=401, detail="Account not found")
        
        customer = customers.data[0]
        
        # Find user by Stripe customer ID
        user = user_manager.get_user_by_stripe_customer_id(customer.id)
        
        if not user:
            raise HTTPException(status_code=401, detail="User account not found")
        
        # Find subscription that's being cancelled
        subscriptions = stripe.Subscription.list(customer=customer.id, status='active', limit=1)
        
        if not subscriptions.data:
            raise HTTPException(status_code=400, detail="No active subscription found")
        
        subscription = subscriptions.data[0]
        
        if not subscription.cancel_at_period_end:
            raise HTTPException(status_code=400, detail="Subscription is not cancelled")
        
        # Reactivate subscription
        renewed_subscription = stripe.Subscription.modify(
            subscription.id,
            cancel_at_period_end=False
        )
        
        # Update local billing status
        user_manager.update_user_billing_status(user.access_code, 'active')
        
        return {
            "success": True,
            "message": "Subscription renewed successfully",
            "current_period_end": renewed_subscription.current_period_end
        }
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Subscription error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Renew subscription error: {e}")
        raise HTTPException(status_code=500, detail="Failed to renew subscription")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 