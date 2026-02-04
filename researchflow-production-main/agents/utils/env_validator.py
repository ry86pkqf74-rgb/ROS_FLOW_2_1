#!/usr/bin/env python3
"""
Environment Variable Validator for ResearchFlow Agents

Validates required environment variables and configurations at startup.
Prevents silent failures due to missing or invalid configuration.

Features:
- Required vs optional variables
- Type validation (int, bool, url, etc.)
- Format validation (email, API key, etc.)
- Detailed error messages
- Startup validation

@author Claude
@created 2025-01-30
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity of validation issues"""
    CRITICAL = "critical"  # Will prevent startup
    ERROR = "error"  # Should prevent startup
    WARNING = "warning"  # Should be fixed but not blocking
    INFO = "info"  # Informational


@dataclass
class ValidationRule:
    """Validation rule for an environment variable"""
    name: str
    required: bool = False
    severity: ValidationSeverity = ValidationSeverity.ERROR
    validator: Optional[Callable[[str], bool]] = None
    default: Optional[str] = None
    description: str = ""
    example: str = ""


@dataclass
class ValidationResult:
    """Result of validating a single variable"""
    var_name: str
    passed: bool
    severity: ValidationSeverity
    message: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None


class EnvValidator:
    """
    Validator for environment variables.
    
    Example:
        >>> validator = EnvValidator()
        >>> validator.add_rule(ValidationRule(
        ...     name="DATABASE_URL",
        ...     required=True,
        ...     severity=ValidationSeverity.CRITICAL,
        ...     validator=lambda v: v.startswith("postgresql://"),
        ...     description="PostgreSQL connection URL"
        ... ))
        >>> results = validator.validate_all()
        >>> if not validator.is_valid():
        ...     validator.print_report()
        ...     exit(1)
    """
    
    def __init__(self):
        self.rules: Dict[str, ValidationRule] = {}
        self.results: List[ValidationResult] = []
    
    def add_rule(self, rule: ValidationRule):
        """Add a validation rule"""
        self.rules[rule.name] = rule
    
    def add_rules(self, rules: List[ValidationRule]):
        """Add multiple validation rules"""
        for rule in rules:
            self.add_rule(rule)
    
    def validate_all(self) -> List[ValidationResult]:
        """
        Validate all registered rules.
        
        Returns:
            List of validation results
        """
        self.results = []
        
        for var_name, rule in self.rules.items():
            result = self._validate_variable(rule)
            self.results.append(result)
        
        return self.results
    
    def _validate_variable(self, rule: ValidationRule) -> ValidationResult:
        """Validate a single variable"""
        value = os.getenv(rule.name)
        
        # Check if required variable is missing
        if rule.required and not value:
            return ValidationResult(
                var_name=rule.name,
                passed=False,
                severity=rule.severity,
                message=f"Required variable '{rule.name}' is not set",
                suggested_value=rule.example or rule.default
            )
        
        # If optional and not set, that's ok
        if not rule.required and not value:
            if rule.default:
                return ValidationResult(
                    var_name=rule.name,
                    passed=True,
                    severity=ValidationSeverity.INFO,
                    message=f"Optional variable '{rule.name}' not set, using default: {rule.default}",
                    suggested_value=rule.default
                )
            return ValidationResult(
                var_name=rule.name,
                passed=True,
                severity=ValidationSeverity.INFO,
                message=f"Optional variable '{rule.name}' not set",
                current_value=None
            )
        
        # Run custom validator if provided
        if value and rule.validator:
            try:
                if not rule.validator(value):
                    return ValidationResult(
                        var_name=rule.name,
                        passed=False,
                        severity=rule.severity,
                        message=f"Validation failed for '{rule.name}': {rule.description}",
                        current_value=self._mask_sensitive(value),
                        suggested_value=rule.example
                    )
            except Exception as e:
                return ValidationResult(
                    var_name=rule.name,
                    passed=False,
                    severity=rule.severity,
                    message=f"Validation error for '{rule.name}': {str(e)}",
                    current_value=self._mask_sensitive(value)
                )
        
        # Passed validation
        return ValidationResult(
            var_name=rule.name,
            passed=True,
            severity=ValidationSeverity.INFO,
            message=f"Variable '{rule.name}' is valid",
            current_value=self._mask_sensitive(value)
        )
    
    def is_valid(self) -> bool:
        """
        Check if all validations passed.
        
        Returns:
            True if no critical or error level failures
        """
        for result in self.results:
            if not result.passed and result.severity in [
                ValidationSeverity.CRITICAL,
                ValidationSeverity.ERROR
            ]:
                return False
        return True
    
    def get_failures(self) -> List[ValidationResult]:
        """Get all failed validations"""
        return [r for r in self.results if not r.passed]
    
    def get_critical_failures(self) -> List[ValidationResult]:
        """Get critical failures"""
        return [
            r for r in self.results 
            if not r.passed and r.severity == ValidationSeverity.CRITICAL
        ]
    
    def print_report(self, verbose: bool = False):
        """
        Print validation report to console.
        
        Args:
            verbose: Show all results, not just failures
        """
        print("\\n" + "=" * 70)
        print("🔍 ENVIRONMENT VALIDATION REPORT")
        print("=" * 70)
        
        # Group by severity
        critical = [r for r in self.results if not r.passed and r.severity == ValidationSeverity.CRITICAL]
        errors = [r for r in self.results if not r.passed and r.severity == ValidationSeverity.ERROR]
        warnings = [r for r in self.results if not r.passed and r.severity == ValidationSeverity.WARNING]
        info = [r for r in self.results if r.passed or r.severity == ValidationSeverity.INFO]
        
        if critical:
            print(f"\\n❌ CRITICAL FAILURES ({len(critical)}):")
            for result in critical:
                self._print_result(result)
        
        if errors:
            print(f"\\n❌ ERRORS ({len(errors)}):")
            for result in errors:
                self._print_result(result)
        
        if warnings:
            print(f"\\n⚠️  WARNINGS ({len(warnings)}):")
            for result in warnings:
                self._print_result(result)
        
        if verbose and info:
            print(f"\\n✅ INFO ({len(info)}):")
            for result in info:
                self._print_result(result)
        
        # Summary
        print(f"\\n{'=' * 70}")
        print(f\"Summary: {len(critical)} critical, {len(errors)} errors, {len(warnings)} warnings\")
        
        if not self.is_valid():
            print(\"\\n❌ VALIDATION FAILED - Fix issues above before starting\")\n            print(\"=" * 70 + \"\\n\")\n        else:\n            print(\"\\n✅ VALIDATION PASSED\")\n            print(\"=\" * 70 + \"\\n\")\n    \n    def _print_result(self, result: ValidationResult):\n        \"\"\"Print a single validation result\"\"\"\n        icon = \"✅\" if result.passed else \"❌\"\n        print(f\"  {icon} {result.var_name}\")\n        print(f\"     {result.message}\")\n        \n        if result.current_value:\n            print(f\"     Current: {result.current_value}\")\n        \n        if result.suggested_value:\n            print(f\"     Suggested: {result.suggested_value}\")\n        \n        print()\n    \n    def _mask_sensitive(self, value: str) -> str:\n        \"\"\"Mask sensitive values in output\"\"\"\n        if not value:\n            return \"(not set)\"\n        \n        # Mask API keys, tokens, passwords\n        sensitive_patterns = [\n            r'key',\n            r'token',\n            r'password',\n            r'secret',\n            r'credential'\n        ]\n        \n        # Show first 4 and last 4 characters for debugging\n        if len(value) > 12:\n            return f\"{value[:4]}...{value[-4:]}\"\n        elif len(value) > 4:\n            return f\"{value[:2]}...{value[-2:]}\"\n        else:\n            return \"***\"\n    \n    def get_json_report(self) -> Dict[str, Any]:\n        \"\"\"Get validation report as JSON\"\"\"\n        return {\n            \"valid\": self.is_valid(),\n            \"summary\": {\n                \"total\": len(self.results),\n                \"passed\": sum(1 for r in self.results if r.passed),\n                \"failed\": sum(1 for r in self.results if not r.passed),\n                \"critical\": len(self.get_critical_failures())\n            },\n            \"results\": [\n                {\n                    \"var\": r.var_name,\n                    \"passed\": r.passed,\n                    \"severity\": r.severity.value,\n                    \"message\": r.message\n                }\n                for r in self.results\n            ]\n        }


# Common validators

def is_url(value: str) -> bool:
    \"\"\"Validate URL format\"\"\"\n    url_pattern = re.compile(\n        r'^https?://'\n        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\\.)+[A-Z]{2,6}\\.?|'\n        r'localhost|'\n        r'\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})'\n        r'(?::\\d+)?'\n        r'(?:/?|[/?]\\S+)$', re.IGNORECASE)\n    return bool(url_pattern.match(value))\n\n\ndef is_postgres_url(value: str) -> bool:\n    \"\"\"Validate PostgreSQL URL\"\"\"\n    return value.startswith(('postgresql://', 'postgres://'))\n\n\ndef is_redis_url(value: str) -> bool:\n    \"\"\"Validate Redis URL\"\"\"\n    return value.startswith('redis://')\n\n\ndef is_positive_int(value: str) -> bool:\n    \"\"\"Validate positive integer\"\"\"\n    try:\n        return int(value) > 0\n    except ValueError:\n        return False\n\n\ndef is_boolean(value: str) -> bool:\n    \"\"\"Validate boolean value\"\"\"\n    return value.lower() in ['true', 'false', '1', '0', 'yes', 'no']\n\n\ndef is_api_key(value: str) -> bool:\n    \"\"\"Validate API key format (basic check)\"\"\"\n    # At least 20 characters, alphanumeric with possible dashes/underscores\n    return len(value) >= 20 and bool(re.match(r'^[A-Za-z0-9_-]+$', value))\n\n\n# Pre-configured validators for common use cases\n\ndef get_agent_validator() -> EnvValidator:\n    \"\"\"Get validator configured for ResearchFlow agents\"\"\"\n    validator = EnvValidator()\n    \n    # Critical variables\n    validator.add_rules([\n        ValidationRule(\n            name=\"COMPOSIO_API_KEY\",\n            required=True,\n            severity=ValidationSeverity.CRITICAL,\n            validator=is_api_key,\n            description=\"Composio API key for agent integrations\",\n            example=\"comp_xxxxxxxxxxxxxxxxxxxx\"\n        ),\n        ValidationRule(\n            name=\"OPENAI_API_KEY\",\n            required=True,\n            severity=ValidationSeverity.CRITICAL,\n            validator=is_api_key,\n            description=\"OpenAI API key\",\n            example=\"sk-xxxxxxxxxxxxxxxxxxxx\"\n        ),\n    ])\n    \n    # Optional but recommended\n    validator.add_rules([\n        ValidationRule(\n            name=\"ANTHROPIC_API_KEY\",\n            required=False,\n            severity=ValidationSeverity.WARNING,\n            validator=is_api_key,\n            description=\"Anthropic API key for Claude access\"\n        ),\n        ValidationRule(\n            name=\"GITHUB_TOKEN\",\n            required=False,\n            severity=ValidationSeverity.WARNING,\n            description=\"GitHub personal access token\"\n        ),\n        ValidationRule(\n            name=\"NOTION_API_KEY\",\n            required=False,\n            severity=ValidationSeverity.INFO,\n            description=\"Notion integration token\"\n        ),\n    ])\n    \n    return validator\n\n\ndef get_service_validator() -> EnvValidator:\n    \"\"\"Get validator for service configuration\"\"\"\n    validator = EnvValidator()\n    \n    validator.add_rules([\n        ValidationRule(\n            name=\"DATABASE_URL\",\n            required=True,\n            severity=ValidationSeverity.CRITICAL,\n            validator=is_postgres_url,\n            description=\"PostgreSQL database connection URL\",\n            example=\"postgresql://user:pass@localhost:5432/db\"\n        ),\n        ValidationRule(\n            name=\"REDIS_URL\",\n            required=True,\n            severity=ValidationSeverity.CRITICAL,\n            validator=is_redis_url,\n            description=\"Redis connection URL\",\n            example=\"redis://:password@localhost:6379\"\n        ),\n        ValidationRule(\n            name=\"PORT\",\n            required=False,\n            severity=ValidationSeverity.INFO,\n            validator=is_positive_int,\n            default=\"3001\",\n            description=\"Service port number\"\n        ),\n    ])\n    \n    return validator


def validate_startup_environment(validator: Optional[EnvValidator] = None) -> bool:\n    \"\"\"\n    Validate environment at startup.\n    \n    Args:\n        validator: Custom validator or None for default agent validator\n        \n    Returns:\n        True if validation passed, False otherwise\n        \n    Example:\n        >>> if not validate_startup_environment():\n        ...     sys.exit(1)\n    \"\"\"\n    if validator is None:\n        validator = get_agent_validator()\n    \n    logger.info(\"🔍 Validating environment configuration...\")\n    \n    validator.validate_all()\n    validator.print_report(verbose=False)\n    \n    return validator.is_valid()\n