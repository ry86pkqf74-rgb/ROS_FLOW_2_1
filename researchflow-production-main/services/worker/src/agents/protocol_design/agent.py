"""
Protocol Design Agent - Stage 1: PICO-based protocol design and hypothesis generation.

This agent handles the initial protocol design phase with PICO framework:
- Entry Mode Detection: Quick Entry vs. Direct PICO vs. Hypothesis
- PICO Extraction: Convert natural language to structured PICO using LLM
- PICO Validation: Quality assessment and completeness checks  
- Hypothesis Generation: Create research hypotheses from PICO elements
- Study Type Detection: Identify appropriate study design (RCT, cohort, etc.)
- Protocol Outline: Generate structured research protocol outline

All LLM calls route through the orchestrator's AI Router for PHI compliance.
The PICO framework flows from Stage 1 to subsequent stages (Literature, IRB).

See: IMPLEMENTATION_NEXT_STEPS.md and README_STAGE_01_IMPLEMENTATION.md
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging

from langgraph.graph import StateGraph, END

from ..base.langgraph_base import LangGraphBaseAgent
from ..base.state import AgentState, AgentId, Message
from ..common.pico import PICOElements, PICOValidator, PICOExtractor

logger = logging.getLogger(__name__)


class ProtocolDesignAgent(LangGraphBaseAgent):
    """
    Stage 1 Protocol Design Agent with PICO framework.

    Handles:
    - Quick Entry to PICO conversion via LLM
    - Direct PICO element validation and quality assessment
    - Research hypothesis generation (null, alternative, comparative)
    - Study type detection and recommendation
    - Protocol outline generation (7+ section minimum)
    - Quality gates and improvement loops
    """

    def __init__(self, llm_bridge: Any, checkpointer: Optional[Any] = None):
        """
        Initialize the Protocol Design agent.

        Args:
            llm_bridge: AIRouterBridge instance for LLM calls
            checkpointer: Optional LangGraph checkpointer
        """
        super().__init__(
            llm_bridge=llm_bridge,
            stages=[1],  # Stage 1 only
            agent_id='protocol_design',
            checkpointer=checkpointer,
        )

    def get_quality_criteria(self) -> Dict[str, Any]:
        """
        Quality criteria for Protocol Design agent.

        Returns:
            Dict of criterion name to threshold/requirement
        """
        return {
            'pico_complete': True,  # All PICO elements present
            'pico_quality_score': 70.0,  # PICO quality score >= 70
            'hypothesis_generated': True,  # Research hypothesis created
            'study_type_identified': True,  # Study design selected  
            'protocol_sections': 7,  # Minimum protocol sections
            'min_protocol_length': 500,  # Minimum protocol outline length
            'phi_compliant': True,  # No PHI in output
        }

    def build_graph(self) -> StateGraph:
        """
        Build the Protocol Design agent's LangGraph.

        Graph structure:
        start -> detect_entry_mode -> (quick_to_pico | validate_pico) ->
        generate_hypothesis -> detect_study_type -> generate_protocol ->
        quality_gate -> (human_review | save_version | END) ->
        improve -> validate_pico (loop)
        """
        # Create the state graph
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("detect_entry_mode", self.detect_entry_mode_node)
        graph.add_node("convert_quick_to_pico", self.convert_quick_to_pico_node)
        graph.add_node("validate_pico", self.validate_pico_node)
        graph.add_node("generate_hypothesis", self.generate_hypothesis_node)
        graph.add_node("detect_study_type", self.detect_study_type_node)
        graph.add_node("generate_protocol", self.generate_protocol_outline_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_node("human_review", self.human_review_node)
        graph.add_node("save_version", self.save_version_node)
        graph.add_node("improve", self.improve_node)

        # Set entry point
        graph.set_entry_point("detect_entry_mode")

        # Conditional routing after entry mode detection
        graph.add_conditional_edges(
            "detect_entry_mode",
            self._route_entry_mode,
            {
                "quick_entry": "convert_quick_to_pico",
                "pico_direct": "validate_pico",
                "hypothesis_mode": "detect_study_type",  # Skip PICO if hypothesis provided
            }
        )

        # From conversion, always validate
        graph.add_edge("convert_quick_to_pico", "validate_pico")

        # Linear flow after PICO validation
        graph.add_edge("validate_pico", "generate_hypothesis")
        graph.add_edge("generate_hypothesis", "detect_study_type") 
        graph.add_edge("detect_study_type", "generate_protocol")
        graph.add_edge("generate_protocol", "quality_gate")

        # Conditional routing after quality gate
        graph.add_conditional_edges(
            "quality_gate",
            self._route_after_quality_gate,
            {
                "human_review": "human_review",
                "save_version": "save_version",
                "end": END,
            }
        )

        graph.add_edge("human_review", "save_version")

        # Improvement loop routing
        graph.add_conditional_edges(
            "save_version",
            self.should_continue_improvement,
            {
                "continue": "improve",
                "complete": END,
            }
        )

        # Improvement goes back to validation to recheck PICO
        graph.add_edge("improve", "validate_pico")

        # Compile with checkpointer
        return graph.compile(checkpointer=self.checkpointer)

    def _route_entry_mode(self, state: AgentState) -> str:
        """Route based on detected entry mode."""
        entry_mode = state.get('entry_mode', 'quick_entry')
        return {
            'quick_entry': 'quick_entry',
            'pico_direct': 'pico_direct', 
            'hypothesis_mode': 'hypothesis_mode'
        }.get(entry_mode, 'quick_entry')

    def _route_after_quality_gate(self, state: AgentState) -> str:
        """Route after quality gate evaluation."""
        gate_status = state.get('gate_status', 'pending')
        governance_mode = state.get('governance_mode', 'DEMO')

        # In LIVE mode, require human review for protocol design
        if governance_mode == 'LIVE' and gate_status in ['passed', 'needs_human']:
            return "human_review"

        if gate_status == 'needs_human':
            return "human_review"

        if gate_status == 'passed':
            return "save_version"

        # Failed - still save version for improvement
        return "save_version"

    # =========================================================================
    # Node Implementations
    # =========================================================================

    async def detect_entry_mode_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Detect user entry mode based on input.

        Modes:
        - quick_entry: Natural language topic description (most common)
        - pico_direct: Structured PICO elements provided directly
        - hypothesis_mode: Research hypothesis already formulated
        """
        logger.info(f"[ProtocolDesign] Detecting entry mode", extra={'run_id': state.get('run_id')})

        messages = state.get('messages', [])
        
        # Get latest user message
        user_messages = [m for m in messages if m['role'] == 'user']
        if not user_messages:
            return {
                'entry_mode': 'quick_entry',
                'current_stage': 1,
            }

        latest_message = user_messages[-1]['content']

        # Simple heuristic-based detection
        pico_keywords = ['population', 'intervention', 'comparator', 'outcome', 'timeframe']
        hypothesis_keywords = ['hypothesis', 'we hypothesize', 'will show', 'compared to', 'significant']

        pico_count = sum(1 for keyword in pico_keywords if keyword.lower() in latest_message.lower())
        hypothesis_count = sum(1 for keyword in hypothesis_keywords if keyword.lower() in latest_message.lower())

        # Determine mode
        if pico_count >= 3:
            entry_mode = 'pico_direct'
        elif hypothesis_count >= 2:
            entry_mode = 'hypothesis_mode'
        else:
            entry_mode = 'quick_entry'

        logger.info(f"Detected entry mode: {entry_mode}")

        return {
            'entry_mode': entry_mode,
            'current_stage': 1,
            'input_text': latest_message,
        }

    async def convert_quick_to_pico_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Convert quick entry natural language to PICO elements using LLM.

        Uses PICOExtractor.extract_from_text() for LLM-based extraction.
        """
        logger.info(f"[ProtocolDesign] Converting quick entry to PICO", extra={'run_id': state.get('run_id')})

        input_text = state.get('input_text', '')
        if not input_text:
            return {
                'error': 'No input text provided for PICO conversion',
                'current_output': 'Error: Missing input for PICO conversion'
            }

        # Use PICO extractor
        try:
            pico = await PICOExtractor.extract_from_text(
                text=input_text,
                llm_bridge=self.llm,
                state=state,
                model_tier='STANDARD',
            )

            if pico is None:
                return {
                    'error': 'Failed to extract PICO from input text',
                    'current_output': 'Error: Could not extract PICO elements from the provided text. Please provide more structured input.'
                }

            # Create assistant message
            message = self.add_assistant_message(
                state,
                f"I've extracted the PICO framework from your research description:\n\n"
                f"**Population**: {pico.population}\n"
                f"**Intervention**: {pico.intervention}\n" 
                f"**Comparator**: {pico.comparator}\n"
                f"**Outcomes**: {', '.join(pico.outcomes)}\n"
                f"**Timeframe**: {pico.timeframe}"
            )

            return {
                'pico_elements': pico.dict(),
                'current_output': f"PICO Extraction Complete:\n{pico.dict()}",
                'messages': [message],
            }

        except Exception as e:
            logger.error(f"PICO extraction failed: {e}")
            return {
                'error': f'PICO extraction error: {str(e)}',
                'current_output': f'Error during PICO extraction: {str(e)}'
            }

    async def validate_pico_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Validate PICO elements for completeness and quality.

        Uses PICOValidator for validation and quality assessment.
        """
        logger.info(f"[ProtocolDesign] Validating PICO elements", extra={'run_id': state.get('run_id')})

        pico_data = state.get('pico_elements')
        if not pico_data:
            return {
                'error': 'No PICO elements to validate',
                'current_output': 'Error: Missing PICO elements for validation'
            }

        try:
            # Create PICO object and validate
            pico = PICOElements(**pico_data)
            is_valid, errors = PICOValidator.validate(pico)
            quality = PICOValidator.assess_quality(pico)

            # Prepare validation results
            validation_summary = f"""PICO Validation Results:
✅ Valid: {is_valid}
📊 Quality Score: {quality['score']}/100 ({quality['quality_level']})

PICO Elements:
- Population: {pico.population}
- Intervention: {pico.intervention}  
- Comparator: {pico.comparator}
- Outcomes: {', '.join(pico.outcomes)}
- Timeframe: {pico.timeframe}

Quality Assessment:
- Strengths: {', '.join(quality['strengths']) if quality['strengths'] else 'None identified'}
- Recommendations: {'; '.join(quality['recommendations']) if quality['recommendations'] else 'None'}
"""

            if not is_valid:
                validation_summary += f"\n❌ Validation Errors:\n" + '\n'.join(f"- {error}" for error in errors)

            return {
                'pico_valid': is_valid,
                'pico_quality': quality,
                'pico_errors': errors,
                'current_output': validation_summary,
            }

        except Exception as e:
            logger.error(f"PICO validation failed: {e}")
            return {
                'error': f'PICO validation error: {str(e)}',
                'current_output': f'Error during PICO validation: {str(e)}'
            }

    async def generate_hypothesis_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate research hypotheses from validated PICO elements.

        Creates null, alternative, and comparative hypothesis statements.
        """
        logger.info(f"[ProtocolDesign] Generating hypotheses", extra={'run_id': state.get('run_id')})

        pico_data = state.get('pico_elements')
        if not pico_data:
            return {
                'error': 'No PICO elements for hypothesis generation',
                'current_output': 'Error: Missing PICO elements for hypothesis generation'
            }

        try:
            pico = PICOElements(**pico_data)

            # Generate all three hypothesis types
            null_hypothesis = PICOValidator.to_hypothesis(pico, style="null")
            alternative_hypothesis = PICOValidator.to_hypothesis(pico, style="alternative")
            comparative_hypothesis = PICOValidator.to_hypothesis(pico, style="comparative")

            hypotheses = {
                'null': null_hypothesis,
                'alternative': alternative_hypothesis, 
                'comparative': comparative_hypothesis,
                'primary': alternative_hypothesis,  # Default primary
            }

            # Create detailed output
            hypothesis_summary = f"""Research Hypotheses Generated:

🎯 **Primary Hypothesis (Alternative)**:
{alternative_hypothesis}

🔍 **Null Hypothesis**:  
{null_hypothesis}

📊 **Comparative Hypothesis**:
{comparative_hypothesis}

The primary hypothesis will be used for statistical planning and sample size calculations.
"""

            return {
                'hypotheses': hypotheses,
                'primary_hypothesis': alternative_hypothesis,
                'current_output': hypothesis_summary,
            }

        except Exception as e:
            logger.error(f"Hypothesis generation failed: {e}")
            return {
                'error': f'Hypothesis generation error: {str(e)}',
                'current_output': f'Error during hypothesis generation: {str(e)}'
            }

    async def detect_study_type_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Detect and recommend appropriate study design based on PICO and research context.

        Study types: RCT, Cohort, Case-Control, Cross-Sectional, Observational
        """
        logger.info(f"[ProtocolDesign] Detecting study type", extra={'run_id': state.get('run_id')})

        pico_data = state.get('pico_elements')
        hypotheses = state.get('hypotheses', {})
        input_text = state.get('input_text', '')

        if not pico_data:
            return {
                'error': 'No PICO elements for study type detection',
                'current_output': 'Error: Missing PICO elements for study type detection'
            }

        # Build context for LLM
        pico = PICOElements(**pico_data)
        context = f"""
PICO Elements:
- Population: {pico.population}
- Intervention: {pico.intervention}
- Comparator: {pico.comparator}  
- Outcomes: {', '.join(pico.outcomes)}
- Timeframe: {pico.timeframe}

Primary Hypothesis: {hypotheses.get('primary', 'Not generated')}

Original Research Description: {input_text}
"""

        prompt = f"""Based on this research context, recommend the most appropriate study design:

{context}

Consider these study types and provide recommendation:

1. **Randomized Controlled Trial (RCT)**: Participants randomly assigned to intervention vs control
2. **Prospective Cohort**: Follow groups over time, observe outcomes
3. **Retrospective Cohort**: Look back at historical data for exposure-outcome relationships
4. **Case-Control**: Compare cases (with outcome) to controls (without outcome)  
5. **Cross-Sectional**: Snapshot assessment at single time point
6. **Observational**: Observe natural variation without intervention

Provide:
1. Recommended study design with justification
2. Key advantages for this research question
3. Potential limitations and mitigation strategies
4. Feasibility considerations (timeline, resources, ethical)
5. Alternative study designs if primary isn't feasible

Format as structured recommendations with clear rationale.
"""

        try:
            study_design_analysis = await self.call_llm(
                prompt=prompt,
                task_type='study_design_selection',
                state=state,
                model_tier='STANDARD',
            )

            # Extract primary recommendation with simple parsing
            lines = study_design_analysis.lower().split('\n')
            detected_type = 'observational'  # Default fallback

            for line in lines:
                if 'recommend' in line or 'suggested' in line:
                    if 'randomized' in line or 'rct' in line:
                        detected_type = 'randomized_controlled_trial'
                    elif 'prospective' in line and 'cohort' in line:
                        detected_type = 'prospective_cohort'
                    elif 'retrospective' in line and 'cohort' in line:
                        detected_type = 'retrospective_cohort'
                    elif 'case-control' in line or 'case control' in line:
                        detected_type = 'case_control'
                    elif 'cross-sectional' in line:
                        detected_type = 'cross_sectional'
                    break

            result_summary = f"""Study Design Recommendation:

📋 **Recommended Design**: {detected_type.replace('_', ' ').title()}

{study_design_analysis}

This recommendation is based on the PICO framework, research objectives, and feasibility considerations.
"""

            return {
                'study_type': detected_type,
                'study_design_analysis': study_design_analysis,
                'current_output': result_summary,
            }

        except Exception as e:
            logger.error(f"Study type detection failed: {e}")
            return {
                'error': f'Study type detection error: {str(e)}',
                'current_output': f'Error during study type detection: {str(e)}'
            }

    async def generate_protocol_outline_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate comprehensive research protocol outline.

        Creates structured protocol with minimum 7 sections plus study-specific details.
        """
        logger.info(f"[ProtocolDesign] Generating protocol outline", extra={'run_id': state.get('run_id')})

        pico_data = state.get('pico_elements')
        hypotheses = state.get('hypotheses', {})
        study_type = state.get('study_type', 'observational')
        study_design_analysis = state.get('study_design_analysis', '')

        if not pico_data:
            return {
                'error': 'No PICO elements for protocol generation',
                'current_output': 'Error: Missing PICO elements for protocol generation'
            }

        pico = PICOElements(**pico_data)

        # Build comprehensive context
        context = f"""
PICO Framework:
- Population: {pico.population}
- Intervention: {pico.intervention}
- Comparator: {pico.comparator}
- Outcomes: {', '.join(pico.outcomes)}
- Timeframe: {pico.timeframe}

Primary Hypothesis: {hypotheses.get('primary', 'Not specified')}
Study Design: {study_type.replace('_', ' ').title()}

Study Design Analysis:
{study_design_analysis}
"""

        prompt = f"""Generate a comprehensive research protocol outline based on this information:

{context}

Create a structured protocol with these required sections and detailed content:

## 1. Study Summary
- Title, objectives, hypothesis, design overview

## 2. Background and Rationale  
- Literature context, knowledge gaps, study justification

## 3. Study Objectives and Hypotheses
- Primary and secondary objectives, null/alternative hypotheses

## 4. Study Design and Methods
- Design type, setting, timeline, study flow

## 5. Participant Selection
- Inclusion criteria, exclusion criteria, recruitment strategy

## 6. Interventions/Exposures  
- Detailed intervention description, comparator details, administration

## 7. Outcome Measures
- Primary endpoints, secondary endpoints, measurement methods

## 8. Statistical Analysis Plan
- Sample size justification, statistical methods, analysis populations

## 9. Data Management
- Data collection, storage, quality assurance, monitoring

## 10. Ethical Considerations
- IRB requirements, informed consent, risk/benefit analysis

## Additional Sections (as appropriate):
- Regulatory considerations
- Quality control procedures  
- Publication plan
- Budget considerations
- Risk management

Provide detailed, actionable content for each section. Include specific methodological details appropriate for the chosen study design. Ensure the protocol supports the stated hypotheses and objectives.

Format as a comprehensive, professional research protocol outline ready for IRB submission preparation.
"""

        try:
            protocol_outline = await self.call_llm(
                prompt=prompt,
                task_type='protocol_generation',
                state=state,
                model_tier='STANDARD',
            )

            # Create final summary message
            message = self.add_assistant_message(
                state,
                f"I've generated a comprehensive research protocol outline based on your PICO framework. "
                f"The protocol includes {len(protocol_outline.split('##'))-1} main sections and is ready for "
                f"refinement and IRB preparation."
            )

            final_output = f"""# Research Protocol Design Complete

## PICO Framework Summary:
- **Population**: {pico.population}
- **Intervention**: {pico.intervention}
- **Comparator**: {pico.comparator}  
- **Outcomes**: {', '.join(pico.outcomes)}
- **Timeframe**: {pico.timeframe}

## Primary Hypothesis:
{hypotheses.get('primary', 'Not specified')}

## Recommended Study Design:
{study_type.replace('_', ' ').title()}

---

{protocol_outline}

---

**Next Steps**: This protocol outline is ready for Stage 2 (Literature Review) and Stage 3 (IRB Documentation). The PICO framework will automatically flow to subsequent stages for literature search and regulatory preparation.
"""

            return {
                'protocol_outline': protocol_outline,
                'final_output': final_output,
                'current_output': final_output,
                'messages': [message],
            }

        except Exception as e:
            logger.error(f"Protocol generation failed: {e}")
            return {
                'error': f'Protocol generation error: {str(e)}',
                'current_output': f'Error during protocol generation: {str(e)}'
            }

    async def improve_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Improve protocol design based on feedback from quality gate or human review.

        Focuses on specific failed criteria and incorporates feedback directly.
        """
        logger.info(f"[ProtocolDesign] Improving based on feedback", extra={'run_id': state.get('run_id')})

        feedback = state.get('feedback', '')
        current_output = state.get('current_output', '')
        gate_result = state.get('gate_result', {})
        pico_data = state.get('pico_elements', {})

        # Build improvement prompt focusing on specific issues
        prompt = f"""Improve this protocol design based on the feedback and quality gate results:

Current Protocol:
{current_output}

Current PICO:
{pico_data}

Quality Gate Results:
- Score: {gate_result.get('score', 'N/A')}/1.0
- Failed Criteria: {gate_result.get('criteria_failed', [])}
- Reason: {gate_result.get('reason', 'N/A')}

Human Feedback:
{feedback if feedback else 'No specific feedback provided'}

Address these specific improvement areas:
1. Fix any failed quality criteria
2. Incorporate human feedback directly
3. Enhance PICO specificity if needed
4. Improve protocol section detail and clarity
5. Ensure statistical and methodological rigor

Provide an improved version that addresses all identified issues while maintaining the core research framework.
"""

        try:
            improved_result = await self.call_llm(
                prompt=prompt,
                task_type='protocol_improvement',
                state=state,
                model_tier='STANDARD',
            )

            # Try to extract improved PICO if present in improvement
            # (This is a simple approach - in production, might want more sophisticated parsing)
            updated_pico = pico_data  # Default to current

            return {
                'current_output': improved_result,
                'pico_elements': updated_pico,
                'feedback': None,  # Clear feedback after applying
                'iteration_improved': True,
            }

        except Exception as e:
            logger.error(f"Protocol improvement failed: {e}")
            return {
                'error': f'Improvement error: {str(e)}',
                'current_output': f'Error during improvement: {str(e)}'
            }

    # =========================================================================
    # Quality Criteria Evaluation (Override from base class)
    # =========================================================================

    def _evaluate_criterion(
        self,
        criterion: str,
        threshold: Any,
        output: str,
        state: AgentState,
    ) -> tuple[bool, float]:
        """Evaluate Protocol Design specific quality criteria."""

        if criterion == 'pico_complete':
            pico_data = state.get('pico_elements')
            if not pico_data:
                return False, 0.0
            
            try:
                pico = PICOElements(**pico_data)
                is_valid, errors = PICOValidator.validate(pico)
                return is_valid, 1.0 if is_valid else 0.3
            except:
                return False, 0.0

        if criterion == 'pico_quality_score':
            pico_quality = state.get('pico_quality', {})
            if not pico_quality:
                return False, 0.0
            
            score = pico_quality.get('score', 0)
            passed = score >= threshold
            normalized_score = min(1.0, score / 100.0)
            return passed, normalized_score

        if criterion == 'hypothesis_generated':
            hypotheses = state.get('hypotheses', {})
            has_hypotheses = bool(hypotheses.get('primary'))
            return has_hypotheses, 1.0 if has_hypotheses else 0.0

        if criterion == 'study_type_identified':
            study_type = state.get('study_type')
            has_study_type = bool(study_type and study_type != 'unknown')
            return has_study_type, 1.0 if has_study_type else 0.0

        if criterion == 'protocol_sections':
            # Count protocol sections (look for ## headers)
            section_count = len([line for line in output.split('\n') if line.strip().startswith('##')])
            passed = section_count >= threshold
            score = min(1.0, section_count / threshold) if threshold > 0 else 1.0
            return passed, score

        if criterion == 'min_protocol_length':
            actual_length = len(output)
            passed = actual_length >= threshold
            score = min(1.0, actual_length / threshold) if threshold > 0 else 1.0
            return passed, score

        if criterion == 'phi_compliant':
            # Simple PHI detection (in production, would use proper PHI scanner)
            phi_indicators = ['ssn', 'social security', 'date of birth', 'phone number', 'address']
            has_phi = any(indicator in output.lower() for indicator in phi_indicators)
            return not has_phi, 0.0 if has_phi else 1.0

        # Fallback to base implementation
        return super()._evaluate_criterion(criterion, threshold, output, state)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_stage_output_for_next_stages(self, state: AgentState) -> Dict[str, Any]:
        """
        Prepare output for consumption by subsequent stages (Literature, IRB).

        This is the key integration point - ensures PICO flows to other stages.
        
        Returns:
            Dict with standardized output for Stage 2+ consumption
        """
        return {
            'pico_elements': state.get('pico_elements', {}),
            'hypotheses': state.get('hypotheses', {}),
            'primary_hypothesis': state.get('primary_hypothesis', ''),
            'study_type': state.get('study_type', 'observational'),
            'study_design_analysis': state.get('study_design_analysis', ''),
            'protocol_outline': state.get('protocol_outline', ''),
            'search_query': self._generate_search_query(state),
            'stage_1_complete': True,
            'agent_id': self.agent_id,
            'completion_timestamp': datetime.utcnow().isoformat(),
        }

    def _generate_search_query(self, state: AgentState) -> str:
        """Generate search query for Stage 2 Literature Review."""
        pico_data = state.get('pico_elements')
        if not pico_data:
            return ""
        
        try:
            pico = PICOElements(**pico_data)
            return PICOValidator.to_search_query(pico, use_boolean=True)
        except:
            return ""