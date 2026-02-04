# 🚨 SENTRY ERROR HANDLING AGENT - MISSION BRIEFING

**Agent Type**: Sentry Continuous AI Agent
**Priority**: MEDIUM (Dependent on Agents 1-3)
**Estimated Time**: 1 hour
**Dependencies**: Import resolution + Security clearance + Basic testing

## 🎯 **PRIMARY MISSION**

**ERROR HANDLING**: Audit and enhance error handling across all components
**MONITORING**: Ensure proper error tracking and monitoring integration
**RESILIENCE**: Validate graceful degradation and recovery scenarios

## 🔍 **ERROR HANDLING AUDIT SCOPE**

### **Target #1: PHI Compliance Error Handling**
**File**: `services/worker/src/security/phi_compliance.py`
**Critical Areas**:
- PHI detection failures and edge cases
- Sanitization errors and recovery
- Compliance validation exceptions
- Performance timeouts and limits

### **Target #2: Enhanced Generation Error Handling**  
**File**: `services/worker/src/enhanced_protocol_generation.py`
**Critical Areas**:
- Configuration loading failures
- Template processing errors
- Batch generation failures
- Async processing exceptions

### **Target #3: API Error Handling**
**File**: `services/worker/src/api/protocol_api.py`
**Critical Areas**:
- Request validation errors
- Response serialization failures
- Dependency service failures
- Authentication/authorization errors

### **Target #4: Configuration Error Handling**
**File**: `services/worker/src/config/protocol_config.py`  
**Critical Areas**:
- File I/O errors
- JSON/YAML parsing failures
- Environment variable missing
- Validation constraint violations

## 🚨 **CRITICAL ERROR SCENARIOS**

### **Scenario #1: PHI Detection Failures**
```python
# Current error handling in phi_compliance.py:
try:
    phi_matches = self.detector.detect_phi(content, context)
except Exception as e:
    logger.error(f"PHI validation failed: {str(e)}")  # ⚠️ May leak PHI
    return PHIValidationResult(is_compliant=False)
```
**Issues**:
- Error message may contain PHI data
- No differentiation between error types
- No recovery/retry mechanism
- Insufficient error context

### **Scenario #2: API Service Failures**
```python
# Current error handling in protocol_api.py:
@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")  # ⚠️ May leak sensitive data
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```
**Issues**:
- Generic error responses
- Potential sensitive data leakage
- No error correlation IDs
- Limited error recovery

### **Scenario #3: Configuration Loading Failures**
```python
# Current error handling in protocol_config.py:
try:
    with open(config_file, 'r') as f:
        config_data = json.load(f)
except Exception as e:
    logger.error(f"Failed to load config from {config_file}: {str(e)}")
    raise
```
**Issues**:
- File paths exposed in logs
- No fallback configuration
- Cascading failure potential
- Poor error recovery

## 🛠️ **ERROR HANDLING IMPROVEMENTS**

### **IMPROVEMENT #1: Structured Error Handling**

**Create**: `services/worker/src/utils/error_handling.py`
```python
"""
Enhanced Error Handling Utilities
Provides structured error handling with PHI safety and monitoring integration.
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union
from enum import Enum

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for better classification."""
    PHI_COMPLIANCE = "phi_compliance"
    PROTOCOL_GENERATION = "protocol_generation"
    API_VALIDATION = "api_validation"
    CONFIGURATION = "configuration"
    SYSTEM = "system"

class StructuredError:
    """Structured error with context and safety features."""
    
    def __init__(self,
                 message: str,
                 category: ErrorCategory,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 error_code: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None,
                 original_exception: Optional[Exception] = None):
        
        self.error_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now()
        self.message = message
        self.category = category
        self.severity = severity
        self.error_code = error_code or f"{category.value.upper()}_ERROR"
        self.context = self._sanitize_context(context or {})
        self.original_exception = original_exception
        self.stack_trace = self._get_safe_stack_trace()
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove potentially sensitive data from error context."""
        sanitized = {}
        
        # PHI-related keywords to exclude
        phi_keywords = ['ssn', 'phone', 'email', 'name', 'patient', 'address']
        
        for key, value in context.items():
            key_lower = key.lower()
            
            # Skip PHI-related fields
            if any(phi_word in key_lower for phi_word in phi_keywords):
                sanitized[key] = "[REDACTED_PHI]"
            
            # Skip sensitive config data
            elif any(sens_word in key_lower for sens_word in ['password', 'secret', 'key', 'token']):
                sanitized[key] = "[REDACTED_CREDENTIAL]"
            
            # Truncate long values
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "...[TRUNCATED]"
            
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_safe_stack_trace(self) -> Optional[str]:
        """Get stack trace with sensitive data removed."""
        if self.original_exception:
            try:
                trace_lines = traceback.format_exception(
                    type(self.original_exception),
                    self.original_exception,
                    self.original_exception.__traceback__
                )
                
                # Filter sensitive file paths and data
                safe_lines = []
                for line in trace_lines:
                    # Remove absolute paths, keep relative
                    if 'services/worker/src' in line:
                        line = line.replace(str(Path.cwd()), '[PROJECT_ROOT]')
                    safe_lines.append(line)
                
                return ''.join(safe_lines)
            except Exception:
                return "Stack trace unavailable"
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/API responses."""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "context": self.context
        }
    
    def to_api_response(self) -> Dict[str, Any]:
        """Convert to safe API response (no internal details)."""
        return {
            "error": True,
            "error_id": self.error_id,
            "message": self.message,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat()
        }

class ErrorHandler:
    """Centralized error handling with monitoring integration."""
    
    def __init__(self, enable_monitoring: bool = True):
        self.enable_monitoring = enable_monitoring
        self.logger = logging.getLogger(__name__)
        
    def handle_error(self,
                    message: str,
                    category: ErrorCategory,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None,
                    exception: Optional[Exception] = None) -> StructuredError:
        """Handle error with proper logging and monitoring."""
        
        structured_error = StructuredError(
            message=message,
            category=category,
            severity=severity,
            context=context,
            original_exception=exception
        )
        
        # Log based on severity
        log_data = structured_error.to_dict()
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical("CRITICAL ERROR: %(message)s [ID: %(error_id)s]", log_data)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error("HIGH SEVERITY: %(message)s [ID: %(error_id)s]", log_data)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning("MEDIUM SEVERITY: %(message)s [ID: %(error_id)s]", log_data)
        else:
            self.logger.info("LOW SEVERITY: %(message)s [ID: %(error_id)s]", log_data)
        
        # Send to monitoring if enabled
        if self.enable_monitoring:
            self._send_to_monitoring(structured_error)
        
        return structured_error
    
    def _send_to_monitoring(self, error: StructuredError):
        """Send error to monitoring system (Sentry integration point)."""
        try:
            # This is where Sentry integration would go
            # For now, just additional logging
            self.logger.info(f"Error {error.error_id} sent to monitoring system")
            
            # Future Sentry integration:
            # import sentry_sdk
            # sentry_sdk.set_context("error_details", error.to_dict())
            # sentry_sdk.capture_exception(error.original_exception)
            
        except Exception as e:
            self.logger.error(f"Failed to send error to monitoring: {str(e)}")

# Global error handler instance
error_handler = ErrorHandler()

# Convenience functions
def handle_phi_error(message: str, context: Optional[Dict] = None, exception: Optional[Exception] = None) -> StructuredError:
    """Handle PHI-related errors."""
    return error_handler.handle_error(message, ErrorCategory.PHI_COMPLIANCE, ErrorSeverity.HIGH, context, exception)

def handle_api_error(message: str, context: Optional[Dict] = None, exception: Optional[Exception] = None) -> StructuredError:
    """Handle API-related errors."""
    return error_handler.handle_error(message, ErrorCategory.API_VALIDATION, ErrorSeverity.MEDIUM, context, exception)

def handle_config_error(message: str, context: Optional[Dict] = None, exception: Optional[Exception] = None) -> StructuredError:
    """Handle configuration-related errors."""
    return error_handler.handle_error(message, ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH, context, exception)

def handle_system_error(message: str, context: Optional[Dict] = None, exception: Optional[Exception] = None) -> StructuredError:
    """Handle system-level errors."""
    return error_handler.handle_error(message, ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL, context, exception)
```

### **IMPROVEMENT #2: Enhanced Error Recovery**

**Update**: `services/worker/src/security/phi_compliance.py`
```python
# Add to PHIComplianceValidator class:

def validate_content_with_recovery(self, content: str, context: str = "") -> PHIValidationResult:
    """Enhanced validation with error recovery and structured error handling."""
    from utils.error_handling import handle_phi_error
    
    try:
        return self.validate_content(content, context)
        
    except Exception as e:
        # Handle different error types appropriately
        if "timeout" in str(e).lower():
            error = handle_phi_error(
                "PHI validation timeout - content too large or complex patterns",
                context={"content_length": len(content), "context": context[:100]},
                exception=e
            )
            
            # Return partial validation result
            return PHIValidationResult(
                is_compliant=False,
                audit_log=[{
                    "error": error.to_dict(),
                    "message": "Validation failed due to timeout",
                    "fallback_used": True
                }],
                recommendations=["Break content into smaller chunks", "Simplify PHI patterns"]
            )
            
        elif "memory" in str(e).lower():
            error = handle_phi_error(
                "PHI validation memory error - insufficient resources",
                context={"content_length": len(content)},
                exception=e
            )
            
            return PHIValidationResult(
                is_compliant=False,
                audit_log=[error.to_dict()],
                recommendations=["Process content in smaller batches"]
            )
        
        else:
            # Generic error handling
            error = handle_phi_error(
                "PHI validation failed with unknown error",
                context={"content_length": len(content)},
                exception=e
            )
            
            return PHIValidationResult(
                is_compliant=False,
                audit_log=[error.to_dict()],
                recommendations=["Review input data and try again"]
            )
```

### **IMPROVEMENT #3: API Error Enhancement**

**Update**: `services/worker/src/api/protocol_api.py`
```python
from utils.error_handling import handle_api_error, StructuredError, ErrorSeverity

# Enhanced exception handlers:

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Enhanced HTTP exception handling."""
    error = handle_api_error(
        f"HTTP {exc.status_code}: {exc.detail}",
        context={
            "status_code": exc.status_code,
            "path": str(request.url.path),
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error.to_api_response()
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Enhanced validation error handling."""
    error = handle_api_error(
        "Request validation failed",
        context={
            "path": str(request.url.path),
            "validation_errors": str(exc)[:200]  # Truncated
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            **error.to_api_response(),
            "validation_errors": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Catch-all exception handler with safety."""
    error = handle_api_error(
        "Internal server error occurred",
        context={
            "path": str(request.url.path),
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exception=exc
    )
    
    return JSONResponse(
        status_code=500,
        content=error.to_api_response()
    )
```

## 🔍 **MONITORING & ALERTING SETUP**

### **Health Check Enhancements**
```python
# Add to protocol_api.py health endpoint:

@app.get("/api/v1/protocols/health/detailed")
async def detailed_health_check():
    """Detailed health check with error tracking."""
    from utils.error_handling import error_handler
    
    try:
        generator = get_enhanced_protocol_generator()
        health_info = generator.get_system_health()
        
        # Add error tracking metrics
        health_info["error_tracking"] = {
            "recent_errors": len(error_handler.recent_errors),
            "critical_errors": len([e for e in error_handler.recent_errors if e.severity == ErrorSeverity.CRITICAL]),
            "phi_errors": len([e for e in error_handler.recent_errors if e.category == ErrorCategory.PHI_COMPLIANCE])
        }
        
        return health_info
        
    except Exception as e:
        error = handle_system_error("Health check failed", exception=e)
        return {
            "status": "unhealthy",
            "error": error.to_api_response(),
            "timestamp": datetime.now().isoformat()
        }
```

### **Error Metrics Collection**
```python
# Add to utils/error_handling.py:

class ErrorMetrics:
    """Collect error metrics for monitoring."""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.error_history = []
        self.max_history = 1000
    
    def record_error(self, error: StructuredError):
        """Record error for metrics."""
        key = f"{error.category.value}:{error.severity.value}"
        self.error_counts[key] += 1
        
        self.error_history.append(error)
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current error metrics."""
        recent_errors = [e for e in self.error_history 
                        if (datetime.now() - e.timestamp).total_seconds() < 3600]
        
        return {
            "total_errors": len(self.error_history),
            "recent_errors_1h": len(recent_errors),
            "error_counts_by_category": dict(self.error_counts),
            "error_rate_per_minute": len(recent_errors) / 60,
            "most_common_errors": self._get_most_common_errors()
        }
    
    def _get_most_common_errors(self) -> List[Dict[str, Any]]:
        """Get most common error patterns."""
        error_patterns = defaultdict(int)
        for error in self.error_history[-100:]:  # Last 100 errors
            pattern = f"{error.category.value}:{error.error_code}"
            error_patterns[pattern] += 1
        
        return [{"pattern": pattern, "count": count} 
                for pattern, count in sorted(error_patterns.items(), 
                                           key=lambda x: x[1], reverse=True)[:5]]
```

## 📋 **DELIVERABLES**

### **Enhanced Error Handling System**:
- [ ] `services/worker/src/utils/error_handling.py` (New file - 400+ lines)
- [ ] Updated error handling in all 4 target files
- [ ] Structured error responses with correlation IDs
- [ ] PHI-safe error logging and monitoring

### **Monitoring Integration**:
- [ ] Enhanced health check endpoints
- [ ] Error metrics collection
- [ ] Alert thresholds and rules
- [ ] Monitoring dashboard readiness

### **Error Recovery Mechanisms**:
- [ ] Graceful degradation for PHI validation
- [ ] Retry logic for transient failures
- [ ] Fallback configurations
- [ ] Circuit breaker patterns where appropriate

## 📊 **VALIDATION SCENARIOS**

### **Scenario Testing**:
1. **PHI Detection Timeout**: Large text with complex patterns
2. **API Service Failure**: Database connection loss during request
3. **Configuration Corruption**: Invalid JSON in config file
4. **Memory Exhaustion**: Large batch processing request
5. **Network Failures**: External service dependencies unavailable

### **Recovery Testing**:
1. **Partial Failure Recovery**: Some PHI patterns fail, others succeed  
2. **Fallback Configuration**: Default config when custom config fails
3. **Graceful Degradation**: Limited functionality when services unavailable
4. **Alert Threshold Testing**: Error rates trigger appropriate alerts

## 🎯 **SUCCESS CRITERIA**

**ERROR HANDLING EXCELLENCE**:
- [ ] All exceptions caught and handled gracefully
- [ ] No PHI data leaked in error messages or logs
- [ ] Structured errors with correlation IDs
- [ ] Appropriate error recovery mechanisms
- [ ] Comprehensive error monitoring and alerting

**PRODUCTION READINESS**:
- [ ] Error handling tested under load
- [ ] Alert thresholds validated  
- [ ] Monitoring dashboard functional
- [ ] Error recovery mechanisms validated
- [ ] Documentation updated with error scenarios

## ⏰ **EXECUTION TIMELINE**

**Phase 1** (0-20 min): Error Handling Framework
- Create structured error handling utility
- Define error categories and severity levels
- Implement PHI-safe logging

**Phase 2** (20-40 min): Component Integration
- Update PHI compliance error handling
- Enhance API error responses  
- Improve configuration error recovery

**Phase 3** (40-50 min): Monitoring Setup
- Add error metrics collection
- Enhance health check endpoints
- Set up alert thresholds

**Phase 4** (50-60 min): Validation & Testing
- Test error scenarios
- Validate recovery mechanisms
- Generate error handling report

## 🚨 **FINAL ERROR HANDLING REPORT**

```markdown
# ERROR HANDLING AUDIT REPORT

## SUMMARY
- **Files Updated**: 5 (1 new, 4 enhanced)
- **Error Scenarios Covered**: 15+
- **PHI Safety**: ✅ VALIDATED
- **Monitoring Integration**: ✅ READY
- **Recovery Mechanisms**: ✅ IMPLEMENTED

## CRITICAL IMPROVEMENTS
1. ✅ Structured error handling with correlation IDs
2. ✅ PHI-safe error logging and responses
3. ✅ Enhanced API error responses
4. ✅ Configuration error recovery
5. ✅ Monitoring and alerting integration

## PRODUCTION READINESS
- **Error Handling**: ✅ ENTERPRISE-GRADE
- **Monitoring**: ✅ COMPREHENSIVE
- **Recovery**: ✅ GRACEFUL DEGRADATION
- **Security**: ✅ PHI-COMPLIANT

## RECOMMENDATION: ✅ APPROVED FOR DEPLOYMENT
```

---

## 🚨 **AGENT: RELIABILITY THROUGH RESILIENCE**

**Error handling is the foundation of production stability!**
**Every failure must be handled gracefully and securely.**
**PHI data must never appear in error messages or logs.**
**Monitoring is essential for proactive issue resolution.**

**Execute with focus on safety and recoverability!**