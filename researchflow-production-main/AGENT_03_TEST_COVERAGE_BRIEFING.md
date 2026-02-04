# 🧪 TEST COVERAGE AGENT - MISSION BRIEFING

**Agent Type**: Improve Test Coverage Agent
**Priority**: HIGH (Dependent on Agents 1 & 2)
**Estimated Time**: 2.5 hours
**Dependencies**: Import resolution (Agent 1) + Security clearance (Agent 2)

## 🎯 **PRIMARY MISSION**

**COVERAGE**: Achieve >80% test coverage for all new protocol enhancement components
**INTEGRATION**: Create comprehensive end-to-end test scenarios  
**VALIDATION**: Ensure production-ready quality through exhaustive testing

## 📊 **CURRENT COVERAGE GAPS**

### **Gap #1: PHI Compliance System** - 0% Coverage
**File**: `services/worker/src/security/phi_compliance.py` (1,200+ lines)
**Missing Tests**:
- 15+ PHI detection patterns (unit tests)
- Sanitization methods (security tests)
- Compliance validation scenarios (integration tests)
- Performance under load (stress tests)

### **Gap #2: Enhanced Protocol Generation** - 0% Coverage  
**File**: `services/worker/src/enhanced_protocol_generation.py` (800+ lines)
**Missing Tests**:
- End-to-end protocol generation (integration tests)
- Configuration integration (unit tests)
- Batch processing (performance tests)
- Error handling scenarios (failure tests)

### **Gap #3: REST API Endpoints** - 0% Coverage
**File**: `services/worker/src/api/protocol_api.py` (600+ lines)
**Missing Tests**:
- 5+ REST endpoints (API tests)  
- Request/response validation (unit tests)
- Error handling (negative tests)
- Authentication/authorization (security tests)

### **Gap #4: Configuration Management** - 0% Coverage
**File**: `services/worker/src/config/protocol_config.py` (800+ lines)
**Missing Tests**:
- Environment configuration loading (unit tests)
- User preference management (integration tests)
- Validation logic (edge case tests)
- File I/O operations (system tests)

## 🔧 **DETAILED TEST IMPLEMENTATION**

### **TEST SUITE 1: PHI Compliance Tests** (60 minutes)

**File**: `tests/unit/test_phi_compliance.py`
```python
import pytest
from services.worker.src.security.phi_compliance import (
    PHIDetector, PHISanitizer, PHIComplianceValidator,
    PHIType, ComplianceLevel, PHIMatch
)

class TestPHIDetector:
    """Test PHI detection patterns and accuracy."""
    
    def test_ssn_detection(self):
        """Test SSN pattern detection with various formats."""
        detector = PHIDetector()
        
        # Test cases
        test_cases = [
            ("123-45-6789", True, "Standard SSN format"),
            ("123 45 6789", True, "Space-separated SSN"),
            ("123456789", True, "No separator SSN"),
            ("12-345-6789", False, "Invalid SSN format"),
            ("abc-de-fghi", False, "Non-numeric SSN"),
        ]
        
        for text, should_detect, description in test_cases:
            matches = detector.detect_phi(f"Patient SSN: {text}")
            if should_detect:
                assert len(matches) > 0, f"Failed to detect: {description}"
                assert matches[0].phi_type == PHIType.SSN
            else:
                ssn_matches = [m for m in matches if m.phi_type == PHIType.SSN]
                assert len(ssn_matches) == 0, f"False positive: {description}"
    
    def test_phone_detection(self):
        """Test phone number pattern detection."""
        detector = PHIDetector()
        
        test_cases = [
            ("(555) 123-4567", True),
            ("555-123-4567", True), 
            ("555.123.4567", True),
            ("5551234567", True),
            ("555-1234", False),  # Too short
        ]
        
        for phone, should_detect in test_cases:
            matches = detector.detect_phi(f"Call {phone} for info")
            phone_matches = [m for m in matches if m.phi_type == PHIType.PHONE]
            if should_detect:
                assert len(phone_matches) > 0, f"Missed phone: {phone}"
            else:
                assert len(phone_matches) == 0, f"False positive: {phone}"
    
    def test_email_detection(self):
        """Test email pattern detection.""" 
        detector = PHIDetector()
        
        test_cases = [
            ("john.doe@example.com", True),
            ("patient123@hospital.org", True),
            ("invalid@", False),
            ("@invalid.com", False),
            ("not-an-email", False),
        ]
        
        for email, should_detect in test_cases:
            matches = detector.detect_phi(f"Contact: {email}")
            email_matches = [m for m in matches if m.phi_type == PHIType.EMAIL]
            if should_detect:
                assert len(email_matches) > 0, f"Missed email: {email}"
            else:
                assert len(email_matches) == 0, f"False positive: {email}"
    
    def test_performance_large_text(self):
        """Test PHI detection performance on large text."""
        detector = PHIDetector()
        large_text = "This is sample text. " * 10000 + "SSN: 123-45-6789"
        
        import time
        start_time = time.time()
        matches = detector.detect_phi(large_text)
        duration = time.time() - start_time
        
        assert duration < 2.0, f"PHI detection too slow: {duration}s"
        assert len(matches) == 1, "Should find exactly one SSN"
        assert matches[0].phi_type == PHIType.SSN

class TestPHISanitizer:
    """Test PHI sanitization and masking."""
    
    def test_redaction_sanitization(self):
        """Test redaction-based sanitization."""
        sanitizer = PHISanitizer()
        
        # Create mock PHI match
        phi_match = PHIMatch(
            phi_type=PHIType.SSN,
            value="123-45-6789",
            start_pos=15,
            end_pos=26,
            confidence=0.95
        )
        
        text = "Patient SSN is 123-45-6789 for reference"
        sanitized = sanitizer.sanitize_text(text, [phi_match], "redact")
        
        assert "123-45-6789" not in sanitized, "PHI not removed"
        assert "[SSN_REDACTED]" in sanitized, "Redaction marker not added"
    
    def test_masking_sanitization(self):
        """Test pattern-preserving masking."""
        sanitizer = PHISanitizer()
        
        phi_match = PHIMatch(
            phi_type=PHIType.SSN,
            value="123-45-6789", 
            start_pos=0,
            end_pos=11,
            confidence=0.95
        )
        
        sanitized = sanitizer.sanitize_text("123-45-6789", [phi_match], "mask")
        assert sanitized == "XXX-XX-XXXX", f"Expected XXX-XX-XXXX, got {sanitized}"

class TestPHIComplianceValidator:
    """Test complete PHI compliance validation."""
    
    def test_strict_compliance(self):
        """Test strict compliance mode."""
        validator = PHIComplianceValidator(compliance_level=ComplianceLevel.STRICT)
        
        # Text with PHI should fail strict compliance
        text_with_phi = "Patient John Doe, SSN 123-45-6789, phone 555-1234"
        result = validator.validate_content(text_with_phi)
        
        assert not result.is_compliant, "Should fail strict compliance with PHI"
        assert len(result.phi_matches) > 0, "Should detect PHI matches"
        assert result.risk_score > 0, "Should have non-zero risk score"
    
    def test_permissive_compliance(self):
        """Test permissive compliance mode."""
        validator = PHIComplianceValidator(compliance_level=ComplianceLevel.PERMISSIVE)
        
        text_with_phi = "Patient information available"
        result = validator.validate_content(text_with_phi)
        
        assert result.is_compliant, "Should pass permissive compliance"
    
    def test_compliance_recommendations(self):
        """Test generation of compliance recommendations."""
        validator = PHIComplianceValidator()
        
        text = "SSN: 123-45-6789, Email: john@example.com"
        result = validator.validate_content(text)
        
        assert len(result.recommendations) > 0, "Should provide recommendations"
        assert any("SSN" in rec for rec in result.recommendations), "Should recommend SSN handling"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### **TEST SUITE 2: Enhanced Protocol Generation Tests** (45 minutes)

**File**: `tests/integration/test_enhanced_generation.py`  
```python
import pytest
import asyncio
from services.worker.src.enhanced_protocol_generation import EnhancedProtocolGenerator
from services.worker.src.workflow_engine.stages.study_analyzers.protocol_generator import ProtocolFormat

class TestEnhancedProtocolGeneration:
    """Integration tests for enhanced protocol generation."""
    
    @pytest.fixture
    async def generator(self):
        """Create generator instance for testing."""
        return EnhancedProtocolGenerator("default")
    
    @pytest.mark.asyncio
    async def test_basic_protocol_generation(self, generator):
        """Test basic protocol generation functionality."""
        study_data = {
            "study_title": "Test Clinical Trial",
            "principal_investigator": "Dr. Test",
            "primary_objective": "Test primary objective",
            "estimated_sample_size": 100
        }
        
        result = await generator.generate_protocol_enhanced(
            template_id="rct_basic",
            study_data=study_data,
            output_format=ProtocolFormat.MARKDOWN
        )
        
        assert result["success"], f"Generation failed: {result.get('error')}"
        assert "protocol_content" in result
        assert len(result["protocol_content"]) > 100, "Protocol too short"
        assert "Test Clinical Trial" in result["protocol_content"], "Study title missing"
    
    @pytest.mark.asyncio 
    async def test_phi_compliance_integration(self, generator):
        """Test PHI compliance integration."""
        study_data = {
            "study_title": "Test Study",
            "principal_investigator": "Dr. John Smith",
            "patient_contact": "john.doe@example.com",  # Contains PHI
            "site_phone": "555-123-4567"  # Contains PHI
        }
        
        result = await generator.generate_protocol_enhanced(
            template_id="rct_basic",
            study_data=study_data,
            phi_check=True
        )
        
        assert result["success"], "Should succeed even with PHI"
        phi_info = result["enhanced_features"]["phi_compliance"]
        assert phi_info["enabled"], "PHI compliance should be enabled"
        
        if phi_info["validation_result"]:
            assert "phi_matches" in phi_info["validation_result"]
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, generator):
        """Test batch protocol generation."""
        requests = [
            {
                "template_id": "rct_basic",
                "study_data": {"study_title": f"Study {i}", "principal_investigator": "Dr. Test"},
                "output_format": ProtocolFormat.MARKDOWN
            }
            for i in range(3)
        ]
        
        result = await generator.batch_generate_enhanced(requests)
        
        assert result["success"], "Batch generation should succeed"
        assert len(result["results"]) == 3, "Should have 3 results"
        assert result["batch_statistics"]["successful_requests"] == 3
    
    def test_template_listing(self, generator):
        """Test enhanced template listing."""
        templates = generator.get_available_templates_enhanced()
        
        assert len(templates) > 0, "Should have templates available"
        for template_id, info in templates.items():
            assert "enhanced_features" in info, f"Template {template_id} missing enhanced features"
            assert "phi_compliance" in info["enhanced_features"]
```

### **TEST SUITE 3: REST API Tests** (45 minutes)

**File**: `tests/integration/test_protocol_api.py`
```python
import pytest
from fastapi.testclient import TestClient
from services.worker.src.api.protocol_api import app

class TestProtocolAPI:
    """Integration tests for Protocol REST API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/protocols/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "templates_loaded" in data
        assert data["templates_loaded"] > 0
    
    def test_get_templates(self, client):
        """Test templates listing endpoint."""
        response = client.get("/api/v1/protocols/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert data["total_count"] > 0
        assert len(data["templates"]) == data["total_count"]
    
    def test_generate_protocol(self, client):
        """Test protocol generation endpoint."""
        request_data = {
            "template_id": "rct_basic",
            "study_data": {
                "study_title": "API Test Study",
                "principal_investigator": "Dr. API Test",
                "primary_objective": "Test API functionality"
            },
            "output_format": "markdown"
        }
        
        response = client.post("/api/v1/protocols/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "protocol_content" in data
        assert "API Test Study" in data["protocol_content"]
    
    def test_validate_variables(self, client):
        """Test variable validation endpoint."""
        request_data = {
            "template_id": "rct_basic", 
            "variables": {
                "study_title": "Test Study",
                "principal_investigator": "Dr. Test"
            }
        }
        
        response = client.post("/api/v1/protocols/validate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "missing_variables" in data
    
    def test_batch_generation(self, client):
        """Test batch generation endpoint."""
        request_data = {
            "requests": [
                {
                    "template_id": "rct_basic",
                    "study_data": {"study_title": f"Batch Study {i}"},
                    "output_format": "markdown"
                }
                for i in range(2)
            ]
        }
        
        response = client.post("/api/v1/protocols/batch", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["total_requests"] == 2
    
    def test_error_handling(self, client):
        """Test API error handling."""
        # Test invalid template ID
        response = client.post("/api/v1/protocols/generate", json={
            "template_id": "nonexistent",
            "study_data": {},
            "output_format": "markdown"
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_input_validation(self, client):
        """Test input validation."""
        # Test invalid output format
        response = client.post("/api/v1/protocols/generate", json={
            "template_id": "rct_basic",
            "study_data": {"study_title": "Test"},
            "output_format": "invalid_format"
        })
        
        assert response.status_code == 422  # Validation error
```

### **TEST SUITE 4: Configuration Tests** (30 minutes)

**File**: `tests/unit/test_protocol_config.py`
```python
import pytest
import tempfile
import json
from pathlib import Path
from services.worker.src.config.protocol_config import (
    ProtocolConfig, ConfigManager, ConfigEnvironment,
    PHIComplianceSettings, APIConfiguration
)

class TestProtocolConfig:
    """Test configuration management system."""
    
    def test_default_config_creation(self):
        """Test default configuration creation."""
        config = ProtocolConfig()
        
        assert config.environment == ConfigEnvironment.DEVELOPMENT
        assert config.debug_mode == False
        assert config.phi_compliance.enabled == True
        assert config.api_config.port == 8002
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = ProtocolConfig()
        result = config.validate_configuration()
        
        assert result["valid"], f"Default config should be valid: {result['errors']}"
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
    
    def test_config_serialization(self):
        """Test config serialization to JSON."""
        config = ProtocolConfig()
        json_str = config.to_json()
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "environment" in parsed
        assert "phi_compliance" in parsed
    
    def test_config_file_operations(self):
        """Test saving/loading config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(Path(temp_dir))
            
            # Create and save config
            config = ProtocolConfig()
            config.debug_mode = True
            config_manager.save_config(config, "test")
            
            # Load and verify
            loaded_config = config_manager.load_config("test")
            assert loaded_config.debug_mode == True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## 📊 **COVERAGE TARGETS & METRICS**

### **Target Coverage Levels**:
- **Unit Tests**: >85% line coverage
- **Integration Tests**: >80% functionality coverage  
- **API Tests**: 100% endpoint coverage
- **Error Scenarios**: >75% error path coverage

### **Performance Benchmarks**:
- PHI detection: <100ms for 10KB text
- Protocol generation: <5 seconds per protocol
- API response: <200ms for simple requests
- Batch processing: <30 seconds for 10 protocols

### **Quality Gates**:
- All tests must pass
- No test failures in CI/CD
- Coverage reports generated
- Performance benchmarks met

## ⚡ **EXECUTION STRATEGY**

### **Phase 1** (0-60 min): Core Component Tests
- Implement PHI compliance test suite
- Focus on critical detection patterns
- Test sanitization functionality

### **Phase 2** (60-105 min): Integration Tests  
- Enhanced protocol generation tests
- End-to-end workflow validation
- Configuration integration tests

### **Phase 3** (105-135 min): API & System Tests
- REST API endpoint testing
- Error handling validation  
- Performance benchmark tests

### **Phase 4** (135-150 min): Coverage Analysis & Reporting
- Generate coverage reports
- Identify remaining gaps
- Provide final test results

## 🎯 **SUCCESS CRITERIA**

**CRITICAL SUCCESS FACTORS**:
- [ ] >80% overall test coverage achieved
- [ ] All critical components tested (PHI, API, Config)  
- [ ] Integration tests validate end-to-end functionality
- [ ] Performance benchmarks met
- [ ] Error handling comprehensively tested

**QUALITY METRICS**:
- Test execution time: <5 minutes total
- Test reliability: >99% consistent results
- Coverage accuracy: <5% false positives/negatives
- Documentation: All tests documented

## 📋 **DELIVERABLES**

### **Test Suites** (4 files created):
- `tests/unit/test_phi_compliance.py`
- `tests/integration/test_enhanced_generation.py`  
- `tests/integration/test_protocol_api.py`
- `tests/unit/test_protocol_config.py`

### **Coverage Report**:
```
Coverage Report - Protocol Enhancement System
============================================
File                               Lines   Miss  Cover
----------------------------------------------------
src/security/phi_compliance.py      1200    120    90%
src/enhanced_protocol_generation.py  800     80    90%
src/api/protocol_api.py              600     60    90%
src/config/protocol_config.py        800     80    90%
----------------------------------------------------
TOTAL                               3400    340    90%
```

### **Test Execution Report**:
- Total tests: 50+
- Passed: 50+  
- Failed: 0
- Execution time: <5 minutes
- Coverage: >80%

## 🚨 **ESCALATION CONDITIONS**

**IMMEDIATE ESCALATION IF**:
- Test coverage cannot reach >80%
- Critical components cannot be tested effectively
- Integration tests reveal major bugs
- Performance benchmarks cannot be met

---

## 🧪 **AGENT: QUALITY IS NON-NEGOTIABLE**

**Comprehensive testing is essential for production deployment!**
**Focus on critical PHI compliance and API functionality first.**
**Integration tests must validate the complete workflow.**
**Performance testing ensures production scalability.**

**Execute systematically and report progress every 45 minutes!**