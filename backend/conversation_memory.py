import sqlite3
import json
import hashlib
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import gc

class ConversationMemory:
    """Manages conversation history for each user with context-aware memory"""
    
    def __init__(self, db_path: str = "./conversation_memory.db"):
        self.db_path = db_path
        self.max_conversations_per_user = 10
        self.max_messages_per_conversation = 50
        self.max_conversation_age_days = 30
        
        # Initialize database
        self._init_database()
        self._cleanup_old_data()
    
    def _init_database(self):
        """Initialize SQLite database for conversation memory"""
        with sqlite3.connect(self.db_path) as conn:
            # Create conversations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    access_code TEXT NOT NULL,
                    conversation_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Create messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,  -- 'user' or 'assistant'
                    content TEXT NOT NULL,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    context_data TEXT,  -- JSON string of context when message was sent
                    context_type TEXT DEFAULT 'general',
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_access_code ON conversations(access_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_id ON conversations(conversation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role)")
            
            conn.commit()
    
    def _generate_conversation_id(self, access_code: str) -> str:
        """Generate unique conversation ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{access_code}_{timestamp}".encode()).hexdigest()
    
    def _cleanup_old_data(self):
        """Clean up old conversation data"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=self.max_conversation_age_days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Delete old conversations and their messages
                conn.execute("DELETE FROM conversations WHERE last_updated < ?", (cutoff_date,))
                deleted_count = conn.total_changes
                
                if deleted_count > 0:
                    print(f"Cleaned up {deleted_count} old conversations")
                
                conn.commit()
                
        except Exception as e:
            print(f"Error in conversation cleanup: {e}")
    
    def _enforce_memory_limits(self, access_code: str):
        """Enforce memory limits by removing oldest conversations"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get count of conversations for this user
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM conversations WHERE access_code = ? AND is_active = 1",
                    (access_code,)
                )
                count = cursor.fetchone()[0]
                
                if count > self.max_conversations_per_user:
                    # Get oldest conversations to remove
                    cursor = conn.execute("""
                        SELECT conversation_id FROM conversations 
                        WHERE access_code = ? AND is_active = 1 
                        ORDER BY last_updated ASC 
                        LIMIT ?
                    """, (access_code, count - self.max_conversations_per_user))
                    
                    old_conversations = [row[0] for row in cursor.fetchall()]
                    
                    # Delete messages from old conversations
                    for conv_id in old_conversations:
                        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
                    
                    # Mark conversations as inactive
                    conn.execute("""
                        UPDATE conversations 
                        SET is_active = 0 
                        WHERE conversation_id IN ({})
                    """.format(','.join(['?' for _ in old_conversations])), old_conversations)
                    
                    print(f"Enforced memory limits for {access_code}: removed {len(old_conversations)} old conversations")
                
                conn.commit()
                
        except Exception as e:
            print(f"Error enforcing memory limits: {e}")
    
    def start_conversation(self, access_code: str, title: str = None) -> str:
        """Start a new conversation and return conversation ID"""
        try:
            conversation_id = self._generate_conversation_id(access_code)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO conversations (access_code, conversation_id, title, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (access_code, conversation_id, title or "New Conversation", datetime.now().isoformat()))
                
                conn.commit()
            
            # Enforce memory limits
            self._enforce_memory_limits(access_code)
            
            return conversation_id
            
        except Exception as e:
            print(f"Error starting conversation: {e}")
            return None
    
    def add_message(self, conversation_id: str, role: str, content: str, 
                   context_data: Dict = None, context_type: str = "general") -> bool:
        """Add a message to a conversation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Add message
                conn.execute("""
                    INSERT INTO messages (conversation_id, role, content, context_data, context_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    conversation_id, 
                    role, 
                    content, 
                    json.dumps(context_data) if context_data else None,
                    context_type
                ))
                
                # Update conversation metadata
                conn.execute("""
                    UPDATE conversations 
                    SET message_count = message_count + 1, last_updated = ?
                    WHERE conversation_id = ?
                """, (datetime.now().isoformat(), conversation_id))
                
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Error adding message: {e}")
            return False
    
    def get_conversation_history(self, conversation_id: str, max_messages: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT role, content, context_data, context_type, timestamp
                    FROM messages 
                    WHERE conversation_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (conversation_id, max_messages))
                
                messages = []
                for row in cursor.fetchall():
                    role, content, context_data, context_type, timestamp = row
                    messages.append({
                        'role': role,
                        'content': content,
                        'context_data': json.loads(context_data) if context_data else None,
                        'context_type': context_type,
                        'timestamp': timestamp
                    })
                
                # Return in chronological order (oldest first)
                return list(reversed(messages))
                
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    def get_active_conversation(self, access_code: str) -> Optional[str]:
        """Get the most recent active conversation for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT conversation_id 
                    FROM conversations 
                    WHERE access_code = ? AND is_active = 1
                    ORDER BY last_updated DESC
                    LIMIT 1
                """, (access_code,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            print(f"Error getting active conversation: {e}")
            return None
    
    def get_user_conversations(self, access_code: str) -> List[Dict]:
        """Get all conversations for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT conversation_id, title, created_at, last_updated, message_count
                    FROM conversations 
                    WHERE access_code = ? AND is_active = 1
                    ORDER BY last_updated DESC
                """, (access_code,))
                
                conversations = []
                for row in cursor.fetchall():
                    conv_id, title, created_at, last_updated, message_count = row
                    conversations.append({
                        'conversation_id': conv_id,
                        'title': title,
                        'created_at': created_at,
                        'last_updated': last_updated,
                        'message_count': message_count
                    })
                
                return conversations
                
        except Exception as e:
            print(f"Error getting user conversations: {e}")
            return []
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear all messages from a conversation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
                conn.execute("""
                    UPDATE conversations 
                    SET message_count = 0, last_updated = ?
                    WHERE conversation_id = ?
                """, (datetime.now().isoformat(), conversation_id))
                
                conn.commit()
            return True
            
        except Exception as e:
            print(f"Error clearing conversation: {e}")
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
                conn.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
                
                conn.commit()
            return True
            
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def format_conversation_context(self, conversation_id: str, max_messages: int = 5) -> str:
        """Format conversation history as context for AI"""
        try:
            messages = self.get_conversation_history(conversation_id, max_messages)
            
            if not messages:
                return ""
            
            context = "\n\n=== CONVERSATION HISTORY ===\n"
            
            for i, msg in enumerate(messages, 1):
                role_emoji = "👤" if msg['role'] == 'user' else "🤖"
                context += f"\n{role_emoji} {msg['role'].title()} (Message {i}):\n{msg['content']}\n"
                
                # Add context data if available
                if msg['context_data']:
                    context += f"Context: {json.dumps(msg['context_data'], indent=2)[:200]}...\n"
            
            return context
            
        except Exception as e:
            print(f"Error formatting conversation context: {e}")
            return ""
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get conversation stats
                cursor = conn.execute("SELECT COUNT(*) FROM conversations WHERE is_active = 1")
                active_conversations = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT access_code) FROM conversations WHERE is_active = 1")
                unique_users = cursor.fetchone()[0]
                
                return {
                    'active_conversations': active_conversations,
                    'total_messages': total_messages,
                    'unique_users': unique_users,
                    'database_size_mb': os.path.getsize(self.db_path) / (1024 * 1024)
                }
                
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {} 