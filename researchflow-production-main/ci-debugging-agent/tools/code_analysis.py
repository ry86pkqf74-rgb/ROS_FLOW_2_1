#!/usr/bin/env python3
"""
Code Analysis Tools

TypeScript, ESLint, Python linting and analysis tools.
"""
import os
import re
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CodeError:
    """Represents a code error."""
    file: str
    line: int
    column: int
    code: str
    message: str
    severity: str = "error"
    fixable: bool = False
    suggested_fix: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of code analysis."""
    total_errors: int
    errors_by_type: dict
    errors: list[CodeError]
    fixable_count: int = 0


def run_typescript_check(repo_path: str) -> AnalysisResult:
    """Run TypeScript compiler and analyze errors."""
    env = {**os.environ, "PATH": f"/Users/ros/.npm-global/bin:{os.environ.get('PATH', '')}"}
    
    result = subprocess.run(
        ["pnpm", "exec", "tsc", "--noEmit"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=300,
        env=env
    )
    
    output = result.stderr + result.stdout
    errors = []
    
    for line in output.split('\n'):
        match = re.match(r'(.+?)\((\d+),(\d+)\): error (TS\d+): (.+)', line)
        if match:
            code = match.group(4)
            errors.append(CodeError(
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                code=code,
                message=match.group(5),
                fixable=code in ['TS2614', 'TS2503', 'TS2305'],
                suggested_fix=get_ts_fix_suggestion(code, match.group(5))
            ))
    
    # Group by error code
    by_code = {}
    for err in errors:
        if err.code not in by_code:
            by_code[err.code] = 0
        by_code[err.code] += 1
    
    return AnalysisResult(
        total_errors=len(errors),
        errors_by_type=by_code,
        errors=errors,
        fixable_count=sum(1 for e in errors if e.fixable)
    )


def get_ts_fix_suggestion(code: str, message: str) -> Optional[str]:
    """Get fix suggestion for TypeScript error."""
    suggestions = {
        'TS2614': "Change named import to default import: import X from 'y' instead of import { X } from 'y'",
        'TS2503': "Add missing import for namespace (e.g., import { z } from 'zod')",
        'TS2305': "Check if the export exists in the source module or add it",
        'TS2339': "Add missing property to interface or use type assertion",
        'TS2322': "Fix type mismatch or use type assertion",
        'TS2702': "Import runtime value, not just type: import X from 'y' instead of import type X from 'y'",
        'TS2741': "Add required property to object literal",
    }
    return suggestions.get(code)


def run_eslint_check(repo_path: str, pattern: str = "**/*.{ts,tsx}") -> AnalysisResult:
    """Run ESLint and analyze results."""
    env = {**os.environ, "PATH": f"/Users/ros/.npm-global/bin:{os.environ.get('PATH', '')}"}
    
    try:
        result = subprocess.run(
            ["pnpm", "exec", "eslint", "--format", "json", pattern],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300,
            env=env
        )
        
        if result.stdout:
            data = json.loads(result.stdout)
            errors = []
            for file_result in data:
                for msg in file_result.get('messages', []):
                    errors.append(CodeError(
                        file=file_result['filePath'],
                        line=msg.get('line', 0),
                        column=msg.get('column', 0),
                        code=msg.get('ruleId', 'unknown'),
                        message=msg.get('message', ''),
                        severity='error' if msg.get('severity') == 2 else 'warning',
                        fixable=msg.get('fix') is not None
                    ))
            
            by_code = {}
            for err in errors:
                if err.code not in by_code:
                    by_code[err.code] = 0
                by_code[err.code] += 1
            
            return AnalysisResult(
                total_errors=len(errors),
                errors_by_type=by_code,
                errors=errors,
                fixable_count=sum(1 for e in errors if e.fixable)
            )
    except Exception as e:
        print(f"ESLint error: {e}")
    
    return AnalysisResult(total_errors=0, errors_by_type={}, errors=[])


def find_react_env_issues(repo_path: str) -> list[CodeError]:
    """Find React environment variable issues (build-time vs runtime)."""
    errors = []
    
    # Search for process.env usage in frontend files
    for root, dirs, files in os.walk(repo_path):
        # Skip node_modules
        dirs[:] = [d for d in dirs if d != 'node_modules']
        
        for file in files:
            if file.endswith(('.tsx', '.ts', '.jsx', '.js')):
                filepath = os.path.join(root, file)
                # Only check frontend/web directories
                if 'web' in filepath or 'frontend' in filepath or 'ui' in filepath:
                    try:
                        with open(filepath, 'r') as f:
                            content = f.read()
                            
                        # Find process.env without NEXT_PUBLIC_ or VITE_ prefix
                        for i, line in enumerate(content.split('\n'), 1):
                            if 'process.env.' in line:
                                match = re.search(r'process\.env\.(\w+)', line)
                                if match:
                                    var_name = match.group(1)
                                    if not var_name.startswith(('NEXT_PUBLIC_', 'VITE_', 'REACT_APP_')):
                                        errors.append(CodeError(
                                            file=filepath,
                                            line=i,
                                            column=line.find('process.env'),
                                            code='REACT_ENV',
                                            message=f"Server-side env var '{var_name}' used in client code. Prefix with NEXT_PUBLIC_, VITE_, or REACT_APP_",
                                            severity='warning',
                                            fixable=True,
                                            suggested_fix=f"Rename to NEXT_PUBLIC_{var_name} or move to server-side code"
                                        ))
                    except Exception:
                        pass
    
    return errors


def analyze_imports(repo_path: str) -> dict:
    """Analyze import patterns to find issues."""
    issues = {
        'circular_deps': [],
        'missing_exports': [],
        'wrong_import_style': []
    }
    
    # This is a simplified check - a full implementation would use AST parsing
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ['node_modules', 'dist', '.git']]
        
        for file in files:
            if file.endswith(('.ts', '.tsx')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Check for common import issues
                    if "import { Redis } from 'ioredis'" in content:
                        issues['wrong_import_style'].append({
                            'file': filepath,
                            'issue': "ioredis uses default export",
                            'fix': "import Redis from 'ioredis'"
                        })
                    
                    if "import type Anthropic from" in content and "Anthropic." in content:
                        issues['wrong_import_style'].append({
                            'file': filepath,
                            'issue': "Anthropic imported as type but used as namespace",
                            'fix': "import Anthropic from '@anthropic-ai/sdk'"
                        })
                except Exception:
                    pass
    
    return issues
