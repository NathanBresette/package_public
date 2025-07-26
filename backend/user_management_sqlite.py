"""
User Management System for RStudio AI - SQLite Version
Handles user access, cost tracking, monitoring, and revocation
Uses SQLite for better performance and memory efficiency
"""

import os
import sqlite3
import time
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib
import threading

@dataclass
class UserProfile:
    """User profile with access control and cost tracking"""
    access_code: str
    user_name: str
    email: str = ""
    password_hash: str = ""
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

class UserManagerSQLite:
    """Manages users, access control, and cost tracking using SQLite"""
    
    def __init__(self, db_file: str = "users.db"):
        self.db_file = db_file
        self.rate_limit_cache: Dict[str, List[float]] = {}
        self.lock = threading.Lock()  # For thread safety
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database exists with proper schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    access_code TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT,
                    user_name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_activity TEXT,
                    total_requests INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0.0,
                    total_tokens INTEGER DEFAULT 0,
                    daily_limit INTEGER DEFAULT 100,
                    monthly_budget REAL DEFAULT 10.0,
                    rate_limit INTEGER DEFAULT 10,
                    context_count INTEGER DEFAULT 0,
                    notes TEXT,
                    billing_status TEXT DEFAULT 'inactive'
                )
            ''')
            
            # Create usage_records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    access_code TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    request_type TEXT NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    prompt_length INTEGER DEFAULT 0,
                    response_length INTEGER DEFAULT 0,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    FOREIGN KEY (access_code) REFERENCES users (access_code)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_access_code ON users(access_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_access_code ON usage_records(access_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp)')
            
            conn.commit()
    
    def _get_connection(self):
        """Get database connection with proper configuration"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def validate_access(self, access_code: str) -> Tuple[bool, str]:
        """Validate user access and check limits"""
        with self.lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Get user
                    cursor.execute('''
                        SELECT * FROM users WHERE access_code = ? AND is_active = 1
                    ''', (access_code,))
                    user = cursor.fetchone()
                    
                    if not user:
                        return False, "Invalid or inactive access code"
                    
                    # Check rate limit
                    if not self._check_rate_limit(access_code):
                        return False, "Rate limit exceeded"
                    
                    # Check daily limit
                    if not self._check_daily_limit(access_code):
                        return False, "Daily limit exceeded"
                    
                    # Check monthly budget
                    if not self._check_monthly_budget(access_code):
                        return False, "Monthly budget exceeded"
                    
                    # Update last activity
                    cursor.execute('''
                        UPDATE users SET last_activity = ? WHERE access_code = ?
                    ''', (datetime.now().isoformat(), access_code))
                    conn.commit()
                    
                    return True, "Access granted"
                    
            except Exception as e:
                print(f"Error validating access: {e}")
                return False, "Database error"
    
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT rate_limit FROM users WHERE access_code = ?', (access_code,))
            user = cursor.fetchone()
            rate_limit = user['rate_limit'] if user else 10
        
        # Check if under limit
        if len(self.rate_limit_cache[access_code]) >= rate_limit:
            return False
        
        # Add current request
        self.rate_limit_cache[access_code].append(now)
        return True
    
    def _check_daily_limit(self, access_code: str) -> bool:
        """Check daily request limit"""
        today = datetime.now().date().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Count today's requests
            cursor.execute('''
                SELECT COUNT(*) as count FROM usage_records 
                WHERE access_code = ? AND date(timestamp) = ?
            ''', (access_code, today))
            
            today_requests = cursor.fetchone()['count']
            
            # Get user's daily limit
            cursor.execute('SELECT daily_limit FROM users WHERE access_code = ?', (access_code,))
            user = cursor.fetchone()
            daily_limit = user['daily_limit'] if user else 100
            
            return today_requests < daily_limit
    
    def _check_monthly_budget(self, access_code: str) -> bool:
        """Check monthly budget limit"""
        month_start = datetime.now().replace(day=1).date().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Sum this month's costs
            cursor.execute('''
                SELECT COALESCE(SUM(cost), 0) as total_cost FROM usage_records 
                WHERE access_code = ? AND date(timestamp) >= ?
            ''', (access_code, month_start))
            
            month_cost = cursor.fetchone()['total_cost']
            
            # Get user's monthly budget
            cursor.execute('SELECT monthly_budget FROM users WHERE access_code = ?', (access_code,))
            user = cursor.fetchone()
            monthly_budget = user['monthly_budget'] if user else 10.0
            
            return month_cost < monthly_budget
    
    def record_usage(self, access_code: str, usage_info: Dict) -> bool:
        """Record usage for cost tracking"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert usage record
                cursor.execute('''
                    INSERT INTO usage_records (
                        access_code, timestamp, request_type, tokens_used, cost,
                        prompt_length, response_length, success, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    access_code,
                    datetime.now().isoformat(),
                    usage_info.get('request_type', 'unknown'),
                    usage_info.get('tokens_used', 0),
                    usage_info.get('cost', 0.0),
                    usage_info.get('prompt_length', 0),
                    usage_info.get('response_length', 0),
                    usage_info.get('success', True),
                    usage_info.get('error_message', '')
                ))
                
                # Update user totals
                cursor.execute('''
                    UPDATE users SET 
                        total_requests = total_requests + 1,
                        total_cost = total_cost + ?,
                        total_tokens = total_tokens + ?,
                        last_activity = ?
                    WHERE access_code = ?
                ''', (
                    usage_info.get('cost', 0.0),
                    usage_info.get('tokens_used', 0),
                    datetime.now().isoformat(),
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
                cursor = conn.cursor()
                
                # Get user info
                cursor.execute('SELECT * FROM users WHERE access_code = ?', (access_code,))
                user = cursor.fetchone()
                
                if not user:
                    return {}
                
                # Get today's usage
                today = datetime.now().date().isoformat()
                cursor.execute('''
                    SELECT COUNT(*) as requests, COALESCE(SUM(cost), 0) as cost 
                    FROM usage_records 
                    WHERE access_code = ? AND date(timestamp) = ?
                ''', (access_code, today))
                today_stats = cursor.fetchone()
                
                # Get this month's usage
                month_start = datetime.now().replace(day=1).date().isoformat()
                cursor.execute('''
                    SELECT COUNT(*) as requests, COALESCE(SUM(cost), 0) as cost 
                    FROM usage_records 
                    WHERE access_code = ? AND date(timestamp) >= ?
                ''', (access_code, month_start))
                month_stats = cursor.fetchone()
                
                return {
                    'access_code': user['access_code'],
                    'user_name': user['user_name'],
                    'email': user['email'],
                    'is_active': bool(user['is_active']),
                    'created_at': user['created_at'],
                    'last_activity': user['last_activity'],
                    'total_requests': user['total_requests'],
                    'total_cost': user['total_cost'],
                    'total_tokens': user['total_tokens'],
                    'daily_limit': user['daily_limit'],
                    'monthly_budget': user['monthly_budget'],
                    'rate_limit': user['rate_limit'],
                    'billing_status': user['billing_status'],
                    'today_requests': today_stats['requests'],
                    'today_cost': today_stats['cost'],
                    'month_requests': month_stats['requests'],
                    'month_cost': month_stats['cost'],
                    'requests_remaining': max(0, user['daily_limit'] - today_stats['requests']),
                    'budget_remaining': max(0, user['monthly_budget'] - month_stats['cost'])
                }
                
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {}
    
    def get_all_users_summary(self) -> List[Dict]:
        """Get summary of all users for admin dashboard"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        u.*,
                        COUNT(ur.id) as recent_requests,
                        COALESCE(SUM(ur.cost), 0) as recent_cost
                    FROM users u
                    LEFT JOIN usage_records ur ON u.access_code = ur.access_code 
                        AND ur.timestamp >= datetime('now', '-7 days')
                    GROUP BY u.access_code
                    ORDER BY u.created_at DESC
                ''')
                
                users = cursor.fetchall()
                return [dict(user) for user in users]
                
        except Exception as e:
            print(f"Error getting users summary: {e}")
            return []
    
    def create_user(self, access_code: str, user_name: str, email: str = "", 
                   daily_limit: int = 100, monthly_budget: float = 10.0) -> bool:
        """Create a new user"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users (
                        access_code, user_name, email, created_at, daily_limit, monthly_budget
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    access_code, user_name, email, 
                    datetime.now().isoformat(), daily_limit, monthly_budget
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def update_user(self, access_code: str, updates: Dict) -> bool:
        """Update user information"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                values = []
                
                for key, value in updates.items():
                    if key in ['user_name', 'email', 'daily_limit', 'monthly_budget', 
                              'rate_limit', 'notes', 'billing_status']:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if not set_clauses:
                    return False
                
                values.append(access_code)
                query = f"UPDATE users SET {', '.join(set_clauses)} WHERE access_code = ?"
                
                cursor.execute(query, values)
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
    
    def disable_user(self, access_code: str) -> bool:
        """Disable a user"""
        return self.update_user(access_code, {'is_active': False})
    
    def enable_user(self, access_code: str) -> bool:
        """Enable a user"""
        return self.update_user(access_code, {'is_active': True})
    
    def delete_user(self, access_code: str) -> bool:
        """Delete a user and their usage records"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete usage records first (foreign key constraint)
                cursor.execute('DELETE FROM usage_records WHERE access_code = ?', (access_code,))
                
                # Delete user
                cursor.execute('DELETE FROM users WHERE access_code = ?', (access_code,))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False
    
    def generate_access_code(self) -> str:
        """Generate a unique 16-character alphanumeric access code"""
        while True:
            # Use both uppercase and lowercase letters + digits for more randomness
            code = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM users WHERE access_code = ?', (code,))
                if not cursor.fetchone():
                    return code
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        return self.hash_password(password) == password_hash
    
    def create_user_account(self, email: str, password: str, access_code: str, 
                           user_name: str = "", daily_limit: int = 100, 
                           monthly_budget: float = 10.0) -> bool:
        """Create a new user account with email/password"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if email already exists
                cursor.execute('SELECT 1 FROM users WHERE email = ?', (email,))
                if cursor.fetchone():
                    return False
                
                # Check if access code already exists
                cursor.execute('SELECT 1 FROM users WHERE access_code = ?', (access_code,))
                if cursor.fetchone():
                    return False
                
                # Create user
                password_hash = self.hash_password(password)
                user_name = user_name or email.split('@')[0]
                
                cursor.execute('''
                    INSERT INTO users (
                        access_code, email, password_hash, user_name, created_at,
                        daily_limit, monthly_budget
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    access_code, email, password_hash, user_name,
                    datetime.now().isoformat(), daily_limit, monthly_budget
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error creating user account: {e}")
            return False
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user with email and password"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM users WHERE email = ? AND is_active = 1
                ''', (email,))
                user = cursor.fetchone()
                
                if user and self.verify_password(password, user['password_hash']):
                    return dict(user)
                
                return None
                
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user profile by email"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
                user = cursor.fetchone()
                
                if user:
                    return UserProfile(**dict(user))
                
                return None
                
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    def update_user_billing_status(self, email: str, status: str) -> bool:
        """Update user's billing status"""
        return self.update_user_by_email(email, {'billing_status': status})
    
    def update_user_by_email(self, email: str, updates: Dict) -> bool:
        """Update user by email"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                set_clauses = []
                values = []
                
                for key, value in updates.items():
                    if key in ['user_name', 'email', 'daily_limit', 'monthly_budget', 
                              'rate_limit', 'notes', 'billing_status']:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if not set_clauses:
                    return False
                
                values.append(email)
                query = f"UPDATE users SET {', '.join(set_clauses)} WHERE email = ?"
                
                cursor.execute(query, values)
                conn.commit()
                
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error updating user by email: {e}")
            return False
    
    def get_usage_analytics(self, access_code: str = None, days: int = 30) -> Dict:
        """Get usage analytics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if access_code:
                    # User-specific analytics
                    cursor.execute('''
                        SELECT 
                            date(timestamp) as date,
                            COUNT(*) as requests,
                            COALESCE(SUM(cost), 0) as cost,
                            COALESCE(SUM(tokens_used), 0) as tokens
                        FROM usage_records 
                        WHERE access_code = ? AND timestamp >= datetime('now', '-{} days')
                        GROUP BY date(timestamp)
                        ORDER BY date
                    '''.format(days), (access_code,))
                else:
                    # System-wide analytics
                    cursor.execute('''
                        SELECT 
                            date(timestamp) as date,
                            COUNT(*) as requests,
                            COALESCE(SUM(cost), 0) as cost,
                            COALESCE(SUM(tokens_used), 0) as tokens
                        FROM usage_records 
                        WHERE timestamp >= datetime('now', '-{} days')
                        GROUP BY date(timestamp)
                        ORDER BY date
                    '''.format(days))
                
                records = cursor.fetchall()
                
                return {
                    'daily_data': [dict(record) for record in records],
                    'total_requests': sum(r['requests'] for r in records),
                    'total_cost': sum(r['cost'] for r in records),
                    'total_tokens': sum(r['tokens'] for r in records)
                }
                
        except Exception as e:
            print(f"Error getting usage analytics: {e}")
            return {'daily_data': [], 'total_requests': 0, 'total_cost': 0, 'total_tokens': 0}

# Create global instance
user_manager = UserManagerSQLite() 