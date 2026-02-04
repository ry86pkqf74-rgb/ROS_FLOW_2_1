"""
Release Validators - Validation utilities for gate checks

Implements validators for GitHub CI status, evidence pack hashing,
Notion signoffs, and deployment mode determination.

Linear Issue: ROS-150
"""

import os
import hashlib
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# GitHub CI Validator
# =============================================================================

class GitHubCIValidator:
    """Validates GitHub Actions CI status."""

    async def check_ci_status(
        self,
        token: str,
        owner: str,
        repo: str,
        branch: str = "main",
        commit: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Check GitHub Actions CI status.

        Args:
            token: GitHub API token
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            commit: Optional specific commit SHA

        Returns:
            List of check results with status and conclusion
        """
        try:
            import httpx

            if not token:
                logger.warning("No GitHub token provided for CI check")
                return []

            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            # Get latest run for the branch
            runs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
            async with httpx.AsyncClient() as client:
                runs_response = await client.get(
                    runs_url,
                    headers=headers,
                    params={"branch": branch, "per_page": 1},
                )

                if runs_response.status_code != 200:
                    logger.error(
                        f"GitHub API error: {runs_response.status_code}: "
                        f"{runs_response.text}"
                    )
                    return []

                runs_data = runs_response.json()
                if not runs_data.get("workflow_runs"):
                    logger.warning(f"No runs found for {owner}/{repo} on {branch}")
                    return []

                latest_run = runs_data["workflow_runs"][0]
                run_id = latest_run["id"]
                run_conclusion = latest_run.get("conclusion")

                # Get check runs for this workflow run
                checks_url = (
                    f"https://api.github.com/repos/{owner}/{repo}/check-runs"
                )
                checks_response = await client.get(
                    checks_url,
                    headers=headers,
                    params={"check_run_type": "all"},
                )

                if checks_response.status_code != 200:
                    return [
                        {
                            "name": "workflow_run",
                            "passed": run_conclusion == "success",
                            "status": latest_run.get("status"),
                            "conclusion": run_conclusion,
                            "run_id": run_id,
                        }
                    ]

                checks_data = checks_response.json()
                checks = []

                for check in checks_data.get("check_runs", []):
                    checks.append(
                        {
                            "name": check.get("name"),
                            "passed": check.get("conclusion") == "success",
                            "status": check.get("status"),
                            "conclusion": check.get("conclusion"),
                            "url": check.get("html_url"),
                        }
                    )

                return checks if checks else [
                    {
                        "name": "workflow_run",
                        "passed": run_conclusion == "success",
                        "status": latest_run.get("status"),
                        "conclusion": run_conclusion,
                    }
                ]

        except Exception as e:
            logger.error(f"CI status check error: {e}")
            return []


# =============================================================================
# Evidence Hash Validator
# =============================================================================

class EvidenceHashValidator:
    """Validates evidence pack existence and computes/verifies hashes."""

    async def verify_and_hash_pack(
        self, pack_path: str, hash_algorithm: str = "sha256"
    ) -> Dict[str, Any]:
        """
        Verify evidence pack exists and compute its hash.

        Args:
            pack_path: Path to evidence pack (file or directory)
            hash_algorithm: Hash algorithm to use (sha256, sha512)

        Returns:
            Dictionary with pack info: exists, hash, size, created, modified
        """
        try:
            path = Path(pack_path)

            if not path.exists():
                return {
                    "exists": False,
                    "path": str(path),
                    "error": "Path does not exist",
                }

            # Handle file
            if path.is_file():
                file_hash = await self._compute_file_hash(path, hash_algorithm)
                stat = path.stat()

                return {
                    "exists": True,
                    "path": str(path),
                    "hash": file_hash,
                    "size": stat.st_size,
                    "type": "file",
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }

            # Handle directory
            if path.is_dir():
                dir_hash = await self._compute_directory_hash(path, hash_algorithm)
                file_count = sum(1 for _ in path.rglob("*") if _.is_file())
                dir_size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

                stat = path.stat()
                return {
                    "exists": True,
                    "path": str(path),
                    "hash": dir_hash,
                    "size": dir_size,
                    "file_count": file_count,
                    "type": "directory",
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }

        except Exception as e:
            logger.error(f"Evidence pack hash error: {e}")
            return {
                "exists": False,
                "path": str(pack_path),
                "error": str(e),
            }

    async def _compute_file_hash(
        self, file_path: Path, algorithm: str = "sha256"
    ) -> str:
        """Compute hash of a single file."""
        hasher = hashlib.new(algorithm)
        chunk_size = 8192

        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)

        return hasher.hexdigest()

    async def _compute_directory_hash(
        self, dir_path: Path, algorithm: str = "sha256"
    ) -> str:
        """Compute combined hash of directory contents."""
        hasher = hashlib.new(algorithm)

        # Process files in sorted order for consistency
        files = sorted(
            [f for f in dir_path.rglob("*") if f.is_file()],
            key=lambda p: str(p),
        )

        for file_path in files:
            # Hash file path relative to root
            rel_path = file_path.relative_to(dir_path)
            hasher.update(str(rel_path).encode("utf-8"))

            # Hash file contents
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)

        return hasher.hexdigest()


# =============================================================================
# Notion Signoff Validator
# =============================================================================

class NotionSignoffValidator:
    """Validates signoffs via Notion database."""

    async def check_release_signoffs(
        self,
        notion_token: str,
        database_id: str,
        release_id: str,
    ) -> Dict[str, Any]:
        """
        Check release signoff status in Notion.

        Args:
            notion_token: Notion API token
            database_id: Notion database ID for signoffs
            release_id: Release identifier to look up

        Returns:
            Dictionary with signoff status and required signers
        """
        try:
            import httpx

            if not notion_token:
                logger.warning("No Notion token provided for signoff check")
                return {
                    "complete": False,
                    "error": "Missing Notion token",
                }

            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            }

            # Query Notion database for release
            query_url = f"https://api.notion.com/v1/databases/{database_id}/query"

            query_body = {
                "filter": {
                    "property": "Release ID",
                    "rich_text": {"equals": release_id},
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    query_url,
                    headers=headers,
                    json=query_body,
                )

                if response.status_code != 200:
                    logger.error(
                        f"Notion API error: {response.status_code}: {response.text}"
                    )
                    return {
                        "complete": False,
                        "error": f"API error: {response.status_code}",
                    }

                data = response.json()
                results = data.get("results", [])

                if not results:
                    return {
                        "complete": False,
                        "error": f"Release {release_id} not found in Notion",
                    }

                # Extract signoff status from first result
                release_page = results[0]
                properties = release_page.get("properties", {})

                signoffs = {
                    "product_owner": self._extract_checkbox(
                        properties.get("Product Owner Signoff")
                    ),
                    "security": self._extract_checkbox(
                        properties.get("Security Review")
                    ),
                    "qa": self._extract_checkbox(
                        properties.get("QA Sign-off")
                    ),
                    "deployment": self._extract_checkbox(
                        properties.get("Deployment Readiness")
                    ),
                }

                complete = all(signoffs.values())

                return {
                    "complete": complete,
                    "release_id": release_id,
                    "signoffs": signoffs,
                    "page_url": release_page.get("url"),
                }

        except Exception as e:
            logger.error(f"Notion signoff check error: {e}")
            return {
                "complete": False,
                "error": str(e),
            }

    def _extract_checkbox(self, property_value: Optional[Dict[str, Any]]) -> bool:
        """Extract checkbox value from Notion property."""
        if not property_value:
            return False
        return property_value.get("checkbox", False)


# =============================================================================
# Deployment Mode Validator
# =============================================================================

class DeploymentModeValidator:
    """Determines deployment mode (DEMO vs LIVE)."""

    @staticmethod
    def determine_mode(context: Dict[str, Any]) -> str:
        """
        Determine deployment mode based on context.

        Args:
            context: Release context

        Returns:
            "LIVE" or "DEMO"
        """
        # Explicit mode in context
        if "deployment_mode" in context:
            mode = context["deployment_mode"].upper()
            if mode in ["LIVE", "DEMO"]:
                return mode

        # Check branch - main/master = LIVE, others = DEMO
        branch = context.get("branch", "develop").lower()
        if branch in ["main", "master", "production"]:
            return "LIVE"

        # Check deployment target
        target = context.get("target", "").lower()
        if "prod" in target or "production" in target:
            return "LIVE"

        # Default to DEMO
        return "DEMO"

    @staticmethod
    def get_mode_requirements(mode: str) -> Dict[str, Any]:
        """
        Get requirements specific to deployment mode.

        Args:
            mode: Deployment mode

        Returns:
            Dictionary of mode-specific requirements
        """
        if mode.upper() == "LIVE":
            return {
                "require_faves": True,
                "require_rollback_test": True,
                "require_security_review": True,
                "require_monitoring": True,
                "require_signoffs": True,
                "notification_level": "URGENT",
            }
        else:  # DEMO
            return {
                "require_faves": False,
                "require_rollback_test": False,
                "require_security_review": False,
                "require_monitoring": True,
                "require_signoffs": False,
                "notification_level": "INFO",
            }
