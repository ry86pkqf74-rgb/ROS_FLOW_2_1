"""Markdown exporter."""

from __future__ import annotations

from typing import List

from ..imrad_assembler import IMRaDSection, ManuscriptBundle


class MarkdownExporter:
    format: str = "markdown"

    def export(self, bundle: ManuscriptBundle) -> str:
        order: List[IMRaDSection] = [
            "title",
            "abstract",
            "methods",
            "results",
            "discussion",
            "references",
            "supplementary",
        ]
        lines: List[str] = []
        title = bundle.title
        lines.append(f"# {title}")
        lines.append("")

        for sec in order:
            if sec not in bundle.sections:
                continue
            s = bundle.sections[sec]
            if sec == "title":
                continue
            heading = s.heading.strip() if s.heading else sec.capitalize()
            if heading:
                lines.append(f"## {heading}")
            text = (s.text or "").strip()
            lines.append(text)
            lines.append("")
        return "\n".join(lines).strip() + "\n"
