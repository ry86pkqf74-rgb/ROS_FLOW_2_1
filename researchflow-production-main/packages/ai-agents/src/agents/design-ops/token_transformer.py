"""
Token Transformation Utilities

Handles parsing, validation, transformation, and diff generation for design tokens.
Converts Figma tokens to Tailwind configuration format.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Enumeration of supported design token types."""
    COLOR = "color"
    SPACING = "spacing"
    TYPOGRAPHY = "typography"
    RADIUS = "radius"
    SHADOW = "shadow"
    OPACITY = "opacity"
    BORDER_WIDTH = "borderWidth"
    DURATION = "duration"
    SIZING = "sizing"
    ZINDEX = "zIndex"


class TokenCategory(Enum):
    """Enumeration of token categories."""
    BASE = "base"
    SEMANTIC = "semantic"
    COMPONENT = "component"


@dataclass
class TokenValue:
    """Represents a single design token value."""
    name: str
    type: TokenType
    value: Any
    category: TokenCategory
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "category": self.category.value,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass
class TokenDiff:
    """Represents a change in a design token."""
    action: str  # "added", "modified", "deleted"
    token_name: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    change_description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert diff to dictionary."""
        return asdict(self)


class FigmaTokenParser:
    """Parse raw Figma tokens and normalize them."""

    def __init__(self):
        """Initialize parser."""
        self.parsed_tokens: Dict[str, TokenValue] = {}
        self.errors: List[str] = []
        logger.info("FigmaTokenParser initialized")

    def parse(self, figma_data: Dict[str, Any]) -> Dict[str, TokenValue]:
        """
        Parse raw Figma token data.

        Args:
            figma_data: Raw token data exported from Figma

        Returns:
            Dictionary of normalized TokenValue objects

        Raises:
            ValueError: If token data is invalid
        """
        if not figma_data:
            raise ValueError("Figma data cannot be empty")

        self.parsed_tokens = {}
        self.errors = []

        try:
            # Handle both direct token objects and nested structures
            if "tokens" in figma_data:
                token_groups = figma_data["tokens"]
            else:
                token_groups = figma_data

            for group_name, group_data in token_groups.items():
                self._parse_token_group(group_name, group_data)

            if self.errors:
                logger.warning(f"Parsing completed with {len(self.errors)} errors")

            logger.info(f"Successfully parsed {len(self.parsed_tokens)} tokens")
            return self.parsed_tokens

        except Exception as e:
            error_msg = f"Failed to parse Figma data: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _parse_token_group(
        self, group_name: str, group_data: Any, prefix: str = ""
    ) -> None:
        """
        Recursively parse token groups.

        Args:
            group_name: Name of the token group
            group_data: Token group data
            prefix: Prefix for nested tokens
        """
        if isinstance(group_data, dict):
            # Check if this is a token value (has 'value' key) or a nested group
            if "value" in group_data:
                self._parse_token_value(group_name, group_data, prefix)
            else:
                # Recurse into nested groups
                new_prefix = f"{prefix}.{group_name}" if prefix else group_name
                for key, value in group_data.items():
                    self._parse_token_group(key, value, new_prefix)

    def _parse_token_value(
        self, token_name: str, token_data: Dict[str, Any], prefix: str = ""
    ) -> None:
        """
        Parse individual token value.

        Args:
            token_name: Name of the token
            token_data: Token data with 'value' key
            prefix: Prefix for the token name
        """
        try:
            full_name = f"{prefix}.{token_name}" if prefix else token_name

            # Infer token type from structure or type field
            token_type = self._infer_token_type(token_data)
            category = self._infer_token_category(full_name)

            value = token_data.get("value")

            token = TokenValue(
                name=full_name,
                type=token_type,
                value=value,
                category=category,
                description=token_data.get("description"),
                metadata={
                    "source": token_data.get("$type", "unknown"),
                    "sets": token_data.get("$sets", []),
                },
            )

            self.parsed_tokens[full_name] = token

        except Exception as e:
            error_msg = f"Failed to parse token '{token_name}': {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)

    def _infer_token_type(self, token_data: Dict[str, Any]) -> TokenType:
        """Infer token type from token data."""
        if "$type" in token_data:
            type_str = token_data["$type"].lower()
            type_mapping = {
                "color": TokenType.COLOR,
                "spacing": TokenType.SPACING,
                "typography": TokenType.TYPOGRAPHY,
                "radius": TokenType.RADIUS,
                "shadow": TokenType.SHADOW,
                "opacity": TokenType.OPACITY,
                "borderwidth": TokenType.BORDER_WIDTH,
                "duration": TokenType.DURATION,
                "sizing": TokenType.SIZING,
                "zindex": TokenType.ZINDEX,
            }
            return type_mapping.get(type_str, TokenType.COLOR)

        # Infer from value
        value = token_data.get("value")
        if isinstance(value, str):
            if value.startswith("#") or value.startswith("rgb"):
                return TokenType.COLOR
            elif "px" in value or "rem" in value or "em" in value:
                if "shadow" in str(token_data).lower():
                    return TokenType.SHADOW
                return TokenType.SPACING
        elif isinstance(value, dict) and "x" in value and "y" in value:
            return TokenType.SHADOW

        return TokenType.COLOR

    def _infer_token_category(self, token_name: str) -> TokenCategory:
        """Infer token category from name."""
        name_lower = token_name.lower()
        if "semantic" in name_lower:
            return TokenCategory.SEMANTIC
        elif "component" in name_lower:
            return TokenCategory.COMPONENT
        else:
            return TokenCategory.BASE


class TailwindConfigGenerator:
    """Generate Tailwind configuration from design tokens."""

    def __init__(self):
        """Initialize generator."""
        logger.info("TailwindConfigGenerator initialized")

    def generate(self, tokens: Dict[str, TokenValue]) -> str:
        """
        Generate Tailwind configuration TypeScript file.

        Args:
            tokens: Dictionary of TokenValue objects

        Returns:
            TypeScript code for tailwind.config.ts
        """
        logger.info("Generating Tailwind configuration")

        # Organize tokens by category
        config_sections = {
            "colors": self._extract_colors(tokens),
            "spacing": self._extract_spacing(tokens),
            "fontSize": self._extract_typography_sizes(tokens),
            "fontFamily": self._extract_typography_families(tokens),
            "fontWeight": self._extract_typography_weights(tokens),
            "borderRadius": self._extract_border_radius(tokens),
            "boxShadow": self._extract_shadows(tokens),
            "opacity": self._extract_opacity(tokens),
            "zIndex": self._extract_zindex(tokens),
        }

        # Generate TypeScript configuration
        config_ts = self._build_config_file(config_sections)

        logger.info("Tailwind configuration generated successfully")
        return config_ts

    def _extract_colors(self, tokens: Dict[str, TokenValue]) -> Dict[str, Any]:
        """Extract color tokens for Tailwind."""
        colors = {}
        for token in tokens.values():
            if token.type == TokenType.COLOR:
                # Normalize token name to Tailwind format
                key = self._normalize_key(token.name)
                if isinstance(token.value, str):
                    colors[key] = token.value
                elif isinstance(token.value, dict):
                    # Handle color palettes
                    for shade, color_val in token.value.items():
                        colors[f"{key}-{shade}"] = color_val

        return colors

    def _extract_spacing(self, tokens: Dict[str, TokenValue]) -> Dict[str, Any]:
        """Extract spacing tokens for Tailwind."""
        spacing = {}
        for token in tokens.values():
            if token.type == TokenType.SPACING:
                key = self._normalize_key(token.name)
                spacing[key] = token.value

        return spacing

    def _extract_typography_sizes(
        self, tokens: Dict[str, TokenValue]
    ) -> Dict[str, Any]:
        """Extract font size tokens for Tailwind."""
        sizes = {}
        for token in tokens.values():
            if token.type == TokenType.TYPOGRAPHY and "size" in token.name.lower():
                key = self._normalize_key(token.name.replace("typography.", ""))
                if isinstance(token.value, dict):
                    # Figma typography has nested structure
                    sizes[key] = [token.value.get("fontSize", "1rem")]
                else:
                    sizes[key] = token.value

        return sizes

    def _extract_typography_families(
        self, tokens: Dict[str, TokenValue]
    ) -> Dict[str, Any]:
        """Extract font family tokens for Tailwind."""
        families = {}
        for token in tokens.values():
            if token.type == TokenType.TYPOGRAPHY and "family" in token.name.lower():
                key = self._normalize_key(token.name.replace("typography.", ""))
                if isinstance(token.value, dict):
                    families[key] = token.value.get("fontFamily", "sans-serif")
                else:
                    families[key] = token.value

        return families

    def _extract_typography_weights(
        self, tokens: Dict[str, TokenValue]
    ) -> Dict[str, Any]:
        """Extract font weight tokens for Tailwind."""
        weights = {}
        for token in tokens.values():
            if token.type == TokenType.TYPOGRAPHY and "weight" in token.name.lower():
                key = self._normalize_key(token.name.replace("typography.", ""))
                if isinstance(token.value, dict):
                    weights[key] = token.value.get("fontWeight", "400")
                else:
                    weights[key] = token.value

        return weights

    def _extract_border_radius(self, tokens: Dict[str, TokenValue]) -> Dict[str, Any]:
        """Extract border radius tokens for Tailwind."""
        radii = {}
        for token in tokens.values():
            if token.type == TokenType.RADIUS:
                key = self._normalize_key(token.name)
                radii[key] = token.value

        return radii

    def _extract_shadows(self, tokens: Dict[str, TokenValue]) -> Dict[str, Any]:
        """Extract shadow tokens for Tailwind."""
        shadows = {}
        for token in tokens.values():
            if token.type == TokenType.SHADOW:
                key = self._normalize_key(token.name)
                # Convert shadow object to CSS string
                if isinstance(token.value, dict):
                    shadow_css = self._shadow_to_css(token.value)
                    shadows[key] = shadow_css
                else:
                    shadows[key] = token.value

        return shadows

    def _extract_opacity(self, tokens: Dict[str, TokenValue]) -> Dict[str, Any]:
        """Extract opacity tokens for Tailwind."""
        opacity = {}
        for token in tokens.values():
            if token.type == TokenType.OPACITY:
                key = self._normalize_key(token.name)
                opacity[key] = token.value

        return opacity

    def _extract_zindex(self, tokens: Dict[str, TokenValue]) -> Dict[str, Any]:
        """Extract z-index tokens for Tailwind."""
        zindex = {}
        for token in tokens.values():
            if token.type == TokenType.ZINDEX:
                key = self._normalize_key(token.name)
                zindex[key] = token.value

        return zindex

    def _shadow_to_css(self, shadow_obj: Dict[str, Any]) -> str:
        """Convert shadow object to CSS shadow string."""
        try:
            x = shadow_obj.get("x", 0)
            y = shadow_obj.get("y", 0)
            blur = shadow_obj.get("blur", 0)
            spread = shadow_obj.get("spread", 0)
            color = shadow_obj.get("color", "rgba(0, 0, 0, 0.1)")

            return f"{x}px {y}px {blur}px {spread}px {color}"
        except Exception as e:
            logger.error(f"Failed to convert shadow: {str(e)}")
            return "0 0 0 0 rgba(0, 0, 0, 0.1)"

    def _normalize_key(self, name: str) -> str:
        """Normalize token name to Tailwind key format."""
        # Remove common prefixes
        name = name.replace("semantic.", "").replace("component.", "").replace("base.", "")
        # Convert to kebab-case
        name = name.replace("_", "-").lower()
        return name

    def _build_config_file(self, sections: Dict[str, Dict[str, Any]]) -> str:
        """Build complete tailwind.config.ts file."""
        # Filter out empty sections
        sections = {k: v for k, v in sections.items() if v}

        # Build theme object
        theme_obj = self._build_theme_object(sections)

        config_content = '''import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./packages/ui/src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
'''

        for section, values in sections.items():
            config_content += f"      {section}: {json.dumps(values, indent=8)},\n"

        config_content += '''    },
  },
  plugins: [],
};

export default config;
'''

        return config_content

    def _build_theme_object(self, sections: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Build theme extend object."""
        return sections


class TokenValidator:
    """Validate design token structure and values."""

    def __init__(self):
        """Initialize validator."""
        logger.info("TokenValidator initialized")
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []

    def validate(self, tokens: Dict[str, TokenValue]) -> bool:
        """
        Validate token collection.

        Args:
            tokens: Dictionary of TokenValue objects

        Returns:
            True if all tokens are valid, False otherwise
        """
        self.validation_errors = []
        self.validation_warnings = []

        if not tokens:
            self.validation_errors.append("No tokens provided for validation")
            return False

        for token_name, token in tokens.items():
            self._validate_token(token)

        # Check for naming conflicts
        self._check_naming_conflicts(tokens)

        # Check for orphaned references
        self._check_orphaned_references(tokens)

        logger.info(
            f"Validation complete: {len(self.validation_errors)} errors, "
            f"{len(self.validation_warnings)} warnings"
        )

        return len(self.validation_errors) == 0

    def _validate_token(self, token: TokenValue) -> None:
        """Validate individual token."""
        try:
            # Check required fields
            if not token.name or not isinstance(token.name, str):
                self.validation_errors.append(
                    f"Token has invalid name: {token.name}"
                )

            if token.value is None:
                self.validation_errors.append(
                    f"Token '{token.name}' has no value"
                )

            # Type-specific validation
            if token.type == TokenType.COLOR:
                self._validate_color(token)
            elif token.type == TokenType.SPACING:
                self._validate_spacing(token)
            elif token.type == TokenType.SHADOW:
                self._validate_shadow(token)

        except Exception as e:
            error_msg = f"Validation error for token '{token.name}': {str(e)}"
            logger.error(error_msg)
            self.validation_errors.append(error_msg)

    def _validate_color(self, token: TokenValue) -> None:
        """Validate color token."""
        value = token.value
        if isinstance(value, str):
            # Check hex color format
            if value.startswith("#"):
                if len(value) not in (4, 7, 9):
                    self.validation_warnings.append(
                        f"Color '{token.name}' has unusual hex format: {value}"
                    )
            # Check rgb/rgba format
            elif not value.startswith("rgb"):
                self.validation_warnings.append(
                    f"Color '{token.name}' has non-standard format: {value}"
                )

    def _validate_spacing(self, token: TokenValue) -> None:
        """Validate spacing token."""
        value = str(token.value)
        # Check for valid units
        valid_units = ("px", "rem", "em", "%")
        if not any(unit in value for unit in valid_units):
            self.validation_warnings.append(
                f"Spacing '{token.name}' missing unit: {value}"
            )

    def _validate_shadow(self, token: TokenValue) -> None:
        """Validate shadow token."""
        if isinstance(token.value, dict):
            required_keys = {"x", "y", "blur"}
            actual_keys = set(token.value.keys())
            if not required_keys.issubset(actual_keys):
                missing = required_keys - actual_keys
                self.validation_warnings.append(
                    f"Shadow '{token.name}' missing keys: {missing}"
                )

    def _check_naming_conflicts(self, tokens: Dict[str, TokenValue]) -> None:
        """Check for naming conflicts."""
        token_names = [t.name.lower() for t in tokens.values()]
        duplicates = [name for name in set(token_names) if token_names.count(name) > 1]
        for dup in duplicates:
            self.validation_warnings.append(f"Naming conflict detected: {dup}")

    def _check_orphaned_references(self, tokens: Dict[str, TokenValue]) -> None:
        """Check for references to non-existent tokens."""
        token_names = {t.name for t in tokens.values()}

        for token in tokens.values():
            refs = self._extract_references(str(token.value))
            for ref in refs:
                if ref not in token_names:
                    self.validation_warnings.append(
                        f"Token '{token.name}' references undefined token: {ref}"
                    )

    def _extract_references(self, value_str: str) -> Set[str]:
        """Extract token references from value string."""
        import re

        # Look for patterns like {color.primary} or $primary
        pattern = r"\{([^}]+)\}|\$([A-Za-z0-9._]+)"
        matches = re.findall(pattern, value_str)
        return {match[0] or match[1] for match in matches}

    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return self.validation_errors

    def get_warnings(self) -> List[str]:
        """Get validation warnings."""
        return self.validation_warnings


class DiffGenerator:
    """Generate diffs for design token changes."""

    def __init__(self):
        """Initialize diff generator."""
        logger.info("DiffGenerator initialized")

    def generate_diffs(
        self, old_tokens: Dict[str, TokenValue], new_tokens: Dict[str, TokenValue]
    ) -> List[TokenDiff]:
        """
        Generate list of token changes.

        Args:
            old_tokens: Previous token set
            new_tokens: New token set

        Returns:
            List of TokenDiff objects
        """
        diffs: List[TokenDiff] = []

        # Find added and modified tokens
        for name, new_token in new_tokens.items():
            if name not in old_tokens:
                diff = TokenDiff(
                    action="added",
                    token_name=name,
                    new_value=new_token.value,
                    change_description=f"New {new_token.type.value} token",
                )
                diffs.append(diff)
            else:
                old_token = old_tokens[name]
                if old_token.value != new_token.value:
                    diff = TokenDiff(
                        action="modified",
                        token_name=name,
                        old_value=old_token.value,
                        new_value=new_token.value,
                        change_description=f"Updated {new_token.type.value} value",
                    )
                    diffs.append(diff)

        # Find deleted tokens
        for name, old_token in old_tokens.items():
            if name not in new_tokens:
                diff = TokenDiff(
                    action="deleted",
                    token_name=name,
                    old_value=old_token.value,
                    change_description=f"Removed {old_token.type.value} token",
                )
                diffs.append(diff)

        logger.info(f"Generated {len(diffs)} token diffs")
        return diffs

    def generate_pr_description(self, diffs: List[TokenDiff]) -> str:
        """
        Generate PR description from token diffs.

        Args:
            diffs: List of TokenDiff objects

        Returns:
            Markdown formatted PR description
        """
        if not diffs:
            return "No design token changes"

        # Categorize diffs
        added = [d for d in diffs if d.action == "added"]
        modified = [d for d in diffs if d.action == "modified"]
        deleted = [d for d in diffs if d.action == "deleted"]

        description = "# Design System Token Updates\n\n"
        description += f"Automated token synchronization from Figma\n\n"
        description += f"**Timestamp:** {datetime.now().isoformat()}\n\n"

        description += "## Summary\n\n"
        description += f"- Added: {len(added)} token(s)\n"
        description += f"- Modified: {len(modified)} token(s)\n"
        description += f"- Deleted: {len(deleted)} token(s)\n\n"

        if added:
            description += "## Added Tokens\n\n"
            for diff in added:
                description += f"- `{diff.token_name}`: {diff.new_value}\n"
            description += "\n"

        if modified:
            description += "## Modified Tokens\n\n"
            for diff in modified:
                description += (
                    f"- `{diff.token_name}`: `{diff.old_value}` → `{diff.new_value}`\n"
                )
            description += "\n"

        if deleted:
            description += "## Deleted Tokens\n\n"
            for diff in deleted:
                description += f"- `{diff.token_name}` (was: {diff.old_value})\n"
            description += "\n"

        description += "---\n\n"
        description += (
            "*Generated by DesignOps Agent - "
            "Figma Design Tokens Integration*\n"
        )

        return description
