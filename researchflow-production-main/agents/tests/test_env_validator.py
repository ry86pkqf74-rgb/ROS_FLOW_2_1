#!/usr/bin/env python3
"""
Unit tests for EnvValidator

Tests environment variable validation rules and reporting.
"""

import pytest
import os
from unittest.mock import patch
from agents.utils.env_validator import (
    EnvValidator,
    ValidationRule,
    ValidationSeverity,
    ValidationResult,
    is_url,
    is_postgres_url,
    is_redis_url,
    is_positive_int,
    is_boolean,
    is_api_key,
    get_agent_validator,
    get_service_validator,
    validate_startup_environment
)


class TestValidators:
    """Test validation functions"""
    
    def test_is_url(self):
        """Test URL validation"""
        assert is_url("https://example.com") is True
        assert is_url("http://localhost:3000") is True
        assert is_url("http://192.168.1.1:8080") is True
        assert is_url("not-a-url") is False
        assert is_url("ftp://example.com") is False
    
    def test_is_postgres_url(self):
        """Test PostgreSQL URL validation"""
        assert is_postgres_url("postgresql://user:pass@localhost:5432/db") is True
        assert is_postgres_url("postgres://user:pass@localhost/db") is True
        assert is_postgres_url("mysql://localhost/db") is False
    
    def test_is_redis_url(self):
        """Test Redis URL validation"""
        assert is_redis_url("redis://:password@localhost:6379") is True
        assert is_redis_url("redis://localhost:6379") is True
        assert is_redis_url("http://localhost:6379") is False
    
    def test_is_positive_int(self):
        """Test positive integer validation"""
        assert is_positive_int("123") is True
        assert is_positive_int("1") is True
        assert is_positive_int("0") is False
        assert is_positive_int("-1") is False
        assert is_positive_int("abc") is False
    
    def test_is_boolean(self):
        """Test boolean validation"""
        assert is_boolean("true") is True
        assert is_boolean("false") is True
        assert is_boolean("1") is True
        assert is_boolean("0") is True
        assert is_boolean("yes") is True
        assert is_boolean("no") is True
        assert is_boolean("maybe") is False
    
    def test_is_api_key(self):
        """Test API key validation"""
        assert is_api_key("sk-1234567890abcdefghij") is True
        assert is_api_key("a" * 25) is True
        assert is_api_key("short") is False
        assert is_api_key("has spaces in it but long enough") is False


class TestEnvValidator:
    """Test EnvValidator class"""
    
    def test_add_rule(self):
        """Test adding validation rules"""
        validator = EnvValidator()
        rule = ValidationRule(
            name="TEST_VAR",
            required=True,
            description="Test variable"
        )
        
        validator.add_rule(rule)
        assert "TEST_VAR" in validator.rules
    
    def test_required_variable_present(self):
        """Test validation passes for present required variable"""
        with patch.dict(os.environ, {'REQUIRED_VAR': 'value'}):
            validator = EnvValidator()
            validator.add_rule(ValidationRule(
                name="REQUIRED_VAR",
                required=True,
                severity=ValidationSeverity.CRITICAL
            ))
            
            results = validator.validate_all()
            assert len(results) == 1
            assert results[0].passed is True
    
    def test_required_variable_missing(self):
        """Test validation fails for missing required variable"""
        validator = EnvValidator()
        validator.add_rule(ValidationRule(
            name="MISSING_VAR",
            required=True,
            severity=ValidationSeverity.CRITICAL
        ))
        
        results = validator.validate_all()
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].severity == ValidationSeverity.CRITICAL
    
    def test_optional_variable_missing(self):
        """Test validation passes for missing optional variable"""
        validator = EnvValidator()
        validator.add_rule(ValidationRule(
            name="OPTIONAL_VAR",
            required=False,
            severity=ValidationSeverity.INFO
        ))
        
        results = validator.validate_all()
        assert len(results) == 1
        assert results[0].passed is True
    
    def test_custom_validator_success(self):
        """Test custom validator passes"""
        with patch.dict(os.environ, {'PORT': '3001'}):
            validator = EnvValidator()
            validator.add_rule(ValidationRule(
                name="PORT",
                required=True,
                validator=is_positive_int,
                description="Port number"
            ))
            
            results = validator.validate_all()
            assert results[0].passed is True
    
    def test_custom_validator_failure(self):
        """Test custom validator fails"""
        with patch.dict(os.environ, {'PORT': 'invalid'}):
            validator = EnvValidator()
            validator.add_rule(ValidationRule(
                name="PORT",
                required=True,
                validator=is_positive_int,
                description="Port number"
            ))
            
            results = validator.validate_all()
            assert results[0].passed is False
    
    def test_is_valid_method(self):
        """Test is_valid method"""
        with patch.dict(os.environ, {'KEY1': 'value1'}):
            validator = EnvValidator()
            validator.add_rule(ValidationRule(
                name="KEY1",
                required=True,
                severity=ValidationSeverity.CRITICAL
            ))
            validator.add_rule(ValidationRule(
                name="KEY2",
                required=True,
                severity=ValidationSeverity.CRITICAL
            ))
            
            validator.validate_all()
            
            # Should be invalid because KEY2 is missing
            assert validator.is_valid() is False
    
    def test_get_failures(self):
        """Test get_failures method"""
        with patch.dict(os.environ, {'KEY1': 'value1'}):
            validator = EnvValidator()
            validator.add_rule(ValidationRule(name="KEY1", required=True))
            validator.add_rule(ValidationRule(name="KEY2", required=True))
            validator.add_rule(ValidationRule(name="KEY3", required=True))
            
            validator.validate_all()
            failures = validator.get_failures()
            
            assert len(failures) == 2  # KEY2 and KEY3
            assert all(not f.passed for f in failures)
    
    def test_get_critical_failures(self):
        """Test get_critical_failures method"""
        validator = EnvValidator()
        validator.add_rule(ValidationRule(
            name="CRITICAL_VAR",
            required=True,
            severity=ValidationSeverity.CRITICAL
        ))
        validator.add_rule(ValidationRule(
            name="WARNING_VAR",
            required=True,
            severity=ValidationSeverity.WARNING
        ))
        
        validator.validate_all()
        critical = validator.get_critical_failures()
        
        assert len(critical) == 1
        assert critical[0].severity == ValidationSeverity.CRITICAL
    
    def test_json_report(self):
        """Test JSON report generation"""
        with patch.dict(os.environ, {'KEY1': 'value1'}):
            validator = EnvValidator()
            validator.add_rule(ValidationRule(name="KEY1", required=True))
            validator.add_rule(ValidationRule(name="KEY2", required=True))
            
            validator.validate_all()
            report = validator.get_json_report()
            
            assert 'valid' in report
            assert report['valid'] is False  # KEY2 missing
            assert report['summary']['total'] == 2
            assert report['summary']['passed'] == 1
            assert report['summary']['failed'] == 1


class TestPreConfiguredValidators:
    """Test pre-configured validators"""
    
    def test_agent_validator_structure(self):
        """Test agent validator has expected rules"""
        validator = get_agent_validator()
        
        assert 'COMPOSIO_API_KEY' in validator.rules
        assert 'OPENAI_API_KEY' in validator.rules
        assert validator.rules['COMPOSIO_API_KEY'].required is True
        assert validator.rules['COMPOSIO_API_KEY'].severity == ValidationSeverity.CRITICAL
    
    def test_service_validator_structure(self):
        """Test service validator has expected rules"""
        validator = get_service_validator()
        
        assert 'DATABASE_URL' in validator.rules
        assert 'REDIS_URL' in validator.rules
        assert validator.rules['DATABASE_URL'].required is True


class TestStartupValidation:
    """Test startup validation function"""
    
    def test_validate_startup_success(self, capsys):
        """Test successful startup validation"""
        with patch.dict(os.environ, {
            'COMPOSIO_API_KEY': 'comp_' + 'x' * 20,
            'OPENAI_API_KEY': 'sk-' + 'x' * 20
        }):
            result = validate_startup_environment()
            assert result is True
            
            # Check output
            captured = capsys.readouterr()
            assert "VALIDATION PASSED" in captured.out
    
    def test_validate_startup_failure(self, capsys):
        """Test failed startup validation"""
        # Missing required keys
        result = validate_startup_environment()
        assert result is False
        
        # Check output
        captured = capsys.readouterr()
        assert "VALIDATION FAILED" in captured.out


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
