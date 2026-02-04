"""
Stage 16: Collaboration Handoff

Handles AI-powered collaboration handoff including:
- Team member assignment and access permission configuration
- Deadline and milestone setting
- Notification dispatch
- WebSocket channel and real-time session setup
- Comment thread initialization
- Previous stage summary, key findings, open questions, next steps
- Integration hooks: Slack/Teams, email digest, calendar events

This stage prepares a handoff package for collaborators and produces
config structures for the orchestrator/collab service.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

logger = logging.getLogger("workflow_engine.stage_16_handoff")

# LangChain imports with graceful fallback
try:
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None  # type: ignore
    logger.warning("LangChain not available. Tools will not be available.")

# Default handoff configuration
DEFAULT_HANDOFF_CONFIG = {
    "team_roles": [
        {"id": "pi", "name": "Principal Investigator", "required": True},
        {"id": "co_author", "name": "Co-Author", "required": False},
        {"id": "reviewer", "name": "Reviewer", "required": False},
    ],
    "access_levels": ["view", "edit", "admin"],
    "notification_channels": ["slack", "teams", "email"],
    "default_deadline_days": 14,
    "default_milestones": [
        {"id": "draft_review", "name": "Draft review", "offset_days": 7},
        {"id": "submission", "name": "Submission", "offset_days": 14},
    ],
}


# ---------------------------------------------------------------------------
# Handoff protocols
# ---------------------------------------------------------------------------

def build_team_assignments(
    team_config: List[Dict[str, Any]],
    previous_results: Dict[int, Any],
) -> List[Dict[str, Any]]:
    """Map roles to assignees from config; optionally derive from prior stage outputs.

    Args:
        team_config: List of role configs (id, name, required) and optional assignees
        previous_results: Results from previous stages

    Returns:
        List of assignment dicts with role_id, role_name, assignee, source
    """
    assignments: List[Dict[str, Any]] = []
    roles = team_config if isinstance(team_config, list) else DEFAULT_HANDOFF_CONFIG["team_roles"]

    for role in roles:
        if not isinstance(role, dict):
            continue
        role_id = role.get("id", "unknown")
        role_name = role.get("name", role_id.replace("_", " ").title())
        assignee = role.get("assignee") or role.get("email") or role.get("user_id")
        if not assignee and previous_results:
            # Placeholder from prior stage if available
            for sid, result in previous_results.items():
                out = getattr(result, "output", result) if not isinstance(result, dict) else result.get("output", result)
                if isinstance(out, dict) and out.get("principal_investigator"):
                    assignee = out["principal_investigator"]
                    break
        assignments.append({
            "role_id": role_id,
            "role_name": role_name,
            "assignee": assignee or "Unassigned",
            "required": role.get("required", False),
            "source": "config" if role.get("assignee") else "derived",
        })
    return assignments


def build_access_permissions(
    access_config: Dict[str, Any],
    job_id: str,
) -> Dict[str, Any]:
    """Build permission levels (view/edit/admin), expiry, scope.

    Args:
        access_config: Optional access config with levels, expiry_days, scope
        job_id: Job identifier

    Returns:
        Dict with permissions list, expiry_iso, scope
    """
    config = access_config or {}
    levels = config.get("levels") or DEFAULT_HANDOFF_CONFIG["access_levels"]
    expiry_days = config.get("expiry_days") or 30
    scope = config.get("scope") or "artifacts"
    expiry = datetime.utcnow() + timedelta(days=expiry_days)
    return {
        "job_id": job_id,
        "permission_levels": levels,
        "expiry_iso": expiry.isoformat() + "Z",
        "scope": scope,
        "artifacts_included": config.get("artifacts_included", True),
        "channels_included": config.get("channels_included", True),
    }


def build_deadlines_and_milestones(
    config: Dict[str, Any],
    base_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Build deadlines and milestones from config or defaults.

    Args:
        config: Job config with optional deadlines and milestones
        base_date: Base date for offset calculations

    Returns:
        List of deadline/milestone dicts with id, name, due_iso, offset_days
    """
    base = base_date or datetime.utcnow()
    custom = config.get("deadlines") or config.get("milestones")
    if custom and isinstance(custom, list):
        out: List[Dict[str, Any]] = []
        for m in custom:
            if not isinstance(m, dict):
                continue
            offset = m.get("offset_days", 14)
            due = base + timedelta(days=offset)
            out.append({
                "id": m.get("id", "milestone"),
                "name": m.get("name", "Milestone"),
                "due_iso": due.isoformat() + "Z",
                "offset_days": offset,
            })
        return out
    milestones = DEFAULT_HANDOFF_CONFIG.get("default_milestones", [])
    return [
        {
            "id": m.get("id", "milestone"),
            "name": m.get("name", "Milestone"),
            "due_iso": (base + timedelta(days=m.get("offset_days", 14))).isoformat() + "Z",
            "offset_days": m.get("offset_days", 14),
        }
        for m in milestones
    ]


def build_notification_dispatch_list(
    assignments: List[Dict[str, Any]],
    channels_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build list of who gets notified (Slack/Teams/email) and when.

    Args:
        assignments: Team assignments from build_team_assignments
        channels_config: Config with channel ids, digest_frequency

    Returns:
        List of notification spec dicts
    """
    channels = channels_config.get("channels") or DEFAULT_HANDOFF_CONFIG["notification_channels"]
    digest = channels_config.get("digest_frequency") or "daily"
    dispatch: List[Dict[str, Any]] = []
    for a in assignments:
        assignee = a.get("assignee")
        if assignee and assignee != "Unassigned":
            for ch in channels:
                dispatch.append({
                    "assignee": assignee,
                    "channel": ch,
                    "when": "immediate" if ch == "email" else channels_config.get("when", "immediate"),
                    "digest_frequency": digest,
                })
    return dispatch


# ---------------------------------------------------------------------------
# Collaboration setup (output structures for orchestrator/collab service)
# ---------------------------------------------------------------------------

def build_websocket_channel_config(
    job_id: str,
    participants: List[str],
) -> Dict[str, Any]:
    """Build WebSocket channel config for collab service.

    Args:
        job_id: Job identifier
        participants: List of participant ids or emails

    Returns:
        Dict with channel_id, room_name, participant_ids
    """
    channel_id = f"handoff-{job_id}"
    return {
        "channel_id": channel_id,
        "room_name": f"collab-{job_id}",
        "participant_ids": list(participants) if participants else [],
        "job_id": job_id,
    }


def build_realtime_session_config(
    job_id: str,
    artifact_refs: List[str],
) -> Dict[str, Any]:
    """Build real-time editing session config.

    Args:
        job_id: Job identifier
        artifact_refs: Document/artifact refs for the session

    Returns:
        Dict with session_id, artifact_refs, edit_mode
    """
    return {
        "session_id": f"session-{job_id}",
        "job_id": job_id,
        "artifact_refs": list(artifact_refs) if artifact_refs else [],
        "edit_mode": "edit",
    }


def build_comment_thread_init(
    thread_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build placeholder comment threads (e.g. per section).

    Args:
        thread_config: Config with section_ids or thread_titles

    Returns:
        List of thread placeholders
    """
    sections = thread_config.get("sections") or ["abstract", "introduction", "methods", "results", "discussion"]
    return [
        {"section": s, "thread_id": f"thread-{s}", "comment_count": 0}
        for s in sections
    ]


# ---------------------------------------------------------------------------
# Context transfer
# ---------------------------------------------------------------------------

def generate_previous_stage_summary(previous_results: Dict[int, Any]) -> str:
    """Generate short text summary of prior stages (status, key outputs).

    Args:
        previous_results: Results from previously executed stages

    Returns:
        Summary string
    """
    if not previous_results:
        return "No previous stages executed."
    lines: List[str] = []
    for stage_id in sorted(previous_results.keys()):
        result = previous_results[stage_id]
        status = getattr(result, "status", None) or (result.get("status") if isinstance(result, dict) else None)
        output = getattr(result, "output", None) or (result.get("output", {}) if isinstance(result, dict) else {})
        lines.append(f"Stage {stage_id}: {status or 'unknown'}")
        if isinstance(output, dict) and output:
            keys = list(output.keys())[:3]
            lines.append(f"  Output keys: {', '.join(str(k) for k in keys)}")
    return "\n".join(lines)


def extract_key_findings(previous_results: Dict[int, Any]) -> List[Dict[str, Any]]:
    """Extract findings from results (e.g. stage 9/12) with source stage and snippet.

    Args:
        previous_results: Results from previous stages

    Returns:
        List of finding dicts with stage_id, snippet, category
    """
    findings: List[Dict[str, Any]] = []
    for stage_id in sorted(previous_results.keys()):
        result = previous_results[stage_id]
        output = getattr(result, "output", None) or (result.get("output", {}) if isinstance(result, dict) else {})
        if not isinstance(output, dict):
            continue
        for key in ("findings", "key_findings", "results", "summary"):
            val = output.get(key)
            if isinstance(val, list):
                for i, item in enumerate(val[:5]):
                    snippet = item.get("snippet") or item.get("text") or str(item)[:200]
                    findings.append({"stage_id": stage_id, "snippet": snippet, "category": key})
            elif isinstance(val, str) and val:
                findings.append({"stage_id": stage_id, "snippet": val[:300], "category": key})
    if not findings:
        for stage_id in sorted(previous_results.keys()):
            result = previous_results[stage_id]
            output = getattr(result, "output", None) or (result.get("output", {}) if isinstance(result, dict) else {})
            if isinstance(output, dict) and output:
                findings.append({
                    "stage_id": stage_id,
                    "snippet": str(list(output.keys())[:3]),
                    "category": "output_keys",
                })
    return findings


def extract_open_questions(
    previous_results: Dict[int, Any],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Extract open questions / requested feedback from prior stages or config.

    Args:
        previous_results: Results from previous stages
        config: Job config with optional open_questions

    Returns:
        List of open question dicts
    """
    questions: List[Dict[str, Any]] = []
    from_config = config.get("open_questions") or config.get("requested_feedback")
    if isinstance(from_config, list):
        for q in from_config:
            questions.append({"text": q.get("text", str(q)), "source": "config", "priority": q.get("priority", "medium")})
    for stage_id in sorted(previous_results.keys()):
        result = previous_results[stage_id]
        output = getattr(result, "output", None) or (result.get("output", {}) if isinstance(result, dict) else {})
        if isinstance(output, dict):
            for key in ("open_questions", "requested_feedback", "recommendations"):
                val = output.get(key)
                if isinstance(val, list):
                    for item in val[:3]:
                        text = item.get("text") or item.get("comment") or str(item)
                        questions.append({"text": text, "source": f"stage_{stage_id}", "priority": "medium"})
    return questions


def build_next_steps_recommendations(
    previous_results: Dict[int, Any],
    handoff_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build recommended next steps with owner and priority.

    Args:
        previous_results: Results from previous stages
        handoff_config: Handoff config with team_roles

    Returns:
        List of next step dicts with action, owner, priority
    """
    steps: List[Dict[str, Any]] = []
    assignments = build_team_assignments(
        handoff_config.get("team_roles") or handoff_config.get("team_config") or [],
        previous_results,
    )
    owners = [a.get("assignee") for a in assignments if a.get("assignee") and a.get("assignee") != "Unassigned"]
    default_owner = owners[0] if owners else "Unassigned"
    steps.append({"action": "Review handoff package and artifacts", "owner": default_owner, "priority": "high"})
    steps.append({"action": "Confirm access and deadlines", "owner": default_owner, "priority": "high"})
    steps.append({"action": "Provide feedback on open questions", "owner": default_owner, "priority": "medium"})
    return steps


# ---------------------------------------------------------------------------
# Integration hooks (payload builders)
# ---------------------------------------------------------------------------

def build_slack_teams_notification_payload(
    handoff_summary: Dict[str, Any],
    channels: List[str],
) -> Dict[str, Any]:
    """Build Slack/Teams notification payload (message text, channel ids).

    Args:
        handoff_summary: Summary dict from handoff
        channels: Channel ids or names

    Returns:
        Dict with message_text, channel_ids, optional blocks
    """
    summary_text = handoff_summary.get("summary") or str(handoff_summary.get("context_transfer", {}).get("summary", "Handoff ready."))
    return {
        "message_text": summary_text[:500],
        "channel_ids": list(channels) if channels else [],
        "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": summary_text[:300]}}],
    }


def build_email_digest(
    handoff_summary: Dict[str, Any],
    recipients: List[str],
) -> Dict[str, Any]:
    """Build email digest (subject, body summary, links).

    Args:
        handoff_summary: Summary dict from handoff
        recipients: Email addresses

    Returns:
        Dict with subject, body, links, recipients
    """
    summary = handoff_summary.get("context_transfer", {}).get("summary", "Collaboration handoff is ready.")
    return {
        "subject": "ResearchFlow: Collaboration handoff ready",
        "body": summary[:1000],
        "links": handoff_summary.get("links", []),
        "recipients": list(recipients) if recipients else [],
    }


def build_calendar_event_payload(
    milestones: List[Dict[str, Any]],
    calendar_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build calendar event payloads (title, start/end, attendees, reminder).

    Args:
        milestones: List from build_deadlines_and_milestones
        calendar_config: Config with attendees, reminder_minutes

    Returns:
        List of event dicts
    """
    attendees = calendar_config.get("attendees") or []
    reminder = calendar_config.get("reminder_minutes") or 60
    events: List[Dict[str, Any]] = []
    for m in milestones:
        due = m.get("due_iso", "")
        events.append({
            "title": m.get("name", "Milestone"),
            "start_iso": due,
            "end_iso": due,
            "attendees": list(attendees),
            "reminder_minutes": reminder,
        })
    return events


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@register_stage
class CollaborationHandoffAgent(BaseStageAgent):
    """Stage 16: Collaboration Handoff.

    Prepares handoff protocols, collaboration setup, context transfer,
    and integration hooks. Optionally calls TypeScript manuscript service.
    """

    stage_id = 16
    stage_name = "Collaboration Handoff"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize CollaborationHandoffAgent."""
        bridge_config = None
        if config and config.get("bridge_url"):
            from ..bridge import BridgeConfig
            bridge_config = BridgeConfig(
                base_url=config["bridge_url"],
                timeout=config.get("bridge_timeout", 30.0),
            )
        super().__init__(bridge_config=bridge_config)

    def get_tools(self) -> List[Any]:
        """Get LangChain tools for this stage."""
        if not LANGCHAIN_AVAILABLE or Tool is None:
            return []
        return [
            Tool(
                name="assign_team_members",
                description="Assign team members to roles. Input: JSON with team_config and optional previous_results.",
                func=self._assign_team_members_tool,
            ),
            Tool(
                name="configure_access",
                description="Configure access permissions. Input: JSON with access_config and job_id.",
                func=self._configure_access_tool,
            ),
            Tool(
                name="set_deadlines",
                description="Set deadlines and milestones. Input: JSON with config and optional base_date.",
                func=self._set_deadlines_tool,
            ),
            Tool(
                name="dispatch_notifications",
                description="Build notification dispatch list. Input: JSON with assignments and channels_config.",
                func=self._dispatch_notifications_tool,
            ),
            Tool(
                name="init_websocket_channel",
                description="Initialize WebSocket channel config. Input: JSON with job_id and participants.",
                func=self._init_websocket_channel_tool,
            ),
            Tool(
                name="setup_realtime_session",
                description="Setup real-time session config. Input: JSON with job_id and artifact_refs.",
                func=self._setup_realtime_session_tool,
            ),
            Tool(
                name="init_comment_threads",
                description="Initialize comment threads. Input: JSON with thread_config.",
                func=self._init_comment_threads_tool,
            ),
            Tool(
                name="generate_stage_summary",
                description="Generate previous stage summary. Input: JSON with previous_results.",
                func=self._generate_stage_summary_tool,
            ),
            Tool(
                name="highlight_findings",
                description="Extract key findings from previous results. Input: JSON with previous_results.",
                func=self._highlight_findings_tool,
            ),
            Tool(
                name="document_open_questions",
                description="Document open questions. Input: JSON with previous_results and config.",
                func=self._document_open_questions_tool,
            ),
            Tool(
                name="recommend_next_steps",
                description="Recommend next steps. Input: JSON with previous_results and handoff_config.",
                func=self._recommend_next_steps_tool,
            ),
            Tool(
                name="notify_slack_teams",
                description="Build Slack/Teams notification payload. Input: JSON with handoff_summary and channels.",
                func=self._notify_slack_teams_tool,
            ),
            Tool(
                name="generate_email_digest",
                description="Generate email digest. Input: JSON with handoff_summary and recipients.",
                func=self._generate_email_digest_tool,
            ),
            Tool(
                name="create_calendar_events",
                description="Build calendar event payloads. Input: JSON with milestones and calendar_config.",
                func=self._create_calendar_events_tool,
            ),
        ]

    def get_prompt_template(self):
        """Get prompt template for collaboration handoff."""
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t):
                    return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        try:
            from langchain_core.prompts import PromptTemplate
        except ImportError:
            from langchain.prompts import PromptTemplate  # type: ignore
        return PromptTemplate.from_template("""You are a Collaboration Handoff Specialist for research projects.

Your task is to:
1. Assign team members and configure access permissions
2. Set deadlines and milestones and build notification dispatch
3. Initialize WebSocket channel, real-time session, and comment threads
4. Generate previous stage summary, highlight findings, document open questions, recommend next steps
5. Build Slack/Teams, email digest, and calendar event payloads

Handoff config summary: {handoff_summary}

Input: {input}

Previous Agent Scratchpad: {agent_scratchpad}
""")

    # Tool implementations
    def _parse_input(self, input_json: str) -> Dict[str, Any]:
        try:
            return json.loads(input_json) if isinstance(input_json, str) else input_json
        except Exception:
            return {}

    def _assign_team_members_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        team_config = data.get("team_config", data.get("team_roles", []))
        previous_results = data.get("previous_results", {})
        out = build_team_assignments(team_config, previous_results)
        return json.dumps({"status": "ok", "assignments": out}, indent=2)

    def _configure_access_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_access_permissions(data.get("access_config", {}), data.get("job_id", ""))
        return json.dumps({"status": "ok", "permissions": out}, indent=2)

    def _set_deadlines_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        base = data.get("base_date")
        if base and isinstance(base, str):
            try:
                base = datetime.fromisoformat(base.replace("Z", "+00:00"))
            except Exception:
                base = None
        out = build_deadlines_and_milestones(data.get("config", {}), base)
        return json.dumps({"status": "ok", "deadlines": out}, indent=2)

    def _dispatch_notifications_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_notification_dispatch_list(
            data.get("assignments", []),
            data.get("channels_config", {}),
        )
        return json.dumps({"status": "ok", "dispatch_list": out}, indent=2)

    def _init_websocket_channel_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_websocket_channel_config(
            data.get("job_id", ""),
            data.get("participants", []),
        )
        return json.dumps({"status": "ok", "channel_config": out}, indent=2)

    def _setup_realtime_session_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_realtime_session_config(
            data.get("job_id", ""),
            data.get("artifact_refs", []),
        )
        return json.dumps({"status": "ok", "session_config": out}, indent=2)

    def _init_comment_threads_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_comment_thread_init(data.get("thread_config", {}))
        return json.dumps({"status": "ok", "threads": out}, indent=2)

    def _generate_stage_summary_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = generate_previous_stage_summary(data.get("previous_results", {}))
        return json.dumps({"status": "ok", "summary": out}, indent=2)

    def _highlight_findings_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = extract_key_findings(data.get("previous_results", {}))
        return json.dumps({"status": "ok", "findings": out}, indent=2)

    def _document_open_questions_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = extract_open_questions(data.get("previous_results", {}), data.get("config", {}))
        return json.dumps({"status": "ok", "open_questions": out}, indent=2)

    def _recommend_next_steps_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_next_steps_recommendations(
            data.get("previous_results", {}),
            data.get("handoff_config", {}),
        )
        return json.dumps({"status": "ok", "next_steps": out}, indent=2)

    def _notify_slack_teams_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_slack_teams_notification_payload(
            data.get("handoff_summary", {}),
            data.get("channels", []),
        )
        return json.dumps({"status": "ok", "payload": out}, indent=2)

    def _generate_email_digest_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_email_digest(data.get("handoff_summary", {}), data.get("recipients", []))
        return json.dumps({"status": "ok", "digest": out}, indent=2)

    def _create_calendar_events_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_calendar_event_payload(
            data.get("milestones", []),
            data.get("calendar_config", {}),
        )
        return json.dumps({"status": "ok", "events": out}, indent=2)

    async def execute(self, context: StageContext) -> StageResult:
        """Execute collaboration handoff: protocols, setup, context transfer, integration hooks."""
        started_at = datetime.utcnow().isoformat() + "Z"
        errors: List[str] = []
        warnings: List[str] = []
        output: Dict[str, Any] = {}

        logger.info(f"Starting Collaboration Handoff for job {context.job_id}")

        config = context.config or {}
        team_config = config.get("team_config") or config.get("team_roles") or DEFAULT_HANDOFF_CONFIG["team_roles"]
        access_config = config.get("access_config") or {}
        channels_config = config.get("channels_config") or {}
        inputs = getattr(context, "inputs", config.get("inputs", {}))

        # Serialize previous_results for helpers (they expect Dict[int, Any])
        prev: Dict[int, Any] = {}
        if context.previous_results:
            for k, v in context.previous_results.items():
                prev[k] = asdict(v) if hasattr(v, "__dataclass_fields__") else v

        # Handoff protocols
        assignments = build_team_assignments(team_config, prev)
        permissions = build_access_permissions(access_config, context.job_id)
        deadlines = build_deadlines_and_milestones(config)
        dispatch_list = build_notification_dispatch_list(assignments, channels_config)
        output["handoff_protocols"] = {
            "assignments": assignments,
            "permissions": permissions,
            "deadlines": deadlines,
            "notification_dispatch": dispatch_list,
        }

        # Collaboration setup
        participants = [a.get("assignee") for a in assignments if a.get("assignee") and a.get("assignee") != "Unassigned"]
        artifact_refs = config.get("artifact_refs") or [f"job-{context.job_id}"]
        output["collaboration_setup"] = {
            "websocket": build_websocket_channel_config(context.job_id, participants),
            "realtime_session": build_realtime_session_config(context.job_id, artifact_refs),
            "comment_threads": build_comment_thread_init(config.get("thread_config") or {}),
        }

        # Context transfer
        summary = generate_previous_stage_summary(prev)
        findings = extract_key_findings(prev)
        open_questions = extract_open_questions(prev, config)
        next_steps = build_next_steps_recommendations(prev, config)
        output["context_transfer"] = {
            "summary": summary,
            "key_findings": findings,
            "open_questions": open_questions,
            "next_steps": next_steps,
        }

        # Integration hooks
        handoff_summary = {"context_transfer": output["context_transfer"], "summary": summary}
        output["integration_hooks"] = {
            "slack_teams": build_slack_teams_notification_payload(
                handoff_summary,
                channels_config.get("channels", []) or DEFAULT_HANDOFF_CONFIG["notification_channels"],
            ),
            "email_digest": build_email_digest(handoff_summary, config.get("recipients", []) or participants),
            "calendar_events": build_calendar_event_payload(deadlines, config.get("calendar_config") or {}),
        }

        # Optional bridge call
        try:
            response = await self.call_manuscript_service(
                service_name="manuscript",
                method_name="runStageCollaborationHandoff",
                params={
                    "job_id": context.job_id,
                    "governance_mode": context.governance_mode,
                    "config": config,
                    "inputs": inputs,
                    "stage_id": self.stage_id,
                    "stage_name": self.stage_name,
                    "handoff_output": output,
                },
            )
            if response:
                output["bridge_response"] = response
        except Exception as e:
            logger.warning(f"Bridge runStageCollaborationHandoff failed: {type(e).__name__}: {e}")
            warnings.append(f"Bridge call failed: {str(e)}. Proceeding with in-memory output.")

        status = "failed" if errors else "completed"
        if context.governance_mode == "DEMO":
            output["demo_mode"] = True
            warnings.append("Running in DEMO mode - handoff is simulated")

        return self.create_stage_result(
            context=context,
            status=status,
            started_at=started_at,
            output=output,
            errors=errors,
            warnings=warnings,
            metadata={
                "governance_mode": context.governance_mode,
                "assignment_count": len(assignments),
                "deadline_count": len(deadlines),
            },
        )
