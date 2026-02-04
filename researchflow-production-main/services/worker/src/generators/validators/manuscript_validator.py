"""Manuscript completeness validator."""

from __future__ import annotations

from typing import Dict, List

from ..imrad_assembler import IMRaDSection, ManuscriptSection


class ManuscriptValidator:
    REQUIRED = ["title", "abstract", "methods", "results", "discussion", "references"]

    def validate(self, sections: Dict[IMRaDSection, ManuscriptSection]) -> List[str]:
        errors: List[str] = []
        for s in self.REQUIRED:
            sec = sections.get(s)  # type: ignore[arg-type]
            if sec is None:
                errors.append(f"missing required section: {s}")
                continue
            if s != "title" and not (sec.text or "").strip():
                errors.append(f"empty required section: {s}")
        return errors
