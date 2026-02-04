"""
Literature Search Cache Manager

Provides intelligent caching for literature searches to improve performance
and reduce API calls while respecting data freshness requirements.
"""

import hashlib
import json
import os
import pickle
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import threading

logger = logging.getLogger("workflow_engine.cache_manager")


@dataclass
class CacheEntry:
    """Represents a cached literature search result."""
    search_hash: str
    query: str
    results: List[Dict[str, Any]]
    created_at: datetime
    expires_at: datetime
    hit_count: int
    last_accessed: datetime
    governance_mode: str
    version: str = "1.0"


class LiteratureCacheManager:
    """
    Intelligent cache manager for literature search results.
    
    Features:
    - SQLite-based storage for persistence
    - Configurable TTL per governance mode
    - Query similarity detection
    - Automatic cleanup of expired entries
    - Cache hit/miss statistics
    """
    
    def __init__(
        self, 
        cache_dir: str = "/tmp/literature_cache",
        max_cache_size_mb: int = 100,
        cleanup_interval_hours: int = 24
    ):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache storage
            max_cache_size_mb: Maximum cache size in MB
            cleanup_interval_hours: Hours between cache cleanup
        """
        self.cache_dir = cache_dir
        self.max_cache_size_mb = max_cache_size_mb
        self.cleanup_interval_hours = cleanup_interval_hours
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize database
        self.db_path = os.path.join(cache_dir, "literature_cache.db")
        self._init_database()
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "stores": 0,
            "cleanups": 0,
            "size_mb": 0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Start cleanup thread
        self._last_cleanup = datetime.now()
        
    def _init_database(self):
        """Initialize SQLite database for cache storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS literature_cache (
                    search_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    results_blob BLOB NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    last_accessed TEXT NOT NULL,
                    governance_mode TEXT NOT NULL,
                    version TEXT DEFAULT '1.0',
                    size_bytes INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON literature_cache(expires_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_governance_mode ON literature_cache(governance_mode)
            """)
    
    def get_cached_results(
        self, 
        search_config: Dict[str, Any],
        governance_mode: str = "DEMO"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached results for a search configuration.
        
        Args:
            search_config: Search configuration dictionary
            governance_mode: Current governance mode
            
        Returns:
            Cached results if available and valid, None otherwise
        """
        with self._lock:
            try:
                # Generate search hash
                search_hash = self._generate_search_hash(search_config, governance_mode)
                
                # Check for direct match first
                direct_result = self._get_cached_entry(search_hash)
                if direct_result:
                    self.stats["hits"] += 1
                    return direct_result
                
                # Check for similar queries if no direct match
                similar_result = self._find_similar_cached_query(search_config, governance_mode)
                if similar_result:
                    self.stats["hits"] += 1
                    logger.info(f"Found similar cached query for search: {search_config.get('research_topic', 'Unknown')[:50]}")
                    return similar_result
                
                # Cache miss
                self.stats["misses"] += 1
                return None
                
            except Exception as e:
                logger.error(f"Cache retrieval failed: {e}")
                self.stats["misses"] += 1
                return None
    
    def store_results(
        self,
        search_config: Dict[str, Any],
        results: List[Dict[str, Any]],
        governance_mode: str = "DEMO"
    ) -> bool:
        """
        Store search results in cache.
        
        Args:
            search_config: Search configuration used
            results: Literature search results
            governance_mode: Current governance mode
            
        Returns:
            True if stored successfully, False otherwise
        """
        with self._lock:
            try:
                # Generate search hash
                search_hash = self._generate_search_hash(search_config, governance_mode)
                
                # Determine TTL based on governance mode
                ttl_hours = self._get_ttl_hours(governance_mode)
                expires_at = datetime.now() + timedelta(hours=ttl_hours)
                
                # Serialize results
                results_blob = pickle.dumps(results)
                size_bytes = len(results_blob)
                
                # Check cache size limits
                if not self._check_size_limit(size_bytes):
                    logger.warning("Cache size limit reached, cleaning up...")
                    self._cleanup_cache()
                    if not self._check_size_limit(size_bytes):
                        logger.warning("Cannot cache results: size limit exceeded")
                        return False
                
                # Store in database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO literature_cache 
                        (search_hash, query, results_blob, created_at, expires_at, 
                         hit_count, last_accessed, governance_mode, size_bytes)
                        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
                    """, (
                        search_hash,
                        json.dumps(search_config, sort_keys=True),
                        results_blob,
                        datetime.now().isoformat(),
                        expires_at.isoformat(),
                        datetime.now().isoformat(),
                        governance_mode,
                        size_bytes
                    ))
                
                self.stats["stores"] += 1
                self._update_cache_stats()
                
                logger.debug(f"Cached {len(results)} results for query: {search_config.get('research_topic', 'Unknown')[:50]}")
                return True
                
            except Exception as e:
                logger.error(f"Cache storage failed: {e}")
                return False
    
    def invalidate_pattern(self, pattern: str, governance_mode: Optional[str] = None):
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: SQL LIKE pattern for query matching
            governance_mode: Optional governance mode filter
        """
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    if governance_mode:
                        conn.execute("""
                            DELETE FROM literature_cache 
                            WHERE query LIKE ? AND governance_mode = ?
                        """, (f"%{pattern}%", governance_mode))
                    else:
                        conn.execute("""
                            DELETE FROM literature_cache 
                            WHERE query LIKE ?
                        """, (f"%{pattern}%",))
                
                logger.info(f"Invalidated cache entries matching pattern: {pattern}")
                self._update_cache_stats()
                
            except Exception as e:
                logger.error(f"Cache invalidation failed: {e}")
    
    def cleanup_cache(self, force: bool = False):
        """
        Clean up expired cache entries.
        
        Args:
            force: Force cleanup regardless of interval
        """
        with self._lock:
            now = datetime.now()
            
            if not force and (now - self._last_cleanup).total_seconds() < self.cleanup_interval_hours * 3600:
                return
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Remove expired entries
                    cursor = conn.execute("""
                        DELETE FROM literature_cache 
                        WHERE expires_at < ?
                    """, (now.isoformat(),))
                    
                    deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} expired cache entries")
                
                # Clean up old, rarely accessed entries if cache is large
                self._cleanup_by_usage()
                
                self.stats["cleanups"] += 1
                self._last_cleanup = now
                self._update_cache_stats()
                
            except Exception as e:
                logger.error(f"Cache cleanup failed: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        with self._lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / max(total_requests, 1)) * 100
            
            # Get database stats
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM literature_cache")
                    entry_count = cursor.fetchone()[0]
                    
                    cursor = conn.execute("""
                        SELECT SUM(size_bytes) FROM literature_cache
                    """)
                    total_size = cursor.fetchone()[0] or 0
            except Exception:
                entry_count = 0
                total_size = 0
            
            return {
                "hit_rate_percent": round(hit_rate, 2),
                "total_hits": self.stats["hits"],
                "total_misses": self.stats["misses"],
                "total_stores": self.stats["stores"],
                "cache_entries": entry_count,
                "cache_size_mb": round(total_size / (1024 * 1024), 2),
                "max_size_mb": self.max_cache_size_mb,
                "cleanup_count": self.stats["cleanups"],
                "last_cleanup": self._last_cleanup.isoformat()
            }
    
    def _generate_search_hash(self, search_config: Dict[str, Any], governance_mode: str) -> str:
        """Generate hash for search configuration."""
        # Extract relevant parts for hashing
        hash_data = {
            "research_topic": search_config.get("research_topic", ""),
            "keywords": sorted(search_config.get("keywords", [])),
            "study_types": sorted(search_config.get("study_types", [])),
            "date_range": search_config.get("date_range", {}),
            "max_results": search_config.get("max_results", 50),
            "governance_mode": governance_mode,
            "pico_search_query": search_config.get("pico_search_query", "")
        }
        
        # Create hash
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def _get_cached_entry(self, search_hash: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached entry by hash."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT results_blob, expires_at, hit_count 
                    FROM literature_cache 
                    WHERE search_hash = ?
                """, (search_hash,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                results_blob, expires_at, hit_count = row
                
                # Check expiration
                if datetime.fromisoformat(expires_at) < datetime.now():
                    # Remove expired entry
                    conn.execute("DELETE FROM literature_cache WHERE search_hash = ?", (search_hash,))
                    return None
                
                # Update hit count and last accessed
                conn.execute("""
                    UPDATE literature_cache 
                    SET hit_count = hit_count + 1, last_accessed = ? 
                    WHERE search_hash = ?
                """, (datetime.now().isoformat(), search_hash))
                
                # Deserialize and return results
                return pickle.loads(results_blob)
                
        except Exception as e:
            logger.error(f"Failed to get cached entry: {e}")
            return None
    
    def _find_similar_cached_query(
        self, 
        search_config: Dict[str, Any], 
        governance_mode: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Find cached results for similar queries."""
        try:
            # Extract key terms for similarity matching
            topic = search_config.get("research_topic", "").lower()
            keywords = [k.lower() for k in search_config.get("keywords", [])]
            
            if not topic and not keywords:
                return None
            
            with sqlite3.connect(self.db_path) as conn:
                # Find entries with similar terms
                cursor = conn.execute("""
                    SELECT search_hash, query, results_blob, expires_at
                    FROM literature_cache 
                    WHERE governance_mode = ? AND expires_at > ?
                    ORDER BY hit_count DESC, last_accessed DESC
                    LIMIT 10
                """, (governance_mode, datetime.now().isoformat()))
                
                for row in cursor.fetchall():
                    search_hash, query_json, results_blob, expires_at = row
                    
                    try:
                        cached_config = json.loads(query_json)
                        similarity = self._calculate_query_similarity(search_config, cached_config)
                        
                        # If similarity is high enough, return cached results
                        if similarity > 0.7:  # 70% similarity threshold
                            # Update access stats
                            conn.execute("""
                                UPDATE literature_cache 
                                SET hit_count = hit_count + 1, last_accessed = ? 
                                WHERE search_hash = ?
                            """, (datetime.now().isoformat(), search_hash))
                            
                            return pickle.loads(results_blob)
                            
                    except Exception:
                        continue
                        
            return None
            
        except Exception as e:
            logger.error(f"Failed to find similar query: {e}")
            return None
    
    def _calculate_query_similarity(
        self, 
        config1: Dict[str, Any], 
        config2: Dict[str, Any]
    ) -> float:
        """Calculate similarity score between two search configurations."""
        score = 0.0
        
        # Topic similarity (weight: 40%)
        topic1 = config1.get("research_topic", "").lower()
        topic2 = config2.get("research_topic", "").lower()
        if topic1 and topic2:
            topic_overlap = self._text_overlap(topic1, topic2)
            score += topic_overlap * 0.4
        
        # Keywords similarity (weight: 40%)
        keywords1 = set(k.lower() for k in config1.get("keywords", []))
        keywords2 = set(k.lower() for k in config2.get("keywords", []))
        if keywords1 and keywords2:
            keyword_overlap = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
            score += keyword_overlap * 0.4
        
        # Study types similarity (weight: 20%)
        types1 = set(config1.get("study_types", []))
        types2 = set(config2.get("study_types", []))
        if types1 and types2:
            type_overlap = len(types1.intersection(types2)) / len(types1.union(types2))
            score += type_overlap * 0.2
        
        return score
    
    def _text_overlap(self, text1: str, text2: str) -> float:
        """Calculate text overlap similarity."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
            
        overlap = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return overlap / union if union > 0 else 0.0
    
    def _get_ttl_hours(self, governance_mode: str) -> int:
        """Get TTL in hours based on governance mode."""
        ttl_map = {
            "DEMO": 24,        # 1 day for demo
            "STAGING": 8,      # 8 hours for staging
            "PRODUCTION": 4    # 4 hours for production
        }
        return ttl_map.get(governance_mode, 12)  # Default 12 hours
    
    def _check_size_limit(self, new_entry_size: int) -> bool:
        """Check if cache can accommodate new entry."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(size_bytes) FROM literature_cache")
                current_size = cursor.fetchone()[0] or 0
            
            max_size_bytes = self.max_cache_size_mb * 1024 * 1024
            return (current_size + new_entry_size) <= max_size_bytes
            
        except Exception:
            return True  # Allow storage if check fails
    
    def _cleanup_by_usage(self):
        """Remove least recently used entries if cache is too large."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(size_bytes) FROM literature_cache")
                current_size = cursor.fetchone()[0] or 0
                
                max_size_bytes = self.max_cache_size_mb * 1024 * 1024
                
                if current_size > max_size_bytes:
                    # Remove 25% of least recently used entries
                    cursor = conn.execute("""
                        DELETE FROM literature_cache 
                        WHERE search_hash IN (
                            SELECT search_hash FROM literature_cache 
                            ORDER BY last_accessed ASC, hit_count ASC 
                            LIMIT (SELECT COUNT(*) FROM literature_cache) / 4
                        )
                    """)
                    
                    deleted = cursor.rowcount
                    if deleted > 0:
                        logger.info(f"Cleaned up {deleted} LRU cache entries")
            
        except Exception as e:
            logger.error(f"LRU cleanup failed: {e}")
    
    def _cleanup_cache(self):
        """Alias for cleanup_cache for internal use."""
        self.cleanup_cache(force=True)
    
    def _update_cache_stats(self):
        """Update internal cache statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT SUM(size_bytes) FROM literature_cache")
                total_size = cursor.fetchone()[0] or 0
                self.stats["size_mb"] = total_size / (1024 * 1024)
        except Exception:
            pass