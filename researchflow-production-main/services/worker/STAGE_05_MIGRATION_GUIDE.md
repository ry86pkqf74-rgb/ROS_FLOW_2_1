# Stage 5 PHI Detection - Migration Guide

## Overview

This guide helps you migrate from the basic Stage 5 PHI detection to the enhanced production-grade system with ML capabilities, advanced privacy analysis, and cryptographic audit trails.

## 🔄 Migration Steps

### Step 1: Install Enhanced Dependencies

```bash
# Basic installation (required)
pip install -r requirements-phi-enhanced.txt

# ML models (recommended for production)
python -m spacy download en_core_web_sm

# Clinical models (optional, for medical data)
pip install scispacy
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_ner_bc5cdr_md-0.5.1.tar.gz
```

### Step 2: Update Configuration

#### Before (Basic Configuration)
```python
phi_config = {
    "scan_mode": "standard",
    "enable_redaction": False,
    "validate_compliance": True,
}
```

#### After (Enhanced Configuration)
```python
phi_config = {
    # Existing settings (backwards compatible)
    "scan_mode": "standard",
    "enable_redaction": False,
    "validate_compliance": True,
    
    # New enhanced features
    "enable_ml_detection": True,
    "ml_confidence_threshold": 0.8,
    "enable_quasi_analysis": True,
    "k_anonymity_threshold": 5,
    "enable_audit_chain": True,
    "audit_signing": True,
    
    # Multi-jurisdiction compliance
    "compliance_frameworks": ["HIPAA_SAFE_HARBOR", "GDPR_ARTICLE_4"],
    "gdpr_consent": False,  # Set based on your data processing
    "gdpr_data_portability": True,
    "gdpr_right_to_erasure": True,
}
```

### Step 3: Update Environment Variables

```bash
# Add to your environment configuration
export PHI_ML_DETECTION_ENABLED=true
export PHI_AUDIT_CHAIN_ENABLED=true
export PHI_SIGNING_ENABLED=true
export COMPLIANCE_FRAMEWORKS="HIPAA_SAFE_HARBOR,GDPR_ARTICLE_4"

# Optional: Specify model paths
export SPACY_MODEL_PATH=/models/en_core_web_sm
export CLINICAL_MODEL_PATH=emilyalsentzer/Bio_ClinicalBERT
```

### Step 4: Code Changes (Minimal)

The enhanced Stage 5 is **backwards compatible**. Existing code continues to work unchanged.

#### Basic Usage (No Changes Required)
```python
# This code works exactly the same
from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent

agent = PHIGuardAgent()
result = await agent.execute(context)

# Access existing outputs
phi_detected = result.output['phi_detected']
risk_level = result.output['risk_level']
findings = result.output['findings']
```

#### Enhanced Usage (New Features)
```python
# Access new enhanced outputs
ml_findings = result.output.get('ml_findings', [])
quasi_analysis = result.output.get('quasi_identifier_analysis', {})
compliance_summary = result.output.get('compliance_summary', {})
audit_event_id = result.output.get('audit_event_id')

# Check enhanced capabilities
capabilities = agent.get_enhanced_capabilities()
print(f"ML Detection: {capabilities['ml_detection']}")
print(f"Quasi-ID Analysis: {capabilities['quasi_identifier_analysis']}")
```

### Step 5: Update Monitoring and Alerts

#### Enhanced Monitoring
```python
# Add to your monitoring system
def monitor_enhanced_phi_detection(result):
    # Existing metrics (unchanged)
    phi_count = result.output['total_findings']
    risk_level = result.output['risk_level']
    
    # New enhanced metrics
    ml_findings_count = len(result.output.get('ml_findings', []))
    k_anonymity = result.output.get('quasi_identifier_analysis', {}).get('k_anonymity', {}).get('k_value', 0)
    compliance_score = result.output.get('compliance_summary', {}).get('overall_risk_score', 0)
    
    # Alert on new risk indicators
    if k_anonymity > 0 and k_anonymity < 5:
        send_alert("K_ANONYMITY_VIOLATION", k_anonymity)
    
    if compliance_score > 80:
        send_alert("HIGH_COMPLIANCE_RISK", compliance_score)
```

### Step 6: Verify Migration

#### Test Enhanced Features
```python
# Test script to verify enhanced functionality
import asyncio
from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
from src.workflow_engine.types import StageContext

async def test_enhanced_phi():
    agent = PHIGuardAgent()
    
    # Check capabilities
    capabilities = agent.get_enhanced_capabilities()
    print("Enhanced Capabilities:")
    for feature, available in capabilities.items():
        status = "✅" if available else "❌"
        print(f"  {status} {feature}")
    
    # Test with sample data
    context = StageContext(
        job_id="migration-test",
        config={"phi": {
            "enable_ml_detection": True,
            "enable_quasi_analysis": True,
            "enable_audit_chain": True,
        }},
        dataset_pointer="test_data.csv",
        governance_mode="DEMO"
    )
    
    result = await agent.execute(context)
    
    # Verify enhanced outputs
    assert 'phi_detected' in result.output  # Basic output
    assert 'enhanced_capabilities' in result.metadata  # Enhanced metadata
    
    if capabilities['ml_detection']:
        assert 'ml_findings' in result.output or len(result.warnings) > 0
    
    if capabilities['quasi_identifier_analysis']:
        assert 'quasi_identifier_analysis' in result.output or len(result.warnings) > 0
    
    print("✅ Enhanced PHI detection migration successful!")

# Run test
asyncio.run(test_enhanced_phi())
```

## 📊 Feature Comparison

| Feature | Basic Stage 5 | Enhanced Stage 5 |
|---------|---------------|------------------|
| Pattern-based PHI detection | ✅ | ✅ |
| HIPAA Safe Harbor validation | ✅ | ✅ |
| Column-level risk assessment | ✅ | ✅ |
| Large file support | ✅ | ✅ |
| **ML-enhanced detection** | ❌ | ✅ |
| **K-anonymity analysis** | ❌ | ✅ |
| **Multi-jurisdiction compliance** | ❌ | ✅ |
| **Cryptographic audit chain** | ❌ | ✅ |
| **Contextual PHI scoring** | ❌ | ✅ |
| **Privacy strategy recommendations** | ❌ | ✅ |

## 🔧 Configuration Migration

### Environment-Specific Settings

#### Development Environment
```python
dev_config = {
    "enable_ml_detection": False,  # Faster testing
    "enable_audit_chain": False,   # Not needed for dev
    "k_anonymity_threshold": 3,    # More lenient
    "compliance_frameworks": ["HIPAA_SAFE_HARBOR"],  # Single framework
}
```

#### Staging Environment
```python
staging_config = {
    "enable_ml_detection": True,   # Test ML models
    "enable_audit_chain": True,    # Test audit functionality
    "k_anonymity_threshold": 5,    # Production-like
    "compliance_frameworks": ["HIPAA_SAFE_HARBOR", "GDPR_ARTICLE_4"],
}
```

#### Production Environment
```python
production_config = {
    "enable_ml_detection": True,   # Full ML capabilities
    "enable_audit_chain": True,    # Required for compliance
    "audit_signing": True,         # Cryptographic integrity
    "k_anonymity_threshold": 5,    # Strict privacy requirements
    "compliance_frameworks": ["HIPAA_SAFE_HARBOR", "GDPR_ARTICLE_4"],
    "gdpr_consent": True,          # Based on your legal basis
    "gdpr_data_portability": True,
    "gdpr_right_to_erasure": True,
}
```

## 🐛 Troubleshooting

### Common Migration Issues

#### 1. ML Models Not Loading
```bash
# Error: "SpaCy model not found"
# Solution: Install SpaCy model
python -m spacy download en_core_web_sm

# Error: "Transformers model download failed"
# Solution: Check internet connection or use offline models
export HF_DATASETS_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

#### 2. Memory Issues with Large Files
```python
# Error: "Out of memory during ML detection"
# Solution: Disable ML for large files or increase memory limits
if file_size_mb > 500:  # 500MB threshold
    context.config["phi"]["enable_ml_detection"] = False
    logger.info("Disabled ML detection for large file")
```

#### 3. Cryptographic Key Generation Issues
```bash
# Error: "Permission denied creating audit keys"
# Solution: Ensure proper permissions for key directory
mkdir -p /data/audit/keys
chmod 700 /data/audit/keys

# Error: "Cryptography library not available"
# Solution: Install cryptography package
pip install cryptography>=3.4.8
```

#### 4. Performance Degradation
```python
# If performance is slower after migration
config_optimizations = {
    "ml_confidence_threshold": 0.9,  # Higher threshold = fewer checks
    "enable_quasi_analysis": False,  # Disable for non-structured data
    "k_anonymity_threshold": 3,      # Lower threshold = faster processing
}
```

### Performance Tuning

#### Memory Optimization
```python
# For memory-constrained environments
memory_efficient_config = {
    "enable_ml_detection": False,     # ML models use significant memory
    "enable_audit_chain": True,       # Minimal memory impact
    "k_anonymity_threshold": 3,       # Faster computation
    "dask_partitions": 4,             # Smaller partitions
}
```

#### Processing Speed
```python
# For speed-critical applications
speed_optimized_config = {
    "scan_mode": "standard",          # Faster than "strict"
    "ml_confidence_threshold": 0.9,   # Fewer ML validations
    "assess_column_risk": False,      # Skip detailed risk assessment
    "validate_compliance": False,     # Skip compliance checks in dev
}
```

## 📈 Monitoring Migration Success

### Key Metrics to Track

1. **Processing Time**: Should increase <20% with ML enabled
2. **Memory Usage**: May increase 30-50% with ML models
3. **Detection Accuracy**: Should improve with ML enhancement
4. **False Positive Rate**: Should decrease with contextual analysis

### Success Criteria

- [ ] All existing functionality works unchanged
- [ ] Enhanced features activate when configured
- [ ] Performance remains within acceptable limits
- [ ] No PHI leakage in enhanced outputs
- [ ] Audit chain integrity validates successfully
- [ ] Compliance reports generate correctly

### Rollback Plan

If migration issues occur:

1. **Immediate Rollback**: Disable enhanced features
   ```python
   rollback_config = {
       "enable_ml_detection": False,
       "enable_quasi_analysis": False,  
       "enable_audit_chain": False,
   }
   ```

2. **Staged Rollback**: Enable features one by one
   ```python
   # Enable only audit chain first
   minimal_enhanced_config = {
       "enable_audit_chain": True,  # Minimal impact
       "enable_ml_detection": False,
       "enable_quasi_analysis": False,
   }
   ```

3. **Complete Rollback**: Revert to previous version
   ```bash
   git checkout <previous-commit>
   pip install -r requirements.txt  # Original requirements
   ```

## 🎯 Post-Migration Validation

### Automated Tests
```python
# Add to your CI/CD pipeline
def test_migration_success():
    # Test backwards compatibility
    test_basic_phi_detection()
    
    # Test enhanced features
    test_ml_phi_detection()
    test_quasi_identifier_analysis()
    test_compliance_validation()
    test_audit_chain_integrity()
    
    # Test performance benchmarks
    test_performance_regression()
```

### Manual Validation Checklist

- [ ] Existing PHI detection still works
- [ ] Enhanced features can be enabled/disabled
- [ ] Configuration is backwards compatible
- [ ] Performance is within acceptable range
- [ ] All dependencies install successfully
- [ ] Audit trails are generated and valid
- [ ] Compliance reports are accurate
- [ ] No PHI leakage in any outputs

## 📞 Support

If you encounter issues during migration:

1. Check the [Enhanced README](./phi_analyzers/STAGE_05_ENHANCED_README.md)
2. Review test cases in `tests/unit/workflow_engine/stages/phi_analyzers/`
3. Enable debug logging: `export LOG_LEVEL=DEBUG`
4. Run the migration test script provided above

The enhanced Stage 5 is designed for seamless migration with zero downtime and full backwards compatibility.