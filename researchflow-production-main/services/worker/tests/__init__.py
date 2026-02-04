"""
Phase 8 Testing Module - ResearchFlow Worker Service

Test suite for:
- LangGraph agents (DataPrep, Analysis, Quality, IRB, Manuscript)
- RAG hybrid retriever system
- Agent execution and state management
- PHI detection and validation
- Quality gate evaluation
- Document chunking and retrieval

Test Configuration:
- pytest with asyncio support
- Mock LLM bridges for testing
- Fixtures for test data and state
- Comprehensive agent lifecycle testing
"""

import os

# Configure test environment
os.environ.setdefault('GOVERNANCE_MODE', 'DEMO')
os.environ.setdefault('OCR_ENABLED', 'false')
os.environ.setdefault('SCISPACY_ENABLED', 'false')
os.environ.setdefault('EMBEDDINGS_PROVIDER', 'mock')

__version__ = '8.0.0'
__description__ = 'Phase 8: Testing & Validation for ResearchFlow Agents and RAG'
