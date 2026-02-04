"""Shared types for manuscript assembly/export.

Kept separate to avoid circular imports between assembler and styles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ManuscriptReference:
    id: str
    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    journal: str = ""
    doi: Optional[str] = None
    url: Optional[str] = None
    raw: Optional[str] = None
