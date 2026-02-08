"""
Core Evidence Synthesis Agent Implementation

Based on LangSmith Evidence Synthesis Agent (e22b2945-be8b-4745-9233-5b2651914483)
Implements GRADE methodology for evidence quality assessment
"""
from typing import Any, Dict, List, Tuple, Optional, Literal
import os
import httpx
from agent.schemas import (
    EvidenceSynthesisInputs, 
    EvidenceChunk,
    ConflictAnalysis,
    PICOFramework
)


# GRADE quality levels
GRADE = Literal["High", "Moderate", "Low", "Very Low"]


def decompose_research_question(
    research_question: str,
    pico: Optional[PICOFramework] = None
) -> List[str]:
    """
    Decompose research question into sub-questions using PICO framework
    
    Returns list of focused sub-questions for systematic retrieval
    """
    sub_questions = [research_question]  # Always include the main question
    
    if pico:
        # Generate focused sub-questions from PICO components
        if pico.population and pico.intervention:
            sub_questions.append(
                f"What is the efficacy of {pico.intervention} in {pico.population}?"
            )
        if pico.comparator:
            sub_questions.append(
                f"How does {pico.intervention} compare to {pico.comparator}?"
            )
        if pico.outcome:
            sub_questions.append(
                f"What are the outcomes measured by {pico.outcome}?"
            )
    
    return sub_questions


def assign_grade(
    study_type: str,
    sample_size: Optional[str],
    risk_factors: List[str]
) -> GRADE:
    """
    Assign GRADE quality rating based on study characteristics
    
    Factors:
    - Study design (RCT > cohort > case-control > case series)
    - Sample size (larger is better for precision)
    - Risk of bias, inconsistency, indirectness, imprecision
    """
    study_type_lower = study_type.lower()
    
    # Start with base quality based on study design
    if "systematic review" in study_type_lower or "meta-analysis" in study_type_lower:
        base_grade = "High"
    elif "rct" in study_type_lower or "randomized" in study_type_lower:
        base_grade = "High"
    elif "cohort" in study_type_lower or "longitudinal" in study_type_lower:
        base_grade = "Low"
    elif "case-control" in study_type_lower:
        base_grade = "Low"
    elif "case series" in study_type_lower or "case report" in study_type_lower:
        base_grade = "Very Low"
    elif "expert opinion" in study_type_lower or "commentary" in study_type_lower:
        base_grade = "Very Low"
    else:
        base_grade = "Low"  # Default for observational
    
    # Downgrade based on risk factors
    downgrades = len(risk_factors)
    
    # Small sample size is a risk factor
    if sample_size:
        try:
            size_num = int(''.join(filter(str.isdigit, sample_size)))
            if size_num < 100:
                downgrades += 1
        except:
            pass
    
    # Apply downgrades
    grades = ["Very Low", "Low", "Moderate", "High"]
    current_idx = grades.index(base_grade)
    downgraded_idx = max(0, current_idx - downgrades)
    
    return grades[downgraded_idx]


async def retrieve_evidence_stub(
    sub_question: str,
    mode: str = "DEMO"
) -> List[Dict[str, Any]]:
    """
    Stub for evidence retrieval worker
    
    In production, this would:
    1. Dispatch to Evidence_Retrieval_Worker
    2. Search PubMed, Google Scholar, clinical trial registries
    3. Extract full content from relevant URLs
    4. Return structured evidence chunks
    
    For now, returns mock evidence for demonstration
    """
    # TODO: Implement actual retrieval worker dispatch
    # This would call: workers/retrieval_worker.py
    
    mock_evidence = [
        {
            "source": "Smith et al. (2023). Journal of Evidence Medicine. PMID: 12345678",
            "study_type": "Randomized Controlled Trial",
            "sample_size": "500 participants",
            "population": "Adults with condition X",
            "key_findings": "Intervention showed 30% improvement in primary outcome (p<0.01)",
            "limitations": "Single-center study, limited follow-up period",
            "relevance": "High",
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345678"
        },
        {
            "source": "Johnson et al. (2022). Clinical Research Quarterly. DOI: 10.1234/crq.2022.001",
            "study_type": "Systematic Review",
            "sample_size": "15 studies, 3,200 total participants",
            "population": "Mixed populations",
            "key_findings": "Moderate quality evidence supporting intervention efficacy",
            "limitations": "High heterogeneity across studies (I² = 65%)",
            "relevance": "High",
            "url": "https://doi.org/10.1234/crq.2022.001"
        }
    ]
    
    return mock_evidence


def detect_conflicts(evidence_chunks: List[EvidenceChunk]) -> Optional[List[EvidenceChunk]]:
    """
    Scan evidence for contradictory or inconsistent findings
    
    Returns conflicting evidence if detected, None otherwise
    """
    # Simple heuristic: look for opposing findings in key_findings
    positive_keywords = ["improvement", "effective", "benefit", "positive", "increase"]
    negative_keywords = ["no effect", "ineffective", "no benefit", "negative", "decrease"]
    
    positive_findings = []
    negative_findings = []
    
    for chunk in evidence_chunks:
        findings_lower = chunk.key_findings.lower()
        
        if any(kw in findings_lower for kw in positive_keywords):
            positive_findings.append(chunk)
        if any(kw in findings_lower for kw in negative_keywords):
            negative_findings.append(chunk)
    
    # Conflict detected if we have both positive and negative findings
    if positive_findings and negative_findings:
        return positive_findings + negative_findings
    
    return None


async def analyze_conflicts_stub(
    conflicting_evidence: List[EvidenceChunk]
) -> ConflictAnalysis:
    """
    Stub for conflict analysis worker
    
    In production, this would:
    1. Dispatch to Conflict_Analysis_Worker
    2. Evaluate methodological quality of each side
    3. Identify sources of heterogeneity
    4. Present multi-perspective debate
    5. Provide neutral + interpretive conclusions
    
    For now, returns mock analysis
    """
    # TODO: Implement actual conflict worker dispatch
    # This would call: workers/conflict_worker.py
    
    return ConflictAnalysis(
        conflict_description="Studies show mixed results on intervention efficacy",
        positions=[
            {
                "stance": "Positive",
                "studies": len([c for c in conflicting_evidence if "improvement" in c.key_findings.lower()]),
                "key_arguments": ["Larger sample sizes", "RCT design"],
                "quality": "Moderate to High"
            },
            {
                "stance": "Negative/Null",
                "studies": len([c for c in conflicting_evidence if "no effect" in c.key_findings.lower()]),
                "key_arguments": ["Real-world settings", "Longer follow-up"],
                "quality": "Low to Moderate"
            }
        ],
        methodological_assessment={
            "positive_side": "RCT with good internal validity but limited external validity",
            "negative_side": "Observational with better generalizability but higher risk of bias"
        },
        heterogeneity_sources=[
            "Different populations (age, severity)",
            "Different intervention protocols (dosage, duration)",
            "Different outcome measurements",
            "Different follow-up periods"
        ],
        neutral_presentation="Evidence shows conflicting results. High-quality RCTs suggest benefit, while real-world observational studies show limited effect.",
        interpretive_conclusion="⚠️ INTERPRETIVE: Weight of evidence slightly favors positive effect, but real-world applicability uncertain. Recommend individualized approach.",
        confidence_level="Low to Moderate"
    )


async def run_evidence_synthesis(
    inputs_raw: Dict[str, Any],
    mode: str = "DEMO"
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Main evidence synthesis workflow
    
    Steps:
    1. Clarify and decompose research question (PICO)
    2. Evidence retrieval (dispatch workers)
    3. GRADE quality evaluation
    4. Conflict detection and analysis
    5. Synthesis and report generation
    
    Returns: (outputs, warnings)
    """
    # Validate and parse inputs
    try:
        inputs = EvidenceSynthesisInputs.model_validate(inputs_raw)
    except Exception as e:
        return {
            "error": f"Invalid inputs: {str(e)}",
            "executive_summary": "Validation failed",
            "overall_certainty": "Very Low",
            "evidence_table": [],
            "synthesis_by_subquestion": {},
            "limitations": ["Input validation failed"],
            "methodology_note": {}
        }, [f"Input validation error: {str(e)}"]
    
    warnings: List[str] = []
    
    # Step 1: Decompose research question
    sub_questions = decompose_research_question(
        inputs.research_question,
        inputs.pico
    )
    
    if len(sub_questions) > 1:
        warnings.append(f"Decomposed into {len(sub_questions)} sub-questions")
    
    # Step 2: Evidence retrieval (one worker call per sub-question)
    all_evidence_raw: List[Dict[str, Any]] = []
    for sq in sub_questions:
        evidence = await retrieve_evidence_stub(sq, mode)
        all_evidence_raw.extend(evidence)
    
    # Step 3: GRADE evaluation
    evidence_chunks: List[EvidenceChunk] = []
    for ev in all_evidence_raw:
        # Identify risk factors for GRADE downgrading
        risk_factors = []
        if ev.get("limitations"):
            # Simple heuristic: count limitation mentions
            limitations_str = ev["limitations"].lower()
            if "bias" in limitations_str:
                risk_factors.append("risk_of_bias")
            if "heterogeneity" in limitations_str or "inconsistent" in limitations_str:
                risk_factors.append("inconsistency")
            if "single" in limitations_str or "small" in limitations_str:
                risk_factors.append("imprecision")
        
        grade = assign_grade(
            ev["study_type"],
            ev.get("sample_size"),
            risk_factors
        )
        
        chunk = EvidenceChunk(
            source=ev["source"],
            study_type=ev["study_type"],
            sample_size=ev.get("sample_size"),
            population=ev.get("population"),
            key_findings=ev["key_findings"],
            limitations=ev.get("limitations"),
            relevance=ev.get("relevance", "Medium"),
            grade=grade,
            url=ev.get("url")
        )
        evidence_chunks.append(chunk)
    
    # Step 4: Conflict detection
    conflicting_evidence = detect_conflicts(evidence_chunks)
    conflict_analysis = None
    
    if conflicting_evidence:
        warnings.append(f"Detected {len(conflicting_evidence)} conflicting studies")
        conflict_analysis = await analyze_conflicts_stub(conflicting_evidence)
    else:
        warnings.append("No conflicts detected - evidence shows consensus")
    
    # Step 5: Synthesis and report generation
    # Calculate overall certainty (lowest GRADE among high-relevance evidence)
    high_rel_grades = [c.grade for c in evidence_chunks if c.relevance == "High"]
    grades_order = ["Very Low", "Low", "Moderate", "High"]
    if high_rel_grades:
        overall_certainty = min(high_rel_grades, key=lambda g: grades_order.index(g))
    else:
        overall_certainty = "Low"
    
    # Generate synthesis by sub-question
    synthesis_by_sq = {}
    for i, sq in enumerate(sub_questions):
        relevant_chunks = [c for c in evidence_chunks if c.relevance == "High"]
        if relevant_chunks:
            synthesis_by_sq[f"Q{i+1}"] = f"{sq}: {len(relevant_chunks)} high-quality studies identified."
        else:
            synthesis_by_sq[f"Q{i+1}"] = f"{sq}: Limited high-quality evidence available."
    
    # Generate executive summary
    exec_summary = f"Systematic review of {len(evidence_chunks)} studies on: {inputs.research_question}. "
    if conflict_analysis:
        exec_summary += f"Evidence shows conflicting results. Overall certainty: {overall_certainty}. "
    else:
        exec_summary += f"Evidence shows consensus. Overall certainty: {overall_certainty}. "
    
    high_quality_count = len([c for c in evidence_chunks if c.grade in ["High", "Moderate"]])
    exec_summary += f"{high_quality_count}/{len(evidence_chunks)} studies rated as moderate-to-high quality."
    
    # Compile outputs
    outputs = {
        "executive_summary": exec_summary,
        "overall_certainty": overall_certainty,
        "evidence_table": [c.model_dump() for c in evidence_chunks],
        "synthesis_by_subquestion": synthesis_by_sq,
        "conflicting_evidence": conflict_analysis.model_dump() if conflict_analysis else None,
        "limitations": [
            "Search limited to stub data (production will search PubMed, etc.)",
            "Conflict analysis uses simplified heuristics",
            f"Retrieved {len(evidence_chunks)} studies (max requested: {inputs.max_papers})"
        ],
        "methodology_note": {
            "search_strategy": "PICO-based decomposition with systematic retrieval",
            "sources_searched": ["PubMed (stub)", "Google Scholar (stub)", "ClinicalTrials.gov (stub)"],
            "search_date": "2026-02-07",
            "studies_screened": len(evidence_chunks),
            "studies_included": len(evidence_chunks),
            "quality_assessment": "GRADE methodology"
        }
    }
    
    return outputs, warnings
