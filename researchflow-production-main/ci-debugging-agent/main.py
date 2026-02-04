#!/usr/bin/env python3
"""
CI Debugging Agent - Main Entry Point

A multi-agent system using LangGraph and Composio for automated CI/CD debugging.
"""
import asyncio
import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

console = Console()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CI Debugging Agent - Automated multi-agent debugging system"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="ry86pkqf74-rgb/researchflow-production",
        help="GitHub repository in owner/repo format"
    )
    parser.add_argument(
        "--branch",
        type=str,
        default="main",
        help="Target branch to analyze"
    )
    parser.add_argument(
        "--local-path",
        type=str,
        default="/Users/lhglosser/researchflow-production",
        help="Local path to repository"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    return parser.parse_args()


def display_header(args):
    """Display the startup header."""
    console.print(Panel.fit(
        "[bold blue]CI Debugging Agent[/bold blue]\n"
        "[dim]Powered by LangGraph + Composio[/dim]",
        border_style="blue"
    ))

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Repository", args.repo)
    table.add_row("Branch", args.branch)
    table.add_row("Local Path", args.local_path)

    console.print(table)
    console.print()


async def analyze_typescript_errors(local_path: str) -> dict:
    """Analyze TypeScript errors in the repository."""
    console.print("[cyan]Analyzing TypeScript errors...[/cyan]")
    
    import subprocess
    result = subprocess.run(
        ["pnpm", "exec", "tsc", "--noEmit"],
        cwd=local_path,
        capture_output=True,
        text=True,
        timeout=300
    )
    
    errors = result.stderr + result.stdout
    error_lines = [l for l in errors.split('\n') if 'error TS' in l]
    
    # Categorize errors
    categories = {}
    for line in error_lines:
        if 'TS2305' in line:
            cat = 'missing_exports'
        elif 'TS2503' in line:
            cat = 'namespace_not_found'
        elif 'TS2339' in line:
            cat = 'property_not_exist'
        elif 'TS2322' in line:
            cat = 'type_mismatch'
        elif 'TS2702' in line:
            cat = 'namespace_as_value'
        else:
            cat = 'other'
        
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(line)
    
    return {
        'total_errors': len(error_lines),
        'categories': {k: len(v) for k, v in categories.items()},
        'sample_errors': error_lines[:20]
    }


async def analyze_with_composio(repo: str) -> dict:
    """Use Composio GitHub tools to analyze the repository."""
    console.print("[cyan]Analyzing with Composio GitHub tools...[/cyan]")
    
    try:
        from composio_langchain import ComposioToolSet
        
        toolset = ComposioToolSet()
        tools = toolset.get_tools(apps=['github'])
        
        console.print(f"  [green]✓ Loaded {len(tools)} GitHub tools[/green]")
        
        return {
            'tools_loaded': len(tools),
            'tool_names': [t.name for t in tools[:10]]
        }
    except Exception as e:
        console.print(f"  [yellow]⚠ Composio not available: {e}[/yellow]")
        return {'error': str(e)}


async def run_debugging_session(args):
    """Run the main debugging session."""
    console.print("[cyan]Starting parallel analysis...[/cyan]\n")
    
    # Run analyses in parallel
    results = await asyncio.gather(
        analyze_typescript_errors(args.local_path),
        analyze_with_composio(args.repo),
        return_exceptions=True
    )
    
    ts_results, composio_results = results
    
    # Display results
    console.print("\n[bold green]═══ Analysis Results ═══[/bold green]\n")
    
    if isinstance(ts_results, dict) and 'total_errors' in ts_results:
        console.print(f"[bold]TypeScript Errors:[/bold] {ts_results['total_errors']}")
        for cat, count in ts_results.get('categories', {}).items():
            console.print(f"  • {cat}: {count}")
    
    if isinstance(composio_results, dict) and 'tools_loaded' in composio_results:
        console.print(f"\n[bold]Composio Tools:[/bold] {composio_results['tools_loaded']} loaded")
    
    return {'typescript': ts_results, 'composio': composio_results}


def main():
    """Main entry point."""
    args = parse_args()
    display_header(args)

    try:
        result = asyncio.run(run_debugging_session(args))
        console.print("\n[green]Analysis complete[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
