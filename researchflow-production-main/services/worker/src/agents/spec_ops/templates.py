"""
SpecOps Agent - GitHub Issue Templates

This module provides standardized templates for creating GitHub issues
from Notion PRD (Product Requirements Document) entries.

Templates support:
- FEATURE_ISSUE_TEMPLATE: New features and enhancements
- BUG_ISSUE_TEMPLATE: Bug reports and defects
- TASK_ISSUE_TEMPLATE: Technical tasks and refactoring
- EPIC_ISSUE_TEMPLATE: Large initiatives and epics
"""

from typing import Dict, List, Optional

# =============================================================================
# Feature Issue Template
# =============================================================================

FEATURE_ISSUE_TEMPLATE = """# {title}

## Description
{description}

## User Story
{user_story}

## Acceptance Criteria
{acceptance_criteria}

## Technical Requirements
{technical_requirements}

## Dependencies
{dependencies}

## Estimated Effort
- Story Points: {story_points}
- Complexity: {complexity}

## Related PRD
- PRD Link: {prd_link}
- Phase: {phase}

## Labels
{labels}

## Notes
{notes}
"""

# =============================================================================
# Bug Issue Template
# =============================================================================

BUG_ISSUE_TEMPLATE = """# {title}

## Bug Description
{description}

## Reproduction Steps
{reproduction_steps}

## Expected Behavior
{expected_behavior}

## Actual Behavior
{actual_behavior}

## Severity
{severity}

## Related PRD
- PRD Link: {prd_link}
- Affected Component: {component}

## Labels
{labels}

## Notes
{notes}
"""

# =============================================================================
# Task Issue Template
# =============================================================================

TASK_ISSUE_TEMPLATE = """# {title}

## Task Description
{description}

## Objectives
{objectives}

## Deliverables
{deliverables}

## Technical Details
{technical_details}

## Dependencies
{dependencies}

## Estimated Effort
- Story Points: {story_points}
- Priority: {priority}

## Related PRD
- PRD Link: {prd_link}
- Phase: {phase}

## Labels
{labels}

## Notes
{notes}
"""

# =============================================================================
# Epic Issue Template
# =============================================================================

EPIC_ISSUE_TEMPLATE = """# {title}

## Epic Overview
{description}

## Vision & Goals
{vision}

## Key Features
{key_features}

## Success Metrics
{success_metrics}

## User Stories
{user_stories}

## Technical Architecture
{technical_architecture}

## Timeline
{timeline}

## Related PRD
- PRD Link: {prd_link}
- Phase: {phase}
- Start Date: {start_date}
- Target Date: {target_date}

## Dependencies
{dependencies}

## Labels
{labels}

## Notes
{notes}
"""

# =============================================================================
# Default Field Values
# =============================================================================

DEFAULT_TEMPLATE_FIELDS: Dict[str, str] = {
    "title": "Untitled",
    "description": "No description provided",
    "user_story": "As a..., I want..., so that...",
    "acceptance_criteria": "- [ ] Criterion 1\n- [ ] Criterion 2\n- [ ] Criterion 3",
    "technical_requirements": "- No specific technical requirements",
    "dependencies": "- None identified",
    "story_points": "Unknown",
    "complexity": "Unknown",
    "prd_link": "Not specified",
    "phase": "Not specified",
    "labels": "enhancement",
    "notes": "No additional notes",
    "bug_description": "No description provided",
    "reproduction_steps": "1. Step 1\n2. Step 2\n3. Step 3",
    "expected_behavior": "Describe expected behavior",
    "actual_behavior": "Describe actual behavior",
    "severity": "Unknown",
    "component": "Unknown",
    "task_description": "No description provided",
    "objectives": "- No objectives defined",
    "deliverables": "- No deliverables defined",
    "technical_details": "- No technical details",
    "priority": "Unknown",
    "epic_description": "No epic description provided",
    "vision": "No vision statement provided",
    "key_features": "- Feature 1\n- Feature 2\n- Feature 3",
    "success_metrics": "- Metric 1\n- Metric 2\n- Metric 3",
    "user_stories": "- User story 1\n- User story 2\n- User story 3",
    "technical_architecture": "- Component 1\n- Component 2\n- Component 3",
    "timeline": "TBD",
    "start_date": "TBD",
    "target_date": "TBD",
}


def get_template(template_type: str) -> str:
    """
    Get a template by type.

    Args:
        template_type: Type of template (feature, bug, task, epic)

    Returns:
        Template string

    Raises:
        ValueError: If template type is not recognized
    """
    templates = {
        "feature": FEATURE_ISSUE_TEMPLATE,
        "bug": BUG_ISSUE_TEMPLATE,
        "task": TASK_ISSUE_TEMPLATE,
        "epic": EPIC_ISSUE_TEMPLATE,
    }

    if template_type.lower() not in templates:
        raise ValueError(
            f"Unknown template type: {template_type}. "
            f"Valid types: {', '.join(templates.keys())}"
        )

    return templates[template_type.lower()]


def format_template(
    template_type: str,
    fields: Dict[str, str],
    use_defaults: bool = True
) -> str:
    """
    Format a template with provided fields.

    Args:
        template_type: Type of template (feature, bug, task, epic)
        fields: Dictionary of field values
        use_defaults: Whether to use default values for missing fields

    Returns:
        Formatted template string

    Raises:
        ValueError: If required fields are missing and use_defaults=False
    """
    template = get_template(template_type)

    # Prepare field values
    format_dict = {}
    for key in set(list(DEFAULT_TEMPLATE_FIELDS.keys()) + list(fields.keys())):
        if key in fields:
            format_dict[key] = fields[key]
        elif use_defaults:
            format_dict[key] = DEFAULT_TEMPLATE_FIELDS.get(key, "")
        else:
            format_dict[key] = ""

    return template.format(**format_dict)


def validate_template_fields(
    template_type: str,
    fields: Dict[str, str],
    required_fields: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Validate that all required fields are present and non-empty.

    Args:
        template_type: Type of template
        fields: Dictionary of field values
        required_fields: List of required field names (uses defaults if None)

    Returns:
        Dictionary of validation errors (empty if valid)

    Raises:
        ValueError: If template type is invalid
    """
    template = get_template(template_type)

    # Default required fields by template type
    if required_fields is None:
        required_fields_map = {
            "feature": ["title", "description", "acceptance_criteria"],
            "bug": ["title", "description", "reproduction_steps"],
            "task": ["title", "description", "objectives"],
            "epic": ["title", "vision", "key_features"],
        }
        required_fields = required_fields_map.get(
            template_type.lower(),
            ["title", "description"]
        )

    errors = {}
    for field in required_fields:
        if field not in fields or not fields[field].strip():
            errors[field] = f"Required field '{field}' is missing or empty"

    return errors
