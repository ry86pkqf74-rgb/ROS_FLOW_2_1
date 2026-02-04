"""
SpecOps Agent - GitHub Synchronization Utilities

This module provides utilities for creating and managing GitHub issues
from Notion PRD requirements, including:
- Creating GitHub issues from requirements
- Mapping PRD phases to milestones
- Managing labels and categorization
- Updating Notion with GitHub issue links

Linear Issues: ROS-105, ROS-106
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from .prd_parser import Requirement, UserStory, AcceptanceCriteria
from .templates import format_template, validate_template_fields

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class GitHubIssue:
    """Represents a GitHub issue to be created."""
    title: str
    body: str
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)
    milestone: Optional[str] = None
    prd_requirement_id: Optional[str] = None
    issue_type: str = "feature"  # feature, bug, task, epic


@dataclass
class Milestone:
    """Represents a GitHub milestone."""
    title: str
    description: str
    due_date: Optional[str] = None
    state: str = "open"


# =============================================================================
# Issue Creator
# =============================================================================

class IssueCreator:
    """Create GitHub issues from parsed requirements."""

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize issue creator.

        Args:
            logger_instance: Optional logger instance
        """
        self.logger = logger_instance or logger

    def create_from_requirement(self, requirement: Requirement) -> GitHubIssue:
        """
        Create a GitHub issue from a requirement.

        Args:
            requirement: Parsed requirement object

        Returns:
            GitHubIssue ready for creation
        """
        self.logger.info(f"Creating issue from requirement: {requirement.title}")

        # Prepare template fields
        fields = self._prepare_fields(requirement)

        # Format template
        body = format_template(requirement.requirement_type, fields)

        # Create issue
        issue = GitHubIssue(
            title=requirement.title,
            body=body,
            labels=self._generate_labels(requirement),
            prd_requirement_id=requirement.id,
            issue_type=requirement.requirement_type
        )

        return issue

    def _prepare_fields(self, requirement: Requirement) -> Dict[str, str]:
        """Prepare fields for template formatting."""
        fields = {
            "title": requirement.title,
            "description": requirement.description,
            "prd_link": requirement.metadata.get("prd_url", "Not specified"),
            "phase": requirement.metadata.get("phase", "Not specified"),
            "story_points": requirement.estimated_effort or "Unknown",
            "complexity": self._estimate_complexity(requirement),
            "labels": ", ".join(requirement.tags),
            "notes": f"From PRD: {requirement.id}",
        }

        # Add user stories
        if requirement.user_stories:
            stories_text = "\n".join([
                f"- As a {s.as_role}, I want to {s.i_want_to}, so that {s.so_that}"
                for s in requirement.user_stories
            ])
            fields["user_story"] = stories_text

        # Add acceptance criteria
        if requirement.acceptance_criteria:
            criteria_text = "\n".join([
                f"- [ ] {c}"
                for c in requirement.acceptance_criteria
            ])
            fields["acceptance_criteria"] = criteria_text

        # Add dependencies
        if requirement.dependencies:
            fields["dependencies"] = "\n".join([
                f"- {d}"
                for d in requirement.dependencies
            ])

        # Bug-specific fields
        if requirement.requirement_type == "bug":
            fields["reproduction_steps"] = self._extract_reproduction_steps(
                requirement
            )
            fields["expected_behavior"] = self._extract_expected_behavior(
                requirement
            )
            fields["actual_behavior"] = self._extract_actual_behavior(
                requirement
            )
            fields["severity"] = requirement.priority or "Unknown"

        # Task-specific fields
        if requirement.requirement_type == "task":
            fields["objectives"] = self._extract_objectives(requirement)
            fields["deliverables"] = self._extract_deliverables(requirement)
            fields["priority"] = requirement.priority or "Unknown"

        # Epic-specific fields
        if requirement.requirement_type == "epic":
            fields["vision"] = requirement.description
            fields["key_features"] = self._extract_key_features(requirement)
            fields["timeline"] = self._estimate_timeline(requirement)

        return fields

    def _generate_labels(self, requirement: Requirement) -> List[str]:
        """Generate GitHub labels for an issue."""
        labels = [requirement.requirement_type]

        # Add priority label
        priority_map = {
            "high": "priority-high",
            "critical": "priority-critical",
            "medium": "priority-medium",
            "low": "priority-low",
        }
        priority_label = priority_map.get(
            requirement.priority.lower() if requirement.priority else "medium"
        )
        if priority_label:
            labels.append(priority_label)

        # Add custom tags
        labels.extend(requirement.tags)

        # Add component labels
        for component in requirement.related_components:
            labels.append(f"component/{component}")

        return labels

    def _estimate_complexity(self, requirement: Requirement) -> str:
        """Estimate complexity level."""
        if requirement.estimated_effort:
            effort = requirement.estimated_effort.lower()
            if any(x in effort for x in ["simple", "small", "easy", "1", "2"]):
                return "low"
            elif any(x in effort for x in ["medium", "3", "4", "5"]):
                return "medium"
            elif any(x in effort for x in ["complex", "high", "hard", "8", "13", "21"]):
                return "high"

        return "medium"

    def _extract_reproduction_steps(self, requirement: Requirement) -> str:
        """Extract reproduction steps from requirement."""
        # Try to find numbered list in description
        import re
        pattern = r"(?:steps?|reproduction)[\s:]*((?:\d+\..+\n?)+)"
        match = re.search(pattern, requirement.description, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "1. Step 1\n2. Step 2\n3. Step 3"

    def _extract_expected_behavior(self, requirement: Requirement) -> str:
        """Extract expected behavior from requirement."""
        import re
        pattern = r"(?:expected|should)[\s:]*(.*?)(?:\n\n|expected|actual|$)"
        match = re.search(pattern, requirement.description, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return "Describe expected behavior"

    def _extract_actual_behavior(self, requirement: Requirement) -> str:
        """Extract actual behavior from requirement."""
        import re
        pattern = r"(?:actual|currently)[\s:]*(.*?)(?:\n\n|severity|$)"
        match = re.search(pattern, requirement.description, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return "Describe actual behavior"

    def _extract_objectives(self, requirement: Requirement) -> str:
        """Extract task objectives from requirement."""
        import re
        pattern = r"(?:objectives?|goals?)[\s:]*((?:\-.*\n?)+)"
        match = re.search(pattern, requirement.description, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "- Objective 1\n- Objective 2"

    def _extract_deliverables(self, requirement: Requirement) -> str:
        """Extract deliverables from requirement."""
        import re
        pattern = r"(?:deliverables?)[\s:]*((?:\-.*\n?)+)"
        match = re.search(pattern, requirement.description, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "- Deliverable 1\n- Deliverable 2"

    def _extract_key_features(self, requirement: Requirement) -> str:
        """Extract key features for epic from requirement."""
        import re
        pattern = r"(?:features?|capabilities?)[\s:]*((?:\-.*\n?)+)"
        match = re.search(pattern, requirement.description, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "- Feature 1\n- Feature 2\n- Feature 3"

    def _estimate_timeline(self, requirement: Requirement) -> str:
        """Estimate timeline for epic."""
        effort = requirement.estimated_effort or "Unknown"
        if "weeks" in effort.lower():
            return f"Estimated duration: {effort}"
        elif "months" in effort.lower():
            return f"Estimated duration: {effort}"
        return "Timeline: TBD"


# =============================================================================
# Label Manager
# =============================================================================

class LabelManager:
    """Manage and apply GitHub labels."""

    # Standard labels
    STANDARD_LABELS = {
        # Type labels
        "feature": {"color": "7366bd", "description": "New feature"},
        "bug": {"color": "b60205", "description": "Bug report"},
        "task": {"color": "ffd700", "description": "Technical task"},
        "epic": {"color": "c2e0c6", "description": "Epic initiative"},
        "docs": {"color": "0075ca", "description": "Documentation"},

        # Priority labels
        "priority-critical": {"color": "ff0000", "description": "Critical priority"},
        "priority-high": {"color": "ff7700", "description": "High priority"},
        "priority-medium": {"color": "ffff00", "description": "Medium priority"},
        "priority-low": {"color": "dddddd", "description": "Low priority"},

        # Status labels
        "status-in-progress": {"color": "006b75", "description": "In progress"},
        "status-blocked": {"color": "d73a49", "description": "Blocked"},
        "status-review": {"color": "0052cc", "description": "Under review"},
        "status-done": {"color": "28a745", "description": "Completed"},

        # Component labels (will be dynamically created with prefix)
        # Component labels should be added as needed
    }

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize label manager.

        Args:
            logger_instance: Optional logger instance
        """
        self.logger = logger_instance or logger

    def get_standard_labels(self) -> Dict[str, Dict[str, str]]:
        """Get all standard labels."""
        return self.STANDARD_LABELS.copy()

    def create_component_label(self, component: str) -> Tuple[str, Dict[str, str]]:
        """
        Create a component-specific label.

        Args:
            component: Component name

        Returns:
            Tuple of (label_name, label_config)
        """
        label_name = f"component/{component}".lower()
        label_config = {
            "color": "cccccc",
            "description": f"Related to {component} component"
        }
        return label_name, label_config

    def validate_labels(self, labels: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate labels against standard set.

        Args:
            labels: List of labels to validate

        Returns:
            Tuple of (valid_labels, warnings)
        """
        valid = []
        warnings = []

        for label in labels:
            if label in self.STANDARD_LABELS or label.startswith("component/"):
                valid.append(label)
            else:
                warnings.append(f"Unknown label: {label}")

        return valid, warnings


# =============================================================================
# Milestone Mapper
# =============================================================================

class MilestoneMapper:
    """Map PRD phases to GitHub milestones."""

    # Default phase to milestone mapping
    PHASE_MILESTONE_MAP = {
        "phase_1": {"title": "Phase 1: Discovery", "weeks": 2},
        "phase_2": {"title": "Phase 2: Design", "weeks": 3},
        "phase_3": {"title": "Phase 3: Development", "weeks": 6},
        "phase_4": {"title": "Phase 4: Testing", "weeks": 2},
        "phase_5": {"title": "Phase 5: Launch", "weeks": 1},
    }

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize milestone mapper.

        Args:
            logger_instance: Optional logger instance
        """
        self.logger = logger_instance or logger

    def map_requirement_to_milestone(
        self,
        requirement: Requirement
    ) -> Optional[Milestone]:
        """
        Map a requirement to a milestone.

        Args:
            requirement: Parsed requirement

        Returns:
            Milestone or None
        """
        phase = requirement.metadata.get("phase", "").lower()

        if not phase:
            return None

        # Try to find matching phase
        milestone_config = self.PHASE_MILESTONE_MAP.get(phase)
        if not milestone_config:
            # Try partial match
            for key, config in self.PHASE_MILESTONE_MAP.items():
                if key.replace("_", " ") in phase or phase in key:
                    milestone_config = config
                    break

        if milestone_config:
            due_date = self._calculate_due_date(
                milestone_config.get("weeks", 4)
            )
            return Milestone(
                title=milestone_config["title"],
                description=f"Phase for requirement: {requirement.title}",
                due_date=due_date
            )

        return None

    def _calculate_due_date(self, weeks: int) -> str:
        """Calculate due date based on weeks."""
        due = datetime.now() + timedelta(weeks=weeks)
        return due.strftime("%Y-%m-%d")

    def create_custom_milestone(
        self,
        phase_name: str,
        description: str,
        weeks: int = 4
    ) -> Milestone:
        """
        Create a custom milestone.

        Args:
            phase_name: Name of the phase
            description: Phase description
            weeks: Duration in weeks

        Returns:
            Milestone object
        """
        return Milestone(
            title=phase_name,
            description=description,
            due_date=self._calculate_due_date(weeks)
        )


# =============================================================================
# Notion Link Updater
# =============================================================================

class NotionLinkUpdater:
    """Update Notion pages with GitHub issue links."""

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize Notion link updater.

        Args:
            logger_instance: Optional logger instance
        """
        self.logger = logger_instance or logger

    def create_issue_link_update(
        self,
        requirement_id: str,
        github_issue_number: int,
        github_url: str,
        repository: str
    ) -> Dict[str, Any]:
        """
        Create an update payload for Notion.

        Args:
            requirement_id: PRD requirement ID
            github_issue_number: GitHub issue number
            github_url: Full GitHub issue URL
            repository: Repository name

        Returns:
            Update payload for Notion
        """
        return {
            "requirement_id": requirement_id,
            "github_issue": {
                "number": github_issue_number,
                "url": github_url,
                "repository": repository,
                "linked_at": datetime.now().isoformat(),
            }
        }

    def batch_update_links(
        self,
        updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Prepare batch updates for Notion.

        Args:
            updates: List of individual updates

        Returns:
            Batch update payload
        """
        return {
            "updates": updates,
            "total": len(updates),
            "timestamp": datetime.now().isoformat(),
        }
