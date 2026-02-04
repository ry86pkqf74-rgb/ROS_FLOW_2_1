"""Stage 17 — Citation Generation (Enhanced)

Generate bibliography entries from sources and inline citations with comprehensive
reference management including DOI validation, duplicate detection, and quality assessment.

Spec: docs/stages/STAGE_WORKER_SPECS.md (PUBLISH Phase).
Enhanced: Linear Issues ROS-XXX
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .stage_base import (
    call_llm_async,
    make_error,
    make_result,
    parse_json_from_llm,
    VALIDATION_ERROR,
    INCONSISTENT_OUTPUT,
    INCOMPLETE_METADATA,
)

# Import enhanced reference management system
try:
    from .writing.reference_management_service import get_reference_service
    from .writing.types import ReferenceState, CitationStyle, Reference
    from .writing.collaborative_references import get_collaborative_manager
    from .writing.journal_intelligence import get_journal_intelligence
    from .writing.monitoring import get_system_monitor
    ENHANCED_REFERENCE_MANAGEMENT = True
    logger.info("Enhanced reference management system available")
except ImportError as e:
    logger.warning(f"Enhanced reference management not available: {e}")
    ENHANCED_REFERENCE_MANAGEMENT = False

logger = logging.getLogger(__name__)

STAGE = 17

CITATION_STYLES = ("apa", "mla", "chicago", "ieee", "footnote", "ama", "vancouver", "harvard", "nature", "cell", "jama")


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    sources = inputs.get("sources")
    if not sources or not isinstance(sources, list):
        errors.append("sources array is required")
    # For enhanced mode, inline citations are optional (can be extracted from manuscript)
    if not ENHANCED_REFERENCE_MANAGEMENT:
        inline = inputs.get("inlineCitations") or inputs.get("inline_citations")
        if not inline or not isinstance(inline, list):
            errors.append("inlineCitations array is required")
    style = inputs.get("citationStyle") or inputs.get("citation_style")
    if not style or style not in CITATION_STYLES:
        errors.append("citationStyle must be one of: " + ", ".join(CITATION_STYLES))
    return errors


def _source_to_citation_input(s: Dict[str, Any]) -> str:
    """Build a short description of source for LLM."""
    parts = []
    if s.get("authors"):
        authors = s["authors"]
        parts.append("Authors: " + (authors if isinstance(authors, str) else ", ".join(authors)))
    if s.get("title"):
        parts.append("Title: " + str(s["title"]))
    if s.get("publisher"):
        parts.append("Publisher: " + str(s["publisher"]))
    if s.get("publishedAt") or s.get("published_at"):
        parts.append("Date: " + str(s.get("publishedAt") or s.get("published_at")))
    if s.get("url"):
        parts.append("URL: " + str(s["url"]))
    return "; ".join(parts) if parts else str(s.get("id", ""))


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 17: Enhanced Citation Generation.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: sources, inlineCitations, citationStyle, manuscript_text.

    Returns:
        Canonical result with bibliography, citationMap, and enhanced metadata.
    """
    run_id = stage_data.get("runId", "")
    inputs = stage_data.get("inputs") or stage_data
    
    # Try enhanced reference management first
    if ENHANCED_REFERENCE_MANAGEMENT:
        try:
            return await _process_enhanced(workflow_id, run_id, inputs)
        except Exception as e:
            logger.warning(f"Enhanced processing failed, falling back to legacy: {e}")
    
    # Fall back to legacy processing
    return await _process_legacy(workflow_id, run_id, inputs)


async def _process_enhanced(workflow_id: str, run_id: str, inputs: Dict[str, Any]) -> dict:
    """
    Process with enhanced reference management system.
    """
    # Validate inputs for enhanced mode
    validation_errors = _validate_inputs(inputs)
    if validation_errors:
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error(VALIDATION_ERROR, "; ".join(validation_errors))],
        )
    
    # Get enhanced reference management service
    ref_service = await get_reference_service()
    
    # Extract inputs
    sources = inputs.get("sources") or []
    inline_citations = inputs.get("inlineCitations") or inputs.get("inline_citations") or []
    manuscript_text = inputs.get("manuscript_text") or inputs.get("manuscriptText") or ""
    citation_style_str = (inputs.get("citationStyle") or inputs.get("citation_style") or "ama").lower()
    
    # Map style string to CitationStyle enum
    style_mapping = {
        "ama": CitationStyle.AMA,
        "apa": CitationStyle.APA,
        "vancouver": CitationStyle.VANCOUVER,
        "harvard": CitationStyle.HARVARD,
        "chicago": CitationStyle.CHICAGO,
        "nature": CitationStyle.NATURE,
        "cell": CitationStyle.CELL,
        "jama": CitationStyle.JAMA,
        "mla": CitationStyle.MLA,
        "ieee": CitationStyle.IEEE
    }
    
    citation_style = style_mapping.get(citation_style_str, CitationStyle.AMA)
    
    # Create enhanced reference state
    ref_state = ReferenceState(
        study_id=workflow_id,
        manuscript_text=manuscript_text,
        literature_results=sources,
        target_style=citation_style,
        enable_doi_validation=inputs.get("enable_doi_validation", True),
        enable_duplicate_detection=inputs.get("enable_duplicate_detection", True),
        enable_quality_assessment=inputs.get("enable_quality_assessment", True),
        max_references=inputs.get("max_references"),
        manuscript_type=inputs.get("manuscript_type"),
        target_journal=inputs.get("target_journal"),
        research_field=inputs.get("research_field")
    )
    
    # Process references with enhanced system
    ref_result = await ref_service.process_references(ref_state)
    
    # Get journal recommendations if enabled
    journal_recommendations = []
    citation_impact_analysis = {}
    
    if inputs.get('enable_journal_recommendations', False):
        try:
            journal_intel = await get_journal_intelligence()
            journal_recommendations = await journal_intel.recommend_target_journals(
                ref_result.references,
                manuscript_text,
                ref_state.research_field or "general",
                target_impact_range=inputs.get('target_impact_range', (1.0, 100.0)),
                open_access_preference=inputs.get('open_access_preference', False)
            )
            
            citation_impact_analysis = await journal_intel.analyze_citation_impact(
                ref_result.references
            )
        except Exception as e:
            logger.warning(f"Journal intelligence failed: {e}")
    
    # Get monitoring status
    monitoring_status = {}
    try:
        monitor = await get_system_monitor()
        monitoring_status = await monitor.get_system_status_summary()
    except Exception as e:
        logger.warning(f"Monitoring status failed: {e}")
    
    # Convert to legacy format for backward compatibility
    bibliography = [
        {
            "sourceId": citation.reference_id,
            "citationText": citation.formatted_text,
            "style": citation.style.value,
            "isComplete": citation.is_complete,
            "completenessScore": citation.completeness_score
        }
        for citation in ref_result.citations
    ]
    
    # Create citation map
    citation_map = [
        {
            "marker": marker,
            "citationKeys": [ref_id],
            "referenceId": ref_id
        }
        for marker, ref_id in ref_result.citation_map.items()
    ]
    
    # Prepare warnings
    warnings = []
    
    if ref_result.warnings:
        for warning in ref_result.warnings:
            warnings.append({
                "code": warning.warning_type,
                "message": warning.message,
                "severity": warning.severity,
                "referenceId": warning.reference_id,
                "recommendation": warning.recommendation
            })
    
    if ref_result.missing_citations:
        warnings.append({
            "code": "MISSING_CITATIONS",
            "message": f"{len(ref_result.missing_citations)} citations still needed",
            "details": ref_result.missing_citations[:5]  # First 5 examples
        })
    
    if ref_result.duplicate_references:
        warnings.append({
            "code": "DUPLICATES_FOUND",
            "message": f"Found {len(ref_result.duplicate_references)} duplicate groups",
            "duplicateGroups": ref_result.duplicate_references
        })
    
    # Enhanced outputs
    enhanced_outputs = {
        "bibliography": bibliography,
        "citationMap": citation_map,
        "formattedBibliography": ref_result.bibliography,
        "totalReferences": ref_result.total_references,
        "styleComplianceScore": ref_result.style_compliance_score,
        "qualityScores": [
            {
                "referenceId": score.reference_id,
                "overallScore": score.overall_score,
                "qualityLevel": score.quality_level.value,
                "strengths": score.strengths,
                "weaknesses": score.weaknesses,
                "recommendations": score.recommendations
            }
            for score in ref_result.quality_scores
        ],
        "processingMetadata": {
            "processingTimeSeconds": ref_result.processing_time_seconds,
            "apiCallsMade": ref_result.api_calls_made,
            "cacheHits": ref_result.cache_hits,
            "cacheMisses": ref_result.cache_misses,
            "doiVerified": ref_result.doi_verified,
            "enhancedMode": True
        },
        "journalRecommendations": journal_recommendations,
        "citationImpactAnalysis": citation_impact_analysis,
        "monitoringStatus": monitoring_status
    }
    
    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs=enhanced_outputs,
        warnings=warnings if warnings else None,
    )


async def _process_legacy(workflow_id: str, run_id: str, inputs: Dict[str, Any]) -> dict:
    """
    Legacy citation generation processing.
    """
    validation_errors = _validate_inputs(inputs)
    if validation_errors:
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error(VALIDATION_ERROR, "; ".join(validation_errors))],
        )

    sources = inputs.get("sources") or []
    inline_citations = inputs.get("inlineCitations") or inputs.get("inline_citations") or []
    citation_style = (
        inputs.get("citationStyle") or inputs.get("citation_style") or "apa"
    ).lower()
    if citation_style not in CITATION_STYLES:
        citation_style = "apa"
    
    logger.info(f"Processing {len(sources)} sources in legacy mode with {citation_style} style")

    # Build bibliography: one citation per source (same source => same citationText)
    sources_by_id: Dict[str, Dict[str, Any]] = {}
    for s in sources:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        if sid:
            sources_by_id[sid] = s

    bibliography: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    has_incomplete = False

    if not sources_by_id:
        return make_result(
            ok=True,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={
                "bibliography": [],
                "citationMap": [
                    {
                        "marker": inc.get("marker", ""),
                        "citationKeys": inc.get("sourceIds") or inc.get("source_ids") or [],
                    }
                    for inc in inline_citations
                    if isinstance(inc, dict)
                ],
            },
        )

    # Batch citation generation via LLM for all sources
    source_list_text = "\n".join(
        f"- id: {sid}, {_source_to_citation_input(s)}"
        for sid, s in sources_by_id.items()
    )
    system_prompt = f"""You are a citation expert. Output valid JSON only (no markdown).
Generate bibliography entries in {citation_style.upper()} style.
Return: {{ "citations": [ {{ "sourceId": string, "citationText": string }}, ... ] }}.
Same sourceId must always get the same citationText. Use best-effort if metadata is missing."""

    prompt = f"""Generate {citation_style.upper()} bibliography entries for these sources.
Sources (id and metadata):
{source_list_text[:6000]}

Return JSON: {{ "citations": [ {{ "sourceId": "...", "citationText": "..." }}, ... ] }}."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage17_citation_generation",
            max_tokens=4096,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage17_citation_generation")
    except Exception as e:
        logger.exception("Stage 17 LLM failed: %s", e)
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error("UPSTREAM_5XX", str(e), retryable=True)],
        )

    if not parsed or not isinstance(parsed.get("citations"), list):
        # Fallback: best-effort citation from metadata
        has_incomplete = True
        for sid, s in sources_by_id.items():
            citation_text = _source_to_citation_input(s)
            if len(citation_text) < 10:
                citation_text = f"[{sid}] (incomplete metadata)"
            bibliography.append({"sourceId": sid, "citationText": citation_text})
        warnings.append(
            {
                "code": INCOMPLETE_METADATA,
                "message": "LLM did not return valid citations; used best-effort from metadata",
            }
        )
    else:
        seen_ids = set()
        for c in parsed["citations"]:
            if not isinstance(c, dict):
                continue
            sid = c.get("sourceId") or c.get("source_id")
            ct = c.get("citationText") or c.get("citation_text")
            if not sid:
                continue
            if sid not in sources_by_id:
                continue
            if not ct or len(ct.strip()) < 2:
                has_incomplete = True
                ct = _source_to_citation_input(sources_by_id[sid]) or f"[{sid}]"
            bibliography.append({"sourceId": sid, "citationText": ct.strip()})
            seen_ids.add(sid)
        # Ensure every source has an entry
        for sid in sources_by_id:
            if sid not in seen_ids:
                has_incomplete = True
                bibliography.append(
                    {
                        "sourceId": sid,
                        "citationText": _source_to_citation_input(sources_by_id[sid])
                        or f"[{sid}]",
                    }
                )
        if has_incomplete:
            warnings.append(
                {
                    "code": INCOMPLETE_METADATA,
                    "message": "Some sources had missing metadata; used best-effort citations",
                }
            )

    # citationMap: marker -> citationKeys (sourceIds for that marker)
    citation_map: List[Dict[str, Any]] = []
    for inc in inline_citations:
        if not isinstance(inc, dict):
            continue
        marker = inc.get("marker", "")
        source_ids = inc.get("sourceIds") or inc.get("source_ids") or []
        if not isinstance(source_ids, list):
            source_ids = [source_ids] if source_ids else []
        citation_map.append({"marker": marker, "citationKeys": source_ids})

    # Add legacy mode indicator
    outputs = {
        "bibliography": bibliography, 
        "citationMap": citation_map,
        "processingMetadata": {
            "enhancedMode": False,
            "legacyMode": True,
            "totalReferences": len(bibliography)
        },
        "journalRecommendations": [],
        "citationImpactAnalysis": {},
        "monitoringStatus": {}
    }
    
    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs=outputs,
        warnings=warnings if warnings else None,
    )
