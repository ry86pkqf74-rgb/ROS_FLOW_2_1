"""DOCX exporter using python-docx.

Falls back to the existing generators/docx_generator.generate_docx helper.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..imrad_assembler import ManuscriptBundle
from ..docx_generator import generate_docx


class DocxExporter:
    format: str = "docx"

    def export_bytes(self, bundle: ManuscriptBundle) -> bytes:
        sections_payload: List[Dict[str, Any]] = []
        # Keep order stable
        order = ["abstract", "methods", "results", "discussion", "references", "supplementary"]
        for key in order:
            if key in bundle.sections:
                s = bundle.sections[key]  # type: ignore[index]
                sections_payload.append(
                    {
                        "heading": s.heading or key.capitalize(),
                        "paragraphs": [p for p in (s.text or "").split("\n") if p.strip()],
                    }
                )
        content = {"title": bundle.title, "sections": sections_payload}
        return generate_docx(content)
