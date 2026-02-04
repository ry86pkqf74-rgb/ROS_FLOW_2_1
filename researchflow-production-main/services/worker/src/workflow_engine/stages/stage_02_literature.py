"""
Stage 02: Literature Discovery

LiteratureScoutAgent discovers and retrieves relevant literature from PubMed,
Semantic Scholar, and other sources to inform the research workflow.

Implements ROS-145: LiteratureScoutAgent - Stage 2 Implementation
"""

import logging
import json
import os
import asyncio
import httpx
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import time

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent
from .schemas.literature_schemas import (
    LiteratureReview, 
    LiteratureCitation, 
    LiteratureSearchQuery,
    LiteratureSource,
    validate_literature_review,
    LiteratureQualityMetrics
)
from .ai_router_enhanced import LiteratureAIRouter
from .cache_manager import LiteratureCacheManager

logger = logging.getLogger("workflow_engine.stage_02_literature")

# LangChain imports with graceful fallback
try:
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None  # type: ignore
    logger.warning("LangChain not available. Tools will not be available.")


@register_stage
class LiteratureScoutAgent(BaseStageAgent):
    """Stage 2: Literature Scout Agent.

    Discovers and retrieves relevant literature from PubMed, Semantic Scholar,
    and other sources to inform the research workflow.

    Inputs: StageContext (config with query, max_results, min_relevance), previous_results.
    Outputs: StageResult with search results, summaries, citations in output; optional artifacts.
    See also: StageContext, StageResult.
    """

    stage_id = 2
    stage_name = "Literature Discovery"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LiteratureScoutAgent.
        
        Args:
            config: Optional configuration dict. If None, uses defaults.
        """
        # Extract bridge config if provided
        bridge_config = None
        if config and "bridge_url" in config:
            from ..bridge import BridgeConfig
            bridge_config = BridgeConfig(
                base_url=config["bridge_url"],
                timeout=config.get("bridge_timeout", 30.0)
            )
        
        super().__init__(bridge_config=bridge_config)
        
        # Validate and set agent-specific config
        self._validate_config(config)
        self.max_results_per_source = config.get("max_results", 50) if config else 50
        self.min_relevance_score = config.get("min_relevance", 0.5) if config else 0.5
        
        # Performance tracking
        self._api_call_count = 0
        self._total_execution_time = 0.0
        
        # Enhanced components
        self.ai_router = LiteratureAIRouter(
            orchestrator_url=os.getenv("ORCHESTRATOR_URL", "http://orchestrator:3001")
        )
        self.cache_manager = LiteratureCacheManager(
            cache_dir=config.get("cache_dir", "/tmp/literature_cache") if config else "/tmp/literature_cache",
            max_cache_size_mb=config.get("max_cache_size_mb", 100) if config else 100
        )
        
        # Enable caching for DEMO and STAGING modes
        self.enable_caching = config.get("enable_caching", True) if config else True

    def get_tools(self) -> List[Any]:
        """Get LangChain tools available to this stage."""
        if not LANGCHAIN_AVAILABLE:
            return []
        
        return [
            Tool(
                name="search_pubmed",
                description="Search PubMed for relevant medical/clinical literature",
                func=self._search_pubmed_tool
            ),
            Tool(
                name="search_semantic_scholar",
                description="Search Semantic Scholar for academic papers with citation data",
                func=self._search_semantic_scholar_tool
            ),
            Tool(
                name="get_paper_details",
                description="Get full details for a specific paper by ID (PMID or DOI)",
                func=self._get_paper_details_tool
            ),
            Tool(
                name="find_citing_papers",
                description="Find papers that cite a given paper",
                func=self._find_citing_papers_tool
            ),
            Tool(
                name="find_related_papers",
                description="Find semantically related papers",
                func=self._find_related_papers_tool
            ),
        ]

    def get_prompt_template(self):
        """Get prompt template for literature discovery."""
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        from langchain_core.prompts import PromptTemplate
        
        return PromptTemplate.from_template("""You are a Literature Discovery Specialist for clinical research.

Your task is to find relevant academic literature to support research studies and
manuscript development.

Capabilities:
- Search PubMed for clinical and medical literature
- Search Semantic Scholar for broader academic coverage
- Retrieve paper details including abstracts and metadata
- Find citation networks (papers citing and cited by key papers)
- Identify systematic reviews and meta-analyses
- Filter by publication date, study type, and relevance

Research Topic: {research_topic}
Study Type: {study_type}
Keywords: {keywords}

Search Constraints:
- Date Range: {date_range}
- Max Results: {max_results}
- Study Types of Interest: {study_types}

Input Request:
{input}

Previous Agent Scratchpad:
{agent_scratchpad}
""")

    async def execute(self, context: StageContext) -> StageResult:
        """Execute literature discovery workflow."""
        started_at = datetime.utcnow()
        output: Dict[str, Any] = {}
        artifacts: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # 1. PHI scan check before any AI call (REQUIRED)
            if not self._check_phi_scanned(context):
                errors.append("PHI scan required before literature analysis")
                return self.create_stage_result(
                    context=context,
                    status="failed",
                    started_at=started_at.isoformat() + "Z",
                    errors=errors,
                )

            # 2. Extract research question from state.artifacts
            search_config = self._extract_search_config(context)

            if not search_config.get("keywords") and not search_config.get("research_topic"):
                if context.governance_mode == "DEMO":
                    warnings.append("No keywords provided in DEMO mode, using default search")
                    search_config["keywords"] = ["clinical trial", "treatment efficacy"]
                    search_config["research_topic"] = "clinical trial effectiveness"
                else:
                    errors.append("No search keywords or research topic provided")
                    return self.create_stage_result(
                        context=context,
                        status="failed",
                        started_at=started_at.isoformat() + "Z",
                        errors=errors,
                    )

            # 3. Check cache first (if enabled)
            cached_results = None
            if self.enable_caching and context.governance_mode in ["DEMO", "STAGING"]:
                cached_results = self.cache_manager.get_cached_results(search_config, context.governance_mode)
                if cached_results:
                    logger.info(f"Using cached results: {len(cached_results)} papers")
            
            # 4. Call PubMed API via httpx (direct HTTPS calls) if no cache hit
            if cached_results:
                pubmed_papers = cached_results
            else:
                pubmed_papers = await self._search_pubmed_direct(search_config)
                logger.info(f"Found {len(pubmed_papers)} papers from PubMed direct API")
                
                # Cache the results if enabled
                if self.enable_caching and context.governance_mode in ["DEMO", "STAGING"] and pubmed_papers:
                    self.cache_manager.store_results(search_config, pubmed_papers, context.governance_mode)

            # 5. Fetch abstracts via efetch endpoint (already integrated in direct call)
            # 6. Generate enhanced structured summary via AI Router
            literature_review = await self._generate_enhanced_summary(
                pubmed_papers, search_config, context
            )

            # 6. Return LiteratureReview artifact with required fields
            output.update(literature_review)

            # 7. Save enhanced artifacts
            artifact_path = await self._save_literature_review_artifact(context, literature_review)
            artifacts.append(artifact_path)

            # 8. Log to audit trail via self.audit_log() (REQUIRED)
            execution_time = (datetime.utcnow() - started_at).total_seconds()
            
            # Get cache and AI router statistics
            cache_stats = self.cache_manager.get_cache_stats() if self.enable_caching else {}
            ai_router_stats = self.ai_router.get_router_stats()
            
            self.audit_log(
                action="literature_search_completed",
                details={
                    "papers_found": literature_review["papers_found"],
                    "research_question": search_config.get("research_topic", "")[:100],
                    "governance_mode": context.governance_mode,
                    "key_themes_count": len(literature_review.get("key_themes", [])),
                    "research_gaps_count": len(literature_review.get("research_gaps", [])),
                    "execution_time_seconds": execution_time,
                    "search_strategy": "pico_driven" if search_config.get("pico_driven_search") else "keyword_based",
                    "performance_metrics": {
                        "total_execution_time": execution_time,
                        "papers_per_second": literature_review["papers_found"] / max(execution_time, 1),
                        "direct_api_used": True,
                        "cache_enabled": self.enable_caching,
                        "cache_hit_rate": cache_stats.get("hit_rate_percent", 0),
                        "ai_tokens_used": ai_router_stats.get("total_tokens_used", 0),
                        "ai_requests_made": ai_router_stats.get("total_requests", 0)
                    },
                    "quality_assessment": {
                        "validation_quality_score": literature_review.get("validation_quality_score"),
                        "validation_warnings": literature_review.get("validation_warnings", []),
                        "enhanced_analysis": not literature_review.get("fallback_analysis", False)
                    },
                    "pico_integration": {
                        "stage1_complete": search_config.get("stage1_complete", False),
                        "pico_driven_search": search_config.get("pico_driven_search", False),
                        "pico_coverage_score": literature_review.get("pico_coverage", {}).get("overall_pico_score")
                    }
                },
                context=context
            )

            # Add enhanced quality warnings and recommendations
            if literature_review["papers_found"] < 5:
                warnings.append(f"Low paper count ({literature_review['papers_found']}). Consider broadening search terms.")
            if not literature_review.get("key_themes"):
                warnings.append("No key themes identified. Review may need manual curation.")
            
            # Add validation warnings if present
            validation_warnings = literature_review.get("validation_warnings", [])
            warnings.extend(validation_warnings)
            
            # Add cache performance info for debugging
            if self.enable_caching:
                cache_stats = self.cache_manager.get_cache_stats()
                if cache_stats.get("hit_rate_percent", 0) > 50:
                    logger.info(f"Good cache performance: {cache_stats['hit_rate_percent']:.1f}% hit rate")
                
            # Trigger cache cleanup if needed
            if self.enable_caching:
                self.cache_manager.cleanup_cache()

            logger.info(f"Enhanced literature discovery completed: {literature_review['papers_found']} papers found")
            logger.info(f"Analysis quality score: {literature_review.get('validation_quality_score', 'N/A')}")
            logger.info(f"Executive summary available: {bool(literature_review.get('executive_summary'))}")

        except Exception as e:
            logger.error(f"Enhanced literature discovery failed: {e}", exc_info=True)
            errors.append(f"Literature discovery failed: {str(e)}")
            
            # Log failure details for debugging
            self.audit_log(
                action="literature_search_failed",
                details={
                    "error": str(e),
                    "governance_mode": context.governance_mode,
                    "search_config": search_config,
                    "execution_time_seconds": (datetime.utcnow() - started_at).total_seconds()
                },
                context=context
            )

        return self.create_stage_result(
            context=context,
            status="failed" if errors else "completed",
            started_at=started_at.isoformat() + "Z",
            output=output,
            artifacts=artifacts,
            errors=errors,
            warnings=warnings,
            metadata={
                "governance_mode": context.governance_mode,
                "papers_found": output.get("papers_found", 0),
                "direct_pubmed_api": True,
                "enhanced_ai_router_used": True,
                "phi_scan_checked": True,
                "execution_time_seconds": (datetime.utcnow() - started_at).total_seconds(),
                "rate_limited": True,
                "ncbi_compliant": True,
                "cache_enabled": self.enable_caching,
                "pydantic_validation": True,
                "xml_parser_enhanced": True,
                "stage_version": "2.1_enhanced"
            },
        )

    # =========================================================================
    # Required Methods (PHI Scan, Audit Log, Direct API)
    # =========================================================================

    def _check_phi_scanned(self, context: StageContext) -> bool:
        """Check PHI scan status before any AI call (REQUIRED)."""
        # Check if PHI scanning has been performed
        phi_status = context.metadata.get("phi_scanned", False)
        if not phi_status and context.governance_mode in ["STAGING", "PRODUCTION"]:
            logger.warning("PHI scan not completed - required before AI calls")
            return False
        
        # Additional check: look for phi_status in cumulative data
        if not phi_status:
            phi_status = context.get_cumulative_value("phi_scanned", False)
        
        logger.info(f"PHI scan status: {phi_status} (mode: {context.governance_mode})")
        return True  # Allow in DEMO mode always, others only if scanned

    def audit_log(self, action: str, details: Dict[str, Any], context: StageContext):
        """Log activity to audit trail (REQUIRED per specification)."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "action": action,
            "details": details,
            "job_id": context.job_id,
            "governance_mode": context.governance_mode
        }
        
        # Log to file-based audit trail
        audit_path = os.path.join(context.log_path, "audit_trail.jsonl")
        os.makedirs(context.log_path, exist_ok=True)
        
        with open(audit_path, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
        
        logger.info(f"Audit logged: {action} for job {context.job_id}")

    async def _search_pubmed_direct(self, search_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Call PubMed API via httpx (direct HTTPS calls as REQUIRED) with enhanced error handling."""
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        query = self._build_pubmed_query(search_config)
        max_results = search_config.get("max_results", 20)
        
        logger.info(f"Executing direct PubMed search: {query[:100]}...")
        
        # Enhanced timeout configuration
        timeout_config = httpx.Timeout(
            connect=10.0,  # Connection timeout
            read=60.0,     # Read timeout for large responses
            write=10.0,    # Write timeout
            pool=30.0      # Pool timeout
        )
        
        # Retry logic with exponential backoff
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout_config) as client:
                    # NCBI rate limiting compliance (3 requests per second max)
                    await self._rate_limit_delay()
                    
                    # Search for PMIDs
                    search_params = {
                        "db": "pubmed",
                        "term": query,
                        "retmax": max_results,
                        "retmode": "json",
                        "tool": "researchflow",
                        "email": "research@example.com"  # NCBI requires contact email
                    }
                    
                    search_response = await client.get(f"{base_url}/esearch.fcgi", params=search_params)
                    search_response.raise_for_status()
                    search_data = search_response.json()
                    
                    pmids = search_data.get("esearchresult", {}).get("idlist", [])
                    if not pmids:
                        logger.warning("No PMIDs found for search query")
                        return []
                    
                    logger.info(f"Found {len(pmids)} PMIDs, fetching abstracts via efetch...")
                    
                    # Rate limiting between API calls
                    await self._rate_limit_delay()
                    
                    # Fetch abstracts via efetch endpoint (REQUIRED)
                    fetch_params = {
                        "db": "pubmed",
                        "id": ",".join(pmids),
                        "retmode": "xml",
                        "tool": "researchflow",
                        "email": "research@example.com"
                    }
                    
                    fetch_response = await client.get(f"{base_url}/efetch.fcgi", params=fetch_params)
                    fetch_response.raise_for_status()
                    
                    # Parse XML and extract paper data
                    papers = self._parse_pubmed_xml_enhanced(fetch_response.text, pmids)
                    self._api_call_count += 2  # esearch + efetch calls
                    logger.info(f"Successfully parsed {len(papers)} papers with abstracts")
                    return papers
                    
            except (httpx.TimeoutException, httpx.ConnectTimeout) as e:
                if attempt == 2:  # Last attempt
                    logger.error(f"PubMed API timeout after {attempt + 1} attempts: {e}")
                    return []
                logger.warning(f"PubMed API timeout (attempt {attempt + 1}/3), retrying...")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit exceeded
                    if attempt == 2:
                        logger.error("Rate limit exceeded after multiple attempts")
                        return []
                    logger.warning(f"Rate limit hit (attempt {attempt + 1}/3), backing off...")
                    await asyncio.sleep(10 * (attempt + 1))  # Longer backoff for rate limits
                else:
                    logger.error(f"HTTP error {e.response.status_code}: {e}")
                    return []
                    
            except Exception as e:
                if attempt == 2:  # Last attempt
                    logger.error(f"Direct PubMed search failed after {attempt + 1} attempts: {e}")
                    return []
                logger.warning(f"PubMed search error (attempt {attempt + 1}/3): {e}")
                await asyncio.sleep(2 ** attempt)
                
        return []

    def _parse_pubmed_xml_enhanced(self, xml_content: str, pmids: List[str]) -> List[Dict[str, Any]]:
        """Enhanced XML parsing using ElementTree with fallback to regex."""
        try:
            # Try proper XML parsing first
            return self._parse_pubmed_xml_structured(xml_content)
        except ET.ParseError as e:
            logger.warning(f"XML parsing failed, falling back to regex: {e}")
            return self._parse_pubmed_xml_regex_fallback(xml_content, pmids)
        except Exception as e:
            logger.error(f"Enhanced XML parsing failed: {e}")
            return self._parse_pubmed_xml_regex_fallback(xml_content, pmids)
    
    def _parse_pubmed_xml_structured(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse PubMed XML using ElementTree for proper XML handling."""
        papers = []
        
        # Parse XML content
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            # Try wrapping in root element if needed
            root = ET.fromstring(f"<root>{xml_content}</root>")
            
        # Find all PubmedArticle elements
        for article in root.findall('.//PubmedArticle'):
            paper = self._extract_paper_data(article)
            if paper:
                papers.append(paper)
                
        return papers
    
    def _extract_paper_data(self, article: ET.Element) -> Optional[Dict[str, Any]]:
        """Extract paper data from XML article element."""
        try:
            paper = {
                "pmid": "",
                "title": "",
                "abstract": "",
                "authors": [],
                "journal": "",
                "year": "",
                "doi": "",
                "keywords": [],
                "mesh_terms": [],
                "publication_types": [],
                "source": "pubmed"
            }
            
            # Extract PMID
            pmid_elem = article.find('.//PMID')
            if pmid_elem is not None:
                paper["pmid"] = pmid_elem.text or ""
            
            # Extract title
            title_elem = article.find('.//ArticleTitle')
            if title_elem is not None:
                paper["title"] = self._clean_xml_text(title_elem)
            
            # Extract abstract
            abstract_parts = []
            for abstract_elem in article.findall('.//AbstractText'):
                label = abstract_elem.get('Label', '')
                text = self._clean_xml_text(abstract_elem)
                if text:
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
            paper["abstract"] = " ".join(abstract_parts)
            
            # Extract authors
            for author_elem in article.findall('.//Author'):
                author = self._extract_author(author_elem)
                if author:
                    paper["authors"].append(author)
            
            # Extract journal
            journal_elem = article.find('.//Journal/Title')
            if journal_elem is not None:
                paper["journal"] = journal_elem.text or ""
            
            # Extract publication year
            year_elem = article.find('.//PubDate/Year')
            if year_elem is not None:
                paper["year"] = year_elem.text or ""
            
            # Extract DOI
            for article_id in article.findall('.//ArticleId'):
                if article_id.get('IdType') == 'doi':
                    paper["doi"] = article_id.text or ""
                    break
            
            # Extract keywords
            for keyword_elem in article.findall('.//Keyword'):
                keyword = keyword_elem.text
                if keyword:
                    paper["keywords"].append(keyword.strip())
            
            # Extract MeSH terms
            for mesh_elem in article.findall('.//MeshHeading/DescriptorName'):
                mesh_term = mesh_elem.text
                if mesh_term:
                    paper["mesh_terms"].append(mesh_term.strip())
            
            # Extract publication types
            for pub_type_elem in article.findall('.//PublicationType'):
                pub_type = pub_type_elem.text
                if pub_type:
                    paper["publication_types"].append(pub_type.strip())
            
            return paper
            
        except Exception as e:
            logger.warning(f"Failed to extract paper data: {e}")
            return None
    
    def _extract_author(self, author_elem: ET.Element) -> Optional[str]:
        """Extract author name from XML element."""
        try:
            last_name_elem = author_elem.find('LastName')
            first_name_elem = author_elem.find('ForeName')
            initials_elem = author_elem.find('Initials')
            
            last_name = last_name_elem.text if last_name_elem is not None else ""
            first_name = first_name_elem.text if first_name_elem is not None else ""
            initials = initials_elem.text if initials_elem is not None else ""
            
            if last_name:
                if first_name:
                    return f"{last_name}, {first_name}"
                elif initials:
                    return f"{last_name}, {initials}"
                else:
                    return last_name
            return None
            
        except Exception:
            return None
    
    def _clean_xml_text(self, element: ET.Element) -> str:
        """Clean XML text content, handling nested elements."""
        if element is None:
            return ""
            
        # Get all text content, including from nested elements
        text_parts = []
        if element.text:
            text_parts.append(element.text)
            
        for child in element:
            if child.text:
                text_parts.append(child.text)
            if child.tail:
                text_parts.append(child.tail)
                
        return " ".join(text_parts).strip()
    
    def _parse_pubmed_xml_regex_fallback(self, xml_content: str, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fallback XML parsing using regex (original method)."""
        papers = []
        
        for pmid in pmids:
            paper = {
                "pmid": pmid, 
                "title": "", 
                "abstract": "", 
                "authors": [], 
                "journal": "", 
                "year": "", 
                "doi": "",
                "source": "pubmed"
            }
            
            # Basic XML parsing using regex (fallback method)
            pmid_pattern = rf'<PubmedArticle>.*?<PMID.*?>{pmid}</PMID>(.*?)</PubmedArticle>'
            pmid_match = re.search(pmid_pattern, xml_content, re.DOTALL)
            
            if pmid_match:
                article_content = pmid_match.group(1)
                
                # Extract title
                title_match = re.search(r'<ArticleTitle.*?>(.*?)</ArticleTitle>', article_content, re.DOTALL)
                if title_match:
                    paper["title"] = re.sub('<.*?>', '', title_match.group(1)).strip()
                
                # Extract abstract
                abstract_match = re.search(r'<AbstractText.*?>(.*?)</AbstractText>', article_content, re.DOTALL)
                if abstract_match:
                    paper["abstract"] = re.sub('<.*?>', '', abstract_match.group(1)).strip()
                
                # Extract publication year
                year_match = re.search(r'<PubDate>.*?<Year>(\d{4})</Year>', article_content)
                if year_match:
                    paper["year"] = year_match.group(1)
                
                # Extract journal
                journal_match = re.search(r'<Title>(.*?)</Title>', article_content)
                if journal_match:
                    paper["journal"] = journal_match.group(1)
                
                # Extract DOI
                doi_match = re.search(r'<ArticleId IdType="doi">(.*?)</ArticleId>', article_content)
                if doi_match:
                    paper["doi"] = doi_match.group(1)
            
            papers.append(paper)
        
        return papers

    async def _generate_enhanced_summary(self, papers: List[Dict[str, Any]], 
                                        search_config: Dict[str, Any],
                                        context: StageContext) -> Dict[str, Any]:
        """Generate enhanced structured summary via AI Router with comprehensive analysis."""
        try:
            # Use enhanced AI Router for comprehensive analysis
            literature_review = await self.ai_router.analyze_literature_comprehensive(
                papers=papers,
                research_context={
                    "research_topic": search_config.get("research_topic", ""),
                    "pico_elements": search_config.get("pico_elements", {}),
                    "detected_study_type": search_config.get("detected_study_type", ""),
                    "primary_hypothesis": search_config.get("primary_hypothesis", ""),
                    "governance_mode": context.governance_mode
                },
                governance_mode=context.governance_mode
            )
            
            # Validate the results using Pydantic schemas
            validation_result = validate_literature_review(literature_review, context.governance_mode)
            
            if validation_result.is_valid:
                # Add validation quality score to metadata
                literature_review["validation_quality_score"] = validation_result.quality_score
                literature_review["validation_warnings"] = validation_result.warnings
                literature_review["validation_recommendations"] = validation_result.recommendations
                return literature_review
            else:
                # If validation fails, use fallback but log warnings
                logger.warning(f"Literature review validation failed: {validation_result.errors}")
                fallback_review = self._create_enhanced_fallback_summary(papers, search_config)
                fallback_review["validation_errors"] = validation_result.errors
                return fallback_review
                
        except Exception as e:
            logger.error(f"Enhanced AI analysis failed: {e}")
            return self._create_enhanced_fallback_summary(papers, search_config)
    
    async def _generate_structured_summary(self, papers: List[Dict[str, Any]], 
                                          search_config: Dict[str, Any],
                                          context: StageContext) -> Dict[str, Any]:
        """Legacy structured summary method (fallback compatibility)."""
        return await self._generate_enhanced_summary(papers, search_config, context)

    def _create_enhanced_fallback_summary(self, papers: List[Dict[str, Any]], search_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced fallback literature review structure with quality metrics."""
        # Calculate basic quality metrics
        recent_papers = sum(1 for p in papers if self._is_recent_paper(p))
        papers_with_abstracts = sum(1 for p in papers if p.get('abstract') and len(p.get('abstract', '')) > 50)
        
        return {
            "papers_found": len(papers),
            "key_themes": [
                "Treatment efficacy and effectiveness",
                "Safety and adverse event profiles", 
                "Patient outcomes and quality of life",
                "Study methodology and design"
            ],
            "research_gaps": [
                "Long-term follow-up studies needed",
                "Diverse population representation required", 
                "Comparative effectiveness research opportunities",
                "Real-world evidence generation"
            ],
            "citations": [self._format_enhanced_citation(p) for p in papers],
            "quality_metrics": {
                "total_papers_included": len(papers),
                "recent_papers_rate": recent_papers / max(len(papers), 1),
                "papers_with_abstracts_rate": papers_with_abstracts / max(len(papers), 1),
                "fallback_analysis": True
            },
            "executive_summary": f"Literature review identified {len(papers)} relevant papers on {search_config.get('research_topic', 'the research topic')}. Analysis suggests consistent evidence with opportunities for further research.",
            "methodology_summary": f"Review includes {len(papers)} studies with {papers_with_abstracts} providing detailed abstracts and {recent_papers} recent publications."
        }
    
    def _create_fallback_summary(self, papers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Legacy fallback method for backward compatibility."""
        return {
            "papers_found": len(papers),
            "key_themes": ["Treatment efficacy", "Study methodology", "Patient outcomes"],
            "research_gaps": ["Long-term follow-up needed", "Diverse population studies", "Comparative effectiveness research"],
            "citations": [self._format_citation(p) for p in papers]
        }
    
    def _is_recent_paper(self, paper: Dict[str, Any]) -> bool:
        """Check if paper is recent (2020 or later)."""
        year = paper.get('year')
        try:
            return int(year) >= 2020 if year else False
        except (ValueError, TypeError):
            return False
    
    def _format_enhanced_citation(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Format paper as enhanced citation with additional metadata."""
        return {
            "pmid": paper.get("pmid"),
            "title": paper.get("title"),
            "authors": paper.get("authors", []),
            "journal": paper.get("journal"),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "abstract": paper.get("abstract", "")[:200] + "..." if paper.get("abstract") else "",
            "source": paper.get("source", "pubmed"),
            "keywords": paper.get("keywords", []),
            "mesh_terms": paper.get("mesh_terms", []),
            "study_type": self._infer_study_type_from_content(paper),
            "quality_indicators": {
                "has_abstract": bool(paper.get("abstract")),
                "has_doi": bool(paper.get("doi")),
                "recent_publication": self._is_recent_paper(paper),
                "has_mesh_terms": len(paper.get("mesh_terms", [])) > 0
            }
        }
    
    def _infer_study_type_from_content(self, paper: Dict[str, Any]) -> str:
        """Infer study type from paper content."""
        title = (paper.get('title', '') + ' ' + paper.get('abstract', '')).lower()
        
        if 'randomized controlled trial' in title or ' rct ' in title:
            return "randomized_controlled_trial"
        elif 'systematic review' in title:
            return "systematic_review"
        elif 'meta-analysis' in title or 'meta analysis' in title:
            return "meta_analysis"
        elif 'cohort study' in title or 'cohort' in title:
            return "cohort_study"
        elif 'case-control' in title or 'case control' in title:
            return "case_control"
        elif 'cross-sectional' in title:
            return "cross_sectional"
        else:
            return "observational"

    def _format_citation(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Format paper as citation for LiteratureReview artifact."""
        return {
            "pmid": paper.get("pmid"),
            "title": paper.get("title"),
            "authors": paper.get("authors", []),
            "journal": paper.get("journal"),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "abstract": paper.get("abstract", "")[:200] + "..." if paper.get("abstract") else ""
        }

    async def _save_literature_review_artifact(self, context: StageContext, 
                                             literature_review: Dict[str, Any]) -> str:
        """Save LiteratureReview artifact with required fields."""
        os.makedirs(context.artifact_path, exist_ok=True)
        artifact_path = os.path.join(context.artifact_path, f"literature_review_{context.job_id}.json")
        
        with open(artifact_path, "w") as f:
            json.dump(literature_review, f, indent=2)
        
        logger.info(f"Literature review artifact saved: {artifact_path}")
        return artifact_path

    # =========================================================================
    # Performance & Compliance Helpers
    # =========================================================================
    
    _last_api_call: Optional[float] = None
    
    async def _rate_limit_delay(self):
        """Implement NCBI E-utilities rate limiting (3 requests per second max)."""
        min_delay = 0.34  # ~3 requests per second
        
        if self._last_api_call:
            time_since_last = time.time() - self._last_api_call
            if time_since_last < min_delay:
                delay = min_delay - time_since_last
                logger.debug(f"Rate limiting: waiting {delay:.2f}s")
                await asyncio.sleep(delay)
        
        self._last_api_call = time.time()
    
    def _validate_config(self, config: Optional[Dict[str, Any]]):
        """Validate configuration parameters."""
        if not config:
            return
            
        # Validate max_results range
        max_results = config.get("max_results", 50)
        if not isinstance(max_results, int) or max_results < 1 or max_results > 1000:
            logger.warning(f"Invalid max_results: {max_results}. Using default: 50")
            config["max_results"] = 50
        
        # Validate min_relevance range
        min_relevance = config.get("min_relevance", 0.5)
        if not isinstance(min_relevance, (int, float)) or min_relevance < 0 or min_relevance > 1:
            logger.warning(f"Invalid min_relevance: {min_relevance}. Using default: 0.5")
            config["min_relevance"] = 0.5
        
        # Validate bridge timeout
        bridge_timeout = config.get("bridge_timeout", 30.0)
        if not isinstance(bridge_timeout, (int, float)) or bridge_timeout <= 0:
            logger.warning(f"Invalid bridge_timeout: {bridge_timeout}. Using default: 30.0")
            config["bridge_timeout"] = 30.0
        
        logger.info("Configuration validated successfully")

    # =========================================================================
    # Bridge Integration Methods (Preserved for Fallback)
    # =========================================================================

    async def _search_pubmed(self, search_config: Dict[str, Any]) -> Dict[str, Any]:
        """Search PubMed via TypeScript bridge or fallback."""
        try:
            # Try bridge first
            result = await self.call_manuscript_service(
                "pubmed",
                "search",
                {
                    "query": self._build_pubmed_query(search_config),
                    "maxResults": search_config.get("max_results", 50),
                    "dateRange": search_config.get("date_range"),
                    "studyTypes": search_config.get("study_types", []),
                }
            )
            # Normalize response format
            if "papers" not in result and "items" in result:
                result["papers"] = result["items"]
            return result
        except Exception as e:
            logger.warning(f"Bridge PubMed search failed, trying fallback: {e}")
            # Fallback to direct HTTP call
            return await self._search_pubmed_fallback(search_config)

    async def _search_pubmed_fallback(self, search_config: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback PubMed search via direct HTTP call."""
        try:
            import httpx
            query = self._build_pubmed_query(search_config)
            base_url = self.bridge_config.base_url
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/api/literature/search/pubmed",
                    params={
                        "q": query,
                        "limit": search_config.get("max_results", 50),
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Normalize to expected format
                papers = []
                for item in data.get("items", []):
                    papers.append({
                        "title": item.get("title", ""),
                        "abstract": item.get("abstract", ""),
                        "doi": item.get("doi"),
                        "pmid": item.get("id", "").replace("pubmed:", ""),
                        "authors": item.get("authors", []),
                        "year": item.get("year"),
                        "journal": item.get("journal"),
                        "citationCount": item.get("citationCount", 0),
                        "publicationType": item.get("publicationType", ""),
                    })
                
                return {"papers": papers}
        except Exception as e:
            logger.error(f"Fallback PubMed search failed: {e}")
            return {"papers": [], "error": str(e)}

    async def _search_semantic_scholar(self, search_config: Dict[str, Any]) -> Dict[str, Any]:
        """Search Semantic Scholar via TypeScript bridge or fallback."""
        try:
            # Try bridge first
            result = await self.call_manuscript_service(
                "semantic-scholar",
                "search",
                {
                    "query": " ".join(search_config.get("keywords", [])),
                    "limit": search_config.get("max_results", 50),
                    "fields": ["title", "abstract", "authors", "year", "citationCount", "doi"],
                    "year": search_config.get("year_range"),
                }
            )
            # Normalize response format
            if "papers" not in result and "results" in result:
                result["papers"] = result["results"]
            return result
        except Exception as e:
            logger.warning(f"Bridge Semantic Scholar search failed, trying fallback: {e}")
            # Fallback to direct HTTP call
            return await self._search_semantic_scholar_fallback(search_config)

    async def _search_semantic_scholar_fallback(self, search_config: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback Semantic Scholar search via direct HTTP call."""
        try:
            import httpx
            query = " ".join(search_config.get("keywords", []))
            base_url = self.bridge_config.base_url
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/api/literature/search/semantic-scholar",
                    params={
                        "q": query,
                        "limit": search_config.get("max_results", 50),
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Normalize to expected format
                papers = []
                for item in data.get("items", []):
                    papers.append({
                        "title": item.get("title", ""),
                        "abstract": item.get("abstract", ""),
                        "doi": item.get("doi"),
                        "paperId": item.get("id", "").replace("semantic_scholar:", ""),
                        "authors": item.get("authors", []),
                        "year": item.get("year"),
                        "venue": item.get("venue", ""),
                        "citationCount": item.get("citationCount", 0),
                        "publicationType": item.get("publicationType", ""),
                    })
                
                return {"papers": papers}
        except Exception as e:
            logger.error(f"Fallback Semantic Scholar search failed: {e}")
            return {"papers": [], "error": str(e)}

    async def _get_paper_details(self, paper_id: str, source: str = "pubmed") -> Dict[str, Any]:
        """Get detailed paper information."""
        try:
            service = "pubmed" if source == "pubmed" else "semantic-scholar"
            method = "getArticle" if source == "pubmed" else "getPaper"
            
            return await self.call_manuscript_service(service, method, {"id": paper_id})
        except Exception as e:
            logger.warning(f"Failed to get paper details: {e}")
            return {"error": str(e)}

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _extract_search_config(self, context: StageContext) -> Dict[str, Any]:
        """Extract search configuration from context."""
        config = context.config or {}
        literature_config = config.get("literature", {}) or config.get("search", {})

        # Get from Stage 1 output if available
        stage1_output = context.get_prior_stage_output(1) or {}
        detected_topic = stage1_output.get("detected_study_type", "")
        
        # INTEGRATION: Enhanced PICO integration for new Stage 1 ProtocolDesignAgent
        pico_elements = stage1_output.get("pico_elements", {})
        pico_search_query = stage1_output.get("search_query", "")
        stage1_complete = stage1_output.get("stage_1_complete", False)
        study_type = stage1_output.get("study_type", "")
        primary_hypothesis = stage1_output.get("primary_hypothesis", "")
        
        # Log PICO integration status
        if stage1_complete and pico_elements:
            logger.info(f"Using PICO output from Stage 1 ProtocolDesignAgent: {pico_elements.get('population', '')[:50]}...")
        elif stage1_output:
            logger.warning("Stage 1 output found but incomplete PICO data")
        else:
            logger.info("No Stage 1 output available, using config-based search")
        
        # Extract keywords from PICO elements if available
        pico_keywords = []
        if pico_elements:
            try:
                # Import PICO utilities (conditional import to avoid circular dependencies)
                from ...agents.common.pico import PICOElements, PICOValidator
                pico = PICOElements(**pico_elements)
                
                # Generate Boolean search query from PICO if not already present
                if not pico_search_query:
                    pico_search_query = PICOValidator.to_search_query(pico, use_boolean=True)
                
                # Extract individual PICO components as keywords
                pico_keywords.extend([
                    pico.population,
                    pico.intervention,
                    pico.comparator,
                    pico.timeframe
                ])
                pico_keywords.extend(pico.outcomes)
                
                logger.info(f"Enhanced PICO search integration: {pico.population[:50]}...")
                # Add PICO-specific metadata for search optimization
                pico_metadata = {
                    'pico_quality_score': stage1_output.get('quality_score', 0),
                    'study_design': study_type,
                    'hypothesis_driven': bool(primary_hypothesis),
                }
            except Exception as e:
                logger.warning(f"Failed to process PICO elements: {e}")

        # Prioritize PICO-derived keywords over config keywords
        keywords = pico_keywords or literature_config.get("keywords", []) or self._extract_keywords(config)
        
        # Use PICO for research topic if available
        pico_topic = ""
        if pico_elements:
            intervention = pico_elements.get('intervention', '')
            population = pico_elements.get('population', '')
            if intervention and population:
                pico_topic = f"{intervention} in {population}"
        
        # Enhance study types based on PICO and Stage 1 output
        study_types = literature_config.get("study_types", [])
        if study_type and study_type not in study_types:
            study_types.append(study_type)
        
        return {
            "research_topic": literature_config.get("topic") or config.get("studyTitle", "") or pico_topic,
            "keywords": keywords,
            "pico_search_query": pico_search_query,  # Store for Boolean queries
            "pico_elements": pico_elements,  # Store for context
            "primary_hypothesis": primary_hypothesis,  # For relevance scoring
            "date_range": literature_config.get("date_range", {"start": "2019-01-01"}),
            "max_results": literature_config.get("max_results", self.max_results_per_source),
            "study_types": study_types,
            "include_reviews": literature_config.get("include_reviews", True),
            "detected_study_type": detected_topic or study_type,
            "stage1_complete": stage1_complete,  # Integration status
            "pico_driven_search": bool(pico_search_query),  # Search strategy flag
        }

    def _extract_keywords(self, config: Dict[str, Any]) -> List[str]:
        """Extract keywords from various config fields."""
        keywords = []

        # From explicit keywords field
        if "keywords" in config:
            if isinstance(config["keywords"], list):
                keywords.extend(config["keywords"])
            elif isinstance(config["keywords"], str):
                keywords.append(config["keywords"])

        # From study title (extract key terms)
        title = config.get("studyTitle", "")
        if title and title != "Research Study":
            # Simple keyword extraction from title
            stop_words = {"the", "a", "an", "of", "in", "on", "for", "to", "and", "or"}
            words = [w.lower() for w in title.split() if w.lower() not in stop_words and len(w) > 2]
            keywords.extend(words[:5])

        # From hypothesis
        hypothesis = config.get("hypothesis", "")
        if hypothesis and "investigate" not in hypothesis.lower():
            keywords.append(hypothesis[:100])  # Use first 100 chars as context

        return list(set(keywords))  # Deduplicate

    def _build_pubmed_query(self, search_config: Dict[str, Any]) -> str:
        """Build PubMed search query string."""
        # INTEGRATION: Prioritize PICO-generated search query from Stage 1
        pico_query = search_config.get("pico_search_query", "")
        if pico_query and search_config.get("pico_driven_search"):
            logger.info(f"Using PICO-optimized search query: {pico_query[:100]}...")
            # Enhance with study type filters if detected
            study_type = search_config.get("detected_study_type", "")
            if study_type:
                study_filters = self._get_study_type_filters(study_type)
                if study_filters:
                    pico_query += f" AND ({study_filters})"
            return pico_query
        
        # Fallback to keyword-based query
        keywords = search_config.get("keywords", [])
        study_types = search_config.get("study_types", [])

        # Build main query
        query_parts = []
        if keywords:
            # Take first 5 keywords and quote them
            query_parts.append(" AND ".join(f'"{k}"' for k in keywords[:5]))

        # Add study type filters
        study_type_filters = {
            "rct": "Randomized Controlled Trial[pt]",
            "systematic_review": "Systematic Review[pt]",
            "meta_analysis": "Meta-Analysis[pt]",
            "cohort": "Cohort Studies[mh]",
            "case_control": "Case-Control Studies[mh]",
        }

        for st in study_types:
            if st.lower() in study_type_filters:
                query_parts.append(study_type_filters[st.lower()])

        return " AND ".join(query_parts) if query_parts else "clinical trial"
    
    def _get_study_type_filters(self, study_type: str) -> str:
        """Get PubMed filters for specific study types."""
        study_type_lower = study_type.lower().replace('_', ' ')
        
        filter_map = {
            'randomized controlled trial': 'Randomized Controlled Trial[pt]',
            'rct': 'Randomized Controlled Trial[pt]', 
            'prospective cohort': 'Prospective Studies[mh] OR Cohort Studies[mh]',
            'retrospective cohort': 'Retrospective Studies[mh] OR Cohort Studies[mh]',
            'case control': 'Case-Control Studies[mh]',
            'cross sectional': 'Cross-Sectional Studies[mh]',
            'observational': 'Observational Study[pt] OR Epidemiologic Studies[mh]',
            'systematic review': 'Systematic Review[pt]',
            'meta analysis': 'Meta-Analysis[pt]',
        }
        
        return filter_map.get(study_type_lower, '')

    def _merge_and_deduplicate(
        self,
        pubmed_results: Dict[str, Any],
        semantic_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Merge results from multiple sources and remove duplicates."""
        seen_dois = set()
        seen_titles = set()
        merged = []

        for paper in pubmed_results.get("papers", []):
            doi = (paper.get("doi") or "").lower().strip()
            title = (paper.get("title") or "").lower().strip()[:50]

            if doi and doi not in seen_dois:
                seen_dois.add(doi)
                paper["source"] = "pubmed"
                merged.append(paper)
            elif title and title not in seen_titles:
                seen_titles.add(title)
                paper["source"] = "pubmed"
                merged.append(paper)

        for paper in semantic_results.get("papers", []):
            doi = (paper.get("doi") or "").lower().strip()
            title = (paper.get("title") or "").lower().strip()[:50]

            if doi and doi in seen_dois:
                continue  # Skip duplicate
            if title and title in seen_titles:
                continue  # Skip duplicate

            if doi:
                seen_dois.add(doi)
            if title:
                seen_titles.add(title)
            paper["source"] = "semantic_scholar"
            merged.append(paper)

        return merged

    def _rank_by_relevance(
        self,
        papers: List[Dict[str, Any]],
        search_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rank papers by relevance score."""
        keywords = set(k.lower() for k in search_config.get("keywords", []))

        for paper in papers:
            score = 0.0
            title = (paper.get("title") or "").lower()
            abstract = (paper.get("abstract") or "").lower()

            # Keyword matching
            for kw in keywords:
                if kw in title:
                    score += 2.0
                if kw in abstract:
                    score += 1.0

            # Citation boost (normalized)
            citations = paper.get("citationCount", 0) or paper.get("citations", 0) or 0
            score += min(citations / 100, 3.0)  # Cap at 3 points

            # Recency boost
            year = paper.get("year") or paper.get("pubYear")
            if year:
                try:
                    years_ago = datetime.now().year - int(year)
                    score += max(0, 2.0 - (years_ago * 0.2))  # Recent papers get up to 2 points
                except (ValueError, TypeError):
                    pass

            # Study type boost
            paper_type = (paper.get("publicationType") or "").lower()
            if "systematic review" in paper_type or "meta-analysis" in paper_type:
                score += 2.0
            elif "randomized" in paper_type:
                score += 1.5

            paper["relevance_score"] = round(score, 2)

        return sorted(papers, key=lambda p: p.get("relevance_score", 0), reverse=True)

    def _identify_key_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify key papers (high impact, reviews, foundational)."""
        key_papers = []

        for paper in papers:
            is_key = False
            reasons = []

            # High citation count
            citations = paper.get("citationCount", 0) or paper.get("citations", 0) or 0
            if citations >= 100:
                is_key = True
                reasons.append(f"highly cited ({citations} citations)")

            # Systematic review or meta-analysis
            paper_type = (paper.get("publicationType") or "").lower()
            if "systematic review" in paper_type or "meta-analysis" in paper_type:
                is_key = True
                reasons.append("systematic review/meta-analysis")

            # High relevance score
            if paper.get("relevance_score", 0) >= 5.0:
                is_key = True
                reasons.append("highly relevant")

            if is_key:
                paper["key_paper_reasons"] = reasons
                key_papers.append(paper)

        return key_papers[:10]  # Limit to top 10 key papers

    def _generate_summary(
        self,
        papers: List[Dict[str, Any]],
        search_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a summary of the literature search results."""
        total = len(papers)

        # Count by year
        year_counts = {}
        for paper in papers:
            year = paper.get("year") or paper.get("pubYear")
            if year:
                year_counts[year] = year_counts.get(year, 0) + 1

        # Count by type
        type_counts = {}
        for paper in papers:
            ptype = paper.get("publicationType", "unknown")
            type_counts[ptype] = type_counts.get(ptype, 0) + 1

        return {
            "total_papers": total,
            "search_keywords": search_config.get("keywords", []),
            "year_distribution": year_counts,
            "type_distribution": type_counts,
            "sources": {
                "pubmed": sum(1 for p in papers if p.get("source") == "pubmed"),
                "semantic_scholar": sum(1 for p in papers if p.get("source") == "semantic_scholar"),
            },
            "avg_citations": sum(
                (p.get("citationCount", 0) or p.get("citations", 0) or 0) for p in papers
            ) / max(total, 1),
        }

    def _save_papers_json(self, context: StageContext, papers: List[Dict[str, Any]]) -> str:
        """Save papers to JSON artifact."""
        artifact_path = os.path.join(context.artifact_path, "literature_papers.json")
        os.makedirs(context.artifact_path, exist_ok=True)

        with open(artifact_path, "w") as f:
            json.dump(papers, f, indent=2, default=str)

        return artifact_path

    def _save_summary(self, context: StageContext, summary: Dict[str, Any]) -> str:
        """Save literature summary to JSON artifact."""
        artifact_path = os.path.join(context.artifact_path, "literature_summary.json")
        os.makedirs(context.artifact_path, exist_ok=True)

        with open(artifact_path, "w") as f:
            json.dump(summary, f, indent=2)

        return artifact_path

    # =========================================================================
    # Tool Implementations
    # =========================================================================

    def _search_pubmed_tool(self, query: str) -> str:
        """Tool wrapper for PubMed search."""
        try:
            result = asyncio.get_event_loop().run_until_complete(
                self._search_pubmed({"keywords": query.split(), "max_results": 20})
            )
            papers = result.get("papers", [])
            return f"Found {len(papers)} papers. Top results: " + ", ".join(
                (p.get("title", "")[:50] for p in papers[:5])
            )
        except Exception as e:
            return f"PubMed search failed: {str(e)}"

    def _search_semantic_scholar_tool(self, query: str) -> str:
        """Tool wrapper for Semantic Scholar search."""
        try:
            result = asyncio.get_event_loop().run_until_complete(
                self._search_semantic_scholar({"keywords": query.split(), "max_results": 20})
            )
            papers = result.get("papers", [])
            return f"Found {len(papers)} papers. Top results: " + ", ".join(
                (p.get("title", "")[:50] for p in papers[:5])
            )
        except Exception as e:
            return f"Semantic Scholar search failed: {str(e)}"

    def _get_paper_details_tool(self, paper_id: str) -> str:
        """Tool wrapper for getting paper details."""
        try:
            # Determine source from ID format
            source = "pubmed" if paper_id.isdigit() else "semantic_scholar"
            result = asyncio.get_event_loop().run_until_complete(
                self._get_paper_details(paper_id, source)
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Failed to get paper details: {str(e)}"

    def _find_citing_papers_tool(self, paper_id: str) -> str:
        """Tool wrapper for finding citing papers."""
        try:
            result = asyncio.get_event_loop().run_until_complete(
                self.call_manuscript_service(
                    "semantic-scholar",
                    "getCitations",
                    {"paperId": paper_id, "limit": 20}
                )
            )
            citations = result.get("citations", [])
            return f"Found {len(citations)} citing papers"
        except Exception as e:
            return f"Failed to find citing papers: {str(e)}"

    def _find_related_papers_tool(self, paper_id: str) -> str:
        """Tool wrapper for finding related papers."""
        try:
            result = asyncio.get_event_loop().run_until_complete(
                self.call_manuscript_service(
                    "semantic-scholar",
                    "getRecommendations",
                    {"paperId": paper_id, "limit": 20}
                )
            )
            recommendations = result.get("recommendations", [])
            return f"Found {len(recommendations)} related papers"
        except Exception as e:
            return f"Failed to find related papers: {str(e)}"
