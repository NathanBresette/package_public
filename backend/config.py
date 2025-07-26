"""
Configuration for RStudio AI Backend
Switch between SQLite and PostgreSQL easily
"""

import os

# Database configuration
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'
DATABASE_URL = os.getenv('DATABASE_URL')

# AI API configuration
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
CLAUDE_API_KEY_HAIKU = os.getenv('CLAUDE_API_KEY_HAIKU', CLAUDE_API_KEY)

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Backend configuration
BACKEND_VERSION = "1.4.0"
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

def get_user_manager():
    """Get the appropriate user manager based on configuration"""
    if USE_POSTGRESQL and DATABASE_URL:
        print("🚀 Using PostgreSQL for user management")
        from user_management_postgres import user_manager
        return user_manager
    else:
        print("🚀 Using SQLite for user management")
        from user_management_sqlite import user_manager
        return user_manager 