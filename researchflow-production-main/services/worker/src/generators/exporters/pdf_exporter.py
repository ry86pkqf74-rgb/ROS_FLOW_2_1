"""PDF exporter.

Uses reportlab if available (it's already used elsewhere in the repo).
"""

from __future__ import annotations

from io import BytesIO
from typing import List

from ..imrad_assembler import ManuscriptBundle


class PdfExporter:
    format: str = "pdf"

    def export_bytes(self, bundle: ManuscriptBundle) -> bytes:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"reportlab not available: {e}")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story: List[object] = []

        story.append(Paragraph(bundle.title, styles["Title"]))
        story.append(Spacer(1, 12))

        order = ["abstract", "methods", "results", "discussion", "references", "supplementary"]
        for key in order:
            if key not in bundle.sections:
                continue
            s = bundle.sections[key]  # type: ignore[index]
            story.append(Paragraph(s.heading or key.capitalize(), styles["Heading2"]))
            story.append(Spacer(1, 6))
            for para in (s.text or "").split("\n"):
                para = para.strip()
                if not para:
                    continue
                story.append(Paragraph(para, styles["BodyText"]))
                story.append(Spacer(1, 6))
            story.append(Spacer(1, 12))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
