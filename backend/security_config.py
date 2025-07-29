"""
Security Configuration for RStudio AI Backend
"""

import os
from typing import List

# CORS Configuration
ALLOWED_ORIGINS = [
    "http://127.0.0.1:*",
    "http://localhost:*",
    # Add your production domains here
    # "https://yourdomain.com",
    # "https://app.yourdomain.com",
]

ALLOWED_METHODS = ["GET", "POST", "DELETE"]
ALLOWED_HEADERS = ["*"]

# Admin Configuration
ADMIN_ACCESS_CODE = os.getenv("ADMIN_ACCESS_CODE", "ADMIN_SECRET_123")

# Rate Limiting (requests per minute per access code)
RATE_LIMIT_PER_MINUTE = 60

# Session Configuration
SESSION_TIMEOUT_MINUTES = 30

# Security Headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
}

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_SENSITIVE_DATA = False  # Set to False in production

# API Key Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Database Security (PostgreSQL only)
ENCRYPT_DB = os.getenv("ENCRYPT_DB", "false").lower() == "true"

# Production Security Checklist
PRODUCTION_SECURITY_CHECKLIST = [
    "✅ Change ADMIN_ACCESS_CODE to a strong secret",
    "✅ Set GEMINI_API_KEY environment variable",
    "✅ Configure ALLOWED_ORIGINS for your domains",
    "✅ Enable HTTPS in production",
    "✅ Set up proper logging",
    "✅ Configure rate limiting",
    "✅ Enable database encryption if needed",
    "✅ Set up monitoring and alerting",
    "✅ Regular security audits",
    "✅ Keep dependencies updated"
]

def get_cors_config():
    """Get CORS configuration based on environment"""
    return {
        "allow_origins": ALLOWED_ORIGINS,
        "allow_credentials": True,
        "allow_methods": ALLOWED_METHODS,
        "allow_headers": ALLOWED_HEADERS,
    }

def is_production():
    """Check if running in production"""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"

def get_security_headers():
    """Get security headers based on environment"""
    headers = SECURITY_HEADERS.copy()
    
    if is_production():
        # Add additional production headers
        headers.update({
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        })
    
    return headers 