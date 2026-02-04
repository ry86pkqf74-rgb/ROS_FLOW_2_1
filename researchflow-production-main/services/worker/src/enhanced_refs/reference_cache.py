"""
Reference Management Cache System

Smart caching for reference metadata with Redis backend and intelligent TTL management.

Linear Issues: ROS-XXX
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import asyncio
import redis.asyncio as redis

from .reference_types import Reference, DOIValidationResult, Citation, QualityScore

logger = logging.getLogger(__name__)


class ReferenceCache:
    """Smart caching system for reference management with different TTLs for different data types."""
    
    # Cache TTLs in seconds
    CACHE_TTLS = {
        'doi_metadata': 7 * 24 * 3600,      # 7 days - DOI metadata rarely changes
        'paper_search': 24 * 3600,          # 1 day - Search results can change
        'citation_format': 30 * 24 * 3600,  # 30 days - Formatted citations stable
        'validation_results': 3 * 24 * 3600, # 3 days - DOI validation results
        'quality_scores': 7 * 24 * 3600,    # 7 days - Quality assessments
        'duplicate_detection': 24 * 3600,   # 1 day - Duplicate detection results
        'api_responses': 6 * 3600,          # 6 hours - External API responses
        'batch_results': 2 * 3600,          # 2 hours - Batch processing results
    }
    
    # Cache key prefixes
    PREFIXES = {
        'doi_metadata': 'ref:doi:',
        'paper_search': 'ref:search:',
        'citation_format': 'ref:citation:',
        'validation_results': 'ref:validation:',
        'quality_scores': 'ref:quality:',
        'duplicate_detection': 'ref:duplicates:',
        'api_responses': 'ref:api:',
        'batch_results': 'ref:batch:',
        'reference_data': 'ref:data:',
        'bibliography': 'ref:bib:',
    }
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize reference cache.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self._redis_pool: Optional[redis.Redis] = None
        self.stats = {
            'hits': 0,
            'misses': 0,
            'writes': 0,
            'errors': 0,
        }
    
    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self._redis_pool = redis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            await self._redis_pool.ping()
            logger.info("Reference cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize reference cache: {e}")
            # Fall back to in-memory cache
            self._redis_pool = None
    
    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._redis_pool:
            await self._redis_pool.close()
    
    def _make_key(self, prefix: str, identifier: str) -> str:
        """Create cache key with prefix."""
        # Hash long identifiers to keep key size reasonable
        if len(identifier) > 100:
            identifier = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"{prefix}{identifier}"
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for cache storage."""
        if isinstance(value, (Reference, Citation, QualityScore, DOIValidationResult)):
            return value.model_dump_json()
        elif isinstance(value, list):
            if value and isinstance(value[0], (Reference, Citation, QualityScore)):
                return json.dumps([item.model_dump() for item in value])
        return json.dumps(value)
    
    def _deserialize_value(self, value: str, value_type: str = 'dict') -> Any:
        """Deserialize value from cache."""
        try:
            if value_type == 'reference':
                return Reference.model_validate_json(value)
            elif value_type == 'citation':
                return Citation.model_validate_json(value)
            elif value_type == 'quality_score':
                return QualityScore.model_validate_json(value)
            elif value_type == 'doi_validation':
                return DOIValidationResult.model_validate_json(value)
            elif value_type == 'reference_list':
                data = json.loads(value)
                return [Reference.model_validate(item) for item in data]
            elif value_type == 'citation_list':
                data = json.loads(value)
                return [Citation.model_validate(item) for item in data]
            else:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Failed to deserialize cached value: {e}")
            return None
    
    async def get(self, cache_type: str, identifier: str, value_type: str = 'dict') -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            cache_type: Type of cached data (key in PREFIXES)
            identifier: Unique identifier for the data
            value_type: Type hint for deserialization
            
        Returns:
            Cached value or None if not found
        """
        if not self._redis_pool or cache_type not in self.PREFIXES:
            return None
        
        try:
            key = self._make_key(self.PREFIXES[cache_type], identifier)
            value = await self._redis_pool.get(key)
            
            if value is None:
                self.stats['misses'] += 1
                return None
            
            self.stats['hits'] += 1
            return self._deserialize_value(value, value_type)
            
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            self.stats['errors'] += 1
            return None
    
    async def set(self, cache_type: str, identifier: str, value: Any, ttl_override: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            cache_type: Type of cached data
            identifier: Unique identifier for the data  
            value: Value to cache
            ttl_override: Optional TTL override in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self._redis_pool or cache_type not in self.PREFIXES:
            return False
        
        try:
            key = self._make_key(self.PREFIXES[cache_type], identifier)
            serialized_value = self._serialize_value(value)
            ttl = ttl_override or self.CACHE_TTLS.get(cache_type, 3600)
            
            await self._redis_pool.setex(key, ttl, serialized_value)
            self.stats['writes'] += 1
            return True
            
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            self.stats['errors'] += 1
            return False
    
    async def get_many(self, cache_type: str, identifiers: List[str], value_type: str = 'dict') -> Dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            cache_type: Type of cached data
            identifiers: List of identifiers
            value_type: Type hint for deserialization
            
        Returns:
            Dictionary mapping identifier to cached value
        """
        if not self._redis_pool or not identifiers:
            return {}
        
        try:
            keys = [self._make_key(self.PREFIXES[cache_type], identifier) for identifier in identifiers]
            values = await self._redis_pool.mget(keys)
            
            result = {}
            for identifier, value in zip(identifiers, values):
                if value is not None:
                    deserialized = self._deserialize_value(value, value_type)
                    if deserialized is not None:
                        result[identifier] = deserialized
                        self.stats['hits'] += 1
                    else:
                        self.stats['misses'] += 1
                else:
                    self.stats['misses'] += 1
            
            return result
            
        except Exception as e:
            logger.warning(f"Cache get_many error: {e}")
            self.stats['errors'] += 1
            return {}
    
    async def set_many(self, cache_type: str, data: Dict[str, Any], ttl_override: Optional[int] = None) -> bool:
        """
        Set multiple values in cache.
        
        Args:
            cache_type: Type of cached data
            data: Dictionary mapping identifier to value
            ttl_override: Optional TTL override in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self._redis_pool or not data:
            return False
        
        try:
            pipe = self._redis_pool.pipeline()
            ttl = ttl_override or self.CACHE_TTLS.get(cache_type, 3600)
            
            for identifier, value in data.items():
                key = self._make_key(self.PREFIXES[cache_type], identifier)
                serialized_value = self._serialize_value(value)
                pipe.setex(key, ttl, serialized_value)
            
            await pipe.execute()
            self.stats['writes'] += len(data)
            return True
            
        except Exception as e:
            logger.warning(f"Cache set_many error: {e}")
            self.stats['errors'] += 1
            return False
    
    async def delete(self, cache_type: str, identifier: str) -> bool:
        """Delete value from cache."""
        if not self._redis_pool:
            return False
        
        try:
            key = self._make_key(self.PREFIXES[cache_type], identifier)
            await self._redis_pool.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Redis pattern (e.g., 'ref:doi:*')
            
        Returns:
            Number of keys deleted
        """
        if not self._redis_pool:
            return 0
        
        try:
            keys = []
            async for key in self._redis_pool.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self._redis_pool.delete(*keys)
            
            return len(keys)
        except Exception as e:
            logger.warning(f"Cache clear_pattern error: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_operations = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_operations if total_operations > 0 else 0.0
        
        result = {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'writes': self.stats['writes'],
            'errors': self.stats['errors'],
            'hit_rate': hit_rate,
            'total_operations': total_operations,
        }
        
        if self._redis_pool:
            try:
                info = await self._redis_pool.info()
                result.update({
                    'redis_used_memory': info.get('used_memory_human', 'N/A'),
                    'redis_connected_clients': info.get('connected_clients', 0),
                    'redis_total_commands_processed': info.get('total_commands_processed', 0),
                })
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")
        
        return result
    
    async def warm_cache(self, cache_type: str, data_loader_func, identifiers: List[str]) -> int:
        """
        Warm cache with data from a loader function.
        
        Args:
            cache_type: Type of data to cache
            data_loader_func: Async function that loads data for given identifiers
            identifiers: List of identifiers to load
            
        Returns:
            Number of items cached
        """
        if not identifiers:
            return 0
        
        try:
            # Check what's already cached
            cached_data = await self.get_many(cache_type, identifiers)
            missing_identifiers = [identifier for identifier in identifiers if identifier not in cached_data]
            
            if not missing_identifiers:
                return 0
            
            # Load missing data
            new_data = await data_loader_func(missing_identifiers)
            
            if new_data:
                await self.set_many(cache_type, new_data)
                return len(new_data)
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache warming error: {e}")
            return 0
    
    async def invalidate_related(self, reference_id: str) -> None:
        """
        Invalidate all cached data related to a reference.
        
        Args:
            reference_id: Reference ID to invalidate
        """
        patterns_to_clear = [
            f"ref:*:{reference_id}*",
            f"ref:citation:*{reference_id}*",
            f"ref:quality:*{reference_id}*",
            f"ref:validation:*{reference_id}*",
        ]
        
        for pattern in patterns_to_clear:
            await self.clear_pattern(pattern)
    
    async def cleanup_expired(self) -> int:
        """
        Manually cleanup expired keys (Redis does this automatically, but useful for stats).
        
        Returns:
            Number of expired keys found
        """
        if not self._redis_pool:
            return 0
        
        expired_count = 0
        try:
            # Scan through all our prefixes
            for prefix in self.PREFIXES.values():
                async for key in self._redis_pool.scan_iter(match=f"{prefix}*"):
                    ttl = await self._redis_pool.ttl(key)
                    if ttl == -2:  # Key doesn't exist (expired)
                        expired_count += 1
        except Exception as e:
            logger.warning(f"Failed to check expired keys: {e}")
        
        return expired_count


# Global cache instance
_cache_instance: Optional[ReferenceCache] = None


async def get_cache() -> ReferenceCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        import os
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        _cache_instance = ReferenceCache(redis_url)
        await _cache_instance.initialize()
    return _cache_instance


async def close_cache() -> None:
    """Close global cache instance."""
    global _cache_instance
    if _cache_instance:
        await _cache_instance.close()
        _cache_instance = None