"""Reference integrity validator."""

from __future__ import annotations

import re
from typing import Dict, List

from ..imrad_assembler import IMRaDSection
from ..manuscript_types import ManuscriptReference


class ReferenceValidator:
    CITE_TOKEN_RE = re.compile(r"\{CITE:([^}]+)\}")

    def validate(self, references: List[ManuscriptReference], texts: Dict[IMRaDSection, str]) -> List[str]:
        warnings: List[str] = []

        cited: List[str] = []
        for _, t in texts.items():
            cited.extend([m.group(1) for m in self.CITE_TOKEN_RE.finditer(t or "")])

        cited_set = set(cited)
        ref_set = set(r.id for r in references)

        missing = sorted(list(cited_set - ref_set))
        if missing:
            warnings.append(f"missing references for citation keys: {', '.join(missing)}")

        unused = sorted(list(ref_set - cited_set))
        if unused:
            warnings.append(f"unused references (not cited): {', '.join(unused)}")

        for r in references:
            if not r.id:
                warnings.append("reference with empty id")
        return warnings
