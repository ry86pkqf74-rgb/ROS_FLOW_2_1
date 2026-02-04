"""
Results Interpretation Agent

Main agent class for interpreting statistical analysis results and translating them
into meaningful clinical findings. Stage 9 component in ResearchFlow workflow.

This agent takes statistical outputs from Stage 7 and contextualizes them with
clinical significance, effect size interpretation, and appropriate confidence levels.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Union

import numpy as np
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from .results_types import (
    ResultsInterpretationState,
    Finding,
    ClinicalSignificanceLevel,
    ConfidenceLevel,
    EffectMagnitude,
    LimitationType,
    Limitation,
    InterpretationRequest,
    InterpretationResponse,
    ClinicalBenchmark,
    StudyDesignContext,
)
from .results_utils import (
    interpret_p_value,
    assess_clinical_magnitude,
    calculate_nnt,
    interpret_cohens_d,
    interpret_odds_ratio,
    interpret_correlation,
    compare_to_literature,
    identify_statistical_limitations,
    identify_design_limitations,
    generate_confidence_statement,
    format_clinical_narrative,
    generate_apa_summary,
    scan_for_phi_in_interpretation,
    redact_phi_from_interpretation,
    assess_statistical_power,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Main Agent Class
# =============================================================================

class ResultsInterpretationAgent:
    """
    Agent for interpreting statistical results and generating clinical insights.
    
    This agent serves as Stage 9 in the ResearchFlow clinical research workflow,
    taking statistical analysis outputs and generating meaningful clinical
    interpretations with appropriate confidence levels and limitations.
    """
    
    def __init__(
        self,
        primary_model: str = "claude-3-5-sonnet-20241022",
        fallback_model: str = "gpt-4o",
        quality_threshold: float = 0.85,
        max_timeout_seconds: int = 300,
        phi_protection: bool = True
    ):
        """
        Initialize the Results Interpretation Agent.
        
        Args:
            primary_model: Primary LLM model for interpretation
            fallback_model: Fallback model if primary fails
            quality_threshold: Minimum quality score (0.0-1.0)
            max_timeout_seconds: Maximum processing time
            phi_protection: Enable PHI protection scanning
        """
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.quality_threshold = quality_threshold
        self.max_timeout_seconds = max_timeout_seconds
        self.phi_protection = phi_protection
        
        # Initialize language models
        self.primary_llm = ChatAnthropic(
            model=primary_model,
            temperature=0.1,
            max_tokens=4000,
            timeout=max_timeout_seconds
        )
        
        self.fallback_llm = ChatOpenAI(
            model=fallback_model,
            temperature=0.1,
            max_tokens=4000,
            request_timeout=max_timeout_seconds
        )
        
        # Initialize prompts
        self._setup_prompts()
        
        logger.info(f"ResultsInterpretationAgent initialized with {primary_model}")
    
    def _setup_prompts(self) -> None:
        """Setup LLM prompts for interpretation tasks."""
        
        # Main interpretation prompt
        self.interpretation_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a clinical research expert specializing in interpreting statistical results for medical research. Your role is to translate statistical findings into meaningful clinical insights.

Key responsibilities:
1. Assess clinical significance beyond statistical significance
2. Interpret effect sizes in practical clinical terms
3. Identify appropriate confidence levels for findings
4. Highlight study limitations and their impact
5. Generate clear, evidence-based interpretations

Guidelines:
- Focus on clinical meaning, not just statistical significance
- Use appropriate clinical terminology
- Acknowledge uncertainty and limitations
- Consider real-world clinical impact
- Maintain scientific rigor and objectivity

Always provide interpretations that would be suitable for publication in peer-reviewed medical journals."""),
            
            HumanMessage(content="""Please interpret the following statistical results in clinical context:

Study Information:
- Study ID: {study_id}
- Design: {study_design}
- Sample Size: {sample_size}
- Primary Outcome: {primary_outcome}

Statistical Results:
{statistical_results}

Study Context:
{study_context}

Please provide:
1. Clinical interpretation of primary findings
2. Assessment of clinical significance levels
3. Effect size interpretations in practical terms
4. Appropriate confidence statements
5. Key limitations and their impact on findings

Format your response as structured clinical findings.""")
        ])
        
        # Effect size interpretation prompt
        self.effect_size_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are an expert in clinical effect size interpretation. Convert statistical effect sizes into clinically meaningful statements that healthcare providers can understand and apply.

Focus on:
- Practical clinical impact
- Number needed to treat/harm when applicable
- Comparison to minimal clinically important differences
- Real-world significance for patient care"""),
            
            HumanMessage(content="""Interpret the following effect sizes in clinical context:

{effect_size_data}

Study Context:
{study_context}

Please provide clear, clinically meaningful interpretations.""")
        ])
        
        # Confidence assessment prompt
        self.confidence_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a clinical epidemiologist assessing the confidence and certainty in research findings. Evaluate the strength of evidence considering study design, statistical power, effect consistency, and potential biases.

Use evidence-based approaches to determine appropriate confidence levels for clinical findings."""),
            
            HumanMessage(content="""Assess the confidence level for these findings:

{findings_data}

Study Design Context:
{design_context}

Statistical Context:
{statistical_context}

Please provide confidence assessments with clear reasoning.""")
        ])
    
    async def execute_interpretation(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """
        Main execution method for results interpretation.
        
        Args:
            state: Current interpretation state with inputs
            
        Returns:
            Updated state with interpretation results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting interpretation for study: {state.study_id}")
            
            # Stage 1: Load and validate analysis results
            state = await self._load_analysis_results(state)
            
            # Stage 2: Contextualize findings with study design
            state = await self._contextualize_findings(state)
            
            # Stage 3: Assess clinical significance
            state = await self._assess_clinical_significance(state)
            
            # Stage 4: Interpret effect sizes
            state = await self._interpret_effect_sizes(state)
            
            # Stage 5: Identify limitations
            state = await self._identify_limitations(state)
            
            # Stage 6: Generate confidence statements
            state = await self._generate_confidence_statements(state)
            
            # Stage 7: Synthesize clinical narrative
            state = await self._synthesize_narrative(state)
            
            # Stage 8: Quality validation
            state = await self._validate_quality(state)
            
            # Stage 9: PHI protection scan
            if self.phi_protection:
                state = await self._scan_for_phi(state)
            
            processing_time = time.time() - start_time
            logger.info(f"Interpretation completed in {processing_time:.2f} seconds")
            
            return state
            
        except Exception as e:
            logger.error(f"Error during interpretation: {str(e)}")
            state.errors.append(f"Interpretation failed: {str(e)}")
            return state
    
    async def _load_analysis_results(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """Load and validate statistical analysis results."""
        try:
            if not state.statistical_results:
                state.warnings.append("No statistical results provided")
                return state
            
            # Extract key statistical information
            primary_outcomes = state.statistical_results.get("primary_outcomes", [])
            secondary_outcomes = state.statistical_results.get("secondary_outcomes", [])
            
            if not primary_outcomes:
                state.warnings.append("No primary outcomes found in statistical results")
            
            # Store extracted information
            state.interpretation_version = "1.0"
            
            logger.info(f"Loaded {len(primary_outcomes)} primary and {len(secondary_outcomes)} secondary outcomes")
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to load analysis results: {str(e)}")
            return state
    
    async def _contextualize_findings(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """Contextualize findings within study design and clinical context."""
        try:
            # Extract study context
            study_design = state.study_context.get("protocol", {}).get("study_design", "Unknown")
            sample_size = state.study_context.get("sample_size", "Unknown")
            primary_outcome = state.study_context.get("primary_outcome", "Unknown")
            
            # Prepare context for interpretation
            context_data = {
                "study_id": state.study_id,
                "study_design": study_design,
                "sample_size": sample_size,
                "primary_outcome": primary_outcome,
                "statistical_results": str(state.statistical_results),
                "study_context": str(state.study_context)
            }
            
            # Generate initial interpretation using LLM
            interpretation_result = await self._generate_interpretation(context_data)
            
            # Parse and store initial findings
            await self._parse_initial_findings(state, interpretation_result)
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to contextualize findings: {str(e)}")
            return state
    
    async def _generate_interpretation(self, context_data: Dict[str, Any]) -> str:
        """Generate interpretation using LLM."""
        try:
            # Try primary model first
            chain = self.interpretation_prompt | self.primary_llm
            result = await chain.ainvoke(context_data)
            return result.content
            
        except Exception as e:
            logger.warning(f"Primary model failed, using fallback: {str(e)}")
            try:
                # Fallback to secondary model
                chain = self.interpretation_prompt | self.fallback_llm
                result = await chain.ainvoke(context_data)
                return result.content
                
            except Exception as fallback_error:
                logger.error(f"Both models failed: {str(fallback_error)}")
                raise fallback_error
    
    async def _parse_initial_findings(
        self,
        state: ResultsInterpretationState,
        interpretation_result: str
    ) -> None:
        """Parse LLM interpretation result into structured findings."""
        try:
            # Extract primary outcomes from statistical results
            primary_outcomes = state.statistical_results.get("primary_outcomes", [])
            
            for i, outcome in enumerate(primary_outcomes):
                # Extract statistical information
                p_value = outcome.get("p_value")
                effect_size = outcome.get("effect_size")
                ci_lower = outcome.get("confidence_interval", {}).get("lower")
                ci_upper = outcome.get("confidence_interval", {}).get("upper")
                
                # Determine statistical significance
                if p_value is not None:
                    if p_value < 0.001:
                        significance = ClinicalSignificanceLevel.HIGHLY_SIGNIFICANT
                        confidence = ConfidenceLevel.HIGH
                    elif p_value < 0.01:
                        significance = ClinicalSignificanceLevel.CLINICALLY_SIGNIFICANT
                        confidence = ConfidenceLevel.HIGH
                    elif p_value < 0.05:
                        significance = ClinicalSignificanceLevel.CLINICALLY_SIGNIFICANT
                        confidence = ConfidenceLevel.MODERATE
                    elif p_value < 0.10:
                        significance = ClinicalSignificanceLevel.MINIMALLY_SIGNIFICANT
                        confidence = ConfidenceLevel.LOW
                    else:
                        significance = ClinicalSignificanceLevel.NOT_SIGNIFICANT
                        confidence = ConfidenceLevel.VERY_LOW
                else:
                    significance = ClinicalSignificanceLevel.NOT_SIGNIFICANT
                    confidence = ConfidenceLevel.VERY_LOW
                
                # Create finding
                hypothesis = outcome.get("hypothesis", f"Primary outcome {i+1}")
                statistical_result = f"p = {p_value:.3f}" if p_value else "p-value not available"
                
                if effect_size:
                    statistical_result += f", effect size = {effect_size:.3f}"
                
                if ci_lower is not None and ci_upper is not None:
                    statistical_result += f", 95% CI [{ci_lower:.3f}, {ci_upper:.3f}]"
                
                # Generate clinical interpretation using utility function
                if p_value:
                    clinical_interp = interpret_p_value(p_value, hypothesis)
                else:
                    clinical_interp = f"Results for {hypothesis} require further statistical evaluation."
                
                # Add effect size context if available
                if effect_size:
                    effect_interp = interpret_cohens_d(effect_size)
                    clinical_interp += f" {effect_interp['interpretation']}"
                
                finding = Finding(
                    hypothesis=hypothesis,
                    statistical_result=statistical_result,
                    clinical_interpretation=clinical_interp,
                    confidence_level=confidence,
                    clinical_significance=significance,
                    effect_size=effect_size,
                    p_value=p_value,
                    confidence_interval=(ci_lower, ci_upper) if ci_lower is not None and ci_upper is not None else None
                )
                
                state.primary_findings.append(finding)
            
            logger.info(f"Parsed {len(state.primary_findings)} primary findings")
            
        except Exception as e:
            state.errors.append(f"Failed to parse initial findings: {str(e)}")
    
    async def _assess_clinical_significance(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """Assess clinical significance beyond statistical significance."""
        try:
            significant_findings = []
            
            for finding in state.primary_findings:
                # Assess clinical magnitude if effect size available
                if finding.effect_size is not None:
                    # Use default MCID of 0.2 for Cohen's d (small effect)
                    mcid = 0.2
                    magnitude = assess_clinical_magnitude(finding.effect_size, mcid)
                    
                    # Update clinical significance based on magnitude
                    if magnitude == "large":
                        if finding.clinical_significance != ClinicalSignificanceLevel.NOT_SIGNIFICANT:
                            finding.clinical_significance = ClinicalSignificanceLevel.HIGHLY_SIGNIFICANT
                    elif magnitude == "moderate":
                        if finding.clinical_significance == ClinicalSignificanceLevel.HIGHLY_SIGNIFICANT:
                            pass  # Keep high significance
                        elif finding.clinical_significance != ClinicalSignificanceLevel.NOT_SIGNIFICANT:
                            finding.clinical_significance = ClinicalSignificanceLevel.CLINICALLY_SIGNIFICANT
                    elif magnitude == "small":
                        if finding.clinical_significance in [ClinicalSignificanceLevel.HIGHLY_SIGNIFICANT, ClinicalSignificanceLevel.CLINICALLY_SIGNIFICANT]:
                            finding.clinical_significance = ClinicalSignificanceLevel.MINIMALLY_SIGNIFICANT
                    else:  # negligible
                        if finding.p_value and finding.p_value < 0.05:
                            finding.clinical_significance = ClinicalSignificanceLevel.STATISTICALLY_ONLY
                        else:
                            finding.clinical_significance = ClinicalSignificanceLevel.NOT_SIGNIFICANT
                
                # Collect significant findings for summary
                if finding.clinical_significance != ClinicalSignificanceLevel.NOT_SIGNIFICANT:
                    significant_findings.append(finding)
            
            # Generate overall clinical significance assessment
            if len(significant_findings) >= len(state.primary_findings) * 0.5:
                state.clinical_significance = "The study demonstrates clinically meaningful effects across the majority of primary outcomes, with findings that are likely to impact clinical practice."
            elif significant_findings:
                state.clinical_significance = "The study shows mixed results with some clinically significant findings, requiring careful interpretation in clinical context."
            else:
                state.clinical_significance = "The study did not demonstrate clinically significant effects for the primary outcomes, though statistical trends may warrant further investigation."
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to assess clinical significance: {str(e)}")
            return state
    
    async def _interpret_effect_sizes(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """Interpret effect sizes in clinical terms."""
        try:
            for finding in state.primary_findings:
                if finding.effect_size is not None:
                    # Interpret effect size based on type
                    if abs(finding.effect_size) <= 2.0:  # Likely Cohen's d
                        interpretation = interpret_cohens_d(finding.effect_size)
                        state.effect_interpretations[finding.hypothesis] = interpretation["interpretation"]
                    else:
                        # Might be odds ratio or other measure
                        state.effect_interpretations[finding.hypothesis] = f"Effect size of {finding.effect_size:.3f} requires domain-specific interpretation."
                    
                    # Calculate NNT if baseline risk available
                    baseline_risk = state.study_context.get("baseline_risk")
                    if baseline_risk:
                        nnt = calculate_nnt(finding.effect_size, baseline_risk)
                        if nnt:
                            state.effect_interpretations[finding.hypothesis] += f" Number needed to treat: {nnt:.1f}."
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to interpret effect sizes: {str(e)}")
            return state
    
    async def _identify_limitations(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """Identify study limitations."""
        try:
            # Statistical limitations
            statistical_limitations = identify_statistical_limitations(state.statistical_results)
            for limitation in statistical_limitations:
                state.limitations_identified.append(f"[{limitation.severity.upper()}] {limitation.description}")
            
            # Design limitations
            design_limitations = identify_design_limitations(state.study_context)
            for limitation in design_limitations:
                state.limitations_identified.append(f"[{limitation.severity.upper()}] {limitation.description}")
            
            # Sample size limitations
            sample_info = state.statistical_results.get("sample_info", {})
            total_n = sample_info.get("total_n", 0)
            if total_n > 0 and total_n < 100:
                state.limitations_identified.append("[MODERATE] Small sample size may limit generalizability and statistical power")
            
            # Missing data limitations
            missing_data_rate = sample_info.get("missing_data_rate", 0)
            if missing_data_rate > 0.1:  # >10% missing data
                state.limitations_identified.append(f"[MODERATE] Missing data rate of {missing_data_rate*100:.1f}% may introduce bias")
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to identify limitations: {str(e)}")
            return state
    
    async def _generate_confidence_statements(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """Generate confidence statements for findings."""
        try:
            for finding in state.primary_findings:
                confidence_statement = generate_confidence_statement(finding, finding.confidence_level)
                state.confidence_statements.append(confidence_statement)
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to generate confidence statements: {str(e)}")
            return state
    
    async def _synthesize_narrative(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """Synthesize findings into coherent clinical narrative."""
        try:
            # This would be enhanced with LLM generation in production
            narrative = format_clinical_narrative(
                primary_findings=state.primary_findings,
                secondary_findings=state.secondary_findings,
                clinical_significance=state.clinical_significance,
                effect_interpretations=state.effect_interpretations,
                limitations=state.limitations_identified,
                confidence_statements=state.confidence_statements
            )
            
            # Store narrative components
            state.effect_interpretations["clinical_narrative"] = narrative
            
            return state
            
        except Exception as e:
            state.errors.append(f"Failed to synthesize narrative: {str(e)}")
            return state
    
    async def _validate_quality(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """Validate interpretation quality against thresholds."""
        try:
            quality_scores = {}
            
            # Completeness (25%)
            completeness_score = 0.0
            if state.primary_findings:
                completeness_score += 0.6
            if state.clinical_significance:
                completeness_score += 0.2
            if state.limitations_identified:
                completeness_score += 0.2
            quality_scores["completeness"] = completeness_score * 0.25
            
            # Clinical assessment (25%)
            clinical_score = 0.0
            significant_findings = [f for f in state.primary_findings 
                                 if f.clinical_significance != ClinicalSignificanceLevel.NOT_SIGNIFICANT]
            if significant_findings:
                clinical_score += 0.5
            if any(f.effect_size for f in state.primary_findings):
                clinical_score += 0.3
            if state.effect_interpretations:
                clinical_score += 0.2
            quality_scores["clinical_assessment"] = clinical_score * 0.25
            
            # Effect interpretation (20%)
            effect_score = len(state.effect_interpretations) / max(len(state.primary_findings), 1)
            quality_scores["effect_interpretation"] = min(effect_score, 1.0) * 0.20
            
            # Limitations (15%)
            limitation_score = 1.0 if state.limitations_identified else 0.0
            quality_scores["limitations"] = limitation_score * 0.15
            
            # Confidence (15%)
            confidence_score = len(state.confidence_statements) / max(len(state.primary_findings), 1)
            quality_scores["confidence"] = min(confidence_score, 1.0) * 0.15
            
            # Calculate total quality score
            total_quality = sum(quality_scores.values())
            
            if total_quality < self.quality_threshold:
                state.warnings.append(f"Quality score ({total_quality:.2f}) below threshold ({self.quality_threshold})")
            
            logger.info(f"Quality validation: {total_quality:.2f} (threshold: {self.quality_threshold})")
            
            return state
            
        except Exception as e:
            state.errors.append(f"Quality validation failed: {str(e)}")
            return state
    
    async def _scan_for_phi(
        self,
        state: ResultsInterpretationState
    ) -> ResultsInterpretationState:
        """Scan outputs for potential PHI and redact if found."""
        try:
            # Scan all text outputs
            text_fields = [
                state.clinical_significance,
                *[f.clinical_interpretation for f in state.primary_findings],
                *[f.clinical_interpretation for f in state.secondary_findings],
                *state.effect_interpretations.values(),
                *state.limitations_identified,
                *state.confidence_statements
            ]
            
            phi_found = False
            for text in text_fields:
                if text:
                    phi_scan = scan_for_phi_in_interpretation(text)
                    if phi_scan["has_phi"]:
                        phi_found = True
                        state.warnings.append(f"PHI detected in interpretation: {phi_scan['phi_types']}")
            
            if phi_found:
                state.warnings.append("PHI detected - review outputs before publication")
            
            return state
            
        except Exception as e:
            state.errors.append(f"PHI scan failed: {str(e)}")
            return state


# =============================================================================
# Factory Function
# =============================================================================

def create_results_interpretation_agent(**kwargs) -> ResultsInterpretationAgent:
    """
    Factory function to create a ResultsInterpretationAgent.
    
    Args:
        **kwargs: Configuration parameters for the agent
        
    Returns:
        Configured ResultsInterpretationAgent instance
    """
    return ResultsInterpretationAgent(**kwargs)


# =============================================================================
# Async Processing Interface
# =============================================================================

async def process_interpretation_request(
    request: InterpretationRequest
) -> InterpretationResponse:
    """
    Process an interpretation request asynchronously.
    
    Args:
        request: InterpretationRequest with study data
        
    Returns:
        InterpretationResponse with results or error
    """
    start_time = time.time()
    
    try:
        # Create agent
        agent = create_results_interpretation_agent()
        
        # Create state from request
        state = ResultsInterpretationState(
            study_id=request.study_id,
            statistical_results=request.statistical_results,
            visualizations=request.visualizations,
            study_context=request.study_context
        )
        
        # Execute interpretation
        result_state = await agent.execute_interpretation(state)
        
        # Create response
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return InterpretationResponse(
            success=len(result_state.errors) == 0,
            study_id=request.study_id,
            interpretation_state=result_state,
            warnings=result_state.warnings,
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        return InterpretationResponse(
            success=False,
            study_id=request.study_id,
            error_message=str(e),
            processing_time_ms=processing_time_ms
        )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def example_usage():
        """Example of how to use the ResultsInterpretationAgent."""
        
        # Example data
        example_request = InterpretationRequest(
            study_id="RCT_2024_001",
            statistical_results={
                "primary_outcomes": [
                    {
                        "hypothesis": "Treatment reduces pain scores compared to placebo",
                        "p_value": 0.025,
                        "effect_size": 0.65,
                        "confidence_interval": {"lower": 0.2, "upper": 1.1}
                    }
                ],
                "sample_info": {
                    "total_n": 120,
                    "missing_data_rate": 0.05
                }
            },
            study_context={
                "protocol": {
                    "study_design": "randomized controlled trial",
                    "randomized": True,
                    "blinding": "double"
                },
                "sample_size": 120,
                "primary_outcome": "pain reduction"
            }
        )
        
        # Process request
        response = await process_interpretation_request(example_request)
        
        if response.success:
            print("Interpretation successful!")
            print(f"Primary findings: {len(response.interpretation_state.primary_findings)}")
            print(f"Clinical significance: {response.interpretation_state.clinical_significance}")
        else:
            print(f"Interpretation failed: {response.error_message}")
    
    # Run example (uncomment to test)
    # asyncio.run(example_usage())