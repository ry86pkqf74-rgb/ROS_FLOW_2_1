#!/usr/bin/env python3
"""
Multi-Agent Executor

Orchestrates specialized agents for full codebase review and automated fixes.

Architecture:
┌──────────────────────┐
│     SUPERVISOR       │ ← Orchestrates workflow, decides next agent
└──────────┬───────────┘
           │
    ┌──────┴──────┬──────────┬─────────────┐
    ▼             ▼          ▼             ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│TypeScript│  │ Docker │  │Frontend│  │ CI/CD  │
│ Agent    │  │ Agent  │  │ Agent  │  │ Agent  │
└────────┘  └────────┘  └────────┘  └────────┘
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.code_analysis import run_typescript_check, find_react_env_issues, analyze_imports
from tools.docker_analysis import run_docker_analysis
from tools.composio_tools import get_workflow_runs, create_github_issue, GitHubIssue

console = Console()

REPO_PATH = "/Users/lhglosser/researchflow-production"
REPO_NAME = "ry86pkqf74-rgb/researchflow-production"


class AgentType(Enum):
    TYPESCRIPT = "typescript"
    DOCKER = "docker"
    FRONTEND = "frontend"
    CICD = "cicd"
    SUPERVISOR = "supervisor"


@dataclass
class BugReport:
    """Represents a bug found by an agent."""
    agent: AgentType
    file: str
    line: int
    code: str
    message: str
    severity: str
    fixable: bool
    fix_applied: bool = False
    suggested_fix: Optional[str] = None


@dataclass
class AgentResult:
    """Result from an agent's analysis."""
    agent: AgentType
    bugs_found: list[BugReport] = field(default_factory=list)
    fixes_applied: int = 0
    errors_remaining: int = 0
    summary: str = ""


@dataclass
class ExecutionState:
    """State of the multi-agent execution."""
    started_at: datetime = field(default_factory=datetime.now)
    completed_agents: list[AgentType] = field(default_factory=list)
    pending_agents: list[AgentType] = field(default_factory=list)
    results: list[AgentResult] = field(default_factory=list)
    total_bugs: int = 0
    total_fixes: int = 0
    status: str = "initializing"


# =============================================================================
# Specialized Agent Implementations
# =============================================================================

class TypeScriptAgent:
    """Agent specialized in TypeScript error detection and fixing."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.name = AgentType.TYPESCRIPT
    
    def analyze(self) -> AgentResult:
        """Run TypeScript analysis."""
        console.print(f"  [cyan]→ Running TypeScript compiler...[/cyan]")
        result = run_typescript_check(self.repo_path)
        
        bugs = [
            BugReport(
                agent=self.name,
                file=err.file,
                line=err.line,
                code=err.code,
                message=err.message,
                severity=err.severity,
                fixable=err.fixable,
                suggested_fix=err.suggested_fix
            )
            for err in result.errors[:100]  # Limit for performance
        ]
        
        return AgentResult(
            agent=self.name,
            bugs_found=bugs,
            errors_remaining=result.total_errors,
            summary=f"Found {result.total_errors} TypeScript errors, {result.fixable_count} auto-fixable"
        )
    
    def fix(self, bugs: list[BugReport]) -> int:
        """Apply fixes for TypeScript errors."""
        fixes_applied = 0
        
        # Group fixable bugs by type
        by_code = {}
        for bug in bugs:
            if bug.fixable and not bug.fix_applied:
                if bug.code not in by_code:
                    by_code[bug.code] = []
                by_code[bug.code].append(bug)
        
        # Apply fixes for ioredis imports (TS2614)
        if 'TS2614' in by_code:
            for bug in by_code['TS2614']:
                if 'ioredis' in bug.message:
                    if self._fix_ioredis_import(bug.file):
                        bug.fix_applied = True
                        fixes_applied += 1
        
        # Apply fixes for missing zod imports (TS2503)
        if 'TS2503' in by_code:
            seen_files = set()
            for bug in by_code['TS2503']:
                if bug.file not in seen_files and "Cannot find namespace 'z'" in bug.message:
                    if self._fix_zod_import(bug.file):
                        bug.fix_applied = True
                        fixes_applied += 1
                        seen_files.add(bug.file)
        
        return fixes_applied
    
    def _fix_zod_import(self, filepath: str) -> bool:
        """Add missing zod import."""
        try:
            # Ensure we use full path
            full_path = filepath if filepath.startswith('/') else os.path.join(self.repo_path, filepath)
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Check if zod is already imported
            if "import { z } from 'zod'" in content or "import { z } from \"zod\"" in content:
                return False
            
            # Add import after first import statement
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') and 'from' in line:
                    lines.insert(i + 1, "import { z } from 'zod';")
                    break
            
            new_content = '\n'.join(lines)
            with open(full_path, 'w') as f:
                f.write(new_content)
            return True
        except Exception as e:
            console.print(f"    [red]Error fixing {filepath}: {e}[/red]")
        return False
    
    def _fix_ioredis_import(self, filepath: str) -> bool:
        """Fix ioredis import to use default export."""
        try:
            # Ensure we use full path
            full_path = filepath if filepath.startswith('/') else os.path.join(self.repo_path, filepath)
            with open(full_path, 'r') as f:
                content = f.read()
            
            if "import { Redis } from 'ioredis'" in content:
                new_content = content.replace(
                    "import { Redis } from 'ioredis'",
                    "import Redis from 'ioredis'"
                )
                with open(full_path, 'w') as f:
                    f.write(new_content)
                return True
        except Exception as e:
            console.print(f"    [red]Error fixing {filepath}: {e}[/red]")
        return False


class DockerAgent:
    """Agent specialized in Docker configuration analysis."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.name = AgentType.DOCKER
    
    def analyze(self) -> AgentResult:
        """Run Docker analysis."""
        console.print(f"  [cyan]→ Analyzing Docker configurations...[/cyan]")
        result = run_docker_analysis(self.repo_path)
        
        bugs = [
            BugReport(
                agent=self.name,
                file=issue.file,
                line=issue.line,
                code=issue.issue_type,
                message=issue.message,
                severity=issue.severity,
                fixable=issue.suggested_fix is not None,
                suggested_fix=issue.suggested_fix
            )
            for issue in result['issues']
        ]
        
        return AgentResult(
            agent=self.name,
            bugs_found=bugs,
            errors_remaining=result['summary']['total_issues'],
            summary=f"Found {result['summary']['total_issues']} Docker issues ({result['summary']['errors']} errors, {result['summary']['warnings']} warnings)"
        )
    
    def fix(self, bugs: list[BugReport]) -> int:
        """Apply fixes for Docker issues."""
        # Docker fixes are more complex and often require manual review
        return 0


class FrontendAgent:
    """Agent specialized in React/frontend issues."""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.name = AgentType.FRONTEND
    
    def analyze(self) -> AgentResult:
        """Run frontend analysis."""
        console.print(f"  [cyan]→ Analyzing frontend code...[/cyan]")
        env_issues = find_react_env_issues(self.repo_path)
        import_issues = analyze_imports(self.repo_path)
        
        bugs = []
        
        for issue in env_issues:
            bugs.append(BugReport(
                agent=self.name,
                file=issue.file,
                line=issue.line,
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
                fixable=issue.fixable,
                suggested_fix=issue.suggested_fix
            ))
        
        for issue_type, issues in import_issues.items():
            for issue in issues:
                bugs.append(BugReport(
                    agent=self.name,
                    file=issue.get('file', ''),
                    line=0,
                    code=issue_type.upper(),
                    message=issue.get('issue', ''),
                    severity='warning',
                    fixable=True,
                    suggested_fix=issue.get('fix')
                ))
        
        return AgentResult(
            agent=self.name,
            bugs_found=bugs,
            errors_remaining=len(bugs),
            summary=f"Found {len(env_issues)} env var issues, {sum(len(v) for v in import_issues.values())} import issues"
        )
    
    def fix(self, bugs: list[BugReport]) -> int:
        """Apply fixes for frontend issues."""
        fixes_applied = 0
        
        for bug in bugs:
            if bug.fixable and not bug.fix_applied:
                if bug.code == 'WRONG_IMPORT_STYLE' and 'ioredis' in bug.message:
                    if self._fix_import(bug.file, bug.suggested_fix):
                        bug.fix_applied = True
                        fixes_applied += 1
        
        return fixes_applied
    
    def _fix_import(self, filepath: str, fix: str) -> bool:
        """Apply an import fix."""
        # Implementation would apply the specific fix
        return False


class CICDAgent:
    """Agent specialized in CI/CD pipeline analysis."""
    
    def __init__(self, repo_path: str, repo_name: str):
        self.repo_path = repo_path
        self.repo_name = repo_name
        self.name = AgentType.CICD
    
    def analyze(self) -> AgentResult:
        """Run CI/CD analysis."""
        console.print(f"  [cyan]→ Analyzing CI/CD pipelines...[/cyan]")
        
        bugs = []
        
        # Check recent workflow runs
        runs = get_workflow_runs(self.repo_name, limit=5)
        failed_runs = [r for r in runs if r.get('conclusion') == 'failure']
        
        for run in failed_runs:
            bugs.append(BugReport(
                agent=self.name,
                file=f".github/workflows/{run.get('name', 'unknown')}.yml",
                line=0,
                code='WORKFLOW_FAILURE',
                message=f"Workflow '{run.get('name')}' failed",
                severity='error',
                fixable=False
            ))
        
        # Check for common CI issues in workflow files
        workflow_dir = os.path.join(self.repo_path, '.github', 'workflows')
        if os.path.exists(workflow_dir):
            for file in os.listdir(workflow_dir):
                if file.endswith(('.yml', '.yaml')):
                    filepath = os.path.join(workflow_dir, file)
                    issues = self._analyze_workflow_file(filepath)
                    bugs.extend(issues)
        
        return AgentResult(
            agent=self.name,
            bugs_found=bugs,
            errors_remaining=len(bugs),
            summary=f"Found {len(failed_runs)} failed workflow runs, {len(bugs) - len(failed_runs)} workflow config issues"
        )
    
    def _analyze_workflow_file(self, filepath: str) -> list[BugReport]:
        """Analyze a workflow file for issues."""
        bugs = []
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Check for deprecated actions
            if 'actions/checkout@v2' in content:
                bugs.append(BugReport(
                    agent=self.name,
                    file=filepath,
                    line=0,
                    code='DEPRECATED_ACTION',
                    message="Using deprecated actions/checkout@v2, upgrade to v4",
                    severity='warning',
                    fixable=True,
                    suggested_fix="Replace actions/checkout@v2 with actions/checkout@v4"
                ))
            
            if 'actions/setup-node@v2' in content:
                bugs.append(BugReport(
                    agent=self.name,
                    file=filepath,
                    line=0,
                    code='DEPRECATED_ACTION',
                    message="Using deprecated actions/setup-node@v2, upgrade to v4",
                    severity='warning',
                    fixable=True,
                    suggested_fix="Replace actions/setup-node@v2 with actions/setup-node@v4"
                ))
        except Exception:
            pass
        
        return bugs
    
    def fix(self, bugs: list[BugReport]) -> int:
        """Apply fixes for CI/CD issues."""
        return 0


# =============================================================================
# Supervisor - Orchestrates All Agents
# =============================================================================

class Supervisor:
    """Supervises and orchestrates all specialized agents."""
    
    def __init__(self, repo_path: str, repo_name: str):
        self.repo_path = repo_path
        self.repo_name = repo_name
        self.state = ExecutionState(
            pending_agents=[AgentType.TYPESCRIPT, AgentType.DOCKER, AgentType.FRONTEND, AgentType.CICD]
        )
        
        # Initialize agents
        self.agents = {
            AgentType.TYPESCRIPT: TypeScriptAgent(repo_path),
            AgentType.DOCKER: DockerAgent(repo_path),
            AgentType.FRONTEND: FrontendAgent(repo_path),
            AgentType.CICD: CICDAgent(repo_path, repo_name),
        }
    
    def run_full_review(self) -> ExecutionState:
        """Run full codebase review with all agents."""
        console.print(Panel.fit(
            "[bold blue]Multi-Agent Code Review[/bold blue]\n"
            "[dim]Supervisor orchestrating specialized agents[/dim]",
            border_style="blue"
        ))
        
        self.state.status = "analyzing"
        
        # Phase 1: Analysis
        console.print("\n[bold cyan]Phase 1: Analysis[/bold cyan]\n")
        
        for agent_type in list(self.state.pending_agents):
            console.print(f"[yellow]Running {agent_type.value} agent...[/yellow]")
            agent = self.agents[agent_type]
            result = agent.analyze()
            self.state.results.append(result)
            self.state.total_bugs += len(result.bugs_found)
            self.state.pending_agents.remove(agent_type)
            self.state.completed_agents.append(agent_type)
            console.print(f"  [green]✓ {result.summary}[/green]\n")
        
        # Phase 2: Fixes
        console.print("\n[bold cyan]Phase 2: Automated Fixes[/bold cyan]\n")
        self.state.status = "fixing"
        
        for result in self.state.results:
            if any(b.fixable for b in result.bugs_found):
                console.print(f"[yellow]Applying fixes for {result.agent.value}...[/yellow]")
                agent = self.agents[result.agent]
                fixes = agent.fix(result.bugs_found)
                result.fixes_applied = fixes
                self.state.total_fixes += fixes
                console.print(f"  [green]✓ Applied {fixes} fixes[/green]\n")
        
        # Phase 3: Verification
        console.print("\n[bold cyan]Phase 3: Verification[/bold cyan]\n")
        self.state.status = "verifying"
        
        # Re-run TypeScript check to verify fixes
        console.print("[yellow]Verifying TypeScript fixes...[/yellow]")
        ts_result = run_typescript_check(self.repo_path)
        console.print(f"  [green]✓ {ts_result.total_errors} errors remaining[/green]\n")
        
        self.state.status = "completed"
        return self.state
    
    def generate_report(self) -> str:
        """Generate a summary report."""
        report = []
        report.append("# Multi-Agent Code Review Report\n")
        report.append(f"**Repository:** {self.repo_name}")
        report.append(f"**Date:** {self.state.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Status:** {self.state.status}\n")
        
        report.append("## Summary\n")
        report.append(f"- **Total bugs found:** {self.state.total_bugs}")
        report.append(f"- **Fixes applied:** {self.state.total_fixes}\n")
        
        report.append("## Agent Results\n")
        for result in self.state.results:
            report.append(f"### {result.agent.value.title()} Agent")
            report.append(f"- {result.summary}")
            report.append(f"- Fixes applied: {result.fixes_applied}\n")
            
            if result.bugs_found:
                report.append("#### Top Issues:")
                for bug in result.bugs_found[:5]:
                    report.append(f"- `{bug.code}`: {bug.message[:80]}...")
                report.append("")
        
        return '\n'.join(report)
    
    def commit_fixes(self, message: str) -> bool:
        """Commit and push fixes to GitHub."""
        try:
            subprocess.run(["git", "add", "-A"], cwd=self.repo_path, check=True)
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=self.repo_path, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


# =============================================================================
# Main Execution
# =============================================================================

def main():
    """Main entry point."""
    console.print("[bold blue]═══ Multi-Agent CI Debugging System ═══[/bold blue]\n")
    
    # Initialize supervisor
    supervisor = Supervisor(REPO_PATH, REPO_NAME)
    
    # Run full review
    state = supervisor.run_full_review()
    
    # Generate and display report
    console.print("\n[bold cyan]═══ Final Report ═══[/bold cyan]\n")
    report = supervisor.generate_report()
    console.print(Markdown(report))
    
    # Summary table
    table = Table(title="Execution Summary")
    table.add_column("Agent", style="cyan")
    table.add_column("Bugs Found", style="yellow")
    table.add_column("Fixes Applied", style="green")
    
    for result in state.results:
        table.add_row(
            result.agent.value.title(),
            str(len(result.bugs_found)),
            str(result.fixes_applied)
        )
    
    table.add_row("─" * 10, "─" * 10, "─" * 10)
    table.add_row("TOTAL", str(state.total_bugs), str(state.total_fixes))
    
    console.print(table)
    
    # Commit fixes if any were applied
    if state.total_fixes > 0:
        console.print("\n[cyan]Committing fixes to GitHub...[/cyan]")
        if supervisor.commit_fixes(f"fix: Multi-agent automated fixes ({state.total_fixes} fixes applied)"):
            console.print("[green]✓ Changes committed and pushed[/green]")
        else:
            console.print("[yellow]⚠ No changes to commit or commit failed[/yellow]")
    
    console.print("\n[bold green]✓ Multi-agent review complete![/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
