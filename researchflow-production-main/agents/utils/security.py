#!/usr/bin/env python3
"""
Security Hardening for ResearchFlow Agents

Provides security utilities for:
- Container security validation
- Input sanitization
- Security headers
- Resource limit enforcement
- Audit logging
- Security monitoring

@author Claude
@created 2025-01-30
"""

import os
import pwd
import grp
import resource
import subprocess
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import hashlib
import secrets
import re

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """Security configuration"""
    enforce_non_root: bool = True
    max_memory_mb: int = 2048  # 2GB
    max_cpu_time: int = 3600   # 1 hour
    max_file_descriptors: int = 1024
    enable_audit_logging: bool = True
    allowed_file_paths: List[str] = None
    blocked_file_patterns: List[str] = None


class SecurityHardening:
    """
    Security hardening utilities for production deployment.
    
    Enforces security best practices including:
    - Non-root execution
    - Resource limits
    - Input validation
    - Audit logging
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.config.allowed_file_paths = self.config.allowed_file_paths or [
            "/app",
            "/tmp",
            "/var/log",
            "/data"
        ]
        self.config.blocked_file_patterns = self.config.blocked_file_patterns or [
            r"\.\.\/",  # Directory traversal
            r"\/etc\/",  # System config
            r"\/proc\/",  # Process info
            r"\/sys\/",   # System info
            r"\.ssh\/",   # SSH keys
        ]
    
    def validate_container_security(self) -> Dict[str, Any]:
        """
        Validate container security configuration.
        
        Returns:
            Security validation report
        """
        checks = {}
        warnings = []
        errors = []
        
        # Check if running as root
        try:
            current_uid = os.getuid()
            current_user = pwd.getpwuid(current_uid).pw_name
            
            if current_uid == 0:
                if self.config.enforce_non_root:
                    errors.append("Running as root user (UID 0) - security risk!")
                else:
                    warnings.append("Running as root user (UID 0)")
                checks["non_root_user"] = False
            else:
                checks["non_root_user"] = True
                logger.info(f"✅ Running as non-root user: {current_user} (UID: {current_uid})")
        except Exception as e:
            warnings.append(f"Could not check user: {e}")
        
        # Check resource limits
        try:
            # Memory limit
            mem_limit = resource.getrlimit(resource.RLIMIT_AS)
            if mem_limit[0] == resource.RLIM_INFINITY:
                warnings.append("No memory limit set")
                checks["memory_limited"] = False
            else:
                checks["memory_limited"] = True
                checks["memory_limit_mb"] = mem_limit[0] // (1024 * 1024)
            
            # File descriptor limit
            fd_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
            checks["max_file_descriptors"] = fd_limit[0]
            if fd_limit[0] > 65536:
                warnings.append(f"High file descriptor limit: {fd_limit[0]}")
            
        except Exception as e:
            warnings.append(f"Could not check resource limits: {e}")
        
        # Check container environment
        if os.path.exists("/.dockerenv"):
            checks["in_container"] = True
        else:
            checks["in_container"] = False
            warnings.append("Not running in container")
        
        # Check for sensitive files
        sensitive_files = [
            "/etc/passwd",
            "/etc/shadow", 
            "/etc/hosts",
            "/proc/version"
        ]
        
        accessible_sensitive = []
        for file_path in sensitive_files:
            if os.path.exists(file_path) and os.access(file_path, os.R_OK):
                accessible_sensitive.append(file_path)
        
        if accessible_sensitive:
            warnings.append(f"Can access sensitive files: {accessible_sensitive}")
        
        checks["accessible_sensitive_files"] = accessible_sensitive
        
        # Overall status
        if errors:
            status = "FAILED"
        elif warnings:
            status = "WARNING" 
        else:
            status = "PASSED"
        
        return {
            "status": status,
            "checks": checks,
            "warnings": warnings,
            "errors": errors
        }
    
    def apply_resource_limits(self):
        """Apply resource limits for security"""
        try:
            # Set memory limit
            if self.config.max_memory_mb > 0:
                memory_bytes = self.config.max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                logger.info(f"✅ Memory limit set to {self.config.max_memory_mb}MB")
            
            # Set CPU time limit
            if self.config.max_cpu_time > 0:
                resource.setrlimit(resource.RLIMIT_CPU, (self.config.max_cpu_time, self.config.max_cpu_time))
                logger.info(f"✅ CPU time limit set to {self.config.max_cpu_time}s")
            
            # Set file descriptor limit
            if self.config.max_file_descriptors > 0:
                resource.setrlimit(resource.RLIMIT_NOFILE, (self.config.max_file_descriptors, self.config.max_file_descriptors))
                logger.info(f"✅ File descriptor limit set to {self.config.max_file_descriptors}")
                
        except Exception as e:
            logger.error(f"❌ Failed to apply resource limits: {e}")
            raise
    
    def validate_file_path(self, file_path: str) -> bool:
        """
        Validate file path for security.
        
        Args:
            file_path: File path to validate
            
        Returns:
            True if path is safe
        """
        # Normalize path
        try:
            normalized_path = os.path.normpath(os.path.abspath(file_path))
        except Exception:
            return False
        
        # Check against blocked patterns
        for pattern in self.config.blocked_file_patterns:
            if re.search(pattern, normalized_path):
                logger.warning(f"🚫 Blocked file path pattern: {normalized_path}")
                return False
        
        # Check against allowed paths
        for allowed_path in self.config.allowed_file_paths:
            if normalized_path.startswith(os.path.abspath(allowed_path)):
                return True
        
        logger.warning(f"🚫 File path not in allowed list: {normalized_path}")
        return False
    
    def sanitize_input(self, input_value: str, max_length: int = 1000) -> str:
        """
        Sanitize user input for security.
        
        Args:
            input_value: Input to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized input
        """
        if not isinstance(input_value, str):
            raise ValueError("Input must be string")
        
        # Length check
        if len(input_value) > max_length:
            raise ValueError(f"Input too long: {len(input_value)} > {max_length}")
        
        # Remove null bytes
        sanitized = input_value.replace('\x00', '')
        
        # Remove control characters except common ones
        sanitized = ''.join(char for char in sanitized 
                          if ord(char) >= 32 or char in ['\n', '\r', '\t'])
        
        return sanitized
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for logging"""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def audit_log(self, event: str, details: Dict[str, Any]):
        """Log security-relevant events"""
        if not self.config.enable_audit_logging:
            return
        
        # Create audit log entry
        audit_entry = {
            "timestamp": logger.handlers[0].formatter.formatTime(
                logging.LogRecord("", 0, "", 0, "", (), None)
            ) if logger.handlers else "",
            "event": event,
            "user": os.getenv("USER", "unknown"),
            "pid": os.getpid(),
            "details": details
        }
        
        # Use structured logging
        logger.info(
            f"AUDIT: {event}",
            extra={
                "audit": True,
                "event_type": event,
                "audit_details": audit_entry
            }
        )


def secure_file_operation(allowed_paths: List[str] = None):
    """
    Decorator to validate file operations.
    
    Args:
        allowed_paths: List of allowed base paths
    """
    security = SecurityHardening()
    if allowed_paths:
        security.config.allowed_file_paths = allowed_paths
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract file paths from arguments
            file_paths = []
            for arg in args:
                if isinstance(arg, (str, Path)) and ('/' in str(arg) or '\\' in str(arg)):
                    file_paths.append(str(arg))
            
            for key, value in kwargs.items():
                if isinstance(value, (str, Path)) and ('/' in str(value) or '\\' in str(value)):
                    file_paths.append(str(value))
            
            # Validate all file paths
            for path in file_paths:
                if not security.validate_file_path(path):
                    raise PermissionError(f"File path not allowed: {path}")
            
            # Log the operation
            security.audit_log("file_operation", {
                "function": func.__name__,
                "paths": file_paths
            })
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global security instance
_security_hardening: Optional[SecurityHardening] = None


def get_security_hardening() -> SecurityHardening:
    """Get global security hardening instance"""
    global _security_hardening
    if _security_hardening is None:
        _security_hardening = SecurityHardening()
    return _security_hardening


def validate_deployment_security() -> bool:
    """
    Validate security for deployment.
    
    Returns:
        True if security validation passes
    """
    security = get_security_hardening()
    report = security.validate_container_security()
    
    print("\n🛡️  Security Validation Report")
    print("=" * 50)
    print(f"Status: {report['status']}")
    
    if report['errors']:
        print(f"\n❌ Errors ({len(report['errors'])}):")
        for error in report['errors']:
            print(f"  - {error}")
    
    if report['warnings']:
        print(f"\n⚠️  Warnings ({len(report['warnings'])}):")
        for warning in report['warnings']:
            print(f"  - {warning}")
    
    print(f"\n✅ Checks:")
    for check, result in report['checks'].items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}: {result}")
    
    return report['status'] == "PASSED"


def apply_security_hardening():
    """Apply security hardening measures"""
    security = get_security_hardening()
    
    try:
        security.apply_resource_limits()
        logger.info("✅ Security hardening applied successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Security hardening failed: {e}")
        return False
