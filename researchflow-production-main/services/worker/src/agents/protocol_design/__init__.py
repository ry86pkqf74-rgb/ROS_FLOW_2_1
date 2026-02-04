"""
Protocol Design Agent - Stage 1

Handles research protocol design with PICO framework:
- Topic declaration (Quick Entry or PICO mode)
- PICO extraction and validation
- Hypothesis generation
- Study type detection
- Protocol outline generation
"""

from .agent import ProtocolDesignAgent

__all__ = ['ProtocolDesignAgent']
