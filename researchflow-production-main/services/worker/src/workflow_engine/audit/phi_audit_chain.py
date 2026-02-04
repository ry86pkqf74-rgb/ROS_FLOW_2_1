"""
PHI Audit Chain

Cryptographically secure audit logging for PHI handling events.
Creates an immutable, tamper-evident chain of audit events with integrity validation.
"""

import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import threading

logger = logging.getLogger(__name__)

# Optional cryptographic dependencies
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("Cryptography library not available. Install with: pip install cryptography")


class AuditEventType(Enum):
    """Types of audit events."""
    PHI_DETECTION = "PHI_DETECTION"
    PHI_REDACTION = "PHI_REDACTION" 
    COMPLIANCE_VALIDATION = "COMPLIANCE_VALIDATION"
    DATA_ACCESS = "DATA_ACCESS"
    DATA_EXPORT = "DATA_EXPORT"
    SCHEMA_VALIDATION = "SCHEMA_VALIDATION"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    GOVERNANCE_VIOLATION = "GOVERNANCE_VIOLATION"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class StorageBackend(Enum):
    """Audit storage backends."""
    FILE_SYSTEM = "FILE_SYSTEM"
    DATABASE = "DATABASE" 
    S3_BUCKET = "S3_BUCKET"
    MEMORY = "MEMORY"  # For testing only


@dataclass
class PHIAuditEvent:
    """An audit event in the PHI handling chain."""
    event_id: str
    timestamp: str
    event_type: AuditEventType
    job_id: str
    stage_id: Optional[Union[int, str]]
    governance_mode: str
    user_id: Optional[str] = None
    
    # Event-specific data (MUST NOT contain raw PHI)
    event_data: Dict[str, Any] = field(default_factory=dict)
    
    # Chain integrity fields
    previous_hash: Optional[str] = None
    content_hash: str = ""
    signature: Optional[str] = None
    
    # Metadata
    source_system: str = "workflow_engine"
    compliance_context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate content hash after initialization."""
        if not self.content_hash:
            self.content_hash = self.calculate_content_hash()
    
    def calculate_content_hash(self) -> str:
        """Calculate SHA256 hash of event content."""
        # Include all fields except hash and signature for integrity
        content_dict = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "job_id": self.job_id,
            "stage_id": self.stage_id,
            "governance_mode": self.governance_mode,
            "user_id": self.user_id,
            "event_data": self.event_data,
            "previous_hash": self.previous_hash,
            "source_system": self.source_system,
            "compliance_context": self.compliance_context,
        }
        
        # Create deterministic JSON string
        content_json = json.dumps(content_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(content_json.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify the event's content hash integrity."""
        expected_hash = self.calculate_content_hash()
        return self.content_hash == expected_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        event_dict = asdict(self)
        event_dict["event_type"] = self.event_type.value
        return event_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PHIAuditEvent":
        """Create event from dictionary."""
        # Convert event_type back to enum
        if isinstance(data.get("event_type"), str):
            data["event_type"] = AuditEventType(data["event_type"])
        
        return cls(**data)


class PHIAuditChain:
    """
    Cryptographically secure audit chain for PHI handling events.
    
    Creates an immutable, tamper-evident chain where each event references
    the previous event's hash, creating a blockchain-like audit trail.
    """
    
    def __init__(self,
                 storage_backend: StorageBackend = StorageBackend.FILE_SYSTEM,
                 storage_path: Optional[str] = None,
                 enable_signing: bool = True,
                 signing_key_path: Optional[str] = None):
        """
        Initialize the PHI audit chain.
        
        Args:
            storage_backend: Storage backend for audit events
            storage_path: Path for file/database storage  
            enable_signing: Whether to cryptographically sign events
            signing_key_path: Path to signing key (generated if not exists)
        """
        self.storage_backend = storage_backend
        self.storage_path = storage_path or self._get_default_storage_path()
        self.enable_signing = enable_signing and CRYPTO_AVAILABLE
        self.signing_key_path = signing_key_path
        
        # Thread safety for concurrent access
        self._lock = threading.Lock()
        
        # In-memory storage for MEMORY backend
        self._memory_events: List[PHIAuditEvent] = []
        
        # Cryptographic keys
        self._private_key = None
        self._public_key = None
        
        # Initialize storage and keys
        self._initialize_storage()
        if self.enable_signing:
            self._initialize_keys()
        
        logger.info(
            f"PHIAuditChain initialized: backend={storage_backend.value}, "
            f"signing={'enabled' if self.enable_signing else 'disabled'}, "
            f"storage={self.storage_path}"
        )
    
    def _get_default_storage_path(self) -> str:
        """Get default storage path based on backend."""
        if self.storage_backend == StorageBackend.FILE_SYSTEM:
            return "/data/audit/phi_events.jsonl"
        elif self.storage_backend == StorageBackend.S3_BUCKET:
            return "audit-logs/phi-events/"
        else:
            return ":memory:"
    
    def _initialize_storage(self):
        """Initialize storage backend."""
        if self.storage_backend == StorageBackend.FILE_SYSTEM:
            # Ensure audit directory exists
            audit_dir = Path(self.storage_path).parent
            audit_dir.mkdir(parents=True, exist_ok=True)
            
            # Create file if it doesn't exist
            if not Path(self.storage_path).exists():
                Path(self.storage_path).touch()
                
        elif self.storage_backend == StorageBackend.MEMORY:
            self._memory_events = []
            
        # Add other backend initialization as needed
    
    def _initialize_keys(self):
        """Initialize cryptographic signing keys."""
        if not CRYPTO_AVAILABLE:
            logger.warning("Cryptography not available - signing disabled")
            self.enable_signing = False
            return
        
        key_dir = Path(self.signing_key_path or "/data/audit/keys")
        key_dir.mkdir(parents=True, exist_ok=True)
        
        private_key_path = key_dir / "audit_private.pem"
        public_key_path = key_dir / "audit_public.pem"
        
        try:
            if private_key_path.exists():
                # Load existing keys
                with open(private_key_path, "rb") as f:
                    self._private_key = serialization.load_pem_private_key(f.read(), password=None)
                with open(public_key_path, "rb") as f:
                    self._public_key = serialization.load_pem_public_key(f.read())
                logger.info("Loaded existing audit signing keys")
            else:
                # Generate new keys
                self._private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
                self._public_key = self._private_key.public_key()
                
                # Save keys
                with open(private_key_path, "wb") as f:
                    f.write(self._private_key.private_key_pem(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                
                with open(public_key_path, "wb") as f:
                    f.write(self._public_key.public_key_pem(
                        encoding=serialization.Encoding.PEM
                    ))
                
                # Set restrictive permissions
                os.chmod(private_key_path, 0o600)
                os.chmod(public_key_path, 0o644)
                
                logger.info("Generated new audit signing keys")
                
        except Exception as e:
            logger.error(f"Failed to initialize signing keys: {e}")
            self.enable_signing = False
    
    def log_phi_event(self,
                      event_type: AuditEventType,
                      job_id: str,
                      stage_id: Optional[Union[int, str]] = None,
                      governance_mode: str = "UNKNOWN",
                      user_id: Optional[str] = None,
                      event_data: Optional[Dict[str, Any]] = None,
                      compliance_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Log a PHI-related audit event.
        
        Args:
            event_type: Type of audit event
            job_id: Job identifier
            stage_id: Stage identifier (if applicable)
            governance_mode: Current governance mode
            user_id: User identifier (if applicable)
            event_data: Event-specific data (MUST NOT contain raw PHI)
            compliance_context: Compliance-related context
            
        Returns:
            Event ID of the logged event
            
        Raises:
            ValueError: If event_data contains potential PHI
        """
        with self._lock:
            # Validate event data for PHI
            if event_data:
                self._validate_no_phi_in_data(event_data)
            
            # Get previous event hash for chain linking
            previous_hash = self._get_last_event_hash()
            
            # Create audit event
            event = PHIAuditEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat() + "Z",
                event_type=event_type,
                job_id=job_id,
                stage_id=stage_id,
                governance_mode=governance_mode,
                user_id=user_id,
                event_data=event_data or {},
                previous_hash=previous_hash,
                compliance_context=compliance_context or {}
            )
            
            # Sign event if signing is enabled
            if self.enable_signing and self._private_key:
                event.signature = self._sign_event(event)
            
            # Store event
            self._store_event(event)
            
            logger.info(
                f"PHI audit event logged: {event.event_id} "
                f"({event_type.value}) for job {job_id}"
            )
            
            return event.event_id
    
    def _validate_no_phi_in_data(self, data: Any, path: str = ""):
        """Validate that event data contains no raw PHI."""
        # Patterns that might indicate PHI
        phi_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}-\d{3}-\d{4}\b',  # Phone pattern
        ]
        
        if isinstance(data, str):
            for pattern in phi_patterns:
                if re.search(pattern, data):
                    raise ValueError(f"Potential PHI detected in audit data at {path}: {pattern}")
        elif isinstance(data, dict):
            for key, value in data.items():
                self._validate_no_phi_in_data(value, f"{path}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_no_phi_in_data(item, f"{path}[{i}]")
    
    def _get_last_event_hash(self) -> Optional[str]:
        """Get hash of the last event in the chain."""
        try:
            if self.storage_backend == StorageBackend.FILE_SYSTEM:
                # Read last line of the file
                if not Path(self.storage_path).exists():
                    return None
                    
                with open(self.storage_path, 'r') as f:
                    lines = f.readlines()
                    if not lines:
                        return None
                    
                    last_event_data = json.loads(lines[-1].strip())
                    return last_event_data.get("content_hash")
                    
            elif self.storage_backend == StorageBackend.MEMORY:
                if not self._memory_events:
                    return None
                return self._memory_events[-1].content_hash
                
        except Exception as e:
            logger.warning(f"Could not get last event hash: {e}")
            
        return None
    
    def _sign_event(self, event: PHIAuditEvent) -> str:
        """Cryptographically sign an audit event."""
        if not self._private_key:
            return ""
        
        try:
            # Sign the content hash
            signature_bytes = self._private_key.sign(
                event.content_hash.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Return base64-encoded signature
            import base64
            return base64.b64encode(signature_bytes).decode()
            
        except Exception as e:
            logger.error(f"Failed to sign audit event: {e}")
            return ""
    
    def _store_event(self, event: PHIAuditEvent):
        """Store audit event to the configured backend."""
        try:
            if self.storage_backend == StorageBackend.FILE_SYSTEM:
                # Append to JSONL file
                with open(self.storage_path, 'a') as f:
                    json.dump(event.to_dict(), f, separators=(',', ':'))
                    f.write('\n')
                    
            elif self.storage_backend == StorageBackend.MEMORY:
                self._memory_events.append(event)
                
            # Add other storage backends as needed
            
        except Exception as e:
            logger.error(f"Failed to store audit event {event.event_id}: {e}")
            raise
    
    def get_audit_trail(self,
                       job_id: Optional[str] = None,
                       event_type: Optional[AuditEventType] = None,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       limit: int = 1000) -> List[PHIAuditEvent]:
        """
        Retrieve audit trail with optional filtering.
        
        Args:
            job_id: Filter by job ID
            event_type: Filter by event type
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return
            
        Returns:
            List of audit events matching the filters
        """
        events = []
        
        try:
            if self.storage_backend == StorageBackend.FILE_SYSTEM:
                with open(self.storage_path, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        
                        event_data = json.loads(line.strip())
                        event = PHIAuditEvent.from_dict(event_data)
                        
                        # Apply filters
                        if job_id and event.job_id != job_id:
                            continue
                        if event_type and event.event_type != event_type:
                            continue
                        if start_time:
                            event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                            if event_time < start_time:
                                continue
                        if end_time:
                            event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                            if event_time > end_time:
                                continue
                        
                        events.append(event)
                        
                        if len(events) >= limit:
                            break
                            
            elif self.storage_backend == StorageBackend.MEMORY:
                for event in self._memory_events:
                    # Apply same filters
                    if job_id and event.job_id != job_id:
                        continue
                    if event_type and event.event_type != event_type:
                        continue
                    if start_time:
                        event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                        if event_time < start_time:
                            continue
                    if end_time:
                        event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                        if event_time > end_time:
                            continue
                    
                    events.append(event)
                    
                    if len(events) >= limit:
                        break
                        
        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {e}")
            
        return events
    
    def validate_chain_integrity(self, 
                                start_event_id: Optional[str] = None,
                                end_event_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate the integrity of the audit chain.
        
        Args:
            start_event_id: Start validation from this event ID
            end_event_id: End validation at this event ID
            
        Returns:
            Validation result with any integrity violations
        """
        events = self.get_audit_trail(limit=10000)  # Get all events
        
        if not events:
            return {
                "valid": True,
                "total_events": 0,
                "violations": [],
                "message": "No events in audit chain"
            }
        
        violations = []
        previous_hash = None
        
        for i, event in enumerate(events):
            # Skip events outside the specified range
            if start_event_id and event.event_id != start_event_id and previous_hash is None:
                continue
            if end_event_id and event.event_id == end_event_id:
                break
            
            # Validate content hash integrity
            if not event.verify_integrity():
                violations.append({
                    "event_id": event.event_id,
                    "violation_type": "CONTENT_HASH_MISMATCH",
                    "description": f"Event {event.event_id} content hash does not match calculated hash"
                })
            
            # Validate chain linking
            if previous_hash is not None and event.previous_hash != previous_hash:
                violations.append({
                    "event_id": event.event_id,
                    "violation_type": "CHAIN_LINK_BROKEN", 
                    "description": f"Event {event.event_id} previous_hash does not match expected value"
                })
            
            # Validate signature if present
            if event.signature and self._public_key:
                if not self._verify_signature(event):
                    violations.append({
                        "event_id": event.event_id,
                        "violation_type": "INVALID_SIGNATURE",
                        "description": f"Event {event.event_id} signature verification failed"
                    })
            
            previous_hash = event.content_hash
        
        return {
            "valid": len(violations) == 0,
            "total_events": len(events),
            "violations": violations,
            "message": "Audit chain integrity verified" if not violations else f"Found {len(violations)} violations"
        }
    
    def _verify_signature(self, event: PHIAuditEvent) -> bool:
        """Verify the cryptographic signature of an event."""
        if not self._public_key or not event.signature:
            return False
        
        try:
            import base64
            signature_bytes = base64.b64decode(event.signature.encode())
            
            self._public_key.verify(
                signature_bytes,
                event.content_hash.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
            
        except (InvalidSignature, Exception) as e:
            logger.warning(f"Signature verification failed for event {event.event_id}: {e}")
            return False
    
    def export_audit_report(self, 
                           output_path: str,
                           format: str = "json",
                           include_integrity_check: bool = True) -> Dict[str, Any]:
        """
        Export comprehensive audit report.
        
        Args:
            output_path: Path to save the report
            format: Report format ('json', 'csv', 'html')
            include_integrity_check: Whether to include integrity validation
            
        Returns:
            Export metadata and statistics
        """
        events = self.get_audit_trail(limit=100000)  # Get all events
        
        # Perform integrity check if requested
        integrity_result = None
        if include_integrity_check:
            integrity_result = self.validate_chain_integrity()
        
        # Generate report data
        report_data = {
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "total_events": len(events),
            "storage_backend": self.storage_backend.value,
            "signing_enabled": self.enable_signing,
            "integrity_check": integrity_result,
            "events": [event.to_dict() for event in events],
        }
        
        # Event statistics
        event_types = {}
        governance_modes = {}
        for event in events:
            event_types[event.event_type.value] = event_types.get(event.event_type.value, 0) + 1
            governance_modes[event.governance_mode] = governance_modes.get(event.governance_mode, 0) + 1
        
        report_data["statistics"] = {
            "event_types": event_types,
            "governance_modes": governance_modes,
        }
        
        # Export in requested format
        try:
            if format == "json":
                with open(output_path, 'w') as f:
                    json.dump(report_data, f, indent=2)
            elif format == "csv":
                import csv
                with open(output_path, 'w', newline='') as f:
                    if events:
                        writer = csv.DictWriter(f, fieldnames=events[0].to_dict().keys())
                        writer.writeheader()
                        for event in events:
                            writer.writerow(event.to_dict())
            # Add HTML format as needed
            
            logger.info(f"Audit report exported to {output_path} ({format} format)")
            
        except Exception as e:
            logger.error(f"Failed to export audit report: {e}")
            raise
        
        return {
            "export_path": output_path,
            "format": format,
            "total_events": len(events),
            "file_size_bytes": Path(output_path).stat().st_size if Path(output_path).exists() else 0,
            "integrity_violations": len(integrity_result["violations"]) if integrity_result else 0,
        }