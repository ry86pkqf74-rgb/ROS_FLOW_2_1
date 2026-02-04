"""Citation style presets.

Provides simple, deterministic formatting for reference lists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Literal

from ..manuscript_types import ManuscriptReference

CitationStylePreset = Literal["Vancouver", "APA", "Chicago"]


@dataclass
class CitationStyle:
    name: str

    def format_bibliography(self, references: Iterable[ManuscriptReference]) -> str:
        refs = list(references)
        lines: List[str] = []
        for i, r in enumerate(refs, start=1):
            lines.append(self.format_reference(i, r))
        return "\n".join([l for l in lines if l.strip()])

    def format_reference(self, index: int, ref: ManuscriptReference) -> str:
        authors = ", ".join(ref.authors) if ref.authors else ""
        year = str(ref.year) if ref.year else ""
        title = (ref.title or "").strip()
        journal = (ref.journal or "").strip()
        doi = f" doi:{ref.doi}" if ref.doi else ""
        url = f" {ref.url}" if ref.url and not ref.doi else ""
        core = ". ".join([p for p in [authors, title, journal, year] if p])
        core = core.strip(" .")
        if self.name == "APA":
            return f"{authors} ({year}). {title}. {journal}.{doi}{url}".strip()
        if self.name == "Chicago":
            return f"{authors}. \"{title}.\" {journal} ({year}).{doi}{url}".strip()
        return f"{index}. {core}.{doi}{url}".strip()


_PRESETS = {
    "Vancouver": CitationStyle(name="Vancouver"),
    "APA": CitationStyle(name="APA"),
    "Chicago": CitationStyle(name="Chicago"),
}


def get_citation_style(preset: CitationStylePreset) -> CitationStyle:
    return _PRESETS.get(preset, _PRESETS["Vancouver"])
