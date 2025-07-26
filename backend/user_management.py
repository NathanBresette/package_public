"""
User Management System for RStudio AI
Handles user access, cost tracking, monitoring, and revocation
"""

import os
import json
import time
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class UserProfile:
    """User profile with access control and cost tracking"""
    access_code: str
    user_name: str
    email: str = ""
    is_active: bool = True
    is_admin: bool = False
    created_at: str = ""
    last_activity: str = ""
    total_requests: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    daily_limit: int = 100  # requests per day
    monthly_budget: float = 10.0  # USD per month
    rate_limit: int = 10  # requests per minute
    context_count: int = 0
    notes: str = ""

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

class UserManager:
    """Manages users, access control, and cost tracking"""
    
    def __init__(self, data_file: str = "user_data.json"):
        self.data_file = data_file
        self.users: Dict[str, UserProfile] = {}
        self.usage_records: List[UsageRecord] = []
        self.rate_limit_cache: Dict[str, List[float]] = {}
        self.load_data()
    
    def load_data(self):
        """Load user data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.users = {
                        code: UserProfile(**user_data) 
                        for code, user_data in data.get('users', {}).items()
                    }
                    self.usage_records = [
                        UsageRecord(**record) 
                        for record in data.get('usage_records', [])
                    ]
        except Exception as e:
            print(f"Error loading user data: {e}")
            self._create_default_users()
    
    def save_data(self):
        """Save user data to file"""
        try:
            data = {
                'users': {code: asdict(user) for code, user in self.users.items()},
                'usage_records': [asdict(record) for record in self.usage_records]
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving user data: {e}")
    
    def _create_default_users(self):
        """Create default users if no data exists"""
        default_users = {
            "DEMO123": UserProfile(
                access_code="DEMO123",
                user_name="Demo User",
                email="demo@example.com",
                created_at=datetime.now().isoformat(),
                daily_limit=50,
                monthly_budget=5.0
            ),
            "TEST456": UserProfile(
                access_code="TEST456", 
                user_name="Test User",
                email="test@example.com",
                created_at=datetime.now().isoformat(),
                daily_limit=100,
                monthly_budget=10.0
            ),
            "FAKE123": UserProfile(
                access_code="FAKE123",
                user_name="Development User", 
                email="dev@example.com",
                created_at=datetime.now().isoformat(),
                daily_limit=200,
                monthly_budget=20.0
            )
        }
        self.users = default_users
        self.save_data()
    
    def validate_access(self, access_code: str) -> Tuple[bool, str]:
        """Validate user access with rate limiting and budget checks"""
        if access_code not in self.users:
            return False, "Invalid access code"
        
        user = self.users[access_code]
        
        # Check if user is active
        if not user.is_active:
            return False, "User account is disabled"
        
        # Check rate limiting
        if not self._check_rate_limit(access_code):
            return False, "Rate limit exceeded"
        
        # Check daily limit
        if not self._check_daily_limit(access_code):
            return False, "Daily request limit exceeded"
        
        # Check monthly budget
        if not self._check_monthly_budget(access_code):
            return False, "Monthly budget exceeded"
        
        # Update last activity
        user.last_activity = datetime.now().isoformat()
        self.save_data()
        
        return True, "Access granted"
    
    def _check_rate_limit(self, access_code: str) -> bool:
        """Check if user is within rate limit"""
        user = self.users[access_code]
        now = time.time()
        
        if access_code not in self.rate_limit_cache:
            self.rate_limit_cache[access_code] = []
        
        # Remove old requests (older than 1 minute)
        self.rate_limit_cache[access_code] = [
            req_time for req_time in self.rate_limit_cache[access_code]
            if now - req_time < 60
        ]
        
        # Check if under limit
        if len(self.rate_limit_cache[access_code]) >= user.rate_limit:
            return False
        
        # Add current request
        self.rate_limit_cache[access_code].append(now)
        return True
    
    def _check_daily_limit(self, access_code: str) -> bool:
        """Check if user is within daily request limit"""
        user = self.users[access_code]
        today = datetime.now().date()
        
        # Count today's requests
        today_requests = sum(
            1 for record in self.usage_records
            if record.access_code == access_code and
            datetime.fromisoformat(record.timestamp).date() == today
        )
        
        return today_requests < user.daily_limit
    
    def _check_monthly_budget(self, access_code: str) -> bool:
        """Check if user is within monthly budget"""
        user = self.users[access_code]
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate this month's costs
        monthly_cost = sum(
            record.cost for record in self.usage_records
            if record.access_code == access_code and
            datetime.fromisoformat(record.timestamp) >= month_start
        )
        
        return monthly_cost < user.monthly_budget
    
    def record_usage(self, access_code: str, usage_info: Dict) -> bool:
        """Record usage for cost tracking"""
        if access_code not in self.users:
            return False
        
        user = self.users[access_code]
        
        # Create usage record
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            access_code=access_code,
            request_type=usage_info.get('request_type', 'chat'),
            tokens_used=usage_info.get('total_tokens', 0),
            cost=usage_info.get('cost', 0.0),
            prompt_length=usage_info.get('prompt_length', 0),
            response_length=usage_info.get('response_length', 0),
            success=usage_info.get('success', True),
            error_message=usage_info.get('error_message', '')
        )
        
        # Add to records
        self.usage_records.append(record)
        
        # Update user stats
        user.total_requests += 1
        user.total_cost += record.cost
        user.total_tokens += record.tokens_used
        user.last_activity = record.timestamp
        
        self.save_data()
        return True
    
    def get_user_stats(self, access_code: str) -> Dict:
        """Get comprehensive user statistics"""
        if access_code not in self.users:
            return {}
        
        user = self.users[access_code]
        now = datetime.now()
        today = now.date()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate today's usage
        today_requests = sum(
            1 for record in self.usage_records
            if record.access_code == access_code and
            datetime.fromisoformat(record.timestamp).date() == today
        )
        
        today_cost = sum(
            record.cost for record in self.usage_records
            if record.access_code == access_code and
            datetime.fromisoformat(record.timestamp).date() == today
        )
        
        # Calculate this month's usage
        monthly_requests = sum(
            1 for record in self.usage_records
            if record.access_code == access_code and
            datetime.fromisoformat(record.timestamp) >= month_start
        )
        
        monthly_cost = sum(
            record.cost for record in self.usage_records
            if record.access_code == access_code and
            datetime.fromisoformat(record.timestamp) >= month_start
        )
        
        return {
            'user_profile': asdict(user),
            'today_requests': today_requests,
            'today_cost': today_cost,
            'monthly_requests': monthly_requests,
            'monthly_cost': monthly_cost,
            'daily_limit_remaining': max(0, user.daily_limit - today_requests),
            'monthly_budget_remaining': max(0, user.monthly_budget - monthly_cost),
            'rate_limit_remaining': max(0, user.rate_limit - len(self.rate_limit_cache.get(access_code, [])))
        }
    
    def get_all_users_summary(self) -> List[Dict]:
        """Get summary of all users for admin dashboard"""
        summaries = []
        now = datetime.now()
        today = now.date()
        
        for user in self.users.values():
            # Calculate today's usage
            today_requests = sum(
                1 for record in self.usage_records
                if record.access_code == user.access_code and
                datetime.fromisoformat(record.timestamp).date() == today
            )
            
            today_cost = sum(
                record.cost for record in self.usage_records
                if record.access_code == user.access_code and
                datetime.fromisoformat(record.timestamp).date() == today
            )
            
            summaries.append({
                'access_code': user.access_code,
                'user_name': user.user_name,
                'email': user.email,
                'is_active': user.is_active,
                'total_requests': user.total_requests,
                'total_cost': user.total_cost,
                'today_requests': today_requests,
                'today_cost': today_cost,
                'last_activity': user.last_activity,
                'context_count': user.context_count
            })
        
        return sorted(summaries, key=lambda x: x['total_cost'], reverse=True)
    
    def create_user(self, access_code: str, user_name: str, email: str = "", 
                   daily_limit: int = 100, monthly_budget: float = 10.0) -> bool:
        """Create a new user"""
        if access_code in self.users:
            return False
        
        user = UserProfile(
            access_code=access_code,
            user_name=user_name,
            email=email,
            created_at=datetime.now().isoformat(),
            daily_limit=daily_limit,
            monthly_budget=monthly_budget
        )
        
        self.users[access_code] = user
        self.save_data()
        return True
    
    def update_user(self, access_code: str, updates: Dict) -> bool:
        """Update user settings"""
        if access_code not in self.users:
            return False
        
        user = self.users[access_code]
        
        # Update allowed fields
        allowed_fields = ['user_name', 'email', 'daily_limit', 'monthly_budget', 
                         'rate_limit', 'notes']
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        self.save_data()
        return True
    
    def disable_user(self, access_code: str) -> bool:
        """Disable user access"""
        if access_code not in self.users:
            return False
        
        self.users[access_code].is_active = False
        self.save_data()
        return True
    
    def enable_user(self, access_code: str) -> bool:
        """Enable user access"""
        if access_code not in self.users:
            return False
        
        self.users[access_code].is_active = True
        self.save_data()
        return True
    
    def delete_user(self, access_code: str) -> bool:
        """Delete user and all their data"""
        if access_code not in self.users:
            return False
        
        # Remove user
        del self.users[access_code]
        
        # Remove usage records
        self.usage_records = [
            record for record in self.usage_records
            if record.access_code != access_code
        ]
        
        # Remove rate limit cache
        if access_code in self.rate_limit_cache:
            del self.rate_limit_cache[access_code]
        
        self.save_data()
        return True
    
    def generate_access_code(self) -> str:
        """Generate a unique access code for new users"""
        while True:
            # Generate a 6-character alphanumeric code
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Check if code already exists
            if code not in self.users:
                return code
    
    def get_usage_analytics(self, access_code: str = None, days: int = 30) -> Dict:
        """Get usage analytics for monitoring"""
        now = datetime.now()
        start_date = now - timedelta(days=days)
        
        if access_code:
            # Single user analytics
            user_records = [
                record for record in self.usage_records
                if record.access_code == access_code and
                datetime.fromisoformat(record.timestamp) >= start_date
            ]
        else:
            # All users analytics
            user_records = [
                record for record in self.usage_records
                if datetime.fromisoformat(record.timestamp) >= start_date
            ]
        
        # Calculate analytics
        total_requests = len(user_records)
        total_cost = sum(record.cost for record in user_records)
        total_tokens = sum(record.tokens_used for record in user_records)
        success_rate = sum(1 for r in user_records if r.success) / max(1, total_requests)
        
        # Daily breakdown
        daily_stats = {}
        for record in user_records:
            date = datetime.fromisoformat(record.timestamp).date()
            if date not in daily_stats:
                daily_stats[date] = {'requests': 0, 'cost': 0, 'tokens': 0}
            daily_stats[date]['requests'] += 1
            daily_stats[date]['cost'] += record.cost
            daily_stats[date]['tokens'] += record.tokens_used
        
        return {
            'period_days': days,
            'total_requests': total_requests,
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'success_rate': success_rate,
            'daily_breakdown': daily_stats,
            'avg_cost_per_request': total_cost / max(1, total_requests),
            'avg_tokens_per_request': total_tokens / max(1, total_requests)
        }

# Global user manager instance
user_manager = UserManager("user_data.json") 