#!/usr/bin/env python3
"""
Stage 3 Implementation Validation Script

This script validates the Stage 3 IRB Drafting Agent implementation
by checking all created files, running basic validation tests, and
verifying the integration patterns work correctly.
"""

import os
import sys
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Any

# Colors for output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def colored_print(message: str, color: str = Colors.NC):
    """Print colored message."""
    print(f"{color}{message}{Colors.NC}")

def check_mark(passed: bool) -> str:
    """Return colored check mark or X."""
    return f"{Colors.GREEN}✓{Colors.NC}" if passed else f"{Colors.RED}✗{Colors.NC}"

def validate_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    exists = os.path.exists(filepath)
    status = check_mark(exists)
    print(f"{status} {description}: {filepath}")
    return exists

def validate_python_syntax(filepath: str, description: str) -> bool:
    """Check if Python file has valid syntax."""
    if not os.path.exists(filepath):
        return False
    
    try:
        with open(filepath, 'r') as f:
            compile(f.read(), filepath, 'exec')
        status = check_mark(True)
        print(f"{status} {description} syntax valid")
        return True
    except SyntaxError as e:
        status = check_mark(False)
        print(f"{status} {description} syntax error: {e}")
        return False

def validate_import(module_path: str, description: str) -> bool:
    """Check if module can be imported."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        status = check_mark(True)
        print(f"{status} {description} imports successfully")
        return True
    except Exception as e:
        status = check_mark(False)
        print(f"{status} {description} import error: {e}")
        return False

def count_test_methods(test_file_path: str) -> int:
    """Count test methods in a test file."""
    if not os.path.exists(test_file_path):
        return 0
    
    try:
        with open(test_file_path, 'r') as f:
            content = f.read()
        
        # Count test methods (functions starting with 'test_' or 'async def test_')
        import re
        test_methods = re.findall(r'\n\s*(async\s+)?def\s+test_\w+\s*\(', content)
        return len(test_methods)
    except Exception:
        return 0

def validate_pydantic_models(schema_path: str) -> Dict[str, Any]:
    """Validate Pydantic models in schema file."""
    results = {
        "models_found": [],
        "validators_found": [],
        "enums_found": []
    }
    
    if not os.path.exists(schema_path):
        return results
    
    try:
        with open(schema_path, 'r') as f:
            content = f.read()
        
        # Find model classes
        import re
        models = re.findall(r'class\s+(\w+)\s*\(.*BaseModel\)', content)
        results["models_found"] = models
        
        # Find validators
        validators = re.findall(r'@validator\([\'"](\w+)[\'"]', content)
        results["validators_found"] = validators
        
        # Find enums
        enums = re.findall(r'class\s+(\w+)\s*\(.*Enum\)', content)
        results["enums_found"] = enums
        
    except Exception as e:
        print(f"Error analyzing Pydantic models: {e}")
    
    return results

def validate_error_classes(error_path: str) -> Dict[str, Any]:
    """Validate error classes in error file."""
    results = {
        "error_classes": [],
        "specific_errors": []
    }
    
    if not os.path.exists(error_path):
        return results
    
    try:
        with open(error_path, 'r') as f:
            content = f.read()
        
        # Find error classes
        import re
        error_classes = re.findall(r'class\s+(\w*Error)\s*\(', content)
        results["error_classes"] = error_classes
        
        # Find IRB-specific errors
        irb_errors = [cls for cls in error_classes if 'IRB' in cls]
        results["specific_errors"] = irb_errors
        
    except Exception as e:
        print(f"Error analyzing error classes: {e}")
    
    return results

def main():
    """Main validation routine."""
    colored_print("🔍 Stage 3 IRB Drafting Agent Implementation Validation", Colors.BLUE)
    colored_print("=" * 70, Colors.BLUE)
    
    # Track overall success
    all_passed = True
    
    # 1. File Existence Check
    colored_print("\n📁 File Existence Validation", Colors.YELLOW)
    files_to_check = [
        ("tests/unit/workflow_engine/stages/test_stage_03_irb.py", "Stage 3 Unit Tests"),
        ("services/worker/src/workflow_engine/stages/schemas/irb_schemas.py", "Pydantic IRB Schemas"),
        ("services/worker/src/workflow_engine/stages/errors.py", "Enhanced Error Classes"),
        ("services/worker/src/workflow_engine/stages/stage_03_irb.py", "Updated Stage 3 Agent"),
        ("tests/integration/test_stage1_to_stage3_integration.py", "Stage Integration Tests"),
        ("services/worker/docs/STAGE_INTEGRATION_PATTERNS.md", "Integration Documentation"),
        ("STAGE_03_IMPLEMENTATION_SUMMARY.md", "Implementation Summary")
    ]
    
    files_exist = []
    for filepath, description in files_to_check:
        exists = validate_file_exists(filepath, description)
        files_exist.append(exists)
        if not exists:
            all_passed = False
    
    # 2. Python Syntax Validation
    colored_print("\n🐍 Python Syntax Validation", Colors.YELLOW)
    python_files = [
        ("tests/unit/workflow_engine/stages/test_stage_03_irb.py", "Unit Tests"),
        ("services/worker/src/workflow_engine/stages/schemas/irb_schemas.py", "Pydantic Schemas"),
        ("services/worker/src/workflow_engine/stages/errors.py", "Error Classes"),
        ("services/worker/src/workflow_engine/stages/stage_03_irb.py", "Stage 3 Agent"),
        ("tests/integration/test_stage1_to_stage3_integration.py", "Integration Tests"),
        ("scripts/validate_stage3_implementation.py", "This validation script")
    ]
    
    syntax_valid = []
    for filepath, description in python_files:
        valid = validate_python_syntax(filepath, description)
        syntax_valid.append(valid)
        if not valid:
            all_passed = False
    
    # 3. Test Coverage Analysis
    colored_print("\n🧪 Test Coverage Analysis", Colors.YELLOW)
    
    # Unit tests
    unit_test_count = count_test_methods("tests/unit/workflow_engine/stages/test_stage_03_irb.py")
    unit_test_good = unit_test_count >= 25  # Expect at least 25 test methods
    status = check_mark(unit_test_good)
    print(f"{status} Unit test methods: {unit_test_count} (target: ≥25)")
    if not unit_test_good:
        all_passed = False
    
    # Integration tests
    integration_test_count = count_test_methods("tests/integration/test_stage1_to_stage3_integration.py")
    integration_test_good = integration_test_count >= 8  # Expect at least 8 integration tests
    status = check_mark(integration_test_good)
    print(f"{status} Integration test methods: {integration_test_count} (target: ≥8)")
    if not integration_test_good:
        all_passed = False
    
    # 4. Pydantic Schema Validation
    colored_print("\n📝 Pydantic Schema Validation", Colors.YELLOW)
    schema_results = validate_pydantic_models("services/worker/src/workflow_engine/stages/schemas/irb_schemas.py")
    
    models_good = len(schema_results["models_found"]) >= 4  # Expect several models
    status = check_mark(models_good)
    print(f"{status} Pydantic models found: {len(schema_results['models_found'])} {schema_results['models_found']}")
    if not models_good:
        all_passed = False
    
    validators_good = len(schema_results["validators_found"]) >= 3  # Expect custom validators
    status = check_mark(validators_good)
    print(f"{status} Custom validators found: {len(schema_results['validators_found'])} {schema_results['validators_found']}")
    if not validators_good:
        all_passed = False
    
    enums_good = len(schema_results["enums_found"]) >= 3  # Expect enums
    status = check_mark(enums_good)
    print(f"{status} Enum classes found: {len(schema_results['enums_found'])} {schema_results['enums_found']}")
    if not enums_good:
        all_passed = False
    
    # 5. Error Handling Validation
    colored_print("\n⚠️ Error Handling Validation", Colors.YELLOW)
    error_results = validate_error_classes("services/worker/src/workflow_engine/stages/errors.py")
    
    error_classes_good = len(error_results["error_classes"]) >= 6  # Expect multiple error types
    status = check_mark(error_classes_good)
    print(f"{status} Error classes found: {len(error_results['error_classes'])} {error_results['error_classes']}")
    if not error_classes_good:
        all_passed = False
    
    irb_errors_good = len(error_results["specific_errors"]) >= 2  # Expect IRB-specific errors
    status = check_mark(irb_errors_good)
    print(f"{status} IRB-specific errors: {len(error_results['specific_errors'])} {error_results['specific_errors']}")
    if not irb_errors_good:
        all_passed = False
    
    # 6. Documentation Validation
    colored_print("\n📚 Documentation Validation", Colors.YELLOW)
    
    # Check documentation completeness
    docs_to_check = [
        ("services/worker/docs/STAGE_INTEGRATION_PATTERNS.md", "Integration Patterns Doc", 5000),
        ("STAGE_03_IMPLEMENTATION_SUMMARY.md", "Implementation Summary", 3000)
    ]
    
    for filepath, description, min_chars in docs_to_check:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
            chars = len(content)
            good = chars >= min_chars
            status = check_mark(good)
            print(f"{status} {description}: {chars} characters (target: ≥{min_chars})")
            if not good:
                all_passed = False
        else:
            status = check_mark(False)
            print(f"{status} {description}: File missing")
            all_passed = False
    
    # 7. Integration Pattern Validation
    colored_print("\n🔗 Integration Pattern Validation", Colors.YELLOW)
    
    # Check if Stage 3 agent imports the new schemas and errors
    stage3_path = "services/worker/src/workflow_engine/stages/stage_03_irb.py"
    if os.path.exists(stage3_path):
        with open(stage3_path, 'r') as f:
            stage3_content = f.read()
        
        # Check for Pydantic integration
        pydantic_integrated = "validate_irb_config" in stage3_content
        status = check_mark(pydantic_integrated)
        print(f"{status} Pydantic schema integration in Stage 3")
        if not pydantic_integrated:
            all_passed = False
        
        # Check for error handling integration
        error_integrated = "IRBValidationError" in stage3_content
        status = check_mark(error_integrated)
        print(f"{status} Enhanced error handling in Stage 3")
        if not error_integrated:
            all_passed = False
        
        # Check for Stage 1 integration
        stage1_integrated = "get_prior_stage_output(1)" in stage3_content
        status = check_mark(stage1_integrated)
        print(f"{status} Stage 1 integration pattern in Stage 3")
        if not stage1_integrated:
            all_passed = False
    else:
        colored_print("⚠️ Stage 3 agent file not found for pattern validation", Colors.RED)
        all_passed = False
    
    # Final Summary
    colored_print("\n" + "=" * 70, Colors.BLUE)
    if all_passed:
        colored_print("🎉 ALL VALIDATIONS PASSED!", Colors.GREEN)
        colored_print("✅ Stage 3 implementation is complete and ready for testing", Colors.GREEN)
    else:
        colored_print("❌ Some validations failed", Colors.RED)
        colored_print("🔧 Please review the failed items above", Colors.YELLOW)
    
    # Recommendations
    colored_print("\n📋 Next Steps:", Colors.BLUE)
    print("1. Run the unit tests: python3 -m pytest tests/unit/workflow_engine/stages/test_stage_03_irb.py -v")
    print("2. Run integration tests: python3 -m pytest tests/integration/test_stage1_to_stage3_integration.py -v")
    print("3. Test with real Stage 1 → Stage 3 workflow")
    print("4. Deploy to development environment for validation")
    print("5. Review integration patterns documentation")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())