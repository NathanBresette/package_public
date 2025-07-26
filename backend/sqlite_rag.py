import sqlite3
import json
import hashlib
import os
from typing import List, Dict, Optional
# SQLite RAG v2 - Force rebuild
from datetime import datetime, timedelta
import gc

class SQLiteRAG:
    """SQLite-based RAG system using FTS5 for memory-efficient context storage and retrieval"""
    
    def __init__(self, db_path: str = "./rag_context.db"):
        self.db_path = db_path
        self.max_contexts_per_user = 20
        self.max_total_contexts = 200
        self.max_context_age_days = 7
        
        # Initialize database
        self._init_database()
        self._cleanup_old_data()
    
    def _init_database(self):
        """Initialize SQLite database with FTS5 tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Create main context table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    access_code TEXT NOT NULL,
                    context_type TEXT NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    timestamp TEXT NOT NULL,
                    is_summarized BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create FTS5 virtual table for full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS contexts_fts USING fts5(
                    content,
                    context_type,
                    access_code,
                    content='contexts',
                    content_rowid='id'
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_access_code ON contexts(access_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON contexts(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON contexts(content_hash)")
            
            # Create triggers to keep FTS5 in sync
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS contexts_ai AFTER INSERT ON contexts BEGIN
                    INSERT INTO contexts_fts(rowid, content, context_type, access_code) 
                    VALUES (new.id, new.content, new.context_type, new.access_code);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS contexts_ad AFTER DELETE ON contexts BEGIN
                    INSERT INTO contexts_fts(contexts_fts, rowid, content, context_type, access_code) 
                    VALUES('delete', old.id, old.content, old.context_type, old.access_code);
                END
            """)
            
            conn.commit()
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _cleanup_old_data(self):
        """Clean up old context data"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=self.max_context_age_days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Delete old contexts
                conn.execute("DELETE FROM contexts WHERE timestamp < ?", (cutoff_date,))
                
                # Get count of deleted rows
                deleted_count = conn.total_changes
                if deleted_count > 0:
                    print(f"Cleaned up {deleted_count} old contexts")
                
                conn.commit()
                
        except Exception as e:
            print(f"Error in cleanup: {e}")
    
    def _enforce_memory_limits(self, access_code: str):
        """Enforce memory limits by removing oldest contexts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check total contexts
                total_count = conn.execute("SELECT COUNT(*) FROM contexts").fetchone()[0]
                
                if total_count > self.max_total_contexts:
                    # Remove oldest contexts
                    excess = total_count - self.max_total_contexts
                    conn.execute("""
                        DELETE FROM contexts WHERE id IN (
                            SELECT id FROM contexts ORDER BY timestamp ASC LIMIT ?
                        )
                    """, (excess,))
                    print(f"Removed {excess} oldest contexts due to total limit")
                
                # Check user-specific limits
                user_count = conn.execute(
                    "SELECT COUNT(*) FROM contexts WHERE access_code = ?", 
                    (access_code,)
                ).fetchone()[0]
                
                if user_count > self.max_contexts_per_user:
                    # Remove oldest contexts for this user
                    excess = user_count - self.max_contexts_per_user
                    conn.execute("""
                        DELETE FROM contexts WHERE id IN (
                            SELECT id FROM contexts 
                            WHERE access_code = ? 
                            ORDER BY timestamp ASC LIMIT ?
                        )
                    """, (access_code, excess))
                    print(f"Removed {excess} oldest contexts for user {access_code}")
                
                conn.commit()
                
        except Exception as e:
            print(f"Error enforcing memory limits: {e}")
    
    def store_context(self, access_code: str, context_data: Dict, context_type: str = "general") -> Optional[str]:
        """Store context data with deduplication"""
        try:
            # Convert context data to JSON string
            content = json.dumps(context_data, sort_keys=True)
            content_hash = self._generate_content_hash(content)
            
            # Check for duplicates
            with sqlite3.connect(self.db_path) as conn:
                existing = conn.execute(
                    "SELECT id FROM contexts WHERE content_hash = ?", 
                    (content_hash,)
                ).fetchone()
                
                if existing:
                    # Update timestamp for existing context
                    conn.execute(
                        "UPDATE contexts SET timestamp = ? WHERE content_hash = ?",
                        (datetime.now().isoformat(), content_hash)
                    )
                    conn.commit()
                    return str(existing[0])
            
            # Enforce memory limits before storing
            self._enforce_memory_limits(access_code)
            
            # Store new context
            with sqlite3.connect(self.db_path) as conn:
                metadata = {
                    "is_summarized": "workspace_summary" in context_data,
                    "summary_type": "environment_summary" if "workspace_summary" in context_data else "full_context"
                }
                
                cursor = conn.execute("""
                    INSERT INTO contexts (access_code, context_type, content_hash, content, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    access_code,
                    context_type,
                    content_hash,
                    content,
                    json.dumps(metadata),
                    datetime.now().isoformat()
                ))
                
                context_id = cursor.lastrowid
                conn.commit()
                
                # Force garbage collection
                gc.collect()
                
                return str(context_id)
                
        except Exception as e:
            print(f"Error storing context: {e}")
            return None
    
    def retrieve_relevant_context(self, access_code: str, query: str, n_results: int = 5) -> List[Dict]:
        """Retrieve relevant context using FTS5 search"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Use FTS5 for semantic search
                results = conn.execute("""
                    SELECT c.id, c.content, c.context_type, c.metadata, c.timestamp,
                           contexts_fts.rank
                    FROM contexts c
                    JOIN contexts_fts ON c.id = contexts_fts.rowid
                    WHERE contexts_fts.access_code = ?
                    AND contexts_fts MATCH ?
                    ORDER BY contexts_fts.rank DESC
                    LIMIT ?
                """, (access_code, query, n_results)).fetchall()
                
                relevant_contexts = []
                for row in results:
                    try:
                        context_id, content, context_type, metadata, timestamp, rank = row
                        context_data = json.loads(content)
                        metadata_dict = json.loads(metadata) if metadata else {}
                        
                        relevant_contexts.append({
                            "content": context_data,
                            "type": context_type,
                            "metadata": metadata_dict,
                            "distance": 1.0 - (rank / 1000.0),  # Convert rank to similarity score
                            "timestamp": timestamp
                        })
                    except json.JSONDecodeError:
                        continue
                
                return relevant_contexts
                
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return []
    
    def get_user_context_summary(self, access_code: str) -> Dict:
        """Get summary of user's context data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get context counts by type
                type_counts = conn.execute("""
                    SELECT context_type, COUNT(*) as count
                    FROM contexts
                    WHERE access_code = ?
                    GROUP BY context_type
                """, (access_code,)).fetchall()
                
                # Get recent contexts
                recent_contexts = conn.execute("""
                    SELECT context_type, timestamp, metadata
                    FROM contexts
                    WHERE access_code = ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                """, (access_code,)).fetchall()
                
                summary = {
                    "total_contexts": sum(count for _, count in type_counts),
                    "context_types": {ctx_type: count for ctx_type, count in type_counts},
                    "recent_contexts": []
                }
                
                for context_type, timestamp, metadata in recent_contexts:
                    metadata_dict = json.loads(metadata) if metadata else {}
                    summary["recent_contexts"].append({
                        "type": context_type,
                        "timestamp": timestamp,
                        "is_summarized": metadata_dict.get("is_summarized", False)
                    })
                
                return summary
                
        except Exception as e:
            print(f"Error getting context summary: {e}")
            return {"total_contexts": 0, "context_types": {}, "recent_contexts": []}
    
    def clear_user_context(self, access_code: str):
        """Clear all context for a specific user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM contexts WHERE access_code = ?", (access_code,))
                conn.commit()
                print(f"Cleared all contexts for user {access_code}")
        except Exception as e:
            print(f"Error clearing user context: {e}")
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_contexts = conn.execute("SELECT COUNT(*) FROM contexts").fetchone()[0]
                total_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                # Get context types breakdown
                type_breakdown = conn.execute("""
                    SELECT context_type, COUNT(*) as count
                    FROM contexts
                    GROUP BY context_type
                """).fetchall()
                
                return {
                    "total_contexts": total_contexts,
                    "database_size_mb": round(total_size / (1024 * 1024), 2),
                    "context_types": {ctx_type: count for ctx_type, count in type_breakdown},
                    "max_contexts_per_user": self.max_contexts_per_user,
                    "max_total_contexts": self.max_total_contexts,
                    "max_context_age_days": self.max_context_age_days
                }
        except Exception as e:
            return {"error": str(e)} 
    
    def get_user_context_analytics(self, access_code: str) -> Dict:
        """Get analytics for user's context data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all contexts for this user
                results = conn.execute("""
                    SELECT context_type, timestamp, metadata, content
                    FROM contexts
                    WHERE access_code = ?
                    ORDER BY timestamp DESC
                """, (access_code,)).fetchall()
                
                analytics = {
                    "access_code": access_code,
                    "context_breakdown": {},
                    "activity_timeline": [],
                    "data_science_insights": {},
                    "usage_patterns": {},
                    "performance_metrics": {}
                }
                
                if results:
                    # Build context breakdown
                    for context_type, timestamp, metadata, content in results:
                        if context_type not in analytics["context_breakdown"]:
                            analytics["context_breakdown"][context_type] = 0
                        analytics["context_breakdown"][context_type] += 1
                        
                        # Build activity timeline
                        metadata_dict = json.loads(metadata) if metadata else {}
                        analytics["activity_timeline"].append({
                            "type": context_type,
                            "timestamp": timestamp,
                            "is_summarized": metadata_dict.get("is_summarized", False)
                        })
                    
                    # Limit activity timeline to last 20
                    analytics["activity_timeline"] = analytics["activity_timeline"][:20]
                
                return analytics
                
        except Exception as e:
            print(f"Error getting user analytics: {e}")
            return {"access_code": access_code, "error": str(e)}
    
    def search_user_context(self, access_code: str, search_term: str, context_type: str = None) -> List[Dict]:
        """Search user's context data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if context_type:
                    # Search specific context type
                    results = conn.execute("""
                        SELECT c.id, c.content, c.context_type, c.metadata, c.timestamp,
                               contexts_fts.rank
                        FROM contexts c
                        JOIN contexts_fts ON c.id = contexts_fts.rowid
                        WHERE contexts_fts.access_code = ? AND contexts_fts.context_type = ?
                        AND contexts_fts MATCH ?
                        ORDER BY contexts_fts.rank DESC
                        LIMIT 10
                    """, (access_code, context_type, search_term)).fetchall()
                else:
                    # Search all context types
                    results = conn.execute("""
                        SELECT c.id, c.content, c.context_type, c.metadata, c.timestamp,
                               contexts_fts.rank
                        FROM contexts c
                        JOIN contexts_fts ON c.id = contexts_fts.rowid
                        WHERE contexts_fts.access_code = ?
                        AND contexts_fts MATCH ?
                        ORDER BY contexts_fts.rank DESC
                        LIMIT 10
                    """, (access_code, search_term)).fetchall()
                
                search_results = []
                for row in results:
                    try:
                        context_id, content, ctx_type, metadata, timestamp, rank = row
                        context_data = json.loads(content)
                        metadata_dict = json.loads(metadata) if metadata else {}
                        
                        search_results.append({
                            "content": context_data,
                            "type": ctx_type,
                            "metadata": metadata_dict,
                            "relevance_score": 1.0 - (rank / 1000.0),
                            "timestamp": timestamp
                        })
                    except json.JSONDecodeError:
                        continue
                
                return search_results
                
        except Exception as e:
            print(f"Error searching context: {e}")
            return [] 