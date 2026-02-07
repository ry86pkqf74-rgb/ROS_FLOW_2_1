# Section writer shared module: grounded section generation with evidence refs (chunk_id/doc_id).
from .bridge import invoke_ai_bridge
from .parser import parse_section_response
from .prompts import build_section_prompt
from .prompts import get_grounding_chunk_and_doc_ids
from .validator import enforce_claims_evidence

__all__ = [
    "invoke_ai_bridge",
    "build_section_prompt",
    "get_grounding_chunk_and_doc_ids",
    "parse_section_response",
    "enforce_claims_evidence",
]
