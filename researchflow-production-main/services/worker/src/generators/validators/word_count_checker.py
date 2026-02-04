"""Word count checker with per-section limits."""

from __future__ import annotations

from typing import Dict, List

from ..imrad_assembler import IMRaDSection, ManuscriptSection


class WordCountChecker:
    def check(self, sections: Dict[IMRaDSection, ManuscriptSection], limits: Dict[str, int]) -> List[str]:
        warnings: List[str] = []
        for sec, limit in (limits or {}).items():
            if sec not in sections:
                continue
            wc = sections[sec].word_count
            if limit and wc > limit:
                warnings.append(f"word limit exceeded for {sec}: {wc} > {limit}")
        return warnings
