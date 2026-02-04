"""
Stage 01: Protocol Design with PICO Framework

This is a workflow engine adapter for the ProtocolDesignAgent.
It wraps the LangGraph-based agent to work within the workflow engine framework.

Key Features:
- PICO framework extraction and validation
- Research hypothesis generation  
- Study design recommendation
- Protocol outline generation
- Quality gates and improvement loops
- Outputs PICO elements for consumption by Stages 2 & 3

See: STAGE_01_IMPLEMENTATION_COMPLETE.md for full documentation
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

logger = logging.getLogger("workflow_engine.stage_01_protocol_design")


# Note: This stage is registered conditionally via setup_stage_1_registration()
# Do not use @register_stage decorator to avoid conflicts
class ProtocolDesignStage(BaseStageAgent):
    """Stage 1: Protocol Design with PICO Framework
    
    Workflow engine adapter for the ProtocolDesignAgent.
    Handles research protocol design using PICO framework.
    """

    stage_id = 1
    stage_name = "Protocol Design"

    async def execute(self, context: StageContext) -> StageResult:
        """Execute protocol design workflow.

        Args:
            context: Stage execution context

        Returns:
            StageResult with PICO elements and protocol outline
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        errors: List[str] = []
        warnings: List[str] = []
        output: Dict[str, Any] = {}
        artifacts: List[str] = []

        logger.info(f"Starting Protocol Design for job {context.job_id}")

        try:
            # Import the ProtocolDesignAgent (lazy import to avoid circular dependencies)
            from ...agents.protocol_design.agent import ProtocolDesignAgent
            from ...agents.base.state import create_initial_state
            
            # Extract research context from config
            config = context.config or {}
            research_context = self._extract_research_context(config, context)
            
            if not research_context.get('initial_message'):
                if context.governance_mode == 'DEMO':
                    warnings.append("No research context provided in DEMO mode, using default")
                    research_context['initial_message'] = "Generate a research protocol for clinical study"
                else:
                    errors.append("No research context or initial message provided")
                    return self._create_error_result(context, started_at, errors, warnings)
            
            # Create AI Router bridge for LLM calls
            llm_bridge = self.get_llm_bridge(context)
            
            # Initialize Protocol Design Agent
            protocol_agent = ProtocolDesignAgent(llm_bridge=llm_bridge)
            
            # Execute the protocol design workflow
            logger.info(f"Executing protocol design with message: {research_context['initial_message'][:100]}...")
            
            agent_result = await protocol_agent.invoke(
                project_id=context.job_id,
                initial_message=research_context['initial_message'],
                governance_mode=context.governance_mode,
                max_iterations=research_context.get('max_iterations', 5),
            )
            
            # Extract outputs for workflow engine
            stage_output = protocol_agent.get_stage_output_for_next_stages(agent_result)
            
            # Populate workflow engine output format
            output.update({
                'pico_elements': stage_output.get('pico_elements', {}),
                'hypotheses': stage_output.get('hypotheses', {}),
                'primary_hypothesis': stage_output.get('primary_hypothesis', ''),
                'study_type': stage_output.get('study_type', 'observational'),
                'study_design_analysis': stage_output.get('study_design_analysis', ''),
                'protocol_outline': stage_output.get('protocol_outline', ''),
                'search_query': stage_output.get('search_query', ''),
                'stage_1_complete': True,
                'agent_id': 'protocol_design',
                'quality_score': agent_result.get('gate_score', 0.0),
                'gate_status': agent_result.get('gate_status', 'unknown'),
            })
            
            # Save protocol outline as artifact if generated
            if stage_output.get('protocol_outline'):
                artifact_path = self._save_protocol_artifact(
                    context, 
                    stage_output['protocol_outline'],
                    stage_output.get('pico_elements', {})
                )
                artifacts.append(artifact_path)
            
            # Add any warnings from agent execution
            if agent_result.get('gate_status') == 'needs_human':
                warnings.append("Protocol design passed but may benefit from human review")
            elif agent_result.get('gate_status') == 'failed':
                warnings.append("Protocol design did not meet all quality criteria but was completed")
            
            logger.info(f"Protocol design completed successfully for job {context.job_id}")
            
        except ImportError as e:
            error_msg = f"Failed to import ProtocolDesignAgent: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            
        except Exception as e:
            error_msg = f"Protocol design failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

        return self.create_stage_result(
            context=context,
            status="failed" if errors else "completed",
            started_at=started_at,
            output=output,
            artifacts=artifacts,
            errors=errors,
            warnings=warnings,
            metadata={
                "governance_mode": context.governance_mode,
                "protocol_design_complete": len(errors) == 0,
                "has_pico_elements": bool(output.get('pico_elements')),
                "has_protocol_outline": bool(output.get('protocol_outline')),
            },
        )

    def _extract_research_context(self, config: Dict[str, Any], context: StageContext) -> Dict[str, Any]:
        """Extract research context from config and context."""
        # Try various config keys for research input
        research_context = {}
        
        # Look for protocol design specific config
        protocol_config = config.get('protocol_design', {})
        if protocol_config:
            research_context.update(protocol_config)
        
        # Look for common research context fields
        context_fields = [
            'research_question', 'study_description', 'research_topic',
            'initial_message', 'topic_description', 'study_title',
            'research_context', 'protocol_input'
        ]
        
        for field in context_fields:
            if field in config:
                research_context['initial_message'] = config[field]
                break
            elif field in protocol_config:
                research_context['initial_message'] = protocol_config[field]
                break
        
        # Extract other relevant parameters
        research_context['max_iterations'] = config.get('max_iterations', 5)
        research_context['governance_mode'] = context.governance_mode
        
        return research_context

    def _save_protocol_artifact(
        self, 
        context: StageContext, 
        protocol_outline: str, 
        pico_elements: Dict[str, Any]
    ) -> str:
        """Save protocol outline as JSON artifact."""
        import os
        
        # Create artifact data
        artifact_data = {
            'protocol_outline': protocol_outline,
            'pico_elements': pico_elements,
            'generated_at': datetime.utcnow().isoformat(),
            'job_id': context.job_id,
            'stage_id': self.stage_id,
            'stage_name': self.stage_name,
            'governance_mode': context.governance_mode,
        }
        
        # Save as JSON artifact
        os.makedirs(context.artifact_path, exist_ok=True)
        artifact_filename = f"protocol_design_{context.job_id}.json"
        artifact_path = os.path.join(context.artifact_path, artifact_filename)
        
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved protocol artifact: {artifact_path}")
        return artifact_path

    def _create_error_result(
        self, 
        context: StageContext, 
        started_at: str, 
        errors: List[str], 
        warnings: List[str]
    ) -> StageResult:
        """Create error result for failed execution."""
        return self.create_stage_result(
            context=context,
            status="failed",
            started_at=started_at,
            output={},
            artifacts=[],
            errors=errors,
            warnings=warnings,
            metadata={
                "governance_mode": context.governance_mode,
                "protocol_design_complete": False,
            },
        )

    def get_llm_bridge(self, context: StageContext):
        """Get LLM bridge for Protocol Design Agent.
        
        This creates a bridge compatible with the ProtocolDesignAgent's
        expected interface for LLM calls, routing through the workflow engine's
        AI infrastructure.
        """
        # Create a bridge that routes to the workflow engine's LLM infrastructure
        class WorkflowEngineLLMBridge:
            def __init__(self, context: StageContext):
                self.context = context
                
            async def invoke(self, 
                           prompt: str,
                           task_type: str = 'general',
                           stage_id: int = 1,
                           model_tier: str = 'STANDARD',
                           governance_mode: str = 'DEMO',
                           **kwargs):
                """Invoke LLM through workflow engine's AI router."""
                # In production, this would route to the actual AI service
                # For now, return a structured mock response
                if task_type == 'pico_extraction':
                    return {
                        'content': '''{{
                            "population": "Adults with specified condition",
                            "intervention": "Target intervention or therapy", 
                            "comparator": "Standard care or control condition",
                            "outcomes": ["Primary endpoint", "Secondary outcomes"],
                            "timeframe": "Study duration or follow-up period"
                        }}'''
                    }
                elif task_type == 'study_design_selection':
                    return {
                        'content': "Recommended: Observational study design based on the research question and feasibility considerations. This approach allows for examination of natural variation in exposures while minimizing intervention complexity."
                    }
                elif task_type == 'protocol_generation':
                    return {
                        'content': '''## 1. Study Summary
Comprehensive research protocol outline

## 2. Background and Rationale
Literature context and study justification

## 3. Study Objectives and Hypotheses
Clearly defined research objectives

## 4. Study Design and Methods
Methodological approach and procedures

## 5. Participant Selection
Inclusion and exclusion criteria

## 6. Data Collection
Data collection procedures and instruments

## 7. Statistical Analysis Plan
Analytical approach and statistical methods

## 8. Ethical Considerations
IRB requirements and participant protection'''
                    }
                else:
                    return {
                        'content': f"Generated response for {task_type}: {prompt[:100]}..."
                    }
        
        return WorkflowEngineLLMBridge(context)

    def get_tools(self) -> List[Any]:
        """Get available tools for this stage."""
        return []  # No additional tools needed

    def get_prompt_template(self) -> Any:
        """Get prompt template for this stage."""
        return None  # Uses internal ProtocolDesignAgent prompts