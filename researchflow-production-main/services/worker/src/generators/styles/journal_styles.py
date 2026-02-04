"""Journal style presets.

These presets define:
- Section headings
- Word limits (defaults)
- Minimal formatting transforms

They are intentionally conservative and safe (no aggressive rewriting).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Literal

JournalStylePreset = Literal["JAMA", "NEJM", "BMJ", "Lancet", "Nature Medicine"]


@dataclass
class JournalStyle:
    name: str
    section_headings: Dict[str, str] = field(default_factory=dict)
    word_limits: Dict[str, int] = field(default_factory=dict)

    def apply_title(self, title: str) -> str:
        title = (title or "").strip() or "Untitled Manuscript"
        return title

    def apply_section(self, section: str, text: str) -> str:
        # Keep changes minimal; only normalize whitespace.
        t = (text or "").strip()
        return t

    def apply_references_block(self, references_text: str) -> str:
        return (references_text or "").strip()


_PRESETS: Dict[JournalStylePreset, JournalStyle] = {
    "JAMA": JournalStyle(
        name="JAMA",
        section_headings={
            "abstract": "Abstract",
            "methods": "Methods",
            "results": "Results",
            "discussion": "Discussion",
            "references": "References",
            "supplementary": "Supplement",
        },
        word_limits={
            "abstract": 350,
            "methods": 3000,
            "results": 3000,
            "discussion": 2500,
        },
    ),
    "NEJM": JournalStyle(
        name="NEJM",
        section_headings={
            "abstract": "Abstract",
            "methods": "Methods",
            "results": "Results",
            "discussion": "Discussion",
            "references": "References",
            "supplementary": "Supplementary Appendix",
        },
        word_limits={
            "abstract": 350,
            "methods": 3500,
            "results": 3500,
            "discussion": 2500,
        },
    ),
    "BMJ": JournalStyle(
        name="BMJ",
        section_headings={
            "abstract": "Abstract",
            "methods": "Methods",
            "results": "Results",
            "discussion": "Discussion",
            "references": "References",
            "supplementary": "Supplementary material",
        },
        word_limits={
            "abstract": 300,
            "methods": 3500,
            "results": 3500,
            "discussion": 3000,
        },
    ),
    "Lancet": JournalStyle(
        name="The Lancet",
        section_headings={
            "abstract": "Summary",
            "methods": "Methods",
            "results": "Results",
            "discussion": "Discussion",
            "references": "References",
            "supplementary": "Supplementary appendix",
        },
        word_limits={
            "abstract": 300,
            "methods": 3500,
            "results": 3500,
            "discussion": 2500,
        },
    ),
    "Nature Medicine": JournalStyle(
        name="Nature Medicine",
        section_headings={
            "abstract": "Abstract",
            "methods": "Methods",
            "results": "Results",
            "discussion": "Discussion",
            "references": "References",
            "supplementary": "Supplementary Information",
        },
        word_limits={
            "abstract": 150,
            "methods": 4000,
            "results": 4000,
            "discussion": 3000,
        },
    ),
}


def get_journal_style(preset: JournalStylePreset) -> JournalStyle:
    return _PRESETS.get(preset, _PRESETS["JAMA"])
