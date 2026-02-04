"""
Tests for PHI Audit Chain

Tests cryptographic audit logging, integrity validation, and tamper detection.
"""

import pytest
import sys
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))


class TestPHIAuditEvent:
    """Tests for PHIAuditEvent data class."""
    
    def test_event_creation(self):
        """Test creating a PHI audit event."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import PHIAuditEvent, AuditEventType
            
            event = PHIAuditEvent(
                event_id="test-123",
                timestamp="2024-01-01T12:00:00Z",
                event_type=AuditEventType.PHI_DETECTION,
                job_id="job-456",
                stage_id=5,
                governance_mode="DEMO",
                user_id="user-789",
                event_data={"findings_count": 10},
                previous_hash="prev-hash-123"
            )
            
            assert event.event_id == "test-123"
            assert event.event_type == AuditEventType.PHI_DETECTION
            assert event.job_id == "job-456"
            assert event.stage_id == 5
            assert event.governance_mode == "DEMO"
            assert event.user_id == "user-789"
            assert event.event_data["findings_count"] == 10
            assert event.previous_hash == "prev-hash-123"
            
        except ImportError:
            pytest.skip("PHI audit chain not available")
    
    def test_content_hash_calculation(self):
        """Test content hash calculation."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import PHIAuditEvent, AuditEventType
            
            event = PHIAuditEvent(
                event_id="test-123",
                timestamp="2024-01-01T12:00:00Z",
                event_type=AuditEventType.PHI_DETECTION,
                job_id="job-456",
                stage_id=5,
                governance_mode="DEMO"
            )
            
            # Content hash should be calculated automatically
            assert event.content_hash is not None
            assert len(event.content_hash) == 64  # SHA256 hex length
            
            # Same content should produce same hash
            event2 = PHIAuditEvent(
                event_id="test-123",
                timestamp="2024-01-01T12:00:00Z",
                event_type=AuditEventType.PHI_DETECTION,
                job_id="job-456",
                stage_id=5,
                governance_mode="DEMO"
            )
            
            assert event.content_hash == event2.content_hash
            
        except ImportError:
            pytest.skip("PHI audit chain not available")
    
    def test_integrity_verification(self):
        """Test event integrity verification."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import PHIAuditEvent, AuditEventType
            
            event = PHIAuditEvent(
                event_id="test-123",
                timestamp="2024-01-01T12:00:00Z",
                event_type=AuditEventType.PHI_DETECTION,
                job_id="job-456",
                stage_id=5,
                governance_mode="DEMO"
            )
            
            # Should verify integrity initially
            assert event.verify_integrity() is True
            
            # Tamper with the event
            event.job_id = "tampered-job"
            
            # Should detect tampering
            assert event.verify_integrity() is False
            
        except ImportError:
            pytest.skip("PHI audit chain not available")
    
    def test_serialization(self):
        """Test event serialization and deserialization."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import PHIAuditEvent, AuditEventType
            
            original_event = PHIAuditEvent(
                event_id="test-123",
                timestamp="2024-01-01T12:00:00Z",
                event_type=AuditEventType.PHI_REDACTION,
                job_id="job-456",
                stage_id=5,
                governance_mode="PRODUCTION",
                event_data={"redacted_count": 5}
            )
            
            # Serialize to dict
            event_dict = original_event.to_dict()
            assert event_dict["event_id"] == "test-123"
            assert event_dict["event_type"] == "PHI_REDACTION"
            assert event_dict["job_id"] == "job-456"
            assert event_dict["event_data"]["redacted_count"] == 5
            
            # Deserialize from dict
            restored_event = PHIAuditEvent.from_dict(event_dict)
            assert restored_event.event_id == original_event.event_id
            assert restored_event.event_type == original_event.event_type
            assert restored_event.job_id == original_event.job_id
            assert restored_event.event_data == original_event.event_data
            
        except ImportError:
            pytest.skip("PHI audit chain not available")


class TestPHIAuditChain:
    """Tests for PHI audit chain functionality."""
    
    @pytest.fixture
    def memory_audit_chain(self):
        """Create audit chain with memory storage for testing."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import PHIAuditChain, StorageBackend
            
            return PHIAuditChain(
                storage_backend=StorageBackend.MEMORY,
                enable_signing=False  # Disable crypto for testing
            )
        except ImportError:
            pytest.skip("PHI audit chain not available")
    
    @pytest.fixture  
    def temp_audit_chain(self):
        """Create audit chain with temporary file storage."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import PHIAuditChain, StorageBackend
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl') as f:
                temp_path = f.name
            
            chain = PHIAuditChain(
                storage_backend=StorageBackend.FILE_SYSTEM,
                storage_path=temp_path,
                enable_signing=False
            )
            
            yield chain
            
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
        except ImportError:
            pytest.skip("PHI audit chain not available")
    
    def test_chain_initialization(self, memory_audit_chain):
        """Test audit chain initialization."""
        from src.workflow_engine.audit.phi_audit_chain import StorageBackend
        
        assert memory_audit_chain.storage_backend == StorageBackend.MEMORY
        assert memory_audit_chain.enable_signing is False
        assert memory_audit_chain._memory_events == []
    
    def test_log_phi_event(self, memory_audit_chain):
        """Test logging PHI events."""
        from src.workflow_engine.audit.phi_audit_chain import AuditEventType
        
        event_id = memory_audit_chain.log_phi_event(
            event_type=AuditEventType.PHI_DETECTION,
            job_id="test-job-123",
            stage_id=5,
            governance_mode="DEMO",
            user_id="test-user",
            event_data={"findings_count": 15},
            compliance_context={"framework": "HIPAA"}
        )
        
        assert event_id is not None
        assert len(memory_audit_chain._memory_events) == 1
        
        event = memory_audit_chain._memory_events[0]
        assert event.event_type == AuditEventType.PHI_DETECTION
        assert event.job_id == "test-job-123"
        assert event.stage_id == 5
        assert event.governance_mode == "DEMO"
        assert event.user_id == "test-user"
        assert event.event_data["findings_count"] == 15
        assert event.compliance_context["framework"] == "HIPAA"
    
    def test_chain_linking(self, memory_audit_chain):
        """Test that events are properly linked in a chain."""
        from src.workflow_engine.audit.phi_audit_chain import AuditEventType
        
        # Log first event
        event_id1 = memory_audit_chain.log_phi_event(
            event_type=AuditEventType.PHI_DETECTION,
            job_id="job-1"
        )
        
        # Log second event
        event_id2 = memory_audit_chain.log_phi_event(
            event_type=AuditEventType.PHI_REDACTION,
            job_id="job-2"
        )
        
        assert len(memory_audit_chain._memory_events) == 2
        
        event1 = memory_audit_chain._memory_events[0]
        event2 = memory_audit_chain._memory_events[1]
        
        # First event should have no previous hash
        assert event1.previous_hash is None
        
        # Second event should link to first event
        assert event2.previous_hash == event1.content_hash
    
    def test_phi_validation_in_event_data(self, memory_audit_chain):
        """Test that PHI is not allowed in event data."""
        from src.workflow_engine.audit.phi_audit_chain import AuditEventType
        
        # Should raise error for potential PHI in event data
        with pytest.raises(ValueError, match="Potential PHI detected"):
            memory_audit_chain.log_phi_event(
                event_type=AuditEventType.PHI_DETECTION,
                job_id="job-1",
                event_data={"patient_ssn": "123-45-6789"}  # Looks like PHI
            )
    
    def test_retrieve_audit_trail(self, memory_audit_chain):
        """Test retrieving audit trail with filtering."""
        from src.workflow_engine.audit.phi_audit_chain import AuditEventType
        
        # Log events for different jobs
        memory_audit_chain.log_phi_event(
            event_type=AuditEventType.PHI_DETECTION,
            job_id="job-1"
        )
        
        memory_audit_chain.log_phi_event(
            event_type=AuditEventType.PHI_REDACTION,
            job_id="job-1"
        )
        
        memory_audit_chain.log_phi_event(
            event_type=AuditEventType.PHI_DETECTION,
            job_id="job-2"
        )
        
        # Get all events
        all_events = memory_audit_chain.get_audit_trail()
        assert len(all_events) == 3
        
        # Filter by job ID
        job1_events = memory_audit_chain.get_audit_trail(job_id="job-1")
        assert len(job1_events) == 2
        
        # Filter by event type
        detection_events = memory_audit_chain.get_audit_trail(
            event_type=AuditEventType.PHI_DETECTION
        )
        assert len(detection_events) == 2
        
        # Filter by both job and event type
        job1_detection = memory_audit_chain.get_audit_trail(
            job_id="job-1",
            event_type=AuditEventType.PHI_DETECTION
        )
        assert len(job1_detection) == 1
    
    def test_file_storage(self, temp_audit_chain):
        """Test file-based storage backend."""
        from src.workflow_engine.audit.phi_audit_chain import AuditEventType
        
        # Log an event
        event_id = temp_audit_chain.log_phi_event(
            event_type=AuditEventType.PHI_DETECTION,
            job_id="test-job",
            event_data={"test": "data"}
        )
        
        # Verify file was created and contains data
        assert os.path.exists(temp_audit_chain.storage_path)
        
        with open(temp_audit_chain.storage_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            event_data = json.loads(lines[0])
            assert event_data["event_id"] == event_id
            assert event_data["job_id"] == "test-job"
    
    def test_integrity_validation(self, memory_audit_chain):
        """Test chain integrity validation."""
        from src.workflow_engine.audit.phi_audit_chain import AuditEventType
        
        # Log a few events to create a chain
        for i in range(3):
            memory_audit_chain.log_phi_event(
                event_type=AuditEventType.PHI_DETECTION,
                job_id=f"job-{i}"
            )
        
        # Validate chain integrity
        validation_result = memory_audit_chain.validate_chain_integrity()
        
        assert validation_result["valid"] is True
        assert validation_result["total_events"] == 3
        assert len(validation_result["violations"]) == 0
        assert "No events in audit chain" not in validation_result["message"]
    
    def test_integrity_violation_detection(self, memory_audit_chain):
        """Test detection of integrity violations."""
        from src.workflow_engine.audit.phi_audit_chain import AuditEventType
        
        # Log events
        memory_audit_chain.log_phi_event(
            event_type=AuditEventType.PHI_DETECTION,
            job_id="job-1"
        )
        
        memory_audit_chain.log_phi_event(
            event_type=AuditEventType.PHI_REDACTION,
            job_id="job-2"
        )
        
        # Tamper with the second event
        memory_audit_chain._memory_events[1].job_id = "tampered-job"
        
        # Validation should detect tampering
        validation_result = memory_audit_chain.validate_chain_integrity()
        
        assert validation_result["valid"] is False
        assert len(validation_result["violations"]) > 0
        
        # Should detect content hash mismatch
        violation_types = [v["violation_type"] for v in validation_result["violations"]]
        assert "CONTENT_HASH_MISMATCH" in violation_types
    
    def test_export_audit_report(self, memory_audit_chain):
        """Test audit report export functionality."""
        from src.workflow_engine.audit.phi_audit_chain import AuditEventType
        
        # Log some events
        for i in range(2):
            memory_audit_chain.log_phi_event(
                event_type=AuditEventType.PHI_DETECTION,
                job_id=f"job-{i}",
                governance_mode="DEMO" if i == 0 else "PRODUCTION"
            )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            report_path = f.name
        
        try:
            # Export report
            export_metadata = memory_audit_chain.export_audit_report(
                output_path=report_path,
                format="json",
                include_integrity_check=True
            )
            
            assert export_metadata["export_path"] == report_path
            assert export_metadata["format"] == "json"
            assert export_metadata["total_events"] == 2
            assert export_metadata["file_size_bytes"] > 0
            
            # Verify report content
            with open(report_path, 'r') as f:
                report_data = json.load(f)
                
                assert "export_timestamp" in report_data
                assert report_data["total_events"] == 2
                assert report_data["signing_enabled"] is False
                assert "integrity_check" in report_data
                assert len(report_data["events"]) == 2
                assert "statistics" in report_data
                
                # Check statistics
                stats = report_data["statistics"]
                assert "event_types" in stats
                assert "governance_modes" in stats
                assert stats["governance_modes"]["DEMO"] == 1
                assert stats["governance_modes"]["PRODUCTION"] == 1
                
        finally:
            if os.path.exists(report_path):
                os.unlink(report_path)
    
    def test_empty_chain_handling(self, memory_audit_chain):
        """Test handling of empty audit chains."""
        # Validate empty chain
        validation_result = memory_audit_chain.validate_chain_integrity()
        
        assert validation_result["valid"] is True
        assert validation_result["total_events"] == 0
        assert "No events in audit chain" in validation_result["message"]
        
        # Get audit trail from empty chain
        events = memory_audit_chain.get_audit_trail()
        assert len(events) == 0
    
    def test_time_based_filtering(self, memory_audit_chain):
        """Test time-based filtering of audit events."""
        from src.workflow_engine.audit.phi_audit_chain import AuditEventType
        from datetime import datetime, timedelta
        
        # Log events at different times (simulated)
        now = datetime.utcnow()
        
        # Mock the log method to set specific timestamps
        original_log = memory_audit_chain.log_phi_event
        
        def mock_log_with_time(timestamp_offset_hours=0, **kwargs):
            event_id = original_log(**kwargs)
            # Update the timestamp of the last event
            if memory_audit_chain._memory_events:
                target_time = now + timedelta(hours=timestamp_offset_hours)
                memory_audit_chain._memory_events[-1].timestamp = target_time.isoformat() + "Z"
            return event_id
        
        # Log events at different times
        mock_log_with_time(
            timestamp_offset_hours=-2,
            event_type=AuditEventType.PHI_DETECTION,
            job_id="old-job"
        )
        
        mock_log_with_time(
            timestamp_offset_hours=0,
            event_type=AuditEventType.PHI_REDACTION,
            job_id="recent-job"
        )
        
        # Filter by time range
        one_hour_ago = now - timedelta(hours=1)
        recent_events = memory_audit_chain.get_audit_trail(start_time=one_hour_ago)
        
        assert len(recent_events) == 1
        assert recent_events[0].job_id == "recent-job"


@patch('src.workflow_engine.audit.phi_audit_chain.CRYPTO_AVAILABLE', True)
class TestCryptographicFeatures:
    """Tests for cryptographic signing features."""
    
    def test_signing_initialization(self):
        """Test cryptographic signing initialization."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import PHIAuditChain, StorageBackend
            
            with tempfile.TemporaryDirectory() as temp_dir:
                chain = PHIAuditChain(
                    storage_backend=StorageBackend.MEMORY,
                    enable_signing=True,
                    signing_key_path=temp_dir
                )
                
                # Should have initialized keys
                assert chain.enable_signing is True
                assert chain._private_key is not None
                assert chain._public_key is not None
                
        except ImportError:
            pytest.skip("PHI audit chain not available")
    
    @patch('src.workflow_engine.audit.phi_audit_chain.rsa')
    @patch('src.workflow_engine.audit.phi_audit_chain.serialization')
    def test_key_generation(self, mock_serialization, mock_rsa):
        """Test cryptographic key generation."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import PHIAuditChain, StorageBackend
            
            # Mock key generation
            mock_private_key = MagicMock()
            mock_public_key = MagicMock()
            mock_private_key.public_key.return_value = mock_public_key
            mock_rsa.generate_private_key.return_value = mock_private_key
            
            with tempfile.TemporaryDirectory() as temp_dir:
                chain = PHIAuditChain(
                    storage_backend=StorageBackend.MEMORY,
                    enable_signing=True,
                    signing_key_path=temp_dir
                )
                
                # Should have called key generation
                mock_rsa.generate_private_key.assert_called_once()
                
        except ImportError:
            pytest.skip("PHI audit chain not available")


class TestAuditEventTypes:
    """Tests for audit event type definitions."""
    
    def test_event_type_enum(self):
        """Test that all expected event types are defined."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import AuditEventType
            
            # Check that expected event types exist
            expected_types = [
                "PHI_DETECTION",
                "PHI_REDACTION", 
                "COMPLIANCE_VALIDATION",
                "DATA_ACCESS",
                "DATA_EXPORT",
                "SCHEMA_VALIDATION",
                "RISK_ASSESSMENT",
                "GOVERNANCE_VIOLATION",
                "SYSTEM_EVENT"
            ]
            
            for event_type in expected_types:
                assert hasattr(AuditEventType, event_type)
                assert isinstance(getattr(AuditEventType, event_type), AuditEventType)
                
        except ImportError:
            pytest.skip("AuditEventType not available")
    
    def test_storage_backend_enum(self):
        """Test storage backend definitions."""
        try:
            from src.workflow_engine.audit.phi_audit_chain import StorageBackend
            
            expected_backends = ["FILE_SYSTEM", "DATABASE", "S3_BUCKET", "MEMORY"]
            
            for backend in expected_backends:
                assert hasattr(StorageBackend, backend)
                assert isinstance(getattr(StorageBackend, backend), StorageBackend)
                
        except ImportError:
            pytest.skip("StorageBackend not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])