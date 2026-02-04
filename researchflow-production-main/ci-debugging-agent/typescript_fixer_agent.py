#!/usr/bin/env python3
"""
TypeScript Fixer Agent - Composio + LangGraph

Automatically analyzes and fixes TypeScript errors using AI-powered code analysis.
"""
import os
import re
import json
import asyncio
from pathlib import Path
from typing import TypedDict, Annotated, Sequence, Literal
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# LangChain imports
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool

# Composio imports
from composio_langchain import ComposioToolSet, Action, App

console = Console()

# =============================================================================
# Agent State
# =============================================================================

class AgentState(TypedDict):
    """State for the TypeScript fixer agent."""
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    errors: list[dict]
    fixes_applied: list[dict]
    current_file: str
    iteration: int
    status: str


# =============================================================================
# Error Analysis Tools
# =============================================================================

@tool
def analyze_typescript_errors(repo_path: str) -> str:
    """
    Run TypeScript compiler and analyze errors.
    
    Args:
        repo_path: Path to the repository
    
    Returns:
        JSON string with categorized errors
    """
    import subprocess
    
    result = subprocess.run(
        ["pnpm", "exec", "tsc", "--noEmit"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "PATH": f"/Users/ros/.npm-global/bin:{os.environ.get('PATH', '')}"}
    )
    
    output = result.stderr + result.stdout
    error_lines = [l for l in output.split('\n') if 'error TS' in l]
    
    # Parse errors into structured format
    errors = []
    for line in error_lines:
        match = re.match(r'(.+?)\((\d+),(\d+)\): error (TS\d+): (.+)', line)
        if match:
            errors.append({
                'file': match.group(1),
                'line': int(match.group(2)),
                'column': int(match.group(3)),
                'code': match.group(4),
                'message': match.group(5)
            })
    
    # Group by error type
    by_code = {}
    for err in errors:
        code = err['code']
        if code not in by_code:
            by_code[code] = []
        by_code[code].append(err)
    
    return json.dumps({
        'total': len(errors),
        'by_code': {k: len(v) for k, v in by_code.items()},
        'sample_errors': errors[:30]
    }, indent=2)


@tool
def read_file_content(file_path: str) -> str:
    """
    Read the content of a file.
    
    Args:
        file_path: Path to the file to read
    
    Returns:
        File content as string
    """
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file_content(file_path: str, content: str) -> str:
    """
    Write content to a file.
    
    Args:
        file_path: Path to the file to write
        content: Content to write
    
    Returns:
        Success or error message
    """
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def apply_fix(file_path: str, old_text: str, new_text: str) -> str:
    """
    Apply a fix by replacing text in a file.
    
    Args:
        file_path: Path to the file
        old_text: Text to replace
        new_text: Replacement text
    
    Returns:
        Success or error message
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        if old_text not in content:
            return f"Error: Could not find text to replace in {file_path}"
        
        new_content = content.replace(old_text, new_text, 1)
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        return f"Successfully applied fix to {file_path}"
    except Exception as e:
        return f"Error applying fix: {e}"


@tool
def git_commit_and_push(repo_path: str, message: str) -> str:
    """
    Stage all changes, commit, and push to GitHub.
    
    Args:
        repo_path: Path to the repository
        message: Commit message
    
    Returns:
        Success or error message
    """
    import subprocess
    
    try:
        # Stage all changes
        subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)
        
        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path,
            check=True
        )
        
        # Push
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=repo_path,
            check=True
        )
        
        return "Successfully committed and pushed changes"
    except subprocess.CalledProcessError as e:
        return f"Git error: {e}"
    except Exception as e:
        return f"Error: {e}"


# =============================================================================
# Fix Patterns - Known TypeScript Error Fixes
# =============================================================================

FIX_PATTERNS = {
    'TS2305': {  # Module has no exported member
        'description': 'Missing export - check if export exists or needs to be added',
        'auto_fixable': False
    },
    'TS2339': {  # Property does not exist on type
        'description': 'Missing property - may need type assertion or interface update',
        'auto_fixable': False
    },
    'TS2503': {  # Cannot find namespace
        'description': 'Namespace not found - usually missing import',
        'auto_fixable': True,
        'fix_template': "Add import statement for the namespace"
    },
    'TS2322': {  # Type is not assignable
        'description': 'Type mismatch - needs type casting or interface fix',
        'auto_fixable': False
    },
    'TS2614': {  # Module has no exported member (default vs named)
        'description': 'Wrong import syntax - switch between default and named import',
        'auto_fixable': True,
        'fix_template': "Change import { X } from 'y' to import X from 'y' or vice versa"
    },
    'TS2702': {  # Type only refers to a type, but is being used as a namespace
        'description': 'Using type as namespace - need to import the runtime value',
        'auto_fixable': True
    }
}


# =============================================================================
# LangGraph Agent Definition  
# =============================================================================

def create_fixer_agent():
    """Create the TypeScript fixer agent using LangGraph."""
    
    # Initialize Composio tools
    composio_toolset = ComposioToolSet()
    
    # Get GitHub tools from Composio
    github_tools = composio_toolset.get_tools(
        actions=[
            Action.GITHUB_GET_A_REPOSITORY,
            Action.GITHUB_LIST_REPOSITORY_ISSUES,
            Action.GITHUB_CREATE_AN_ISSUE,
        ]
    )
    
    # Local tools
    local_tools = [
        analyze_typescript_errors,
        read_file_content,
        write_file_content,
        apply_fix,
        git_commit_and_push
    ]
    
    all_tools = local_tools + github_tools
    
    # Initialize LLM
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        max_tokens=4096
    )
    
    llm_with_tools = llm.bind_tools(all_tools)
    
    # Define the agent function
    def agent_node(state: AgentState) -> AgentState:
        """Main agent reasoning node."""
        system_prompt = """You are an expert TypeScript developer fixing errors in a monorepo.

Your task is to:
1. Analyze TypeScript errors from the compiler output
2. Identify the root cause of each error
3. Apply fixes using the available tools
4. Verify fixes by re-running the TypeScript compiler

Focus on these common fix patterns:
- TS2614: Change `import { X } from 'y'` to `import X from 'y'` for default exports
- TS2503: Add missing imports for namespaces like `import { z } from 'zod'`
- TS2305: Check if the export exists in the source module and add it if missing
- TS2339: Add missing properties to interfaces or use type assertions

Repository path: /Users/lhglosser/researchflow-production

Always explain your reasoning before making changes. Make one fix at a time and verify it works."""

        messages = [SystemMessage(content=system_prompt)] + list(state['messages'])
        response = llm_with_tools.invoke(messages)
        
        return {
            **state,
            'messages': [response],
            'iteration': state['iteration'] + 1
        }
    
    # Define tool execution node
    tool_node = ToolNode(all_tools)
    
    # Define routing function
    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        """Determine if we should continue or end."""
        last_message = state['messages'][-1]
        
        # If max iterations reached, end
        if state['iteration'] >= 10:
            return "end"
        
        # If there are tool calls, execute them
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        
        return "end"
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


# =============================================================================
# Main Execution
# =============================================================================

async def run_fixer_agent():
    """Run the TypeScript fixer agent."""
    console.print(Panel.fit(
        "[bold blue]TypeScript Fixer Agent[/bold blue]\n"
        "[dim]Powered by Composio + LangGraph + Claude[/dim]",
        border_style="blue"
    ))
    
    # Create the agent
    console.print("\n[cyan]Initializing agent...[/cyan]")
    agent = create_fixer_agent()
    
    # Initial state
    initial_state: AgentState = {
        'messages': [
            HumanMessage(content="""Please fix the TypeScript errors in this repository:

1. First, run analyze_typescript_errors to get the current errors
2. Focus on fixing the most impactful errors first (those that cause cascading failures)
3. Start with TS2614 (ioredis import) and TS2305 (missing exports) errors
4. After each fix, verify by running analyze_typescript_errors again
5. Once you've made significant progress, commit the changes

Repository path: /Users/lhglosser/researchflow-production""")
        ],
        'errors': [],
        'fixes_applied': [],
        'current_file': '',
        'iteration': 0,
        'status': 'starting'
    }
    
    # Run the agent
    console.print("\n[cyan]Running fixer agent...[/cyan]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing...", total=None)
        
        final_state = None
        async for state in agent.astream(initial_state):
            if 'agent' in state:
                msg = state['agent']['messages'][-1]
                if hasattr(msg, 'content') and msg.content:
                    # Print agent's response
                    console.print(f"\n[green]Agent:[/green] {msg.content[:500]}...")
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        progress.update(task, description=f"Calling: {tc['name']}")
            
            if 'tools' in state:
                for msg in state['tools']['messages']:
                    if hasattr(msg, 'content'):
                        console.print(f"\n[yellow]Tool Result:[/yellow] {str(msg.content)[:300]}...")
            
            final_state = state
    
    console.print("\n[green]Agent completed![/green]")
    return final_state


def main():
    """Main entry point."""
    # Set environment variables
    os.environ['COMPOSIO_API_KEY'] = 'ak_YhbOJal4TkAsNUR0NX2j'
    
    # Check for Anthropic API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        console.print("[red]Error: ANTHROPIC_API_KEY not set[/red]")
        console.print("Please set your Anthropic API key:")
        console.print("  export ANTHROPIC_API_KEY='your-key-here'")
        return 1
    
    try:
        result = asyncio.run(run_fixer_agent())
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
