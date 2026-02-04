"""
Base Stage Agent

Abstract base class for all 20 workflow stage agents.
Provides common infrastructure for:
- Stage execution (implements Stage protocol)
- ManuscriptClient integration for TypeScript service calls
- LangChain/LangGraph patterns for agent-based stages
- Tool and prompt template management

See: Linear ROS-122
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
import logging
from datetime import datetime

# LangChain/LangGraph imports with graceful fallback
try:
    from langchain_core.tools import BaseTool
    from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = Any  # type: ignore
    ChatPromptTemplate = Any  # type: ignore
    PromptTemplate = Any  # type: ignore
    logging.warning("LangChain not available. Install with: pip install langchain")

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = Any  # type: ignore
    END = None  # type: ignore
    MemorySaver = Any  # type: ignore
    logging.warning("LangGraph not available. Install with: pip install langgraph")

from ..types import StageContext, StageResult
from ..bridge import ManuscriptClient, BridgeConfig

logger = logging.getLogger("workflow_engine.base_stage_agent")


class BaseStageAgent(ABC):
    """
    Abstract base class for all 20 workflow stage agents.
    
    Combines the Stage protocol with LangGraph agent capabilities and
    ManuscriptClient integration for calling TypeScript services.
    
    Subclasses must implement:
    - execute(): Core stage execution logic
    - get_tools(): Return LangChain tools available to this stage
    - get_prompt_template(): Return prompt template for this stage
    
    Optional overrides:
    - build_graph(): Build LangGraph workflow (if using LangGraph)
    - get_quality_criteria(): Return quality gate criteria
    """
    
    # Stage protocol attributes (must be set by subclasses)
    stage_id: int
    stage_name: str
    
    def __init__(
        self,
        bridge_config: Optional[BridgeConfig] = None,
        use_langgraph: bool = False,
        checkpointer: Optional[Any] = None,
    ):
        """
        Initialize the base stage agent.
        
        Args:
            bridge_config: Configuration for ManuscriptClient bridge.
                          If None, loads from environment.
            use_langgraph: Whether to enable LangGraph workflow support
            checkpointer: LangGraph checkpointer (only used if use_langgraph=True)
        """
        self.bridge_config = bridge_config or BridgeConfig.from_env()
        self.use_langgraph = use_langgraph and LANGGRAPH_AVAILABLE
        self.checkpointer = checkpointer or (MemorySaver() if self.use_langgraph else None)
        
        # Lazy initialization
        self._manuscript_client: Optional[ManuscriptClient] = None
        self._tools: Optional[List[BaseTool]] = None
        self._prompt_template: Optional[PromptTemplate] = None
        self._graph: Optional[StateGraph] = None
    
    @property
    def manuscript_client(self) -> ManuscriptClient:
        """
        Get or create ManuscriptClient instance.
        
        Returns:
            ManuscriptClient for calling TypeScript services
        """
        if self._manuscript_client is None:
            self._manuscript_client = ManuscriptClient(self.bridge_config)
        return self._manuscript_client
    
    @property
    def tools(self) -> List[BaseTool]:
        """
        Get LangChain tools for this stage.
        
        Returns:
            List of LangChain tools
        """
        if self._tools is None:
            self._tools = self.get_tools()
        return self._tools
    
    @property
    def prompt_template(self) -> PromptTemplate:
        """
        Get prompt template for this stage.
        
        Returns:
            LangChain PromptTemplate
        """
        if self._prompt_template is None:
            self._prompt_template = self.get_prompt_template()
        return self._prompt_template
    
    @property
    def graph(self) -> Optional[StateGraph]:
        """
        Get LangGraph workflow (if enabled).
        
        Returns:
            Compiled StateGraph or None if LangGraph not enabled
        """
        if not self.use_langgraph:
            return None
        
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph
    
    # =========================================================================
    # Abstract Methods (must be implemented by subclasses)
    # =========================================================================
    
    @abstractmethod
    async def execute(self, context: StageContext) -> StageResult:
        """
        Execute the stage with the given context.
        
        This is the main entry point for stage execution. It implements
        the Stage protocol required by the workflow engine.
        
        Args:
            context: Stage execution context with job info, config, etc.
            
        Returns:
            StageResult containing execution results and artifacts
        """
        pass
    
    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
        """
        Get LangChain tools available to this stage.
        
        Subclasses should return a list of LangChain-compatible tools
        that can be used during stage execution. Return empty list if
        no tools are needed.
        
        Returns:
            List of LangChain BaseTool instances
        """
        if not LANGCHAIN_AVAILABLE:
            logger.warning("LangChain not available, returning empty tools list")
            return []
        return []
    
    @abstractmethod
    def get_prompt_template(self) -> PromptTemplate:
        """
        Get prompt template for this stage.
        
        Subclasses should return a LangChain PromptTemplate that defines
        the prompt structure for this stage's AI interactions.
        
        Returns:
            LangChain PromptTemplate instance
        """
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        return PromptTemplate.from_template(
            "You are executing stage {stage_id}: {stage_name}\n\n"
            "Context: {context}\n\n"
            "Task: {input}"
        )
    
    # =========================================================================
    # Optional Override Methods (for LangGraph-enabled stages)
    # =========================================================================
    
    def build_graph(self) -> Optional[StateGraph]:
        """
        Build LangGraph workflow for this stage (optional).
        
        Override this method if you want to use LangGraph for complex
        multi-step workflows within a single stage.
        
        Returns:
            Compiled StateGraph or None if not using LangGraph
        """
        if not self.use_langgraph:
            return None
        
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not available, cannot build graph")
            return None
        
        # Default simple graph: start -> execute -> end
        graph = StateGraph(dict)  # type: ignore
        
        # Add a single node that calls execute
        graph.add_node("execute", self._graph_execute_node)
        graph.set_entry_point("execute")
        graph.add_edge("execute", END)
        
        # Compile with checkpointer if available
        if self.checkpointer:
            return graph.compile(checkpointer=self.checkpointer)
        return graph.compile()
    
    def get_quality_criteria(self) -> Dict[str, Any]:
        """
        Get quality criteria for this stage (optional).
        
        Override this method to define quality gates for stage output.
        Used by quality gate evaluation if implemented.
        
        Returns:
            Dict mapping criterion names to threshold values
        """
        return {}
    
    # =========================================================================
    # Helper Methods for Stage Execution
    # =========================================================================
    
    async def call_manuscript_service(
        self,
        service_name: str,
        method_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Call a TypeScript manuscript service via the bridge.
        
        Convenience method for subclasses to call TypeScript services.
        
        Args:
            service_name: Name of the service (e.g., 'claude-writer')
            method_name: Name of the method (e.g., 'generateParagraph')
            params: Parameters to pass to the method
            
        Returns:
            Response data from the service
            
        Raises:
            Exception: If service call fails
        """
        async with self.manuscript_client as client:
            return await client.call_service(service_name, method_name, params)
    
    async def generate_paragraph(
        self,
        topic: str,
        context: str,
        key_points: Optional[List[str]] = None,
        section: str = "methods",
        tone: str = "formal",
        target_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a paragraph using Claude writer service.
        
        Convenience method for calling the paragraph generation service.
        
        Args:
            topic: Topic of the paragraph
            context: Context information
            key_points: List of key points to address
            section: Manuscript section (e.g., 'methods', 'results')
            tone: Writing tone ('formal', 'concise', etc.)
            target_length: Target word count (optional)
            
        Returns:
            Generated paragraph with reasoning and metadata
        """
        async with self.manuscript_client as client:
            return await client.generate_paragraph(
                topic=topic,
                context=context,
                key_points=key_points,
                section=section,
                tone=tone,
                target_length=target_length,
            )
    
    async def generate_abstract(
        self,
        manuscript_id: str,
        style: str = "structured",
        journal_template: Optional[str] = None,
        autofill: Optional[Dict[str, Any]] = None,
        max_words: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a research abstract.
        
        Convenience method for calling the abstract generation service.
        
        Args:
            manuscript_id: ID of the manuscript
            style: Abstract style ('structured', 'unstructured', 'journal_specific')
            journal_template: Journal template (e.g., 'nejm', 'jama')
            autofill: Autofill data (studyDesign, sampleSize, etc.)
            max_words: Maximum word count
            
        Returns:
            Generated abstract with sections and metadata
        """
        async with self.manuscript_client as client:
            return await client.generate_abstract(
                manuscript_id=manuscript_id,
                style=style,
                journal_template=journal_template,
                autofill=autofill,
                max_words=max_words,
            )
    
    async def generate_irb_protocol(
        self,
        study_title: str,
        principal_investigator: str,
        study_type: str,
        hypothesis: str,
        population: str,
        data_source: str,
        variables: List[str],
        analysis_approach: str,
        institution: Optional[str] = None,
        expected_duration: Optional[str] = None,
        risks: Optional[List[str]] = None,
        benefits: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate an IRB protocol.
        
        Convenience method for calling the IRB protocol generation service.
        
        Args:
            study_title: Title of the study
            principal_investigator: Name of principal investigator
            study_type: Type of study ('retrospective', 'prospective', 'clinical_trial')
            hypothesis: Research hypothesis
            population: Study population description
            data_source: Data source description
            variables: List of variables to be collected
            analysis_approach: Statistical analysis approach
            institution: Institution name (optional)
            expected_duration: Expected study duration (optional)
            risks: List of potential risks (optional)
            benefits: List of potential benefits (optional)
            
        Returns:
            Generated IRB protocol with sections and attachments
        """
        async with self.manuscript_client as client:
            return await client.generate_irb_protocol(
                study_title=study_title,
                principal_investigator=principal_investigator,
                study_type=study_type,
                hypothesis=hypothesis,
                population=population,
                data_source=data_source,
                variables=variables,
                analysis_approach=analysis_approach,
                institution=institution,
                expected_duration=expected_duration,
                risks=risks,
                benefits=benefits,
            )
    
    def create_stage_result(
        self,
        context: StageContext,
        status: str,
        output: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        started_at: Optional[str] = None,
    ) -> StageResult:
        """
        Create a StageResult with standardized formatting.
        
        Helper method to create properly formatted StageResult objects
        with consistent timestamps and metadata.
        
        Args:
            context: Stage execution context
            status: Result status ('completed', 'failed', 'skipped')
            output: Stage output data
            artifacts: List of artifact file paths
            errors: List of error messages
            warnings: List of warning messages
            metadata: Additional metadata
            started_at: Start timestamp (auto-generated if None)
            
        Returns:
            Formatted StageResult
        """
        if started_at is None:
            started_at = datetime.utcnow().isoformat() + "Z"
        
        completed_at = datetime.utcnow().isoformat() + "Z"
        
        # Calculate duration
        started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        duration_ms = int((completed_dt - started_dt).total_seconds() * 1000)
        
        # Merge metadata with governance mode
        final_metadata = {
            "governance_mode": context.governance_mode,
            **(metadata or {}),
        }
        
        return StageResult(
            stage_id=self.stage_id,
            stage_name=self.stage_name,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            output=output or {},
            artifacts=artifacts or [],
            errors=errors or [],
            warnings=warnings or [],
            metadata=final_metadata,
        )
    
    # =========================================================================
    # Internal Helper Methods
    # =========================================================================
    
    def _graph_execute_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal node function for LangGraph execution.
        
        This is used by the default build_graph() implementation.
        Subclasses can override build_graph() to customize the workflow.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated state dict
        """
        # This would need to be called with proper context
        # For now, this is a placeholder that subclasses should override
        logger.warning("Default graph_execute_node called - override build_graph() for custom behavior")
        return state
