"""
Memory-only context system - NO PII persistence
Processes context in real-time without storing sensitive data
"""

import hashlib
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import threading

class MemoryOnlyContext:
    """Memory-only context processing - NO persistent storage of user data"""
    
    def __init__(self):
        self.session_contexts = {}  # Temporary session storage
        self.lock = threading.Lock()
        self.max_session_age_minutes = 30  # Clear after 30 minutes of inactivity
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _cleanup_expired_sessions(self):
        """Clean up expired session data"""
        with self.lock:
            current_time = datetime.now()
            expired_sessions = []
            
            for access_code, session_data in self.session_contexts.items():
                if current_time - session_data['last_activity'] > timedelta(minutes=self.max_session_age_minutes):
                    expired_sessions.append(access_code)
            
            for access_code in expired_sessions:
                del self.session_contexts[access_code]
                print(f"Cleared expired session for {access_code}")
    
    def process_context(self, access_code: str, context_data: Dict, context_type: str = "general") -> str:
        """Process context in memory only - NO persistence"""
        with self.lock:
            # Clean up expired sessions
            self._cleanup_expired_sessions()
            
            # Initialize session if needed
            if access_code not in self.session_contexts:
                self.session_contexts[access_code] = {
                    'contexts': [],
                    'last_activity': datetime.now()
                }
            
            # Update last activity
            self.session_contexts[access_code]['last_activity'] = datetime.now()
            
            # Process context (no storage)
            context_hash = self._generate_content_hash(json.dumps(context_data, sort_keys=True))
            
            # Return context hash for reference (not stored)
            return context_hash
    
    def get_session_contexts(self, access_code: str) -> List[Dict]:
        """Get current session contexts - NO persistent data"""
        with self.lock:
            if access_code not in self.session_contexts:
                return []
            
            # Update last activity
            self.session_contexts[access_code]['last_activity'] = datetime.now()
            
            # Return empty list (no persistent context)
            return []
    
    def clear_session(self, access_code: str):
        """Clear session data immediately"""
        with self.lock:
            if access_code in self.session_contexts:
                del self.session_contexts[access_code]
                print(f"Cleared session for {access_code}")
    
    def get_session_stats(self, access_code: str) -> Dict:
        """Get session statistics - NO persistent data"""
        with self.lock:
            if access_code not in self.session_contexts:
                return {
                    'context_count': 0,
                    'last_activity': None,
                    'session_active': False
                }
            
            session_data = self.session_contexts[access_code]
            return {
                'context_count': len(session_data['contexts']),
                'last_activity': session_data['last_activity'].isoformat(),
                'session_active': True
            }
    
    def cleanup_all_sessions(self):
        """Clear all session data"""
        with self.lock:
            self.session_contexts.clear()
            print("Cleared all session data")

# Global instance
memory_context = MemoryOnlyContext() 