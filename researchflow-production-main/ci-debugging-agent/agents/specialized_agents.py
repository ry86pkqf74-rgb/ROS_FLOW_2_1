"""
Specialized Debugging Agents for CI Debugging System
"""
from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
import re
import uuid

from agents.state import CIDebugState, BugReport, AnalysisPhase
from tools.code_analysis import run_typescript_check, run_eslint_check, analyze_package_json, find_dead_code, analyze_imports, check_react_components
from tools.docker_analysis import analyze_dockerfile, analyze_docker_compose, check_docker_build, check_container_networking, analyze_environment_vars
from tools.composio_tools import get_composio_tools, get_fallback_tools
from config.settings import settings


def get_llm():
    """Get the configured LLM."""
    if settings.llm.provider == "anthropic":
        return ChatAnthropic(model=settings.llm.model, temperature=settings.llm.temperature, max_tokens=settings.llm.max_tokens)
    return ChatOpenAI(model=settings.llm.model, temperature=settings.llm.temperature, max_tokens=settings.llm.max_tokens)


TYPESCRIPT_AGENT_PROMPT = """You are a TypeScript expert. Analyze compilation errors, type mismatches, ESLint violations.
For ResearchFlow: Watch for @types/express issues, React prop types, async/await patterns.
Report findings with categorization, root cause, and fix recommendations."""

typescript_agent_tools = [run_typescript_check, run_eslint_check, analyze_package_json, find_dead_code, analyze_imports]


def create_typescript_agent():
    return create_react_agent(model=get_llm(), tools=typescript_agent_tools, prompt=TYPESCRIPT_AGENT_PROMPT)


def typescript_agent_node(state: CIDebugState) -> Command[Literal["supervisor"]]:
    agent = create_typescript_agent()
    result = agent.invoke(state)
    new_bugs = extract_bugs_from_analysis(result, "typescript_error")
    return Command(
        update={
            "messages": [HumanMessage(content=result["messages"][-1].content, name="typescript_agent")],
            "bugs": state["bugs"] + new_bugs,
            "analysis_phases": state["analysis_phases"] + [
                AnalysisPhase(phase_name="typescript_analysis", agent_name="typescript_agent", status="completed", findings_count=len(new_bugs), summary=f"Found {len(new_bugs)} TypeScript issues")
            ]
        },
        goto="supervisor"
    )


DOCKER_AGENT_PROMPT = """You are a Docker expert. Analyze Dockerfiles, docker-compose, networking, env vars.
For React/Node.js: Ensure REACT_APP_*/VITE_* are build args, check service networking.
Report with severity, root cause, and code examples."""

docker_agent_tools = [analyze_dockerfile, analyze_docker_compose, check_docker_build, check_container_networking, analyze_environment_vars]


def create_docker_agent():
    return create_react_agent(model=get_llm(), tools=docker_agent_tools, prompt=DOCKER_AGENT_PROMPT)


def docker_agent_node(state: CIDebugState) -> Command[Literal["supervisor"]]:
    agent = create_docker_agent()
    result = agent.invoke(state)
    new_bugs = extract_bugs_from_analysis(result, "docker_issue")
    return Command(
        update={
            "messages": [HumanMessage(content=result["messages"][-1].content, name="docker_agent")],
            "bugs": state["bugs"] + new_bugs,
            "analysis_phases": state["analysis_phases"] + [
                AnalysisPhase(phase_name="docker_analysis", agent_name="docker_agent", status="completed", findings_count=len(new_bugs), summary=f"Found {len(new_bugs)} Docker issues")
            ]
        },
        goto="supervisor"
    )


FRONTEND_AGENT_PROMPT = """You are a React frontend expert. Check components, event handlers, state, CSS issues.
For ResearchFlow: Check landing page buttons, workflow display, MSW handlers, API connectivity.
Report with file paths, root cause, and code fixes."""

frontend_agent_tools = [check_react_components, run_eslint_check, analyze_imports] + get_fallback_tools()[:3]


def create_frontend_agent():
    return create_react_agent(model=get_llm(), tools=frontend_agent_tools, prompt=FRONTEND_AGENT_PROMPT)


def frontend_agent_node(state: CIDebugState) -> Command[Literal["supervisor"]]:
    agent = create_frontend_agent()
    result = agent.invoke(state)
    new_bugs = extract_bugs_from_analysis(result, "frontend_bug")
    return Command(
        update={
            "messages": [HumanMessage(content=result["messages"][-1].content, name="frontend_agent")],
            "bugs": state["bugs"] + new_bugs,
            "analysis_phases": state["analysis_phases"] + [
                AnalysisPhase(phase_name="frontend_analysis", agent_name="frontend_agent", status="completed", findings_count=len(new_bugs), summary=f"Found {len(new_bugs)} frontend issues")
            ]
        },
        goto="supervisor"
    )


CI_AGENT_PROMPT = """You are a CI/CD expert. Analyze GitHub Actions, CI logs, build failures.
Check workflow syntax, environment setup, test commands, artifact handling.
Report with specific locations, root cause, and YAML fixes."""


def create_ci_agent():
    return create_react_agent(model=get_llm(), tools=get_fallback_tools(), prompt=CI_AGENT_PROMPT)


def ci_agent_node(state: CIDebugState) -> Command[Literal["supervisor"]]:
    agent = create_ci_agent()
    result = agent.invoke(state)
    new_bugs = extract_bugs_from_analysis(result, "configuration_error")
    return Command(
        update={
            "messages": [HumanMessage(content=result["messages"][-1].content, name="ci_agent")],
            "bugs": state["bugs"] + new_bugs,
            "analysis_phases": state["analysis_phases"] + [
                AnalysisPhase(phase_name="ci_analysis", agent_name="ci_agent", status="completed", findings_count=len(new_bugs), summary=f"Found {len(new_bugs)} CI/CD issues")
            ]
        },
        goto="supervisor"
    )


def extract_bugs_from_analysis(result: dict, default_category: str) -> list[BugReport]:
    """Extract bug reports from agent output."""
    bugs = []
    if result.get("messages"):
        content = result["messages"][-1].content
        patterns = re.findall(r"(?:^|\n)(?:\d+\.|[-*])\s*(?:Issue|Error|Bug|Problem|Warning):\s*([^\n]+)", content, re.IGNORECASE)
        for issue in patterns[:20]:
            bugs.append(BugReport(id=str(uuid.uuid4())[:8], category=default_category, severity="medium", title=issue[:100], description=issue))
    return bugs


__all__ = ["create_typescript_agent", "typescript_agent_node", "create_docker_agent", "docker_agent_node", "create_frontend_agent", "frontend_agent_node", "create_ci_agent", "ci_agent_node", "get_llm"]
