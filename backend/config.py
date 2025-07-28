"""
Configuration for RStudio AI Backend
Centralized settings and user manager selection
"""

import os
from user_management_postgres import UserManagerPostgreSQL

def get_user_manager():
    """Get the appropriate user manager - PostgreSQL only for PII-free system"""
    # Always use PostgreSQL for PII-free user management
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required for PostgreSQL user management")
    
    return UserManagerPostgreSQL()

# Environment variable configuration
USE_POSTGRESQL = True  # Always True for PII-free system
DATABASE_URL = os.getenv("DATABASE_URL")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
ADMIN_ACCESS_CODE = os.getenv("ADMIN_ACCESS_CODE", "admin123") 