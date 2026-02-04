"""Custom, institution-specific patterns for PHI scanning.

This module provides a small registry that can be populated at runtime or from
configuration files (JSON/YAML) to add organization-specific identifiers such as:
- Medical Record Numbers (MRN) with local formatting rules
- Employee IDs / Staff IDs

The registry produces PatternDef instances compatible with the existing pattern
pipeline (HIPAA + international + custom).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .hipaa_identifiers import PatternDef


@dataclass(frozen=True)
class PatternValidationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


class CustomPatternRegistry:
    """Registry for institution-specific patterns.

    Patterns are stored as PatternDef objects keyed by PatternDef.key.
    """

    def __init__(self, initial: Optional[Dict[str, PatternDef]] = None):
        self._patterns: Dict[str, PatternDef] = dict(initial or {})

    # --------------------------- CRUD ---------------------------

    def register_pattern(
        self,
        key: str,
        description: str,
        regexes: Iterable[str],
        allowlist: Optional[Iterable[str]] = None,
        *,
        replace_existing: bool = True,
        validate: bool = True,
    ) -> PatternDef:
        """Register a new pattern.

        Args:
            key: stable identifier for the pattern (used as detection kind).
            description: human-readable description.
            regexes: one or more regex strings.
            allowlist: optional allowlist regexes for suppression.
            replace_existing: if False and key exists, raises ValueError.
            validate: if True, validates regex compilation and key.
        """

        key = (key or "").strip()
        if not key:
            raise ValueError("Pattern key must be non-empty")
        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", key):
            raise ValueError("Pattern key must be alnum/underscore/dash")

        regex_list = [r for r in (list(regexes) if regexes is not None else []) if str(r).strip()]
        if not regex_list:
            raise ValueError("At least one regex must be provided")

        allow_list = None
        if allowlist is not None:
            allow_list = [a for a in list(allowlist) if str(a).strip()]

        if validate:
            res = self.validate_pattern(key=key, regexes=regex_list, allowlist=allow_list)
            if not res.ok:
                raise ValueError("Invalid pattern: " + "; ".join(res.errors))

        if (not replace_existing) and (key in self._patterns):
            raise ValueError(f"Pattern '{key}' already exists")

        pat = PatternDef(key=key, description=description, regexes=regex_list, allowlist=allow_list)
        self._patterns[key] = pat
        return pat

    def remove_pattern(self, key: str) -> bool:
        """Remove a pattern by key. Returns True if removed."""

        return self._patterns.pop(key, None) is not None

    def list_patterns(self) -> Dict[str, PatternDef]:
        """Return a copy of registered patterns."""

        return dict(self._patterns)

    # ------------------------ validation ------------------------

    @staticmethod
    def validate_pattern(
        *,
        key: str,
        regexes: Iterable[str],
        allowlist: Optional[Iterable[str]] = None,
        flags: int = re.IGNORECASE,
    ) -> PatternValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        if not key or not str(key).strip():
            errors.append("key is required")

        reg_list = [r for r in list(regexes) if str(r).strip()]
        if not reg_list:
            errors.append("regexes must be non-empty")

        for r_str in reg_list:
            try:
                re.compile(str(r_str), flags)
            except Exception as e:
                errors.append(f"regex failed to compile: {r_str!r} ({e})")

        if allowlist is not None:
            for a_str in [a for a in list(allowlist) if str(a).strip()]:
                try:
                    re.compile(str(a_str), flags)
                except Exception as e:
                    errors.append(f"allowlist regex failed to compile: {a_str!r} ({e})")

        # Gentle warnings to avoid pathological patterns
        for r_str in reg_list:
            if len(str(r_str)) > 512:
                warnings.append(f"regex is long ({len(str(r_str))} chars): {r_str[:80]!r}...")
            if "(?=" in str(r_str) or "(?!" in str(r_str):
                warnings.append("regex uses lookarounds; ensure performance is acceptable")

        return PatternValidationResult(ok=(len(errors) == 0), errors=errors, warnings=warnings)

    def test_pattern(
        self,
        *,
        regexes: Iterable[str],
        samples_should_match: Iterable[str] = (),
        samples_should_not_match: Iterable[str] = (),
        flags: int = re.IGNORECASE,
    ) -> PatternValidationResult:
        """Lightweight testing utility for patterns.

        Returns validation-style output with errors when expectations fail.
        """

        errors: List[str] = []
        warnings: List[str] = []

        compiled = []
        for r_str in [r for r in list(regexes) if str(r).strip()]:
            try:
                compiled.append(re.compile(str(r_str), flags))
            except Exception as e:
                errors.append(f"regex failed to compile: {r_str!r} ({e})")

        def any_match(s: str) -> bool:
            return any(r.search(s) for r in compiled)

        for s in samples_should_match:
            if not any_match(str(s)):
                errors.append(f"expected match but found none: {s!r}")

        for s in samples_should_not_match:
            if any_match(str(s)):
                errors.append(f"expected no match but found a match: {s!r}")

        return PatternValidationResult(ok=(len(errors) == 0), errors=errors, warnings=warnings)

    # --------------------- config file loading -------------------

    @classmethod
    def from_config_file(cls, path: str) -> "CustomPatternRegistry":
        """Load patterns from a JSON or YAML file."""

        data = cls._load_config(path)
        reg = cls()

        patterns = data.get("patterns") or data.get("custom_patterns") or []
        if isinstance(patterns, dict):
            # allow mapping of key -> pattern definition
            patterns = [dict({"key": k}, **v) for k, v in patterns.items()]

        if not isinstance(patterns, list):
            raise ValueError("Config must contain 'patterns' as list or dict")

        for p in patterns:
            if not isinstance(p, dict):
                continue
            reg.register_pattern(
                key=str(p.get("key", "")).strip(),
                description=str(p.get("description", "")).strip(),
                regexes=p.get("regexes") or p.get("patterns") or [],
                allowlist=p.get("allowlist") or p.get("allow_list"),
                replace_existing=True,
                validate=True,
            )

        return reg

    @staticmethod
    def _load_config(path: str) -> Dict[str, Any]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(p))

        raw = p.read_text(encoding="utf-8")
        suffix = p.suffix.lower()

        if suffix in {".json"}:
            return json.loads(raw)

        if suffix in {".yml", ".yaml"}:
            try:
                import yaml  # type: ignore
            except Exception as e:
                raise RuntimeError(
                    "YAML config requires 'pyyaml' to be installed"
                ) from e
            data = yaml.safe_load(raw)
            if data is None:
                return {}
            if not isinstance(data, dict):
                raise ValueError("YAML config root must be a mapping")
            return data

        raise ValueError("Unsupported config file type; expected .json/.yml/.yaml")


# Default empty registry exposure compatible with src.phi.patterns import.
# (The BatchScanner imports CUSTOM_PATTERNS and expects a dict-like .values().)
CUSTOM_PATTERNS: Dict[str, PatternDef] = {}


def load_custom_patterns_from_env() -> Dict[str, PatternDef]:
    """Optional helper to load patterns from env-configured file.

    If PHI_CUSTOM_PATTERNS_FILE is set and points to a JSON/YAML file, the
    returned dict contains those patterns. Otherwise returns an empty dict.

    This function does not mutate CUSTOM_PATTERNS; callers may assign/merge.
    """

    cfg = os.getenv("PHI_CUSTOM_PATTERNS_FILE")
    if not cfg:
        return {}
    reg = CustomPatternRegistry.from_config_file(cfg)
    return reg.list_patterns()
