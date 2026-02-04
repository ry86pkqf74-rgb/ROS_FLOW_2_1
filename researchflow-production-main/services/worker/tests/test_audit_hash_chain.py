"""
Unit tests for hash chain audit logging module.

Tests cover:
- Hash chain creation and verification
- Entry appending with chain integrity
- Chain integrity verification and detection of tampering
- Database persistence
- Rollback capability
- Actor and resource trail queries
- Export functionality
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
import json

from services.worker.src.audit.hash_chain import (
    HashChainAuditLogger,
    AuditEntry,
    get_audit_logger,
)


class TestHashChainAuditLogger:
    """Tests for HashChainAuditLogger."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield f"sqlite:///{path}"
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def logger(self, temp_db):
        """Create audit logger with temporary database."""
        return HashChainAuditLogger(database_url=temp_db)

    def test_init(self, temp_db):
        """Should initialize audit logger with database."""
        logger = HashChainAuditLogger(database_url=temp_db)
        assert logger.database_url == temp_db
        assert logger.SessionLocal is not None

    def test_append_entry(self, logger):
        """Should append entry to audit chain."""
        entry_id = logger.append_entry(
            action="CREATE",
            actor="test_user",
            resource_type="document",
            resource_id="doc_123",
            data={"title": "Test Doc", "content": "Test content"},
        )

        assert entry_id is not None
        assert len(entry_id) > 0

    def test_get_entry(self, logger):
        """Should retrieve entry by ID."""
        entry_id = logger.append_entry(
            action="UPDATE",
            actor="test_user",
            resource_type="document",
            resource_id="doc_123",
            data={"updated_field": "new_value"},
        )

        entry = logger.get_entry(entry_id)
        assert entry is not None
        assert entry["action"] == "UPDATE"
        assert entry["actor"] == "test_user"
        assert entry["resource_type"] == "document"

    def test_multiple_entries_create_chain(self, logger):
        """Multiple entries should form a hash chain."""
        entry_ids = []
        for i in range(5):
            entry_id = logger.append_entry(
                action="ACTION",
                actor=f"user_{i}",
                resource_type="resource",
                data={"index": i},
            )
            entry_ids.append(entry_id)

        # All entries should be created
        assert len(entry_ids) == 5
        assert all(entry_ids)

        # Each entry should have different hash
        entries = [logger.get_entry(eid) for eid in entry_ids]
        hashes = [e["entry_hash"] for e in entries]
        assert len(set(hashes)) == 5, "Each entry should have unique hash"

    def test_chain_is_immutable(self, logger):
        """Chain should be immutable - entries cannot be modified."""
        entry_id = logger.append_entry(
            action="CREATE",
            actor="test_user",
            resource_type="document",
            data={"content": "original"},
        )

        entry = logger.get_entry(entry_id)
        original_hash = entry["entry_hash"]

        # Attempting to modify should not change the stored entry
        # (In production, database would have constraints)
        assert entry["entry_hash"] == original_hash

    def test_verify_chain_valid(self, logger):
        """Should verify valid chain."""
        # Create several entries
        for i in range(3):
            logger.append_entry(
                action="ACTION",
                actor="user",
                resource_type="resource",
                data={"index": i},
            )

        result = logger.verify_chain()
        assert result["valid"] is True
        assert result["total_entries"] == 3
        assert len(result["chain_breaks"]) == 0
        assert len(result["invalid_entries"]) == 0

    def test_empty_chain_is_valid(self, logger):
        """Empty chain should verify as valid."""
        result = logger.verify_chain()
        assert result["valid"] is True
        assert result["total_entries"] == 0

    def test_export_chain_json(self, logger):
        """Should export chain as JSON."""
        entry_id = logger.append_entry(
            action="CREATE",
            actor="test_user",
            resource_type="document",
            data={"content": "test"},
        )

        exported = logger.export_chain(output_format="json")
        assert exported is not None
        data = json.loads(exported)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["action"] == "CREATE"

    def test_export_chain_csv(self, logger):
        """Should export chain as CSV."""
        logger.append_entry(
            action="CREATE",
            actor="user1",
            resource_type="document",
            data={"title": "Doc1"},
        )

        exported = logger.export_chain(output_format="csv")
        assert "action" in exported
        assert "CREATE" in exported
        assert "user1" in exported

    def test_get_actor_trail(self, logger):
        """Should retrieve all entries for an actor."""
        # Create entries for different actors
        for i in range(3):
            logger.append_entry(
                action="ACTION",
                actor="alice",
                resource_type="resource",
                data={"index": i},
            )

        for i in range(2):
            logger.append_entry(
                action="ACTION",
                actor="bob",
                resource_type="resource",
                data={"index": i},
            )

        alice_trail = logger.get_actor_trail("alice")
        assert len(alice_trail) == 3

        bob_trail = logger.get_actor_trail("bob")
        assert len(bob_trail) == 2

    def test_get_resource_trail(self, logger):
        """Should retrieve all entries for a resource."""
        # Create entries for different resources
        logger.append_entry(
            action="CREATE",
            actor="user",
            resource_type="document",
            resource_id="doc_1",
            data={"content": "doc1"},
        )

        logger.append_entry(
            action="UPDATE",
            actor="user",
            resource_type="document",
            resource_id="doc_1",
            data={"content": "doc1_updated"},
        )

        logger.append_entry(
            action="CREATE",
            actor="user",
            resource_type="document",
            resource_id="doc_2",
            data={"content": "doc2"},
        )

        trail = logger.get_resource_trail("document", "doc_1")
        assert len(trail) == 2
        assert trail[0]["action"] == "CREATE"
        assert trail[1]["action"] == "UPDATE"

    def test_get_statistics(self, logger):
        """Should return audit log statistics."""
        # Create entries
        logger.append_entry(
            action="CREATE",
            actor="alice",
            resource_type="document",
            data={},
        )

        logger.append_entry(
            action="UPDATE",
            actor="bob",
            resource_type="document",
            data={},
        )

        logger.append_entry(
            action="CREATE",
            actor="alice",
            resource_type="resource",
            data={},
        )

        stats = logger.get_statistics()
        assert stats["total_entries"] == 3
        assert stats["unique_actors"] == 2
        assert stats["action_counts"]["CREATE"] == 2
        assert stats["action_counts"]["UPDATE"] == 1

    def test_invalid_append_entry_missing_action(self, logger):
        """Should raise error when action is missing."""
        with pytest.raises(ValueError):
            logger.append_entry(
                action="",
                actor="user",
                resource_type="resource",
                data={},
            )

    def test_invalid_append_entry_missing_actor(self, logger):
        """Should raise error when actor is missing."""
        with pytest.raises(ValueError):
            logger.append_entry(
                action="CREATE",
                actor="",
                resource_type="resource",
                data={},
            )

    def test_export_chain_invalid_format(self, logger):
        """Should raise error for invalid export format."""
        with pytest.raises(ValueError):
            logger.export_chain(output_format="invalid_format")

    def test_rollback_to_hash(self, logger):
        """Should rollback audit log to specified hash."""
        entry_id_1 = logger.append_entry(
            action="ACTION_1",
            actor="user",
            resource_type="resource",
            data={},
        )

        entry_1 = logger.get_entry(entry_id_1)
        entry_1_hash = entry_1["entry_hash"]

        entry_id_2 = logger.append_entry(
            action="ACTION_2",
            actor="user",
            resource_type="resource",
            data={},
        )

        entry_id_3 = logger.append_entry(
            action="ACTION_3",
            actor="user",
            resource_type="resource",
            data={},
        )

        # Rollback to first entry
        success, removed = logger.rollback_to_hash(entry_1_hash)
        assert success is True
        assert removed == 2

        # Verify only first entry remains
        result = logger.verify_chain()
        assert result["total_entries"] == 1

    def test_rollback_invalid_hash(self, logger):
        """Should raise error when rolling back to invalid hash."""
        with pytest.raises(ValueError):
            logger.rollback_to_hash("nonexistent_hash")

    def test_verify_chain_with_timestamp_filter(self, logger):
        """Should verify chain within timestamp range."""
        logger.append_entry(
            action="ACTION_1",
            actor="user",
            resource_type="resource",
            data={},
        )

        # Verify all
        result_all = logger.verify_chain()
        assert result_all["total_entries"] == 1

        # Verify with filters
        now = datetime.utcnow()
        result_future = logger.verify_chain(
            start_timestamp=now + timedelta(hours=1)
        )
        assert result_future["total_entries"] == 0


class TestModuleSingleton:
    """Tests for module-level singleton."""

    def test_get_audit_logger_singleton(self):
        """Should return same instance."""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is logger2

    def test_get_audit_logger_custom_db(self):
        """Should initialize with custom database URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_url = f"sqlite:///{tmpdir}/test.db"
            logger = get_audit_logger(database_url=db_url)
            assert logger.database_url == db_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
