from __future__ import annotations
from typing import Any, Dict, List, Tuple
from app.schemas import EvidenceSynthInputs


def _format_papers(papers: List[Dict[str, Any]], max_papers: int = 12) -> str:
    lines: List[str] = []
    for i, p in enumerate(papers[:max_papers], start=1):
        title = p.get("title") or ""
        year = p.get("year") or ""
        doi = p.get("doi") or ""
        pmid = p.get("pmid") or ""
        abstract = (p.get("abstract") or "")[:1200]
        lines.append(f"[{i}] {title} ({year}) DOI:{doi} PMID:{pmid}\nAbstract: {abstract}")
    return "\n\n".join(lines)


async def run_evidence_synth(inputs_raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    inputs = EvidenceSynthInputs.model_validate(inputs_raw)
    warnings: List[str] = []

    paper_dicts = [p.model_dump() if hasattr(p, "model_dump") else p for p in inputs.papers]  # defensive

    prompt = (
        "You are an evidence synthesis assistant.\n"
        "Task: Provide a concise synthesis answering the query using ONLY the provided papers.\n"
        "Return a structured response with:\n"
        "- key_findings: bullet list\n"
        "- limitations: bullet list\n"
        "- citations: list of {index, title, doi, pmid, url}\n\n"
        f"Query: {inputs.query}\n\n"
        f"Papers:\n{_format_papers(paper_dicts)}\n"
    )

    from app.llm import ollama_chat  # local-only

    text = await ollama_chat(prompt)

    outputs = {
        "synthesis_text": text,
        "paper_count": len(paper_dicts),
    }
    return outputs, warnings
