"""
User Management System for RStudio AI - PostgreSQL Version
Handles user access, cost tracking, monitoring, and revocation
Uses PostgreSQL for persistent storage on Render
"""

import os
import time
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib
import threading
import psycopg2
from psycopg2.extras import RealDictCursor

@dataclass
class UserProfile:
    """User profile with access control and cost tracking - NO PII stored"""
    access_code: str
    stripe_customer_id: str = ""
    is_active: bool = True
    is_admin: bool = False
    created_at: str = ""
    last_activity: str = ""
    total_requests: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    daily_limit: int = 100
    monthly_budget: float = 10.0
    rate_limit: int = 10
    context_count: int = 0
    notes: str = ""
    billing_status: str = "inactive"

@dataclass
class UsageRecord:
    """Individual usage record for cost tracking"""
    timestamp: str
    access_code: str
    request_type: str
    tokens_used: int
    cost: float
    prompt_length: int
    response_length: int
    success: bool = True
    error_message: str = ""

class UserManagerPostgreSQL:
    """Manages users, access control, and cost tracking using PostgreSQL"""
    
    def __init__(self):
        self.rate_limit_cache: Dict[str, List[float]] = {}
        self.lock = threading.Lock()
        self._ensure_database()
    

    
    def _get_connection(self):
        """Get PostgreSQL connection"""
        # Get database URL from environment variable
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise Exception("DATABASE_URL environment variable not set")
        
        return psycopg2.connect(database_url)
    
    def _ensure_database(self):
        """Ensure database exists with proper schema"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if users table exists and has the right schema
                cursor.execute('''
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'users'
                    )
                ''')
                table_exists = cursor.fetchone()[0]
                
                if table_exists:
                    # Check if stripe_customer_id column exists
                    cursor.execute('''
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns
                            WHERE table_name = 'users' AND column_name = 'stripe_customer_id'
                        )
                    ''')
                    column_exists = cursor.fetchone()[0]
                    
                    if not column_exists:
                        print("🔄 Migrating database schema to PII-free version...")
                        # Add stripe_customer_id column
                        cursor.execute('''
                            ALTER TABLE users 
                            ADD COLUMN stripe_customer_id VARCHAR(255) UNIQUE
                        ''')
                        
                        # Remove PII columns if they exist
                        for column in ['email', 'password_hash']:
                            cursor.execute('''
                                SELECT EXISTS (
                                    SELECT FROM information_schema.columns
                                    WHERE table_name = 'users' AND column_name = %s
                                )
                            ''', (column,))
                            if cursor.fetchone()[0]:
                                cursor.execute(f'ALTER TABLE users DROP COLUMN {column}')
                                print(f"🗑️ Removed PII column: {column}")
                        
                        print("✅ Database migration completed!")
                
                # Create users table - NO PII stored
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        access_code VARCHAR(50) UNIQUE NOT NULL,
                        stripe_customer_id VARCHAR(255) UNIQUE,
                        is_active BOOLEAN DEFAULT TRUE,
                        is_admin BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP,
                        total_requests INTEGER DEFAULT 0,
                        total_cost DECIMAL(10,4) DEFAULT 0.0,
                        total_tokens INTEGER DEFAULT 0,
                        daily_limit INTEGER DEFAULT 100,
                        monthly_budget DECIMAL(10,2) DEFAULT 10.0,
                        rate_limit INTEGER DEFAULT 10,
                        context_count INTEGER DEFAULT 0,
                        notes TEXT,
                        billing_status VARCHAR(50) DEFAULT 'inactive'
                    )
                ''')
                
                # Create usage_records table - NO PII stored
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS usage_records (
                        id SERIAL PRIMARY KEY,
                        access_code VARCHAR(50) NOT NULL,
                        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        request_type VARCHAR(100) NOT NULL,
                        tokens_used INTEGER DEFAULT 0,
                        cost DECIMAL(10,6) DEFAULT 0.0,
                        prompt_length INTEGER DEFAULT 0,
                        response_length INTEGER DEFAULT 0,
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT,
                        FOREIGN KEY (access_code) REFERENCES users (access_code)
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_access_code ON users(access_code)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON users(stripe_customer_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_access_code ON usage_records(access_code)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)')
                
                conn.commit()
                print("✅ PostgreSQL database schema created successfully (PII-free)!")
                
        except Exception as e:
            print(f"❌ Error setting up PostgreSQL database: {e}")
            print("💡 Make sure DATABASE_URL environment variable is set in Render")
    
    def validate_access(self, access_code: str) -> Tuple[bool, str]:
        """Validate user access and check limits"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Simple check: just see if user exists and is active
                cursor.execute('''
                    SELECT access_code, is_active, billing_status 
                    FROM users 
                    WHERE access_code = %s
                ''', (access_code,))
                user = cursor.fetchone()
                
                if not user:
                    return False, "Invalid access code"
                
                # user is a tuple: (access_code, is_active, billing_status)
                if not user[1]:  # is_active is at index 1
                    return False, "User is inactive"
                
                # Update last activity
                cursor.execute('''
                    UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE access_code = %s
                ''', (access_code,))
                conn.commit()
                
                return True, "Access granted"
                    
        except Exception as e:
            print(f"Error validating access: {e}")
            return False, f"Database error: {str(e)}"
    
    def _check_rate_limit(self, access_code: str) -> bool:
        """Check rate limiting (requests per minute)"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        if access_code in self.rate_limit_cache:
            self.rate_limit_cache[access_code] = [
                t for t in self.rate_limit_cache[access_code] 
                if t > minute_ago
            ]
        else:
            self.rate_limit_cache[access_code] = []
        
        # Get user's rate limit
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT rate_limit FROM users WHERE access_code = %s', (access_code,))
                result = cursor.fetchone()
                rate_limit = result[0] if result else 10
        except:
            rate_limit = 10
        
        # Check if under limit
        if len(self.rate_limit_cache[access_code]) >= rate_limit:
            return False
        
        # Add current request
        self.rate_limit_cache[access_code].append(now)
        return True
    
    def _check_daily_limit(self, access_code: str) -> bool:
        """Check daily request limit"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if usage_records table exists
                cursor.execute('''
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'usage_records'
                    )
                ''')
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    # If table doesn't exist, allow the request
                    return True
                
                # Count today's requests
                cursor.execute('''
                    SELECT COUNT(*) FROM usage_records 
                    WHERE access_code = %s AND DATE(timestamp) = CURRENT_DATE
                ''', (access_code,))
                
                today_requests = cursor.fetchone()[0]
                
                # Get user's daily limit
                cursor.execute('SELECT daily_limit FROM users WHERE access_code = %s', (access_code,))
                result = cursor.fetchone()
                daily_limit = result[0] if result else 100
                
                return today_requests < daily_limit
        except Exception as e:
            print(f"Error in _check_daily_limit: {e}")
            return True  # Allow if database error
    
    def _check_monthly_budget(self, access_code: str) -> bool:
        """Check monthly budget limit"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if usage_records table exists
                cursor.execute('''
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'usage_records'
                    )
                ''')
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    # If table doesn't exist, allow the request
                    return True
                
                # Sum this month's costs
                cursor.execute('''
                    SELECT COALESCE(SUM(cost), 0) FROM usage_records 
                    WHERE access_code = %s AND timestamp >= DATE_TRUNC('month', CURRENT_DATE)
                ''', (access_code,))
                
                month_cost = cursor.fetchone()[0]
                
                # Get user's monthly budget
                cursor.execute('SELECT monthly_budget FROM users WHERE access_code = %s', (access_code,))
                result = cursor.fetchone()
                monthly_budget = result[0] if result else 10.0
                
                return month_cost < monthly_budget
        except Exception as e:
            print(f"Error in _check_monthly_budget: {e}")
            return True  # Allow if database error
    
    def record_usage(self, access_code: str, usage_info: Dict) -> bool:
        """Record usage for cost tracking - NO sensitive data stored"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Only store non-sensitive usage data
                safe_usage_info = {
                    'request_type': usage_info.get('request_type', 'unknown'),
                    'tokens_used': usage_info.get('tokens_used', 0),
                    'cost': usage_info.get('cost', 0.0),
                    'prompt_length': usage_info.get('prompt_length', 0),
                    'response_length': usage_info.get('response_length', 0),
                    'success': usage_info.get('success', True),
                    'error_message': usage_info.get('error_message', '')
                }
                
                # Insert usage record - NO sensitive data
                cursor.execute('''
                    INSERT INTO usage_records (
                        access_code, request_type, tokens_used, cost,
                        prompt_length, response_length, success, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    access_code,
                    safe_usage_info['request_type'],
                    safe_usage_info['tokens_used'],
                    safe_usage_info['cost'],
                    safe_usage_info['prompt_length'],
                    safe_usage_info['response_length'],
                    safe_usage_info['success'],
                    safe_usage_info['error_message']
                ))
                
                # Update user totals - NO sensitive data
                cursor.execute('''
                    UPDATE users SET 
                        total_requests = total_requests + 1,
                        total_cost = total_cost + %s,
                        total_tokens = total_tokens + %s,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE access_code = %s
                ''', (
                    safe_usage_info['cost'],
                    safe_usage_info['tokens_used'],
                    access_code
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error recording usage: {e}")
            return False
    
    def get_user_stats(self, access_code: str) -> Dict:
        """Get comprehensive user statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Get user info
                cursor.execute('SELECT * FROM users WHERE access_code = %s', (access_code,))
                user = cursor.fetchone()
                
                if not user:
                    return {}
                
                # Get today's usage
                cursor.execute('''
                    SELECT COUNT(*) as requests, COALESCE(SUM(cost), 0) as cost 
                    FROM usage_records 
                    WHERE access_code = %s AND DATE(timestamp) = CURRENT_DATE
                ''', (access_code,))
                today_stats = cursor.fetchone()
                
                # Get this month's usage
                cursor.execute('''
                    SELECT COUNT(*) as requests, COALESCE(SUM(cost), 0) as cost 
                    FROM usage_records 
                    WHERE access_code = %s AND timestamp >= DATE_TRUNC('month', CURRENT_DATE)
                ''', (access_code,))
                month_stats = cursor.fetchone()
                
                return {
                    'access_code': user['access_code'],
                    'is_active': user['is_active'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else '',
                    'last_activity': user['last_activity'].isoformat() if user['last_activity'] else '',
                    'total_requests': user['total_requests'],
                    'total_cost': float(user['total_cost']),
                    'total_tokens': user['total_tokens'],
                    'daily_limit': user['daily_limit'],
                    'monthly_budget': float(user['monthly_budget']),
                    'rate_limit': user['rate_limit'],
                    'billing_status': user['billing_status'],
                    'today_requests': today_stats['requests'],
                    'today_cost': float(today_stats['cost']),
                    'month_requests': month_stats['requests'],
                    'month_cost': float(month_stats['cost']),
                    'requests_remaining': max(0, user['daily_limit'] - today_stats['requests']),
                    'budget_remaining': max(0, float(user['monthly_budget']) - float(month_stats['cost']))
                }
                
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {}
    
    def generate_access_code(self) -> str:
        """Generate a unique 16-character alphanumeric access code"""
        while True:
            # Use both uppercase and lowercase letters + digits for more randomness
            code = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT 1 FROM users WHERE access_code = %s', (code,))
                    if not cursor.fetchone():
                        return code
            except:
                return code  # Return if database error
    
    def create_user_account(self, stripe_customer_id: str, access_code: str, 
                           daily_limit: int = 100, monthly_budget: float = 10.0) -> bool:
        """Create a new user account with Stripe customer ID - NO PII stored"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if access code already exists
                cursor.execute('SELECT 1 FROM users WHERE access_code = %s', (access_code,))
                if cursor.fetchone():
                    return False
                
                # Check if stripe customer already exists
                cursor.execute('SELECT 1 FROM users WHERE stripe_customer_id = %s', (stripe_customer_id,))
                if cursor.fetchone():
                    return False
                
                # Create user - only non-PII data
                cursor.execute('''
                    INSERT INTO users (
                        access_code, stripe_customer_id, daily_limit, monthly_budget
                    ) VALUES (%s, %s, %s, %s)
                ''', (
                    access_code, stripe_customer_id, daily_limit, monthly_budget
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error creating user account: {e}")
            return False
    
    def get_user_by_stripe_customer_id(self, stripe_customer_id: str) -> Optional[UserProfile]:
        """Get user profile by Stripe customer ID - NO PII returned"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('SELECT * FROM users WHERE stripe_customer_id = %s', (stripe_customer_id,))
                user = cursor.fetchone()
                
                if user:
                    return UserProfile(**dict(user))
                return None
        except Exception as e:
            print(f"Error getting user by Stripe customer ID: {e}")
            return None
    
    def update_user_billing_status(self, access_code: str, status: str) -> bool:
        """Update user's billing status"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET billing_status = %s WHERE access_code = %s
                ''', (status, access_code))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating billing status: {e}")
            return False
    
    def get_all_users_summary(self) -> List[Dict]:
        """Get summary of all users - NO PII returned"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('''
                    SELECT access_code, stripe_customer_id, is_active, 
                           total_requests, total_cost, total_tokens,
                           daily_limit, monthly_budget, billing_status,
                           created_at, last_activity
                    FROM users
                    ORDER BY created_at DESC
                ''')
                users = cursor.fetchall()
                return [dict(user) for user in users]
        except Exception as e:
            print(f"Error getting users summary: {e}")
            return []
    

    
    def cancel_user_subscription(self, access_code: str) -> bool:
        """Cancel user subscription"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET billing_status = 'cancelled' 
                    WHERE access_code = %s
                ''', (access_code,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error cancelling subscription: {e}")
            return False
    
    def renew_user_subscription(self, access_code: str) -> bool:
        """Renew cancelled subscription"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET billing_status = 'active' 
                    WHERE access_code = %s AND billing_status = 'cancelled'
                ''', (access_code,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error renewing subscription: {e}")
            return False
    
    def create_user(self, access_code: str, stripe_customer_id: str = "", 
                   daily_limit: int = 100, monthly_budget: float = 10.0) -> bool:
        """Create a new user - NO PII stored locally"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if access code already exists
                cursor.execute('SELECT 1 FROM users WHERE access_code = %s', (access_code,))
                if cursor.fetchone():
                    return False
                
                # Create user - only non-PII data
                cursor.execute('''
                    INSERT INTO users (
                        access_code, stripe_customer_id, daily_limit, monthly_budget,
                        is_active, billing_status
                    ) VALUES (%s, %s, %s, %s, TRUE, 'active')
                ''', (
                    access_code, stripe_customer_id, daily_limit, monthly_budget
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

# Create global instance
user_manager = UserManagerPostgreSQL() 