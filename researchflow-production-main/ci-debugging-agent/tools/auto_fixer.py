"""
Auto-Fixer Tool for CI Debugging Agent
Provides automated fixes for common TypeScript and code issues.
"""
import os
import re
import subprocess
import json
from typing import Optional, List, Dict
from langchain_core.tools import tool


class TypeScriptAutoFixer:
    """Automated fixer for TypeScript errors."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.fixes_applied = 0
        self.fixes_failed = 0

    def analyze_and_fix(self) -> Dict:
        """Run TypeScript check and apply automated fixes."""
        errors = self._get_typescript_errors()
        results = {
            "total_errors": len(errors),
            "auto_fixable": 0,
            "fixed": 0,
            "errors_by_type": {},
            "fixes_applied": []
        }

        for error in errors:
            code = error.get("code", "unknown")
            results["errors_by_type"][code] = results["errors_by_type"].get(code, 0) + 1

        for error in errors:
            code = error["code"]
            file_path = error["file"]
            message = error["message"]

            if code == "TS2305":
                if self._fix_ts2305_missing_export(file_path, message):
                    results["fixed"] += 1
                    results["fixes_applied"].append(f"Fixed missing export in {file_path}")
                results["auto_fixable"] += 1

            elif code == "TS2339":
                if self._fix_ts2339_missing_property(file_path, error["line"], message):
                    results["fixed"] += 1
                results["auto_fixable"] += 1

            elif code == "TS2503":
                if self._fix_ts2503_missing_namespace(file_path, message):
                    results["fixed"] += 1
                    results["fixes_applied"].append(f"Added namespace import in {file_path}")
                results["auto_fixable"] += 1

            elif code == "TS2307":
                if self._fix_ts2307_missing_module(file_path, message):
                    results["fixed"] += 1
                results["auto_fixable"] += 1

            elif code == "TS1005":
                if ".ts" in file_path and self._has_jsx(file_path):
                    if self._fix_ts_to_tsx(file_path):
                        results["fixed"] += 1
                        results["fixes_applied"].append(f"Renamed {file_path} to .tsx")
                results["auto_fixable"] += 1

            elif code == "TS2614":
                if self._fix_ts2614_default_import(file_path, error["line"]):
                    results["fixed"] += 1
                    results["fixes_applied"].append(f"Fixed default import in {file_path}")
                results["auto_fixable"] += 1

        results["fixes_applied_count"] = results["fixed"]
        return results

    def _get_typescript_errors(self) -> List[Dict]:
        """Get TypeScript errors from tsc."""
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", "--pretty", "false"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            output = result.stdout + result.stderr
            error_pattern = r"(.+)\((\d+),(\d+)\): error (TS\d+): (.+)"
            errors = []
            for match in re.finditer(error_pattern, output):
                errors.append({
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3)),
                    "code": match.group(4),
                    "message": match.group(5)
                })
            return errors
        except Exception as e:
            print(f"Error getting TypeScript errors: {e}")
            return []

    def _has_jsx(self, file_path: str) -> bool:
        """Check if a .ts file contains JSX."""
        full_path = os.path.join(self.repo_path, file_path)
        if not os.path.exists(full_path):
            return False
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            jsx_patterns = [r"<[A-Z][a-zA-Z]*[\s/>]", r"</[A-Z]", r"<[a-z]+\s+[a-zA-Z]+="]
            return any(re.search(p, content) for p in jsx_patterns)
        except:
            return False

    def _fix_ts_to_tsx(self, file_path: str) -> bool:
        """Rename .ts file to .tsx if it contains JSX."""
        try:
            old_path = os.path.join(self.repo_path, file_path)
            new_path = old_path.replace(".ts", ".tsx")
            if os.path.exists(old_path) and not os.path.exists(new_path):
                os.rename(old_path, new_path)
                return True
        except Exception as e:
            print(f"Error renaming file: {e}")
        return False

    def _fix_ts2305_missing_export(self, file_path: str, message: str) -> bool:
        match = re.search(r"has no exported member '(\w+)'", message)
        if not match:
            return False
        return False

    def _fix_ts2339_missing_property(self, file_path: str, line: int, message: str) -> bool:
        return False

    def _fix_ts2503_missing_namespace(self, file_path: str, message: str) -> bool:
        match = re.search(r"Cannot find namespace '(\w+)'", message)
        if not match:
            return False
        namespace = match.group(1)
        full_path = os.path.join(self.repo_path, file_path)
        if not os.path.exists(full_path):
            return False
        common_namespaces = {
            "NodeJS": 'import type { NodeJS } from "node";',
            "Express": 'import type { Express } from "express";',
            "React": 'import * as React from "react";'
        }
        if namespace in common_namespaces:
            try:
                with open(full_path, 'r') as f:
                    content = f.read()
                if common_namespaces[namespace].split()[2] in content:
                    return False
                new_content = common_namespaces[namespace] + "\n" + content
                with open(full_path, 'w') as f:
                    f.write(new_content)
                return True
            except:
                pass
        return False

    def _fix_ts2307_missing_module(self, file_path: str, message: str) -> bool:
        return False

    def _fix_ts2614_default_import(self, file_path: str, line: int) -> bool:
        full_path = os.path.join(self.repo_path, file_path)
        if not os.path.exists(full_path):
            return False
        try:
            with open(full_path, 'r') as f:
                lines = f.readlines()
            if line > len(lines):
                return False
            import_line = lines[line - 1]
            match = re.match(r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]", import_line)
            if match:
                import_name = match.group(1)
                module_name = match.group(2)
                new_line = f"import * as {import_name} from '{module_name}';\n"
                lines[line - 1] = new_line
                with open(full_path, 'w') as f:
                    f.writelines(lines)
                return True
        except Exception as e:
            print(f"Error fixing default import: {e}")
        return False


@tool
def auto_fix_typescript(project_path: str) -> str:
    """Automatically fix common TypeScript errors in a project."""
    fixer = TypeScriptAutoFixer(project_path)
    results = fixer.analyze_and_fix()
    return json.dumps(results, indent=2)


@tool
def fix_duplicate_imports(project_path: str, file_path: str) -> str:
    """Remove duplicate import statements from a TypeScript file."""
    full_path = os.path.join(project_path, file_path)
    if not os.path.exists(full_path):
        return f"File not found: {file_path}"
    try:
        with open(full_path, 'r') as f:
            content = f.read()
        import_pattern = r'^import\s+.*?from\s+[\'"][^\'"]+[\'"];?\s*$'
        imports = re.findall(import_pattern, content, re.MULTILINE)
        seen = set()
        unique_imports = []
        for imp in imports:
            normalized = imp.strip()
            if normalized not in seen:
                seen.add(normalized)
                unique_imports.append(imp)
        if len(unique_imports) < len(imports):
            new_content = re.sub(import_pattern, '', content, flags=re.MULTILINE)
            new_content = '\n'.join(unique_imports) + '\n\n' + new_content.lstrip()
            with open(full_path, 'w') as f:
                f.write(new_content)
            return json.dumps({"fixed": True, "removed": len(imports) - len(unique_imports)})
        return json.dumps({"fixed": False, "reason": "No duplicate imports found"})
    except Exception as e:
        return json.dumps({"fixed": False, "error": str(e)})


@tool
def rename_ts_to_tsx(project_path: str, file_path: str) -> str:
    """Rename a .ts file to .tsx if it contains JSX syntax."""
    if not file_path.endswith('.ts'):
        return json.dumps({"renamed": False, "reason": "File is not a .ts file"})
    full_path = os.path.join(project_path, file_path)
    if not os.path.exists(full_path):
        return json.dumps({"renamed": False, "reason": "File not found"})
    try:
        with open(full_path, 'r') as f:
            content = f.read()
        jsx_patterns = [r"<[A-Z][a-zA-Z]*[\s/>]", r"</[A-Z]", r"<[a-z]+\s+[a-zA-Z]+="]
        has_jsx = any(re.search(p, content) for p in jsx_patterns)
        if has_jsx:
            new_path = full_path.replace('.ts', '.tsx')
            if not os.path.exists(new_path):
                os.rename(full_path, new_path)
                return json.dumps({"renamed": True, "new_path": file_path.replace('.ts', '.tsx')})
        return json.dumps({"renamed": False, "reason": "No JSX syntax found"})
    except Exception as e:
        return json.dumps({"renamed": False, "error": str(e)})


__all__ = ["auto_fix_typescript", "fix_duplicate_imports", "rename_ts_to_tsx", "TypeScriptAutoFixer"]
