"""
Improvement Loop Service for version tracking and diff computation.

Provides functionality for:
- Creating version snapshots of agent outputs
- Computing diffs between versions
- Reverting to previous versions
- Tracking improvement history

All versions are persisted via the orchestrator's version control API.

See: Linear ROS-66 (Phase C: Improvement Loop System)
"""

import difflib
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import json
import hashlib
import logging

import httpx

from ..base.state import VersionSnapshot

logger = logging.getLogger(__name__)


@dataclass
class ImprovementLoop:
    """
    Tracks the improvement loop for an artifact.

    Attributes:
        id: Unique improvement loop ID
        artifact_id: ID of the artifact being improved
        agent_id: Agent performing improvements
        project_id: Associated project ID
        current_version_id: ID of the current version
        versions: List of all version snapshots
        max_iterations: Maximum allowed iterations
        current_iteration: Current iteration count
        status: Loop status (active/complete/reverted)
    """
    id: str
    artifact_id: str
    agent_id: str
    project_id: str
    current_version_id: str = ""
    versions: List[VersionSnapshot] = field(default_factory=list)
    max_iterations: int = 5
    current_iteration: int = 0
    status: str = "active"  # active, complete, reverted
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ImprovementService:
    """
    Service for managing improvement loops and version tracking.

    Provides:
    - Version snapshot creation
    - Diff computation between versions
    - Version history retrieval
    - Revert functionality
    """

    def __init__(
        self,
        orchestrator_url: str,
        auth_token: Optional[str] = None,
    ):
        """
        Initialize the improvement service.

        Args:
            orchestrator_url: URL of the orchestrator service
            auth_token: Optional authentication token
        """
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.auth_token = auth_token
        self._improvement_loops: Dict[str, ImprovementLoop] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for orchestrator requests."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]

    async def create_snapshot(
        self,
        artifact_id: str,
        content: str,
        agent_id: str,
        project_id: str,
        quality_score: float = 0.0,
        improvement_request: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VersionSnapshot:
        """
        Create a version snapshot of agent output.

        Args:
            artifact_id: ID of the artifact
            content: Content to snapshot
            agent_id: Agent that created this version
            project_id: Associated project ID
            quality_score: Quality gate score
            improvement_request: Feedback that triggered this version
            metadata: Additional metadata

        Returns:
            Created VersionSnapshot
        """
        timestamp = datetime.utcnow().isoformat()
        version_id = f"v_{self._compute_content_hash(content)}_{timestamp.replace(':', '-').replace('.', '-')}"

        # Compute changes from previous version
        changes = []
        loop = self._get_or_create_loop(artifact_id, agent_id, project_id)

        if loop.versions:
            previous = loop.versions[-1]
            changes = self._compute_changes(previous["output"], content)

        snapshot: VersionSnapshot = {
            "version_id": version_id,
            "timestamp": timestamp,
            "output": content,
            "quality_score": quality_score,
            "improvement_request": improvement_request,
            "changes": changes,
        }

        # Add to local loop
        loop.versions.append(snapshot)
        loop.current_version_id = version_id
        loop.current_iteration += 1
        loop.updated_at = timestamp

        # Check if we've hit max iterations
        if loop.current_iteration >= loop.max_iterations:
            loop.status = "complete"

        self._improvement_loops[artifact_id] = loop

        # Persist to orchestrator
        try:
            await self._save_to_orchestrator(artifact_id, snapshot, metadata)
        except Exception as e:
            logger.warning(f"Failed to persist snapshot to orchestrator: {e}")

        logger.info(
            f"Created version snapshot",
            extra={
                "artifact_id": artifact_id,
                "version_id": version_id,
                "iteration": loop.current_iteration,
                "quality_score": quality_score,
            }
        )

        return snapshot

    async def get_diff(
        self,
        artifact_id: str,
        version_old: str,
        version_new: str,
        context_lines: int = 3,
    ) -> str:
        """
        Compute diff between two versions.

        Args:
            artifact_id: ID of the artifact
            version_old: ID of the old version
            version_new: ID of the new version
            context_lines: Number of context lines to include

        Returns:
            Unified diff string
        """
        loop = self._improvement_loops.get(artifact_id)
        if not loop:
            return ""

        old_content = None
        new_content = None

        for version in loop.versions:
            if version["version_id"] == version_old:
                old_content = version["output"]
            if version["version_id"] == version_new:
                new_content = version["output"]

        if old_content is None or new_content is None:
            return ""

        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"version: {version_old}",
            tofile=f"version: {version_new}",
            n=context_lines,
        )

        return "".join(diff)

    async def get_latest_diff(
        self,
        artifact_id: str,
        context_lines: int = 3,
    ) -> str:
        """
        Get diff between the two most recent versions.

        Args:
            artifact_id: ID of the artifact
            context_lines: Number of context lines

        Returns:
            Unified diff string
        """
        loop = self._improvement_loops.get(artifact_id)
        if not loop or len(loop.versions) < 2:
            return ""

        return await self.get_diff(
            artifact_id,
            loop.versions[-2]["version_id"],
            loop.versions[-1]["version_id"],
            context_lines,
        )

    async def revert_to(
        self,
        artifact_id: str,
        version_id: str,
    ) -> Optional[VersionSnapshot]:
        """
        Revert artifact to a previous version.

        Args:
            artifact_id: ID of the artifact
            version_id: ID of the version to revert to

        Returns:
            The reverted VersionSnapshot, or None if not found
        """
        loop = self._improvement_loops.get(artifact_id)
        if not loop:
            logger.warning(f"No improvement loop found for artifact: {artifact_id}")
            return None

        # Find the version to revert to
        target_version = None
        target_index = -1

        for i, version in enumerate(loop.versions):
            if version["version_id"] == version_id:
                target_version = version
                target_index = i
                break

        if target_version is None:
            logger.warning(f"Version not found: {version_id}")
            return None

        # Create a new snapshot based on the old version
        timestamp = datetime.utcnow().isoformat()
        new_version_id = f"v_revert_{self._compute_content_hash(target_version['output'])}_{timestamp.replace(':', '-')}"

        reverted_snapshot: VersionSnapshot = {
            "version_id": new_version_id,
            "timestamp": timestamp,
            "output": target_version["output"],
            "quality_score": target_version["quality_score"],
            "improvement_request": f"Reverted to version: {version_id}",
            "changes": [f"Reverted to version {target_index + 1} of {len(loop.versions)}"],
        }

        # Add to versions list
        loop.versions.append(reverted_snapshot)
        loop.current_version_id = new_version_id
        loop.status = "reverted"
        loop.updated_at = timestamp

        self._improvement_loops[artifact_id] = loop

        logger.info(
            f"Reverted artifact to version",
            extra={
                "artifact_id": artifact_id,
                "reverted_to": version_id,
                "new_version_id": new_version_id,
            }
        )

        return reverted_snapshot

    async def get_version_history(
        self,
        artifact_id: str,
        limit: Optional[int] = None,
    ) -> List[VersionSnapshot]:
        """
        Get version history for an artifact.

        Args:
            artifact_id: ID of the artifact
            limit: Maximum number of versions to return

        Returns:
            List of VersionSnapshots, most recent first
        """
        loop = self._improvement_loops.get(artifact_id)
        if not loop:
            return []

        versions = list(reversed(loop.versions))

        if limit:
            versions = versions[:limit]

        return versions

    async def get_improvement_loop(
        self,
        artifact_id: str,
    ) -> Optional[ImprovementLoop]:
        """
        Get the improvement loop for an artifact.

        Args:
            artifact_id: ID of the artifact

        Returns:
            ImprovementLoop if found, None otherwise
        """
        return self._improvement_loops.get(artifact_id)

    async def complete_loop(
        self,
        artifact_id: str,
    ) -> Optional[ImprovementLoop]:
        """
        Mark an improvement loop as complete.

        Args:
            artifact_id: ID of the artifact

        Returns:
            Updated ImprovementLoop
        """
        loop = self._improvement_loops.get(artifact_id)
        if not loop:
            return None

        loop.status = "complete"
        loop.updated_at = datetime.utcnow().isoformat()

        self._improvement_loops[artifact_id] = loop

        logger.info(
            f"Completed improvement loop",
            extra={
                "artifact_id": artifact_id,
                "final_iteration": loop.current_iteration,
                "total_versions": len(loop.versions),
            }
        )

        return loop

    async def can_continue_improvement(
        self,
        artifact_id: str,
    ) -> bool:
        """
        Check if improvement loop can continue.

        Args:
            artifact_id: ID of the artifact

        Returns:
            True if more iterations are allowed
        """
        loop = self._improvement_loops.get(artifact_id)
        if not loop:
            return True  # New loop can start

        return (
            loop.status == "active" and
            loop.current_iteration < loop.max_iterations
        )

    def _get_or_create_loop(
        self,
        artifact_id: str,
        agent_id: str,
        project_id: str,
    ) -> ImprovementLoop:
        """Get existing loop or create a new one."""
        if artifact_id in self._improvement_loops:
            return self._improvement_loops[artifact_id]

        loop = ImprovementLoop(
            id=f"loop_{artifact_id}_{datetime.utcnow().timestamp()}",
            artifact_id=artifact_id,
            agent_id=agent_id,
            project_id=project_id,
        )
        self._improvement_loops[artifact_id] = loop
        return loop

    def _compute_changes(self, old_content: str, new_content: str) -> List[str]:
        """Compute summary of changes between versions."""
        changes = []

        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        additions = 0
        deletions = 0
        modifications = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                additions += j2 - j1
            elif tag == 'delete':
                deletions += i2 - i1
            elif tag == 'replace':
                modifications += max(i2 - i1, j2 - j1)

        if additions > 0:
            changes.append(f"+{additions} lines added")
        if deletions > 0:
            changes.append(f"-{deletions} lines removed")
        if modifications > 0:
            changes.append(f"~{modifications} lines modified")

        return changes

    async def _save_to_orchestrator(
        self,
        artifact_id: str,
        snapshot: VersionSnapshot,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist snapshot to orchestrator's version control."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.orchestrator_url}/api/version-control/versions",
                    headers=self._get_headers(),
                    json={
                        "artifactId": artifact_id,
                        "versionId": snapshot["version_id"],
                        "content": snapshot["output"],
                        "qualityScore": snapshot["quality_score"],
                        "improvementRequest": snapshot.get("improvement_request"),
                        "changes": snapshot.get("changes", []),
                        "metadata": metadata or {},
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to save to orchestrator: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error saving to orchestrator: {e}")
            raise


def create_improvement_service(
    orchestrator_url: str = "http://localhost:4000",
    auth_token: Optional[str] = None,
) -> ImprovementService:
    """
    Factory function to create an improvement service.

    Args:
        orchestrator_url: URL of the orchestrator service
        auth_token: Optional authentication token

    Returns:
        Configured ImprovementService instance
    """
    return ImprovementService(
        orchestrator_url=orchestrator_url,
        auth_token=auth_token,
    )
