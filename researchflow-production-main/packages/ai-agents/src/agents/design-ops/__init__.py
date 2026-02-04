"""
DesignOps Agent Module

Phase 1.2 Implementation: Figma → Design Tokens → Tailwind Config → PR Automation

This module provides automated design system synchronization between Figma and code,
including design token extraction, Tailwind configuration generation, and PR automation.
"""

from .agent import DesignOpsAgent
from .workflows import (
    FigmaTokenExtractionWorkflow,
    TailwindConfigGenerationWorkflow,
    DesignSystemPRWorkflow,
    WebhookHandlerWorkflow,
)
from .token_transformer import (
    FigmaTokenParser,
    TailwindConfigGenerator,
    TokenValidator,
    DiffGenerator,
)

__all__ = [
    "DesignOpsAgent",
    "FigmaTokenExtractionWorkflow",
    "TailwindConfigGenerationWorkflow",
    "DesignSystemPRWorkflow",
    "WebhookHandlerWorkflow",
    "FigmaTokenParser",
    "TailwindConfigGenerator",
    "TokenValidator",
    "DiffGenerator",
]

__version__ = "0.1.0"
