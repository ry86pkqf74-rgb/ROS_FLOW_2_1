"""
Stage 19: Dissemination

Comprehensive agent for research dissemination including:
- Journal submission preparation and formatting
- Preprint server formatting (arXiv, bioRxiv, medRxiv)
- Conference abstract generation
- Press release drafting
- Social media content generation (Twitter/X threads, LinkedIn posts)
- Audience-targeted messaging (academic, industry, policy, public)
- Analytics and tracking setup
- Engagement metric hooks

This stage prepares research outputs for maximum reach and impact.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent, BaseTool, PromptTemplate, LANGCHAIN_AVAILABLE

logger = logging.getLogger("workflow_engine.stages.stage_19_dissemination")


class DisseminationChannel(Enum):
    """Supported dissemination channels."""
    JOURNAL = "journal"
    PREPRINT = "preprint"
    CONFERENCE = "conference"
    PRESS = "press"
    SOCIAL_TWITTER = "twitter"
    SOCIAL_LINKEDIN = "linkedin"
    BLOG = "blog"
    POLICY_BRIEF = "policy_brief"
    PUBLIC_SUMMARY = "public_summary"


class AudienceType(Enum):
    """Target audience types for content adaptation."""
    ACADEMIC = "academic"
    INDUSTRY = "industry"
    POLICY_MAKER = "policy_maker"
    GENERAL_PUBLIC = "general_public"
    MEDIA = "media"
    FUNDING_BODY = "funding_body"


@dataclass
class JournalSubmissionPackage:
    """Complete journal submission package."""
    manuscript_file: str
    cover_letter: str
    highlights: List[str]
    graphical_abstract_path: Optional[str]
    supplementary_files: List[str]
    author_contributions: str
    conflict_of_interest: str
    data_availability: str
    ethics_statement: str
    funding_statement: str
    keywords: List[str]
    suggested_reviewers: List[Dict[str, str]]
    excluded_reviewers: List[Dict[str, str]]
    word_count: int
    figure_count: int
    table_count: int
    reference_count: int


@dataclass
class PreprintPackage:
    """Preprint server submission package."""
    server: str  # arxiv, biorxiv, medrxiv, ssrn, etc.
    manuscript_file: str
    abstract: str
    categories: List[str]
    keywords: List[str]
    license: str
    authors_with_orcid: List[Dict[str, str]]
    funding_sources: List[str]
    competing_interests: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SocialMediaContent:
    """Social media content package."""
    platform: str
    content_type: str  # thread, single_post, carousel
    posts: List[str]
    hashtags: List[str]
    mentions: List[str]
    media_urls: List[str]
    scheduled_time: Optional[str] = None
    engagement_hooks: List[str] = field(default_factory=list)


@dataclass
class PressRelease:
    """Press release content."""
    headline: str
    subheadline: str
    dateline: str
    lead_paragraph: str
    body_paragraphs: List[str]
    quotes: List[Dict[str, str]]
    boilerplate: str
    contact_info: Dict[str, str]
    embargo_date: Optional[str] = None
    multimedia_assets: List[str] = field(default_factory=list)


# Preprint server configurations
PREPRINT_SERVERS = {
    "arxiv": {
        "name": "arXiv",
        "url": "https://arxiv.org",
        "categories": ["cs", "math", "physics", "q-bio", "q-fin", "stat", "eess", "econ"],
        "formats": ["pdf", "tex"],
        "license_options": ["CC BY 4.0", "CC BY-SA 4.0", "CC BY-NC-SA 4.0", "CC0"],
    },
    "biorxiv": {
        "name": "bioRxiv",
        "url": "https://www.biorxiv.org",
        "categories": ["biochemistry", "bioinformatics", "cell-biology", "genetics", "genomics", 
                      "immunology", "microbiology", "neuroscience", "systems-biology"],
        "formats": ["pdf", "docx"],
        "license_options": ["CC BY 4.0", "CC BY-NC 4.0", "CC BY-NC-ND 4.0", "CC0"],
    },
    "medrxiv": {
        "name": "medRxiv",
        "url": "https://www.medrxiv.org",
        "categories": ["addiction-medicine", "allergy", "cardiology", "epidemiology", 
                      "health-informatics", "infectious-diseases", "oncology", "public-health"],
        "formats": ["pdf", "docx"],
        "license_options": ["CC BY 4.0", "CC BY-NC 4.0", "CC BY-NC-ND 4.0"],
    },
    "ssrn": {
        "name": "SSRN",
        "url": "https://www.ssrn.com",
        "categories": ["economics", "finance", "law", "management", "political-science"],
        "formats": ["pdf", "docx"],
        "license_options": ["SSRN Terms of Use"],
    },
}

# Social media platform configurations
SOCIAL_PLATFORMS = {
    "twitter": {
        "max_chars": 280,
        "max_thread_length": 25,
        "supports_media": True,
        "max_hashtags": 5,
        "best_posting_times": ["9:00 AM", "12:00 PM", "5:00 PM"],
    },
    "linkedin": {
        "max_chars": 3000,
        "supports_media": True,
        "max_hashtags": 5,
        "best_posting_times": ["8:00 AM", "10:00 AM", "12:00 PM"],
    },
    "mastodon": {
        "max_chars": 500,
        "max_thread_length": 20,
        "supports_media": True,
        "max_hashtags": 10,
    },
    "bluesky": {
        "max_chars": 300,
        "supports_media": True,
        "max_hashtags": 8,
    },
}


def generate_twitter_thread(
    title: str,
    key_findings: List[str],
    implications: str,
    paper_url: str,
    hashtags: List[str],
) -> List[str]:
    """Generate a Twitter/X thread from research findings.
    
    Args:
        title: Paper title
        key_findings: List of key findings
        implications: Research implications
        paper_url: URL to the paper
        hashtags: Relevant hashtags
    
    Returns:
        List of tweet strings
    """
    thread = []
    hashtag_str = " ".join([f"#{h}" for h in hashtags[:3]])
    
    # Opening tweet
    opening = f"🧵 NEW RESEARCH: {title[:200]}\n\nA thread on what we found and why it matters 👇"
    thread.append(opening)
    
    # Key findings (one per tweet)
    for i, finding in enumerate(key_findings[:5], 1):
        emoji = ["🔬", "📊", "💡", "🎯", "⚡"][i-1]
        finding_tweet = f"{emoji} Finding {i}: {finding[:250]}"
        thread.append(finding_tweet)
    
    # Implications tweet
    implications_tweet = f"🌍 Why this matters:\n\n{implications[:240]}"
    thread.append(implications_tweet)
    
    # Closing tweet with link
    closing = f"📄 Read the full paper: {paper_url}\n\n{hashtag_str}\n\nPlease RT if you found this interesting! 🙏"
    thread.append(closing)
    
    return thread


def generate_linkedin_post(
    title: str,
    abstract: str,
    key_takeaways: List[str],
    author_perspective: str,
    paper_url: str,
    hashtags: List[str],
) -> str:
    """Generate a LinkedIn post from research findings.
    
    Args:
        title: Paper title
        abstract: Paper abstract
        key_takeaways: Key points for professionals
        author_perspective: Personal perspective from author
        paper_url: URL to the paper
        hashtags: Relevant hashtags
    
    Returns:
        LinkedIn post string
    """
    takeaways_text = "\n".join([f"• {t}" for t in key_takeaways[:5]])
    hashtag_str = " ".join([f"#{h}" for h in hashtags[:5]])
    
    post = f"""🔬 Excited to share our latest research: "{title}"

{abstract[:500]}...

Key takeaways for practitioners:

{takeaways_text}

{author_perspective[:300]}

📄 Full paper: {paper_url}

{hashtag_str}

#Research #Science #Innovation"""
    
    return post[:3000]  # LinkedIn limit


def generate_press_release(
    title: str,
    institution: str,
    lead_author: str,
    key_findings: List[str],
    implications: str,
    methodology_summary: str,
    quotes: List[Dict[str, str]],
    contact_info: Dict[str, str],
) -> PressRelease:
    """Generate a press release for research findings.
    
    Args:
        title: Research title
        institution: Lead institution name
        lead_author: Lead author name
        key_findings: List of key findings
        implications: Broader implications
        methodology_summary: Brief methodology overview
        quotes: List of quotes with 'speaker' and 'text' keys
        contact_info: Media contact information
    
    Returns:
        PressRelease dataclass instance
    """
    today = datetime.now().strftime("%B %d, %Y")
    
    headline = f"New Research Reveals {title}"
    subheadline = f"Study from {institution} provides new insights with implications for {implications[:100]}"
    dateline = f"{institution.upper()} — {today}"
    
    lead = (
        f"Researchers at {institution}, led by {lead_author}, have published new findings "
        f"that {key_findings[0].lower() if key_findings else 'advance understanding in the field'}. "
        f"The study, published today, offers significant implications for {implications[:150]}."
    )
    
    body = []
    
    # Findings section
    if len(key_findings) > 1:
        findings_para = "The research team made several key discoveries: " + "; ".join(key_findings[1:4]) + "."
        body.append(findings_para)
    
    # Methodology section
    body.append(f"Using {methodology_summary}, the researchers were able to uncover these patterns.")
    
    # Implications section
    body.append(f"These findings have important implications. {implications}")
    
    boilerplate = (
        f"About {institution}: {institution} is a leading research institution committed to "
        f"advancing knowledge and innovation. For more information, visit our website."
    )
    
    return PressRelease(
        headline=headline,
        subheadline=subheadline,
        dateline=dateline,
        lead_paragraph=lead,
        body_paragraphs=body,
        quotes=quotes,
        boilerplate=boilerplate,
        contact_info=contact_info,
    )


def adapt_content_for_audience(
    content: str,
    source_audience: AudienceType,
    target_audience: AudienceType,
    key_terms: Dict[str, str],
) -> str:
    """Adapt content for different target audiences.
    
    Args:
        content: Original content
        source_audience: Original target audience
        target_audience: New target audience
        key_terms: Dictionary mapping technical terms to simpler explanations
    
    Returns:
        Adapted content string
    """
    adapted = content
    
    # Replace technical terms for public audiences
    if target_audience in [AudienceType.GENERAL_PUBLIC, AudienceType.MEDIA]:
        for term, explanation in key_terms.items():
            adapted = re.sub(
                rf'\b{re.escape(term)}\b',
                f"{term} ({explanation})",
                adapted,
                count=1  # Only explain first occurrence
            )
            # Remove subsequent occurrences of the parenthetical
            adapted = re.sub(
                rf'\b{re.escape(term)}\s*\({re.escape(explanation)}\)',
                term,
                adapted
            )
    
    # Add policy context for policymakers
    if target_audience == AudienceType.POLICY_MAKER:
        if not any(word in adapted.lower() for word in ["policy", "regulation", "legislation"]):
            adapted += "\n\nPolicy Implications: This research has potential implications for policy development and regulatory considerations."
    
    # Add business context for industry
    if target_audience == AudienceType.INDUSTRY:
        if not any(word in adapted.lower() for word in ["market", "commercial", "business", "industry"]):
            adapted += "\n\nIndustry Applications: These findings may have commercial applications and business implications."
    
    return adapted


def generate_blog_post_outline(
    title: str,
    abstract: str,
    key_findings: List[str],
    methodology: str,
    implications: str,
    target_audience: AudienceType,
) -> Dict[str, Any]:
    """Generate a blog post outline for research communication.
    
    Args:
        title: Paper title
        abstract: Paper abstract
        key_findings: Key findings list
        methodology: Methodology summary
        implications: Research implications
        target_audience: Target reader audience
    
    Returns:
        Blog post outline dictionary
    """
    outline = {
        "title": f"New Research: {title}",
        "meta_description": abstract[:160],
        "target_audience": target_audience.value,
        "estimated_read_time": "5-7 minutes",
        "sections": [
            {
                "heading": "Introduction",
                "content_notes": "Hook the reader, explain why this research matters",
                "word_count_target": 150,
            },
            {
                "heading": "The Research Question",
                "content_notes": "What problem were we trying to solve?",
                "word_count_target": 200,
            },
            {
                "heading": "Our Approach",
                "content_notes": f"Simplified explanation of: {methodology}",
                "word_count_target": 250,
            },
            {
                "heading": "Key Discoveries",
                "content_notes": f"Main findings: {'; '.join(key_findings[:3])}",
                "word_count_target": 400,
            },
            {
                "heading": "What This Means",
                "content_notes": f"Implications: {implications}",
                "word_count_target": 200,
            },
            {
                "heading": "Next Steps",
                "content_notes": "Future research directions and open questions",
                "word_count_target": 150,
            },
        ],
        "suggested_images": [
            "Hero image representing the research topic",
            "Infographic of key findings",
            "Author photo(s)",
        ],
        "call_to_action": "Read the full paper / Sign up for updates / Share this post",
    }
    
    return outline


def calculate_dissemination_metrics(
    channels: List[DisseminationChannel],
    audiences: List[AudienceType],
) -> Dict[str, Any]:
    """Calculate expected reach and engagement metrics.
    
    Args:
        channels: Planned dissemination channels
        audiences: Target audiences
    
    Returns:
        Metrics estimation dictionary
    """
    # Base reach estimates per channel
    channel_reach = {
        DisseminationChannel.JOURNAL: {"reach": 500, "engagement_rate": 0.15},
        DisseminationChannel.PREPRINT: {"reach": 2000, "engagement_rate": 0.08},
        DisseminationChannel.CONFERENCE: {"reach": 300, "engagement_rate": 0.25},
        DisseminationChannel.PRESS: {"reach": 10000, "engagement_rate": 0.02},
        DisseminationChannel.SOCIAL_TWITTER: {"reach": 5000, "engagement_rate": 0.04},
        DisseminationChannel.SOCIAL_LINKEDIN: {"reach": 3000, "engagement_rate": 0.06},
        DisseminationChannel.BLOG: {"reach": 1000, "engagement_rate": 0.05},
        DisseminationChannel.POLICY_BRIEF: {"reach": 200, "engagement_rate": 0.20},
        DisseminationChannel.PUBLIC_SUMMARY: {"reach": 1500, "engagement_rate": 0.03},
    }
    
    total_reach = 0
    total_engagement = 0
    channel_breakdown = {}
    
    for channel in channels:
        if channel in channel_reach:
            metrics = channel_reach[channel]
            reach = metrics["reach"]
            engagement = int(reach * metrics["engagement_rate"])
            total_reach += reach
            total_engagement += engagement
            channel_breakdown[channel.value] = {
                "estimated_reach": reach,
                "estimated_engagement": engagement,
                "engagement_rate": f"{metrics['engagement_rate']*100:.1f}%",
            }
    
    return {
        "total_estimated_reach": total_reach,
        "total_estimated_engagement": total_engagement,
        "overall_engagement_rate": f"{(total_engagement/total_reach*100):.2f}%" if total_reach > 0 else "0%",
        "channel_breakdown": channel_breakdown,
        "audiences_targeted": [a.value for a in audiences],
        "coverage_score": min(len(channels) / 5 * 100, 100),  # Percentage of potential coverage
    }


@register_stage
class DisseminationAgent(BaseStageAgent):
    """Stage 19: Comprehensive Dissemination Agent.

    Prepares research outputs for maximum reach and impact through:
    - Journal submission packages
    - Preprint server formatting
    - Conference materials
    - Press releases
    - Social media content
    - Audience-adapted messaging
    - Analytics and tracking setup
    
    Inputs: StageContext with manuscript data and dissemination preferences.
    Outputs: StageResult with complete dissemination package and metrics.
    """

    stage_id = 19
    stage_name = "Dissemination"

    def __init__(self):
        """Initialize the DisseminationAgent."""
        super().__init__()
        self.supported_channels = list(DisseminationChannel)
        self.supported_audiences = list(AudienceType)
        self.preprint_servers = PREPRINT_SERVERS
        self.social_platforms = SOCIAL_PLATFORMS

    def get_tools(self) -> List[BaseTool]:
        """Get LangChain tools for dissemination tasks.

        Returns:
            List of LangChain tools for content generation and adaptation
        """
        if not LANGCHAIN_AVAILABLE:
            return []
        
        tools = []
        
        # Tool for generating social media content
        try:
            from langchain.tools import Tool as LCTool
            
            social_tool = LCTool(
                name="generate_social_content",
                description="Generate social media content for research dissemination",
                func=lambda x: self._generate_social_content_sync(x),
            )
            tools.append(social_tool)
            
            press_tool = LCTool(
                name="generate_press_release",
                description="Generate a press release for research findings",
                func=lambda x: self._generate_press_release_sync(x),
            )
            tools.append(press_tool)
            
            audience_tool = LCTool(
                name="adapt_for_audience",
                description="Adapt research content for specific target audiences",
                func=lambda x: self._adapt_content_sync(x),
            )
            tools.append(audience_tool)
            
        except Exception as e:
            logger.warning(f"Could not create LangChain tools: {e}")
        
        return tools

    def _generate_social_content_sync(self, input_str: str) -> str:
        """Synchronous wrapper for social content generation."""
        try:
            data = json.loads(input_str)
            platform = data.get("platform", "twitter")
            
            if platform == "twitter":
                thread = generate_twitter_thread(
                    title=data.get("title", ""),
                    key_findings=data.get("key_findings", []),
                    implications=data.get("implications", ""),
                    paper_url=data.get("paper_url", ""),
                    hashtags=data.get("hashtags", []),
                )
                return json.dumps({"thread": thread})
            elif platform == "linkedin":
                post = generate_linkedin_post(
                    title=data.get("title", ""),
                    abstract=data.get("abstract", ""),
                    key_takeaways=data.get("key_takeaways", []),
                    author_perspective=data.get("author_perspective", ""),
                    paper_url=data.get("paper_url", ""),
                    hashtags=data.get("hashtags", []),
                )
                return json.dumps({"post": post})
            else:
                return json.dumps({"error": f"Unsupported platform: {platform}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _generate_press_release_sync(self, input_str: str) -> str:
        """Synchronous wrapper for press release generation."""
        try:
            data = json.loads(input_str)
            release = generate_press_release(
                title=data.get("title", ""),
                institution=data.get("institution", ""),
                lead_author=data.get("lead_author", ""),
                key_findings=data.get("key_findings", []),
                implications=data.get("implications", ""),
                methodology_summary=data.get("methodology_summary", ""),
                quotes=data.get("quotes", []),
                contact_info=data.get("contact_info", {}),
            )
            return json.dumps(asdict(release))
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _adapt_content_sync(self, input_str: str) -> str:
        """Synchronous wrapper for audience adaptation."""
        try:
            data = json.loads(input_str)
            adapted = adapt_content_for_audience(
                content=data.get("content", ""),
                source_audience=AudienceType(data.get("source_audience", "academic")),
                target_audience=AudienceType(data.get("target_audience", "general_public")),
                key_terms=data.get("key_terms", {}),
            )
            return json.dumps({"adapted_content": adapted})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_prompt_template(self) -> PromptTemplate:
        """Get prompt template for dissemination planning.

        Returns:
            PromptTemplate for AI-assisted dissemination
        """
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t):
                    return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        
        return PromptTemplate.from_template(
            """You are an expert research communications specialist helping to maximize 
the reach and impact of research findings.

Given the following research manuscript and metadata:
{manuscript_data}

Target audiences: {target_audiences}
Preferred channels: {preferred_channels}

Generate a comprehensive dissemination strategy including:

1. JOURNAL SUBMISSION
   - Recommended target journals (with rationale)
   - Cover letter key points
   - Suggested reviewers

2. PREPRINT STRATEGY
   - Recommended preprint server
   - Optimal timing relative to journal submission
   - Category/tag recommendations

3. SOCIAL MEDIA PLAN
   - Twitter/X thread outline
   - LinkedIn post strategy
   - Key hashtags and engagement hooks

4. PRESS & MEDIA
   - Press release angle
   - Key quotes and soundbites
   - Target media outlets

5. AUDIENCE ADAPTATIONS
   - Plain language summary (public)
   - Policy brief outline (policymakers)
   - Industry application summary (business)

6. METRICS & TRACKING
   - Key performance indicators
   - Tracking recommendations
   - Success benchmarks

Provide actionable, specific recommendations for each section.
"""
        )

    async def execute(self, context: StageContext) -> StageResult:
        """Execute the dissemination stage.

        Args:
            context: Stage execution context

        Returns:
            StageResult containing dissemination outputs
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        logger.info(f"Running Stage 19 (Dissemination) for job {context.job_id}")

        try:
            config = context.config or {}
            inputs = context.inputs or {}
            previous_results = context.previous_results or {}
            
            # Extract manuscript data from previous stages
            manuscript_data = self._extract_manuscript_data(previous_results)
            
            # Get dissemination preferences
            preferences = config.get("dissemination", {})
            target_channels = self._parse_channels(preferences.get("channels", []))
            target_audiences = self._parse_audiences(preferences.get("audiences", []))
            
            # Generate dissemination outputs
            outputs = {}
            artifacts = []
            warnings = []
            
            # 1. Generate social media content
            if DisseminationChannel.SOCIAL_TWITTER in target_channels:
                twitter_content = await self._generate_twitter_content(manuscript_data)
                outputs["twitter_thread"] = twitter_content
                artifacts.append({
                    "type": "social_media",
                    "platform": "twitter",
                    "content": twitter_content,
                })
            
            if DisseminationChannel.SOCIAL_LINKEDIN in target_channels:
                linkedin_content = await self._generate_linkedin_content(manuscript_data)
                outputs["linkedin_post"] = linkedin_content
                artifacts.append({
                    "type": "social_media",
                    "platform": "linkedin",
                    "content": linkedin_content,
                })
            
            # 2. Generate press release if requested
            if DisseminationChannel.PRESS in target_channels:
                press_release = await self._generate_press_release(manuscript_data, config)
                outputs["press_release"] = asdict(press_release) if press_release else None
                if press_release:
                    artifacts.append({
                        "type": "press_release",
                        "content": asdict(press_release),
                    })
            
            # 3. Prepare preprint package if requested
            if DisseminationChannel.PREPRINT in target_channels:
                preprint_package = await self._prepare_preprint_package(
                    manuscript_data, 
                    preferences.get("preprint_server", "biorxiv")
                )
                outputs["preprint_package"] = asdict(preprint_package) if preprint_package else None
                if preprint_package:
                    artifacts.append({
                        "type": "preprint_package",
                        "server": preprint_package.server,
                        "content": asdict(preprint_package),
                    })
            
            # 4. Generate audience-adapted content
            audience_content = {}
            for audience in target_audiences:
                adapted = await self._adapt_for_audience(manuscript_data, audience)
                audience_content[audience.value] = adapted
            outputs["audience_content"] = audience_content
            
            # 5. Generate blog post outline
            if DisseminationChannel.BLOG in target_channels:
                blog_outline = generate_blog_post_outline(
                    title=manuscript_data.get("title", ""),
                    abstract=manuscript_data.get("abstract", ""),
                    key_findings=manuscript_data.get("key_findings", []),
                    methodology=manuscript_data.get("methodology", ""),
                    implications=manuscript_data.get("implications", ""),
                    target_audience=target_audiences[0] if target_audiences else AudienceType.GENERAL_PUBLIC,
                )
                outputs["blog_outline"] = blog_outline
                artifacts.append({
                    "type": "blog_outline",
                    "content": blog_outline,
                })
            
            # 6. Calculate dissemination metrics
            metrics = calculate_dissemination_metrics(target_channels, target_audiences)
            outputs["metrics"] = metrics
            
            # 7. Generate dissemination checklist
            checklist = self._generate_checklist(target_channels, outputs)
            outputs["checklist"] = checklist
            
            # Try to call TypeScript service for additional processing
            try:
                ts_response = await self.call_manuscript_service(
                    service_name="manuscript",
                    method_name="runStageDissemination",
                    params={
                        "job_id": context.job_id,
                        "governance_mode": context.governance_mode,
                        "config": context.config,
                        "inputs": context.inputs,
                        "stage_id": self.stage_id,
                        "stage_name": self.stage_name,
                        "local_outputs": outputs,
                    },
                )
                if ts_response:
                    outputs["typescript_service_response"] = ts_response
            except Exception as ts_error:
                logger.warning(f"TypeScript service call failed (non-fatal): {ts_error}")
                warnings.append(f"TypeScript service unavailable: {str(ts_error)}")

            return self.create_stage_result(
                context=context,
                status="completed",
                started_at=started_at,
                output=outputs,
                artifacts=artifacts,
                errors=[],
                warnings=warnings,
            )

        except Exception as e:
            logger.exception("Stage 19 failed")
            return self.create_stage_result(
                context=context,
                status="failed",
                started_at=started_at,
                output={"error": str(e)},
                artifacts=[],
                errors=[str(e)],
                warnings=[],
            )

    def _extract_manuscript_data(self, previous_results: Dict[int, Any]) -> Dict[str, Any]:
        """Extract manuscript data from previous stage results."""
        data = {
            "title": "",
            "abstract": "",
            "key_findings": [],
            "methodology": "",
            "implications": "",
            "authors": [],
            "keywords": [],
            "institution": "",
        }
        
        # Try to get data from manuscript drafting stage (12)
        if 12 in previous_results:
            stage_12 = previous_results[12]
            if isinstance(stage_12, dict):
                output = stage_12.get("output", {})
                data["title"] = output.get("title", data["title"])
                data["abstract"] = output.get("abstract", data["abstract"])
                data["authors"] = output.get("authors", data["authors"])
        
        # Try to get findings from insight generation (11)
        if 11 in previous_results:
            stage_11 = previous_results[11]
            if isinstance(stage_11, dict):
                output = stage_11.get("output", {})
                data["key_findings"] = output.get("insights", data["key_findings"])
        
        # Try to get methodology from stage 6
        if 6 in previous_results:
            stage_6 = previous_results[6]
            if isinstance(stage_6, dict):
                output = stage_6.get("output", {})
                data["methodology"] = output.get("methodology_summary", data["methodology"])
        
        return data

    def _parse_channels(self, channel_list: List[str]) -> List[DisseminationChannel]:
        """Parse channel strings to enum values."""
        channels = []
        for ch in channel_list:
            try:
                channels.append(DisseminationChannel(ch.lower()))
            except ValueError:
                logger.warning(f"Unknown channel: {ch}")
        
        # Default channels if none specified
        if not channels:
            channels = [
                DisseminationChannel.PREPRINT,
                DisseminationChannel.SOCIAL_TWITTER,
                DisseminationChannel.SOCIAL_LINKEDIN,
            ]
        
        return channels

    def _parse_audiences(self, audience_list: List[str]) -> List[AudienceType]:
        """Parse audience strings to enum values."""
        audiences = []
        for aud in audience_list:
            try:
                audiences.append(AudienceType(aud.lower()))
            except ValueError:
                logger.warning(f"Unknown audience: {aud}")
        
        # Default audiences if none specified
        if not audiences:
            audiences = [AudienceType.ACADEMIC, AudienceType.GENERAL_PUBLIC]
        
        return audiences

    async def _generate_twitter_content(self, manuscript_data: Dict[str, Any]) -> List[str]:
        """Generate Twitter thread content."""
        return generate_twitter_thread(
            title=manuscript_data.get("title", "New Research"),
            key_findings=manuscript_data.get("key_findings", ["Key finding"]),
            implications=manuscript_data.get("implications", "Important implications"),
            paper_url=manuscript_data.get("paper_url", ""),
            hashtags=manuscript_data.get("keywords", ["research", "science"])[:5],
        )

    async def _generate_linkedin_content(self, manuscript_data: Dict[str, Any]) -> str:
        """Generate LinkedIn post content."""
        return generate_linkedin_post(
            title=manuscript_data.get("title", "New Research"),
            abstract=manuscript_data.get("abstract", ""),
            key_takeaways=manuscript_data.get("key_findings", []),
            author_perspective="We're excited to share these findings with the community.",
            paper_url=manuscript_data.get("paper_url", ""),
            hashtags=manuscript_data.get("keywords", ["research"])[:5],
        )

    async def _generate_press_release(
        self, 
        manuscript_data: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Optional[PressRelease]:
        """Generate press release content."""
        authors = manuscript_data.get("authors", [])
        lead_author = authors[0] if authors else "Research Team"
        if isinstance(lead_author, dict):
            lead_author = lead_author.get("name", "Research Team")
        
        return generate_press_release(
            title=manuscript_data.get("title", "New Research Findings"),
            institution=manuscript_data.get("institution", config.get("institution", "Research Institution")),
            lead_author=lead_author,
            key_findings=manuscript_data.get("key_findings", []),
            implications=manuscript_data.get("implications", ""),
            methodology_summary=manuscript_data.get("methodology", "rigorous research methods"),
            quotes=[],
            contact_info=config.get("contact_info", {"email": "media@institution.edu"}),
        )

    async def _prepare_preprint_package(
        self,
        manuscript_data: Dict[str, Any],
        server: str,
    ) -> Optional[PreprintPackage]:
        """Prepare preprint submission package."""
        server_config = PREPRINT_SERVERS.get(server, PREPRINT_SERVERS["biorxiv"])
        
        return PreprintPackage(
            server=server,
            manuscript_file="manuscript.pdf",
            abstract=manuscript_data.get("abstract", ""),
            categories=server_config["categories"][:3],
            keywords=manuscript_data.get("keywords", [])[:10],
            license=server_config["license_options"][0],
            authors_with_orcid=[],
            funding_sources=[],
            competing_interests="None declared",
        )

    async def _adapt_for_audience(
        self,
        manuscript_data: Dict[str, Any],
        audience: AudienceType,
    ) -> str:
        """Adapt content for specific audience."""
        abstract = manuscript_data.get("abstract", "")
        key_terms = manuscript_data.get("key_terms", {})
        
        return adapt_content_for_audience(
            content=abstract,
            source_audience=AudienceType.ACADEMIC,
            target_audience=audience,
            key_terms=key_terms,
        )

    def _generate_checklist(
        self,
        channels: List[DisseminationChannel],
        outputs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate dissemination checklist."""
        checklist = []
        
        for channel in channels:
            item = {
                "channel": channel.value,
                "status": "ready" if channel.value in str(outputs) else "pending",
                "tasks": [],
            }
            
            if channel == DisseminationChannel.PREPRINT:
                item["tasks"] = [
                    "Review preprint package",
                    "Verify author information and ORCIDs",
                    "Select appropriate categories",
                    "Upload to preprint server",
                ]
            elif channel == DisseminationChannel.SOCIAL_TWITTER:
                item["tasks"] = [
                    "Review thread content",
                    "Prepare accompanying images",
                    "Schedule optimal posting time",
                    "Monitor engagement",
                ]
            elif channel == DisseminationChannel.SOCIAL_LINKEDIN:
                item["tasks"] = [
                    "Review post content",
                    "Add relevant connections to notify",
                    "Schedule posting",
                    "Engage with comments",
                ]
            elif channel == DisseminationChannel.PRESS:
                item["tasks"] = [
                    "Review press release",
                    "Get quotes approved",
                    "Identify target journalists",
                    "Prepare media kit",
                ]
            elif channel == DisseminationChannel.JOURNAL:
                item["tasks"] = [
                    "Finalize manuscript formatting",
                    "Prepare cover letter",
                    "Identify suggested reviewers",
                    "Submit to journal portal",
                ]
            
            checklist.append(item)
        
        return checklist
