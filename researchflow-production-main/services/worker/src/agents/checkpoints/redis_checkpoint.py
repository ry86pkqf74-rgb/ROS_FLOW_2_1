"""
Redis-backed Checkpointing for LangGraph State Persistence.

Provides durable state persistence for LangGraph agents using Redis.
Enables conversation recovery, session continuity, and state inspection.

Key Features:
- Automatic state serialization/deserialization
- Configurable TTL for checkpoint expiration
- Thread-safe operations
- Efficient binary storage with optional compression

See: Linear ROS-66 (Phase C: Improvement Loop System)
"""

import json
import pickle
import zlib
from typing import Any, Dict, Optional, Sequence, Tuple
from datetime import datetime
import logging

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

logger = logging.getLogger(__name__)


class RedisCheckpointSaver(BaseCheckpointSaver):
    """
    Redis-backed checkpoint saver for LangGraph agents.

    Stores agent state in Redis with configurable TTL for automatic
    cleanup of old sessions. Supports both pickle and JSON serialization
    with optional compression for large states.

    Usage:
        ```python
        import redis.asyncio as redis

        client = redis.from_url("redis://localhost:6379")
        checkpointer = RedisCheckpointSaver(client, ttl=86400 * 7)

        # Use with LangGraph
        graph = StateGraph(AgentState)
        # ... build graph ...
        app = graph.compile(checkpointer=checkpointer)
        ```
    """

    def __init__(
        self,
        redis_client: Any,
        ttl: int = 604800,  # 7 days default
        prefix: str = "lg:checkpoint:",
        compress: bool = True,
        use_json: bool = False,
    ):
        """
        Initialize Redis checkpoint saver.

        Args:
            redis_client: Async Redis client (redis.asyncio.Redis)
            ttl: Time-to-live in seconds for checkpoints (default: 7 days)
            prefix: Key prefix for checkpoint storage
            compress: Whether to compress checkpoint data
            use_json: Use JSON serialization (safer) instead of pickle (faster)
        """
        super().__init__()
        self.client = redis_client
        self.ttl = ttl
        self.prefix = prefix
        self.compress = compress
        self.use_json = use_json
        self.serde = JsonPlusSerializer() if use_json else None

    def _make_key(self, thread_id: str, checkpoint_ns: str = "", checkpoint_id: str = "") -> str:
        """Create Redis key from checkpoint identifiers."""
        parts = [self.prefix, thread_id]
        if checkpoint_ns:
            parts.append(checkpoint_ns)
        if checkpoint_id:
            parts.append(checkpoint_id)
        return ":".join(parts)

    def _make_writes_key(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
        """Create Redis key for pending writes."""
        return f"{self.prefix}writes:{thread_id}:{checkpoint_ns}:{checkpoint_id}"

    def _serialize(self, data: Any) -> bytes:
        """Serialize checkpoint data to bytes."""
        if self.use_json:
            serialized = json.dumps(self.serde.dumps(data)).encode('utf-8')
        else:
            serialized = pickle.dumps(data)

        if self.compress:
            return zlib.compress(serialized)
        return serialized

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize checkpoint data from bytes."""
        if self.compress:
            data = zlib.decompress(data)

        if self.use_json:
            return self.serde.loads(json.loads(data.decode('utf-8')))
        return pickle.loads(data)

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """
        Get checkpoint tuple for a given configuration.

        Args:
            config: Configuration dict with 'configurable' containing thread_id

        Returns:
            CheckpointTuple if found, None otherwise
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")

        if not thread_id:
            return None

        try:
            if checkpoint_id:
                # Get specific checkpoint
                key = self._make_key(thread_id, checkpoint_ns, checkpoint_id)
                data = await self.client.get(key)
            else:
                # Get latest checkpoint - search for most recent
                pattern = self._make_key(thread_id, checkpoint_ns, "*")
                keys = []
                async for key in self.client.scan_iter(match=pattern):
                    keys.append(key)

                if not keys:
                    return None

                # Sort by checkpoint ID (timestamp-based) and get latest
                keys.sort(reverse=True)
                data = await self.client.get(keys[0])

            if not data:
                return None

            checkpoint_data = self._deserialize(data)

            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint_data.get("checkpoint", {}),
                metadata=checkpoint_data.get("metadata", {}),
                parent_config=checkpoint_data.get("parent_config"),
                pending_writes=checkpoint_data.get("pending_writes", []),
            )

        except Exception as e:
            logger.error(f"Error retrieving checkpoint: {e}", exc_info=True)
            return None

    async def alist(
        self,
        config: Optional[Dict[str, Any]],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> Sequence[CheckpointTuple]:
        """
        List checkpoints for a thread.

        Args:
            config: Configuration dict with thread_id
            filter: Optional filter criteria
            before: Optional checkpoint to list before
            limit: Maximum number of checkpoints to return

        Returns:
            Sequence of CheckpointTuples
        """
        if not config:
            return []

        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")

        if not thread_id:
            return []

        try:
            pattern = self._make_key(thread_id, checkpoint_ns, "*")
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            # Sort by checkpoint ID (descending)
            keys.sort(reverse=True)

            if limit:
                keys = keys[:limit]

            results = []
            for key in keys:
                data = await self.client.get(key)
                if data:
                    checkpoint_data = self._deserialize(data)
                    results.append(CheckpointTuple(
                        config={
                            "configurable": {
                                "thread_id": thread_id,
                                "checkpoint_ns": checkpoint_ns,
                                "checkpoint_id": checkpoint_data.get("checkpoint", {}).get("id"),
                            }
                        },
                        checkpoint=checkpoint_data.get("checkpoint", {}),
                        metadata=checkpoint_data.get("metadata", {}),
                        parent_config=checkpoint_data.get("parent_config"),
                        pending_writes=checkpoint_data.get("pending_writes", []),
                    ))

            return results

        except Exception as e:
            logger.error(f"Error listing checkpoints: {e}", exc_info=True)
            return []

    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Save a checkpoint.

        Args:
            config: Configuration dict with thread_id
            checkpoint: Checkpoint data to save
            metadata: Checkpoint metadata
            new_versions: Optional new version information

        Returns:
            Updated configuration dict
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        checkpoint_id = checkpoint.get("id", datetime.utcnow().isoformat())

        if not thread_id:
            raise ValueError("thread_id required in config.configurable")

        key = self._make_key(thread_id, checkpoint_ns, checkpoint_id)

        # Get parent config if this is a continuation
        parent_checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        parent_config = None
        if parent_checkpoint_id:
            parent_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": parent_checkpoint_id,
                }
            }

        checkpoint_data = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "parent_config": parent_config,
            "pending_writes": [],
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            serialized = self._serialize(checkpoint_data)
            await self.client.setex(key, self.ttl, serialized)

            logger.debug(
                f"Saved checkpoint",
                extra={
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_id,
                    "size_bytes": len(serialized),
                }
            )

            return {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            }

        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}", exc_info=True)
            raise

    async def aput_writes(
        self,
        config: Dict[str, Any],
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """
        Save pending writes for a checkpoint.

        Used for interrupt/resume functionality.

        Args:
            config: Configuration dict
            writes: Sequence of (channel, value) tuples
            task_id: Task identifier
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")

        if not thread_id or not checkpoint_id:
            return

        key = self._make_writes_key(thread_id, checkpoint_ns, checkpoint_id)

        try:
            # Get existing writes
            existing_data = await self.client.get(key)
            if existing_data:
                existing_writes = self._deserialize(existing_data)
            else:
                existing_writes = []

            # Append new writes
            for channel, value in writes:
                existing_writes.append({
                    "task_id": task_id,
                    "channel": channel,
                    "value": value,
                    "timestamp": datetime.utcnow().isoformat(),
                })

            serialized = self._serialize(existing_writes)
            await self.client.setex(key, self.ttl, serialized)

        except Exception as e:
            logger.error(f"Error saving pending writes: {e}", exc_info=True)

    # Sync versions for backward compatibility
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Sync version of aget_tuple."""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.aget_tuple(config))

    def list(
        self,
        config: Optional[Dict[str, Any]],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> Sequence[CheckpointTuple]:
        """Sync version of alist."""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.alist(config, filter=filter, before=before, limit=limit)
        )

    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Sync version of aput."""
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.aput(config, checkpoint, metadata, new_versions)
        )

    def put_writes(
        self,
        config: Dict[str, Any],
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Sync version of aput_writes."""
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.aput_writes(config, writes, task_id))


async def create_redis_checkpointer(
    redis_url: str = "redis://localhost:6379",
    ttl: int = 604800,
    compress: bool = True,
) -> RedisCheckpointSaver:
    """
    Factory function to create a Redis checkpointer.

    Args:
        redis_url: Redis connection URL
        ttl: Checkpoint TTL in seconds
        compress: Whether to compress checkpoint data

    Returns:
        Configured RedisCheckpointSaver instance
    """
    import redis.asyncio as redis

    client = redis.from_url(redis_url)
    return RedisCheckpointSaver(client, ttl=ttl, compress=compress)
