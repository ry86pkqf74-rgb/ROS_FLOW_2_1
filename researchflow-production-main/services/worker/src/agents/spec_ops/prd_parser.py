"""
SpecOps Agent - PRD Parsing Utilities

This module provides utilities for parsing and extracting structured data
from Notion PRD (Product Requirements Document) pages, including:
- Requirements extraction
- Acceptance criteria parsing
- User story generation
- Structured data normalization

Linear Issues: ROS-105, ROS-106
"""

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Requirement:
    """Represents a single requirement from a PRD."""
    id: str
    title: str
    description: str
    requirement_type: str  # feature, bug, task, epic
    priority: str  # high, medium, low
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    user_stories: List[str] = field(default_factory=list)
    estimated_effort: Optional[str] = None
    related_components: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserStory:
    """Represents a user story in INVEST format."""
    as_role: str  # "As a..."
    i_want_to: str  # "I want to..."
    so_that: str  # "So that..."
    acceptance_criteria: List[str] = field(default_factory=list)


@dataclass
class AcceptanceCriteria:
    """Represents acceptance criteria for a requirement."""
    criteria: List[str]
    definition_of_done: Optional[str] = None
    test_scenarios: List[str] = field(default_factory=list)


# =============================================================================
# Abstract Parsers
# =============================================================================

class BaseParser(ABC):
    """Base class for all parsers."""

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize parser.

        Args:
            logger_instance: Optional logger instance
        """
        self.logger = logger_instance or logger

    @abstractmethod
    def parse(self, content: str) -> Any:
        """Parse content and return structured data."""
        pass


# =============================================================================
# Requirement Extractor
# =============================================================================

class RequirementExtractor(BaseParser):
    """Extract and normalize requirements from text."""

    # Pattern definitions
    REQUIREMENT_PATTERN = re.compile(
        r"^#{1,3}\s+(.+?)$",
        re.MULTILINE
    )
    PRIORITY_PATTERN = re.compile(
        r"\b(high|critical|medium|low|p[0-5])\b",
        re.IGNORECASE
    )
    TAG_PATTERN = re.compile(r"#[\w-]+")
    DEPENDENCY_PATTERN = re.compile(r"(?:depends?\s+on|blocked?\s+by):\s*(.+)")

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """Initialize requirement extractor."""
        super().__init__(logger_instance)
        self.requirement_counter = 0

    def parse(self, content: str) -> List[Requirement]:
        """
        Parse content and extract requirements.

        Args:
            content: Raw text content from PRD

        Returns:
            List of parsed requirements
        """
        requirements = []
        sections = self._split_sections(content)

        for section in sections:
            try:
                req = self._extract_requirement(section)
                if req:
                    requirements.append(req)
            except Exception as e:
                self.logger.warning(f"Failed to parse section: {e}")

        return requirements

    def _split_sections(self, content: str) -> List[str]:
        """Split content into requirement sections."""
        sections = self.REQUIREMENT_PATTERN.split(content)
        # Pair headers with their content
        paired = []
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                paired.append(f"# {sections[i]}\n{sections[i+1]}")
        return paired

    def _extract_requirement(self, section: str) -> Optional[Requirement]:
        """Extract requirement from a single section."""
        lines = section.strip().split("\n")
        if not lines:
            return None

        # Extract title
        title_match = self.REQUIREMENT_PATTERN.match(lines[0])
        if not title_match:
            return None

        title = title_match.group(1).strip()
        content = "\n".join(lines[1:])

        # Extract priority
        priority = self._extract_priority(content)

        # Extract tags
        tags = self._extract_tags(content)

        # Extract dependencies
        dependencies = self._extract_dependencies(content)

        self.requirement_counter += 1
        req_id = f"REQ-{self.requirement_counter}"

        return Requirement(
            id=req_id,
            title=title,
            description=content,
            requirement_type=self._infer_type(title, content),
            priority=priority,
            tags=tags,
            dependencies=dependencies,
        )

    def _extract_priority(self, content: str) -> str:
        """Extract priority level from content."""
        match = self.PRIORITY_PATTERN.search(content)
        if match:
            priority = match.group(1).lower()
            # Normalize priority levels
            if priority.startswith("p"):
                return f"p{priority[-1]}"
            elif priority == "critical":
                return "high"
            return priority
        return "medium"

    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content."""
        return self.TAG_PATTERN.findall(content)

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract dependency references from content."""
        dependencies = []
        for match in self.DEPENDENCY_PATTERN.finditer(content):
            dep_text = match.group(1)
            deps = [d.strip() for d in dep_text.split(",")]
            dependencies.extend(deps)
        return dependencies

    def _infer_type(self, title: str, content: str) -> str:
        """Infer requirement type from title and content."""
        title_lower = title.lower()
        content_lower = content.lower()

        if any(word in title_lower for word in ["epic", "initiative", "program"]):
            return "epic"
        elif any(word in title_lower for word in ["bug", "fix", "issue", "error"]):
            return "bug"
        elif any(word in title_lower for word in ["task", "refactor", "refactoring", "cleanup"]):
            return "task"
        elif any(word in title_lower for word in ["feature", "implement", "add", "new"]):
            return "feature"

        # Fallback: check content
        if "reproduction" in content_lower or "steps to reproduce" in content_lower:
            return "bug"
        if "epic" in content_lower or "initiative" in content_lower:
            return "epic"

        return "feature"


# =============================================================================
# Acceptance Criteria Parser
# =============================================================================

class AcceptanceCriteriaParser(BaseParser):
    """Parse acceptance criteria from requirement descriptions."""

    CRITERIA_SECTION_PATTERN = re.compile(
        r"(?:acceptance\s+criteria|given-when-then|gherkin)[\s:]*\n(.+?)(?=\n\n|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    CHECKLIST_PATTERN = re.compile(r"^\s*[-*✓x\[\]]\s+(.+?)$", re.MULTILINE)
    BDD_PATTERN = re.compile(
        r"(?:given|when|then)\s+(.+?)(?=\n\s*(?:given|when|then)|$)",
        re.IGNORECASE
    )

    def parse(self, content: str) -> AcceptanceCriteria:
        """
        Parse acceptance criteria from content.

        Args:
            content: Content containing acceptance criteria

        Returns:
            AcceptanceCriteria object
        """
        criteria_list = []

        # Try to find explicit criteria section
        section_match = self.CRITERIA_SECTION_PATTERN.search(content)
        if section_match:
            criteria_text = section_match.group(1)

            # Try BDD format first
            bdd_criteria = self._parse_bdd_format(criteria_text)
            if bdd_criteria:
                criteria_list.extend(bdd_criteria)
            else:
                # Try checklist format
                checklist_criteria = self._parse_checklist_format(criteria_text)
                criteria_list.extend(checklist_criteria)

        # If no explicit criteria found, try to extract from content
        if not criteria_list:
            criteria_list = self._extract_implicit_criteria(content)

        definition_of_done = self._extract_definition_of_done(content)

        return AcceptanceCriteria(
            criteria=criteria_list,
            definition_of_done=definition_of_done,
            test_scenarios=self._extract_test_scenarios(content)
        )

    def _parse_bdd_format(self, content: str) -> List[str]:
        """Parse BDD (Given-When-Then) format criteria."""
        criteria = []
        matches = self.BDD_PATTERN.findall(content)
        for match in matches:
            if match.strip():
                criteria.append(match.strip())
        return criteria

    def _parse_checklist_format(self, content: str) -> List[str]:
        """Parse checklist format criteria."""
        criteria = []
        matches = self.CHECKLIST_PATTERN.findall(content)
        for match in matches:
            if match.strip():
                criteria.append(match.strip())
        return criteria

    def _extract_implicit_criteria(self, content: str) -> List[str]:
        """Extract criteria from unstructured content."""
        criteria = []
        sentences = re.split(r"[.!?]+", content)

        for sentence in sentences:
            sentence = sentence.strip()
            if any(word in sentence.lower() for word in ["must", "should", "will", "shall"]):
                if len(sentence) > 20:  # Minimum length filter
                    criteria.append(sentence)

        return criteria[:5]  # Limit to 5 criteria

    def _extract_definition_of_done(self, content: str) -> Optional[str]:
        """Extract definition of done from content."""
        pattern = re.compile(
            r"definition\s+of\s+done[\s:]*\n(.+?)(?=\n\n|\Z)",
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        match = pattern.search(content)
        return match.group(1).strip() if match else None

    def _extract_test_scenarios(self, content: str) -> List[str]:
        """Extract test scenarios from content."""
        scenarios = []
        pattern = re.compile(
            r"(?:test\s+scenario|scenario)[\s:]*\n(.+?)(?=\n\n|\Z)",
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        match = pattern.search(content)
        if match:
            scenario_text = match.group(1)
            scenarios = [s.strip() for s in scenario_text.split("\n") if s.strip()]

        return scenarios


# =============================================================================
# User Story Generator
# =============================================================================

class UserStoryGenerator(BaseParser):
    """Generate user stories from requirements."""

    USER_STORY_PATTERN = re.compile(
        r"as\s+a\s+(.+?),?\s+i\s+want\s+(?:to\s+)?(.+?),?\s+so\s+that\s+(.+?)(?:[.!?]|$)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    def parse(self, content: str) -> List[UserStory]:
        """
        Parse user stories from content.

        Args:
            content: Content containing user stories

        Returns:
            List of UserStory objects
        """
        stories = []

        # Try to extract existing user stories
        matches = self.USER_STORY_PATTERN.finditer(content)
        for match in matches:
            story = UserStory(
                as_role=match.group(1).strip(),
                i_want_to=match.group(2).strip(),
                so_that=match.group(3).strip()
            )
            stories.append(story)

        # If no stories found, generate from description
        if not stories:
            stories = self._generate_from_description(content)

        return stories

    def _generate_from_description(self, content: str) -> List[UserStory]:
        """Generate user stories from requirement description."""
        stories = []

        # Extract user role hints
        role_pattern = re.compile(
            r"(?:user|as\s+(?:a|an)|for\s+(?:the|a|an))?\s+(\w+(?:\s+\w+)*)",
            re.IGNORECASE
        )
        role_match = role_pattern.search(content)
        role = role_match.group(1) if role_match else "user"

        # Extract main goal
        sentences = re.split(r"[.!?]+", content)
        if sentences:
            main_sentence = sentences[0].strip()
            if len(main_sentence) > 20:
                story = UserStory(
                    as_role=role,
                    i_want_to=main_sentence,
                    so_that="requirement is fulfilled"
                )
                stories.append(story)

        return stories


# =============================================================================
# Notion PRD Parser
# =============================================================================

class NotionPRDParser:
    """
    Parse complete Notion PRD pages and extract all structured data.

    This is the main entry point for PRD parsing.
    """

    def __init__(
        self,
        logger_instance: Optional[logging.Logger] = None
    ):
        """
        Initialize Notion PRD parser.

        Args:
            logger_instance: Optional logger instance
        """
        self.logger = logger_instance or logger
        self.requirement_extractor = RequirementExtractor(self.logger)
        self.acceptance_parser = AcceptanceCriteriaParser(self.logger)
        self.user_story_generator = UserStoryGenerator(self.logger)

    def parse_prd_page(self, page_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a complete Notion PRD page.

        Args:
            page_content: Notion page content (from Composio)

        Returns:
            Dictionary containing parsed PRD data
        """
        page_id = page_content.get("id", "unknown")
        title = page_content.get("title", "Untitled PRD")
        content = page_content.get("content", "")

        self.logger.info(f"Parsing PRD page: {title} ({page_id})")

        try:
            # Extract requirements
            requirements = self.requirement_extractor.parse(content)

            # Extract user stories and acceptance criteria for each requirement
            enriched_requirements = []
            for req in requirements:
                req.user_stories = self.user_story_generator.parse(
                    req.description
                )
                acceptance = self.acceptance_parser.parse(req.description)
                req.acceptance_criteria = acceptance.criteria

                enriched_requirements.append(req)

            return {
                "page_id": page_id,
                "title": title,
                "requirements": enriched_requirements,
                "total_requirements": len(enriched_requirements),
                "metadata": {
                    "parsed_at": str(self.logger),
                    "parser_version": "1.0.0",
                }
            }

        except Exception as e:
            self.logger.error(f"Error parsing PRD page {page_id}: {e}")
            raise

    def parse_requirement(self, req_text: str) -> Optional[Requirement]:
        """
        Parse a single requirement text.

        Args:
            req_text: Text content of requirement

        Returns:
            Parsed Requirement or None if invalid
        """
        requirements = self.requirement_extractor.parse(req_text)
        if requirements:
            req = requirements[0]
            req.user_stories = self.user_story_generator.parse(req_text)
            acceptance = self.acceptance_parser.parse(req_text)
            req.acceptance_criteria = acceptance.criteria
            return req

        return None
