import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from context_summarizer import ContextSummarizer
import re

class SmartResponseCache:
    """Smart response cache that considers context similarity and question type"""
    
    def __init__(self, max_cache_size: int = 500, cache_ttl_hours: int = 6):
        self.cache = {}
        self.max_cache_size = max_cache_size
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.context_summarizer = ContextSummarizer()
        
        # Question types that are safe to cache
        self.cacheable_patterns = [
            r"how\s+to\s+",
            r"what\s+is\s+",
            r"explain\s+",
            r"create\s+a\s+",
            r"make\s+a\s+",
            r"generate\s+a\s+",
            r"plot\s+",
            r"visualize\s+",
            r"show\s+me\s+how\s+to\s+",
            r"can\s+you\s+explain\s+",
            r"what\s+does\s+",
            r"define\s+",
            r"describe\s+"
        ]
        
        # Question types that should NOT be cached
        self.non_cacheable_patterns = [
            r"what\s+data\s+do\s+i\s+have",
            r"what\s+is\s+wrong\s+with",
            r"error\s+",
            r"debug\s+",
            r"fix\s+",
            r"problem\s+with",
            r"issue\s+with",
            r"what\s+does\s+this\s+output\s+mean",
            r"why\s+is\s+this\s+happening",
            r"what\s+went\s+wrong",
            r"troubleshoot",
            r"diagnose"
        ]
    
    def is_cacheable_question(self, prompt: str) -> bool:
        """Determine if a question is safe to cache"""
        prompt_lower = prompt.lower()
        
        # Check if it's a non-cacheable question
        for pattern in self.non_cacheable_patterns:
            if re.search(pattern, prompt_lower):
                return False
        
        # Check if it's a cacheable question
        for pattern in self.cacheable_patterns:
            if re.search(pattern, prompt_lower):
                return True
        
        # Default: don't cache if unsure
        return False
    
    def get_cache_key(self, prompt: str, context_data: Dict) -> str:
        """Create a cache key based on prompt and context fingerprint"""
        # Create context fingerprint
        context_fingerprint = self.context_summarizer.get_context_fingerprint(context_data)
        
        # Create hash of prompt + context fingerprint
        content = json.dumps({
            "prompt": prompt.lower().strip(),
            "context_fingerprint": context_fingerprint
        }, sort_keys=True)
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt: str, context_data: Dict) -> Optional[Dict]:
        """Get cached response if available and appropriate"""
        # Check if question is cacheable
        if not self.is_cacheable_question(prompt):
            return None
        
        cache_key = self.get_cache_key(prompt, context_data)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Check if cache entry is still valid
            if datetime.now() - entry['timestamp'] < self.cache_ttl:
                # Check context similarity
                context_similarity = self._check_context_similarity(
                    entry['context_fingerprint'], 
                    self.context_summarizer.get_context_fingerprint(context_data)
                )
                
                if context_similarity > 0.8:  # 80% similar context
                    return {
                        'response': entry['response'],
                        'cached': True,
                        'context_similarity': context_similarity,
                        'cache_age': (datetime.now() - entry['timestamp']).total_seconds() / 3600
                    }
        
        return None
    
    def set(self, prompt: str, context_data: Dict, response: str) -> None:
        """Cache a response if appropriate"""
        # Only cache if question is cacheable
        if not self.is_cacheable_question(prompt):
            return
        
        cache_key = self.get_cache_key(prompt, context_data)
        
        self.cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now(),
            'context_fingerprint': self.context_summarizer.get_context_fingerprint(context_data),
            'prompt': prompt.lower().strip()
        }
        
        # Clean up old entries if cache is full
        if len(self.cache) > self.max_cache_size:
            self._cleanup_old_entries()
    
    def _check_context_similarity(self, cached_fingerprint: str, current_fingerprint: str) -> float:
        """Check similarity between cached and current context"""
        try:
            cached_data = json.loads(cached_fingerprint)
            current_data = json.loads(current_fingerprint)
            
            # Simple similarity check based on key elements
            similarities = []
            
            # Check workspace keys similarity
            cached_keys = set(cached_data.get("workspace_keys", []))
            current_keys = set(current_data.get("workspace_keys", []))
            if cached_keys or current_keys:
                key_similarity = len(cached_keys & current_keys) / len(cached_keys | current_keys) if cached_keys | current_keys else 1.0
                similarities.append(key_similarity)
            
            # Check recent commands similarity
            cached_commands = cached_data.get("recent_commands", [])
            current_commands = current_data.get("recent_commands", [])
            if cached_commands or current_commands:
                command_similarity = len(set(cached_commands) & set(current_commands)) / len(set(cached_commands) | set(current_commands)) if set(cached_commands) | set(current_commands) else 1.0
                similarities.append(command_similarity)
            
            # Check packages similarity
            cached_packages = set(cached_data.get("active_packages", []))
            current_packages = set(current_data.get("active_packages", []))
            if cached_packages or current_packages:
                package_similarity = len(cached_packages & current_packages) / len(cached_packages | current_packages) if cached_packages | current_packages else 1.0
                similarities.append(package_similarity)
            
            # Return average similarity
            return sum(similarities) / len(similarities) if similarities else 0.0
            
        except Exception:
            return 0.0
    
    def _cleanup_old_entries(self) -> None:
        """Remove old cache entries"""
        current_time = datetime.now()
        old_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry['timestamp'] > self.cache_ttl:
                old_keys.append(key)
        
        # Remove old entries
        for key in old_keys:
            del self.cache[key]
        
        # If still too many entries, remove oldest
        if len(self.cache) > self.max_cache_size:
            sorted_entries = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])
            entries_to_remove = len(sorted_entries) - self.max_cache_size
            
            for i in range(entries_to_remove):
                del self.cache[sorted_entries[i][0]]
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        current_time = datetime.now()
        total_entries = len(self.cache)
        expired_entries = sum(1 for entry in self.cache.values() 
                            if current_time - entry['timestamp'] > self.cache_ttl)
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "valid_entries": total_entries - expired_entries,
            "cache_size_mb": self._estimate_cache_size(),
            "max_cache_size": self.max_cache_size,
            "cache_ttl_hours": self.cache_ttl.total_seconds() / 3600
        }
    
    def _estimate_cache_size(self) -> float:
        """Estimate cache size in MB"""
        total_size = 0
        for entry in self.cache.values():
            total_size += len(json.dumps(entry))
        return round(total_size / (1024 * 1024), 2)
    
    def clear_cache(self) -> None:
        """Clear all cached entries"""
        self.cache.clear() 