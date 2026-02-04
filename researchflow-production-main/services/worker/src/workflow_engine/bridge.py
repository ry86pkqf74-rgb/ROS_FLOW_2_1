"""
HTTP bridge client for TypeScript manuscript-engine services.

Provides async client for Python workflow stages to call TypeScript services
via HTTP API at /api/services/{serviceName}/{methodName}.
"""

import os
import httpx
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class BridgeConfig:
    """Configuration for the bridge client."""
    base_url: str = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:3001")
    timeout: float = 30.0
    
    @classmethod
    def from_env(cls) -> "BridgeConfig":
        """Create config from environment variables."""
        return cls(
            base_url=os.getenv("ORCHESTRATOR_URL", "http://orchestrator:3001"),
            timeout=float(os.getenv("BRIDGE_TIMEOUT", "30.0"))
        )


class ManuscriptClient:
    """Async client for calling TypeScript manuscript services."""
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        """
        Initialize the manuscript client.
        
        Args:
            config: Bridge configuration. If None, loads from environment.
        """
        self.config = config or BridgeConfig.from_env()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "ManuscriptClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers={"Content-Type": "application/json"}
        )
        return self
    
    async def __aexit__(self, *args):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def call_service(
        self, 
        service_name: str, 
        method_name: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generic method to call any service method.
        
        Args:
            service_name: Name of the service (e.g., 'claude-writer')
            method_name: Name of the method (e.g., 'generateParagraph')
            params: Parameters to pass to the method
            
        Returns:
            Response data from the service
            
        Raises:
            RuntimeError: If client not initialized
            httpx.HTTPStatusError: If HTTP request fails
            Exception: If service returns error
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' statement.")
        
        response = await self._client.post(
            f"/api/services/{service_name}/{method_name}",
            json=params
        )
        response.raise_for_status()
        result = response.json()
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            raise Exception(f"Service error: {error_msg}")
        
        return result.get("data", {})
    
    # Typed convenience methods
    
    async def generate_paragraph(
        self,
        topic: str,
        context: str,
        key_points: Optional[list] = None,
        section: str = "methods",
        tone: str = "formal",
        target_length: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a paragraph using Claude writer.
        
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
        params = {
            "topic": topic,
            "context": context,
            "keyPoints": key_points or [],
            "section": section,
            "tone": tone
        }
        if target_length:
            params["targetLength"] = target_length
            
        return await self.call_service("claude-writer", "generateParagraph", params)
    
    async def generate_abstract(
        self,
        manuscript_id: str,
        style: str = "structured",
        journal_template: Optional[str] = None,
        autofill: Optional[Dict[str, Any]] = None,
        max_words: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a research abstract.
        
        Args:
            manuscript_id: ID of the manuscript
            style: Abstract style ('structured', 'unstructured', 'journal_specific')
            journal_template: Journal template (e.g., 'nejm', 'jama')
            autofill: Autofill data (studyDesign, sampleSize, etc.)
            max_words: Maximum word count
            
        Returns:
            Generated abstract with sections and metadata
        """
        params = {
            "manuscriptId": manuscript_id,
            "style": style
        }
        if journal_template:
            params["journalTemplate"] = journal_template
        if autofill:
            params["autofill"] = autofill
        if max_words:
            params["maxWords"] = max_words
            
        return await self.call_service("abstract-generator", "generateAbstract", params)
    
    async def generate_irb_protocol(
        self,
        study_title: str,
        principal_investigator: str,
        study_type: str,
        hypothesis: str,
        population: str,
        data_source: str,
        variables: list,
        analysis_approach: str,
        institution: Optional[str] = None,
        expected_duration: Optional[str] = None,
        risks: Optional[list] = None,
        benefits: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Generate an IRB protocol.
        
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
        params = {
            "studyTitle": study_title,
            "principalInvestigator": principal_investigator,
            "studyType": study_type,
            "hypothesis": hypothesis,
            "population": population,
            "dataSource": data_source,
            "variables": variables,
            "analysisApproach": analysis_approach
        }
        if institution:
            params["institution"] = institution
        if expected_duration:
            params["expectedDuration"] = expected_duration
        if risks:
            params["risks"] = risks
        if benefits:
            params["benefits"] = benefits
            
        return await self.call_service("irb-generator", "generateProtocol", params)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check bridge health and available services.
        
        Returns:
            Health status with available services
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' statement.")
        
        response = await self._client.get("/api/services/health")
        response.raise_for_status()
        return response.json()


# Usage example:
# async with ManuscriptClient() as client:
#     health = await client.health_check()
#     print(health)
#     
#     result = await client.generate_paragraph(
#         topic="Study design",
#         context="This is a retrospective cohort study",
#         section="methods",
#         tone="formal"
#     )
#     print(result["paragraph"])
