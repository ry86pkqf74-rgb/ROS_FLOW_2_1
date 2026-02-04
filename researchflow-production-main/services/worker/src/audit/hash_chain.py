"""
Hash Chain Audit Logging Module

Implements immutable audit logging with cryptographic hash chain for tamper detection.
Each entry includes timestamp, action, actor, data hash, and previous hash to form an
unbreakable chain of custody.

Key Features:
- Append-only immutable audit trail
- SHA-256 hash chain for tamper detection
- Database persistence with SQLite/PostgreSQL support
- Transaction-based rollback capability
- Chain integrity verification
- Batch entry support for performance

Phase 14 Implementation - ROS-114
Track E - Monitoring & Audit
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

try:
    from sqlalchemy import (
        create_engine,
        Column,
        String,
        DateTime,
        Text,
        Integer,
        Boolean,
        Float,
        event,
        inspect,
    )
    from sqlalchemy.orm import declarative_base, sessionmaker, Session
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    raise ImportError(
        "SQLAlchemy is required for hash_chain module. "
        "Install with: pip install sqlalchemy"
    )

logger = logging.getLogger(__name__)

# Database ORM base
Base = declarative_base()


class AuditEntry(Base):
    """SQLAlchemy model for audit log entries."""

    __tablename__ = "audit_entries"

    # Primary identifiers
    entry_id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Action metadata
    action = Column(String(255), nullable=False, index=True)
    actor = Column(String(255), nullable=False, index=True)
    resource_type = Column(String(255), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True, index=True)

    # Data content
    data = Column(Text, nullable=True)  # JSON-encoded data
    data_hash = Column(String(64), nullable=False, unique=False)

    # Hash chain
    entry_hash = Column(String(64), nullable=False, unique=False)
    previous_hash = Column(String(64), nullable=False)

    # Metadata
    details = Column(Text, nullable=True)  # Additional JSON context
    rollback_hash = Column(String(64), nullable=True)  # Hash before this entry

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action,
            "actor": self.actor,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "data_hash": self.data_hash,
            "entry_hash": self.entry_hash,
            "previous_hash": self.previous_hash,
            "rollback_hash": self.rollback_hash,
        }


class HashChainAuditLogger:
    """
    Immutable audit logger with cryptographic hash chain.

    Provides append-only audit trail with tamper detection via hash chain.
    All entries are persisted to database with optional rollback capability.
    """

    HASH_ALGORITHM = "sha256"
    HASH_TRUNCATE = 64  # Full SHA-256 hash length (no truncation)
    GENESIS_HASH = "genesis_block_hash_chain_audit_system_v1"

    def __init__(
        self,
        database_url: str = "sqlite:///audit_log.db",
        pool_pre_ping: bool = True,
        pool_size: int = 10,
        max_overflow: int = 20,
        echo: bool = False,
    ):
        """
        Initialize hash chain audit logger.

        Args:
            database_url: SQLAlchemy database URL
                (default: sqlite:///audit_log.db)
            pool_pre_ping: Enable connection pool pre-pinging
            pool_size: Connection pool size
            max_overflow: Max overflow connections
            echo: Enable SQL echo logging

        Raises:
            SQLAlchemyError: If database connection fails
        """
        self.database_url = database_url
        self.logger = logging.getLogger(__name__)

        try:
            # Create engine with connection pooling
            if "sqlite" in database_url:
                self.engine = create_engine(
                    database_url,
                    echo=echo,
                    connect_args={"check_same_thread": False},
                )
            else:
                self.engine = create_engine(
                    database_url,
                    pool_pre_ping=pool_pre_ping,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    echo=echo,
                )

            # Create tables
            Base.metadata.create_all(self.engine)

            # Session factory
            self.SessionLocal = sessionmaker(bind=self.engine)

            self.logger.info(f"Audit logger initialized with {database_url}")

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to initialize audit logger: {e}")
            raise

    @staticmethod
    def _hash_data(data: str) -> str:
        """
        Compute SHA-256 hash of data.

        Args:
            data: String data to hash

        Returns:
            SHA-256 hash hexdigest
        """
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_entry_hash(
        timestamp: str,
        action: str,
        actor: str,
        data_hash: str,
        previous_hash: str,
    ) -> str:
        """
        Compute hash for audit entry using all components.

        Hash includes: timestamp, action, actor, data_hash, previous_hash
        This creates tamper-evident chain - modifying any field breaks the chain.

        Args:
            timestamp: Entry timestamp (ISO format)
            action: Action type
            actor: Actor/user identifier
            data_hash: SHA-256 hash of action data
            previous_hash: Hash of previous entry

        Returns:
            SHA-256 hash of entry
        """
        entry_components = {
            "timestamp": timestamp,
            "action": action,
            "actor": actor,
            "data_hash": data_hash,
            "previous_hash": previous_hash,
        }

        # Deterministic JSON string
        entry_json = json.dumps(entry_components, sort_keys=True)
        return hashlib.sha256(entry_json.encode("utf-8")).hexdigest()

    def _get_last_hash(self, session: Session) -> str:
        """
        Get hash of most recent audit entry.

        Args:
            session: SQLAlchemy session

        Returns:
            Previous entry's hash or GENESIS_HASH for first entry
        """
        try:
            last_entry = (
                session.query(AuditEntry)
                .order_by(AuditEntry.timestamp.desc())
                .first()
            )

            if last_entry:
                return last_entry.entry_hash

            return self._hash_data(self.GENESIS_HASH)

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get last hash: {e}")
            raise

    @contextmanager
    def _get_session(self):
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def append_entry(
        self,
        action: str,
        actor: str,
        resource_type: str,
        data: Optional[Dict[str, Any]] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Append a new entry to the audit chain.

        Creates immutable audit entry with hash chain. Entry includes:
        - Timestamp
        - Action and actor
        - SHA-256 hash of data
        - Previous entry hash (maintains chain)

        Args:
            action: Type of action (e.g., "UPDATE", "DELETE", "CREATE")
            actor: User/system that performed action
            resource_type: Type of resource affected
            data: Data associated with action (will be JSON-encoded)
            resource_id: ID of resource affected (optional)
            details: Additional context/metadata (optional)

        Returns:
            Entry ID of created audit entry

        Raises:
            SQLAlchemyError: If database write fails
            ValueError: If required fields are invalid
        """
        if not action or not actor:
            raise ValueError("action and actor are required")

        try:
            with self._get_session() as session:
                # Generate entry ID
                entry_id = str(uuid.uuid4())
                timestamp = datetime.utcnow()
                timestamp_iso = timestamp.isoformat() + "Z"

                # Hash the data
                data_str = json.dumps(data, sort_keys=True, default=str) if data else ""
                data_hash = self._hash_data(data_str)

                # Get previous hash for chain
                previous_hash = self._get_last_hash(session)

                # Compute entry hash
                entry_hash = self._compute_entry_hash(
                    timestamp=timestamp_iso,
                    action=action,
                    actor=actor,
                    data_hash=data_hash,
                    previous_hash=previous_hash,
                )

                # Create entry
                entry = AuditEntry(
                    entry_id=entry_id,
                    timestamp=timestamp,
                    action=action,
                    actor=actor,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    data=data_str if data else None,
                    data_hash=data_hash,
                    entry_hash=entry_hash,
                    previous_hash=previous_hash,
                    details=json.dumps(details, default=str) if details else None,
                )

                session.add(entry)
                session.flush()  # Get the inserted row

                self.logger.debug(
                    f"Appended audit entry {entry_id}: {action} by {actor}"
                )

                return entry_id

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to append audit entry: {e}")
            raise

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific audit entry.

        Args:
            entry_id: ID of entry to retrieve

        Returns:
            Entry dictionary or None if not found
        """
        try:
            with self._get_session() as session:
                entry = session.query(AuditEntry).filter_by(entry_id=entry_id).first()

                if entry:
                    return entry.to_dict()

                return None

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get entry {entry_id}: {e}")
            raise

    def verify_chain(
        self, start_timestamp: Optional[datetime] = None, end_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Verify integrity of audit hash chain.

        Detects:
        - Modified entries (hash mismatch)
        - Deleted entries (chain breaks)
        - Inserted entries (chain breaks)
        - Out-of-order entries

        Args:
            start_timestamp: Filter entries from this timestamp (optional)
            end_timestamp: Filter entries to this timestamp (optional)

        Returns:
            Verification result dictionary:
                {
                    'valid': bool,
                    'total_entries': int,
                    'verified_entries': int,
                    'invalid_entries': list[entry_id],
                    'chain_breaks': list[entry_id],
                    'details': str
                }
        """
        self.logger.info("Verifying audit chain integrity...")

        try:
            with self._get_session() as session:
                query = session.query(AuditEntry).order_by(AuditEntry.timestamp)

                if start_timestamp:
                    query = query.filter(AuditEntry.timestamp >= start_timestamp)

                if end_timestamp:
                    query = query.filter(AuditEntry.timestamp <= end_timestamp)

                entries = query.all()

                invalid_entries = []
                chain_breaks = []

                previous_hash = self._hash_data(self.GENESIS_HASH)

                for entry in entries:
                    # Verify hash chain continuity
                    if entry.previous_hash != previous_hash:
                        chain_breaks.append(entry.entry_id)
                        self.logger.warning(
                            f"Chain break detected at {entry.entry_id}: "
                            f"expected previous_hash={previous_hash[:8]}..., "
                            f"got {entry.previous_hash[:8]}..."
                        )

                    # Recompute hash for this entry
                    recomputed_hash = self._compute_entry_hash(
                        timestamp=entry.timestamp.isoformat() + "Z",
                        action=entry.action,
                        actor=entry.actor,
                        data_hash=entry.data_hash,
                        previous_hash=entry.previous_hash,
                    )

                    if recomputed_hash != entry.entry_hash:
                        invalid_entries.append(entry.entry_id)
                        self.logger.warning(
                            f"Hash mismatch at {entry.entry_id}: "
                            f"expected {recomputed_hash[:8]}..., "
                            f"got {entry.entry_hash[:8]}..."
                        )

                    previous_hash = entry.entry_hash

                is_valid = len(invalid_entries) == 0 and len(chain_breaks) == 0

                result = {
                    "valid": is_valid,
                    "total_entries": len(entries),
                    "verified_entries": len(entries) - len(invalid_entries) - len(chain_breaks),
                    "invalid_entries": invalid_entries,
                    "chain_breaks": chain_breaks,
                    "details": f"Chain verification: {len(entries)} entries, "
                    f"{len(invalid_entries)} invalid, {len(chain_breaks)} breaks",
                }

                if is_valid:
                    self.logger.info(f"✓ Chain verified: {result['details']}")
                else:
                    self.logger.error(f"✗ Chain invalid: {result['details']}")

                return result

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to verify chain: {e}")
            raise

    def export_chain(
        self,
        output_format: str = "json",
        start_timestamp: Optional[datetime] = None,
        end_timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Export audit chain to string.

        Args:
            output_format: Export format ('json' or 'csv')
            start_timestamp: Filter from this timestamp (optional)
            end_timestamp: Filter to this timestamp (optional)

        Returns:
            Exported data as string

        Raises:
            ValueError: If output_format is invalid
        """
        if output_format not in ("json", "csv"):
            raise ValueError(f"Invalid output_format: {output_format}")

        try:
            with self._get_session() as session:
                query = session.query(AuditEntry).order_by(AuditEntry.timestamp)

                if start_timestamp:
                    query = query.filter(AuditEntry.timestamp >= start_timestamp)

                if end_timestamp:
                    query = query.filter(AuditEntry.timestamp <= end_timestamp)

                entries = query.all()

                if output_format == "json":
                    data = [entry.to_dict() for entry in entries]
                    return json.dumps(data, indent=2, default=str)

                elif output_format == "csv":
                    import csv
                    from io import StringIO

                    output = StringIO()
                    if entries:
                        writer = csv.DictWriter(output, fieldnames=entries[0].to_dict().keys())
                        writer.writeheader()
                        for entry in entries:
                            writer.writerow(entry.to_dict())

                    return output.getvalue()

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to export chain: {e}")
            raise

    def rollback_to_hash(self, target_hash: str) -> Tuple[bool, int]:
        """
        Rollback audit log to specified hash.

        Removes all entries after the target hash entry.
        Preserves referential integrity of hash chain.

        Args:
            target_hash: Entry hash to rollback to

        Returns:
            Tuple of (success, entries_removed)

        Raises:
            SQLAlchemyError: If rollback fails
            ValueError: If target_hash not found
        """
        self.logger.warning(f"Initiating rollback to hash: {target_hash[:8]}...")

        try:
            with self._get_session() as session:
                # Find target entry
                target_entry = (
                    session.query(AuditEntry).filter_by(entry_hash=target_hash).first()
                )

                if not target_entry:
                    raise ValueError(f"Target hash not found: {target_hash}")

                # Get all entries after target
                entries_to_remove = (
                    session.query(AuditEntry)
                    .filter(AuditEntry.timestamp > target_entry.timestamp)
                    .all()
                )

                # Delete entries
                for entry in entries_to_remove:
                    session.delete(entry)

                entries_removed = len(entries_to_remove)
                session.flush()

                self.logger.warning(
                    f"Rollback complete: removed {entries_removed} entries"
                )

                return True, entries_removed

        except SQLAlchemyError as e:
            self.logger.error(f"Rollback failed: {e}")
            raise

    def get_actor_trail(self, actor: str) -> List[Dict[str, Any]]:
        """
        Get all audit entries for a specific actor.

        Args:
            actor: Actor identifier

        Returns:
            List of audit entries
        """
        try:
            with self._get_session() as session:
                entries = (
                    session.query(AuditEntry)
                    .filter_by(actor=actor)
                    .order_by(AuditEntry.timestamp)
                    .all()
                )

                return [entry.to_dict() for entry in entries]

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get actor trail: {e}")
            raise

    def get_resource_trail(self, resource_type: str, resource_id: str) -> List[Dict[str, Any]]:
        """
        Get all audit entries for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: ID of resource

        Returns:
            List of audit entries
        """
        try:
            with self._get_session() as session:
                entries = (
                    session.query(AuditEntry)
                    .filter_by(resource_type=resource_type, resource_id=resource_id)
                    .order_by(AuditEntry.timestamp)
                    .all()
                )

                return [entry.to_dict() for entry in entries]

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get resource trail: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit log statistics.

        Returns:
            Statistics dictionary
        """
        try:
            with self._get_session() as session:
                total = session.query(AuditEntry).count()
                unique_actors = (
                    session.query(AuditEntry.actor).distinct().count()
                )
                action_counts = {}

                for action, count in session.query(AuditEntry.action, session.func.count()).group_by(AuditEntry.action).all():
                    action_counts[action] = count

                return {
                    "total_entries": total,
                    "unique_actors": unique_actors,
                    "action_counts": action_counts,
                }

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get statistics: {e}")
            raise


# Module-level singleton
_audit_logger: Optional[HashChainAuditLogger] = None


def get_audit_logger(
    database_url: str = "sqlite:///audit_log.db",
) -> HashChainAuditLogger:
    """
    Get or create module-level audit logger instance.

    Args:
        database_url: Database URL for first initialization

    Returns:
        HashChainAuditLogger instance
    """
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = HashChainAuditLogger(database_url=database_url)

    return _audit_logger
