#!/usr/bin/env python3
"""
Auto Fixer - Automated TypeScript Error Fixer

Applies known fix patterns automatically without LLM assistance.
"""
import os
import re
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

REPO_PATH = "/Users/lhglosser/researchflow-production"


@dataclass
class TypeScriptError:
    """Represents a TypeScript error."""
    file: str
    line: int
    column: int
    code: str
    message: str


@dataclass
class Fix:
    """Represents a fix to apply."""
    file: str
    old_text: str
    new_text: str
    description: str


def run_tsc() -> list[TypeScriptError]:
    """Run TypeScript compiler and parse errors."""
    env = {**os.environ, "PATH": f"/Users/ros/.npm-global/bin:{os.environ.get('PATH', '')}"}
    
    result = subprocess.run(
        ["pnpm", "exec", "tsc", "--noEmit"],
        cwd=REPO_PATH,
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
            errors.append(TypeScriptError(
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                code=match.group(4),
                message=match.group(5)
            ))
    
    return errors


def read_file(path: str) -> str:
    """Read file content."""
    full_path = os.path.join(REPO_PATH, path) if not path.startswith('/') else path
    with open(full_path, 'r') as f:
        return f.read()


def write_file(path: str, content: str):
    """Write file content."""
    full_path = os.path.join(REPO_PATH, path) if not path.startswith('/') else path
    with open(full_path, 'w') as f:
        f.write(content)


def apply_fix(fix: Fix) -> bool:
    """Apply a single fix."""
    try:
        content = read_file(fix.file)
        if fix.old_text not in content:
            return False
        new_content = content.replace(fix.old_text, fix.new_text, 1)
        write_file(fix.file, new_content)
        return True
    except Exception as e:
        console.print(f"[red]Error applying fix: {e}[/red]")
        return False


# =============================================================================
# Fix Generators - Create fixes for specific error patterns
# =============================================================================

def fix_ioredis_import(error: TypeScriptError) -> Optional[Fix]:
    """Fix TS2614: ioredis named import should be default import."""
    if 'ioredis' not in error.message:
        return None
    
    content = read_file(error.file)
    
    # Pattern: import { Redis } from 'ioredis'
    old_pattern = "import { Redis } from 'ioredis'"
    new_pattern = "import Redis from 'ioredis'"
    
    if old_pattern in content:
        return Fix(
            file=error.file,
            old_text=old_pattern,
            new_text=new_pattern,
            description="Fix ioredis import to use default export"
        )
    return None


def fix_missing_zod_import(error: TypeScriptError) -> Optional[Fix]:
    """Fix TS2503: Add missing zod import."""
    if "Cannot find namespace 'z'" not in error.message:
        return None
    
    content = read_file(error.file)
    
    # Check if zod is already imported
    if "import { z } from 'zod'" in content or "import * as z from 'zod'" in content:
        return None
    
    # Find a good place to add the import (after other imports)
    lines = content.split('\n')
    last_import_line = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('import '):
            last_import_line = i
    
    if last_import_line > 0:
        old_line = lines[last_import_line]
        new_line = old_line + "\nimport { z } from 'zod';"
        return Fix(
            file=error.file,
            old_text=old_line,
            new_text=new_line,
            description="Add missing zod import"
        )
    return None


def fix_openai_namespace(error: TypeScriptError) -> Optional[Fix]:
    """Fix TS2702: OpenAI only refers to a type."""
    if "'OpenAI' only refers to a type" not in error.message:
        return None
    
    content = read_file(error.file)
    
    # Change: import type { OpenAI } to import OpenAI
    if "import type OpenAI from 'openai'" in content:
        return Fix(
            file=error.file,
            old_text="import type OpenAI from 'openai'",
            new_text="import OpenAI from 'openai'",
            description="Fix OpenAI import to include runtime value"
        )
    
    # Or add the runtime import alongside type import
    if "import type { OpenAI }" in content:
        return Fix(
            file=error.file,
            old_text="import type { OpenAI }",
            new_text="import OpenAI, { type OpenAI as OpenAIType }",
            description="Fix OpenAI import to include runtime value"
        )
    
    return None


def fix_anthropic_namespace(error: TypeScriptError) -> Optional[Fix]:
    """Fix TS2702: Anthropic only refers to a type."""
    if "'Anthropic' only refers to a type" not in error.message:
        return None
    
    content = read_file(error.file)
    
    if "import type Anthropic from '@anthropic-ai/sdk'" in content:
        return Fix(
            file=error.file,
            old_text="import type Anthropic from '@anthropic-ai/sdk'",
            new_text="import Anthropic from '@anthropic-ai/sdk'",
            description="Fix Anthropic import to include runtime value"
        )
    
    return None


def fix_event_target_value(error: TypeScriptError) -> Optional[Fix]:
    """Fix TS2339: Property 'value' does not exist on EventTarget."""
    if "Property 'value' does not exist on type 'EventTarget" not in error.message:
        return None
    
    # This is typically fixed by using (e.target as HTMLInputElement).value
    # But it's complex to auto-fix without breaking things
    return None


def fix_stream_chunk_done(error: TypeScriptError) -> Optional[Fix]:
    """Fix TS2741: Property 'done' missing in StreamChunk."""
    if "Property 'done' is missing" not in error.message:
        return None
    
    content = read_file(error.file)
    
    # Find the specific line and add done: false
    lines = content.split('\n')
    error_line = lines[error.line - 1] if error.line <= len(lines) else None
    
    if error_line and "type:" in error_line and "content:" in error_line:
        # Add done: false to the object
        if "}" in error_line:
            old_text = error_line
            # Insert done: false before the closing brace
            new_text = error_line.replace("}", ", done: false }")
            return Fix(
                file=error.file,
                old_text=old_text,
                new_text=new_text,
                description="Add missing 'done' property to StreamChunk"
            )
    
    return None


# All fix generators
FIX_GENERATORS = [
    fix_ioredis_import,
    fix_missing_zod_import,
    fix_openai_namespace,
    fix_anthropic_namespace,
    fix_event_target_value,
    fix_stream_chunk_done,
]


def generate_fixes(errors: list[TypeScriptError]) -> list[Fix]:
    """Generate fixes for all errors."""
    fixes = []
    seen_files = set()
    
    for error in errors:
        # Skip if we already have a fix for this file (to avoid conflicts)
        if error.file in seen_files:
            continue
        
        for generator in FIX_GENERATORS:
            try:
                fix = generator(error)
                if fix:
                    fixes.append(fix)
                    seen_files.add(error.file)
                    break
            except Exception as e:
                console.print(f"[yellow]Warning: {e}[/yellow]")
    
    return fixes


def git_commit(message: str):
    """Commit changes to git."""
    subprocess.run(["git", "add", "-A"], cwd=REPO_PATH, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=REPO_PATH, check=True)


def git_push():
    """Push changes to GitHub."""
    subprocess.run(["git", "push", "origin", "main"], cwd=REPO_PATH, check=True)


def main():
    """Main entry point."""
    console.print("[bold blue]TypeScript Auto-Fixer[/bold blue]\n")
    
    # Step 1: Analyze errors
    console.print("[cyan]Step 1: Analyzing TypeScript errors...[/cyan]")
    errors = run_tsc()
    console.print(f"  Found [yellow]{len(errors)}[/yellow] errors\n")
    
    # Group by code
    by_code = {}
    for e in errors:
        if e.code not in by_code:
            by_code[e.code] = []
        by_code[e.code].append(e)
    
    table = Table(title="Error Summary")
    table.add_column("Code", style="cyan")
    table.add_column("Count", style="yellow")
    table.add_column("Sample Message", style="white")
    
    for code, errs in sorted(by_code.items(), key=lambda x: -len(x[1]))[:10]:
        table.add_row(code, str(len(errs)), errs[0].message[:60] + "...")
    
    console.print(table)
    console.print()
    
    # Step 2: Generate fixes
    console.print("[cyan]Step 2: Generating fixes...[/cyan]")
    fixes = generate_fixes(errors)
    console.print(f"  Generated [green]{len(fixes)}[/green] automatic fixes\n")
    
    if not fixes:
        console.print("[yellow]No automatic fixes available. Manual intervention required.[/yellow]")
        return 0
    
    # Step 3: Apply fixes
    console.print("[cyan]Step 3: Applying fixes...[/cyan]")
    applied = 0
    
    for fix in fixes:
        console.print(f"  Fixing: {fix.description}")
        console.print(f"    File: {fix.file}")
        if apply_fix(fix):
            applied += 1
            console.print(f"    [green]✓ Applied[/green]")
        else:
            console.print(f"    [red]✗ Failed[/red]")
    
    console.print(f"\n  Applied [green]{applied}[/green] of {len(fixes)} fixes\n")
    
    # Step 4: Verify
    console.print("[cyan]Step 4: Verifying fixes...[/cyan]")
    new_errors = run_tsc()
    reduction = len(errors) - len(new_errors)
    console.print(f"  Errors reduced by [green]{reduction}[/green] ({len(errors)} → {len(new_errors)})\n")
    
    # Step 5: Commit if improvements were made
    if applied > 0 and reduction > 0:
        console.print("[cyan]Step 5: Committing changes...[/cyan]")
        try:
            git_commit(f"fix: Auto-fix {applied} TypeScript errors (reduced by {reduction})")
            console.print("  [green]✓ Committed[/green]")
            
            console.print("\n[cyan]Step 6: Pushing to GitHub...[/cyan]")
            git_push()
            console.print("  [green]✓ Pushed[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"  [red]Git error: {e}[/red]")
    else:
        console.print("[yellow]No improvements made, skipping commit[/yellow]")
    
    console.print("\n[bold green]Done![/bold green]")
    return 0


if __name__ == "__main__":
    exit(main())
