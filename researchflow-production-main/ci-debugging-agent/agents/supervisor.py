"""
CI Debugging Supervisor Agent
Orchestrates specialized debugging agents using LangGraph.
"""
from typing import Literal
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from pydantic import BaseModel, Field

from agents.state import CIDebugState, BugReport, AnalysisPhase
from agents.specialized_agents import (
    typescript_agent_node,
    docker_agent_node,
    frontend_agent_node,
    ci_agent_node,
    get_llm
)
from config.settings import settings


class SupervisorDecision(BaseModel):
    """Structured output for supervisor routing decisions."""
    next_agent: Literal[
        "typescript_agent",
        "docker_agent",
        "frontend_agent",
        "ci_agent",
        "generate_report",
        "END"
    ] = Field(description="The next agent to route to")
    reasoning: str = Field(description="Brief explanation of why this agent was chosen")


SUPERVISOR_PROMPT = """You are the CI Debugging Supervisor Agent. Your role is to orchestrate a team of specialized debugging agents.

## Your Team:
1. **typescript_agent**: TypeScript compilation errors, type issues, ESLint violations
2. **docker_agent**: Dockerfile, docker-compose, container networking, env vars
3. **frontend_agent**: React components, click handlers, state management, UI rendering
4. **ci_agent**: GitHub Actions workflows, CI logs, build failures

## Routing Guidelines:
- If TypeScript errors haven't been analyzed yet → typescript_agent
- If Docker/container issues haven't been checked → docker_agent
- If frontend UI issues need investigation → frontend_agent
- If CI workflow analysis is needed → ci_agent
- If all agents have reported and we have findings → generate_report
- If the analysis is complete → END

Based on the current state and previous analysis, decide which agent should be activated next."""


def create_supervisor_node():
    """Create the supervisor decision-making node."""
    llm = get_llm().with_structured_output(SupervisorDecision)

    def supervisor(state: CIDebugState) -> Command[Literal[
        "typescript_agent", "docker_agent", "frontend_agent", "ci_agent", "generate_report", END
    ]]:
        completed_phases = [p.phase_name for p in state["analysis_phases"]]
        total_bugs = len(state["bugs"])

        context_message = f"""
## Current Analysis Status:
Repository: {state['repo_owner']}/{state['repo_name']}
Completed Phases: {', '.join(completed_phases) if completed_phases else 'None yet'}
Bugs Found: {total_bugs}

Based on this status, decide which agent should run next."""

        messages = [
            SystemMessage(content=SUPERVISOR_PROMPT),
            HumanMessage(content=context_message)
        ] + list(state["messages"])[-10:]

        try:
            decision = llm.invoke(messages)
            return Command(
                update={
                    "messages": [HumanMessage(content=f"Supervisor: Route to {decision.next_agent}", name="supervisor")],
                    "current_phase": decision.next_agent
                },
                goto=decision.next_agent
            )
        except Exception as e:
            next_agent = _fallback_routing(completed_phases)
            return Command(
                update={"messages": [HumanMessage(content=f"Supervisor fallback: {next_agent}", name="supervisor")], "current_phase": next_agent},
                goto=next_agent
            )

    return supervisor


def _fallback_routing(completed_phases: list[str]) -> str:
    phase_order = [
        ("typescript_analysis", "typescript_agent"),
        ("docker_analysis", "docker_agent"),
        ("frontend_analysis", "frontend_agent"),
        ("ci_analysis", "ci_agent"),
    ]
    for phase_name, agent_name in phase_order:
        if phase_name not in completed_phases:
            return agent_name
    return "generate_report"


def generate_report_node(state: CIDebugState) -> Command[Literal[END]]:
    """Generate the final debugging report."""
    llm = get_llm()
    
    bug_summary = "\n".join([f"- [{b.severity}] {b.title}" for b in state['bugs'][:20]])
    
    report_prompt = f"""Generate a CI debugging report for {state['repo_owner']}/{state['repo_name']}.

Bugs Found ({len(state['bugs'])}):
{bug_summary if bug_summary else 'No bugs found'}

Generate a Markdown report with: Executive Summary, Critical Issues, Recommended Fixes."""

    response = llm.invoke([
        SystemMessage(content="You are a technical report writer."),
        HumanMessage(content=report_prompt)
    ])

    return Command(
        update={"final_report": response.content, "should_continue": False},
        goto=END
    )


def build_supervisor_graph() -> StateGraph:
    """Build the complete supervisor graph."""
    builder = StateGraph(CIDebugState)
    builder.add_node("supervisor", create_supervisor_node())
    builder.add_node("typescript_agent", typescript_agent_node)
    builder.add_node("docker_agent", docker_agent_node)
    builder.add_node("frontend_agent", frontend_agent_node)
    builder.add_node("ci_agent", ci_agent_node)
    builder.add_node("generate_report", generate_report_node)
    builder.add_edge(START, "supervisor")
    return builder.compile()


__all__ = ["build_supervisor_graph", "create_supervisor_node", "generate_report_node"]
