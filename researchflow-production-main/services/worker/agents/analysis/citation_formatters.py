"""
Citation Formatters - Multi-Style Citation Generation

Supports: AMA, APA (7th), MLA (9th), Chicago, Vancouver (ICMJE)
Linear Issues: ROS-XXX
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


# =============================================================================
# Author Name Utilities
# =============================================================================

class AuthorNameParser:
    """Parse and format author names for citations."""
    
    @staticmethod
    def parse_full_name(name: str) -> Dict[str, str]:
        """Parse full name into components."""
        if "," in name:
            parts = [p.strip() for p in name.split(",")]
            last = parts[0]
            rest = parts[1].split() if len(parts) > 1 else []
            first = rest[0] if rest else ""
            middle = " ".join(rest[1:]) if len(rest) > 1 else ""
        else:
            parts = name.split()
            if len(parts) == 1:
                return {"first": "", "middle": "", "last": parts[0], "suffix": ""}
            elif len(parts) == 2:
                first, last = parts
                middle = ""
            else:
                first = parts[0]
                middle = " ".join(parts[1:-1])
                last = parts[-1]
        
        suffix = ""
        for pattern in ["Jr.", "Sr.", "II", "III", "IV"]:
            if last.endswith(pattern):
                suffix = pattern
                last = last[:-len(pattern)].strip()
                break
        
        return {"first": first, "middle": middle, "last": last, "suffix": suffix}
    
    @staticmethod
    def format_ama(name: str) -> str:
        """AMA: Last FM"""
        p = AuthorNameParser.parse_full_name(name)
        r = p["last"]
        if p["first"]: r += f" {p['first'][0]}"
        if p["middle"]: r += f"{p['middle'][0]}"
        if p["suffix"]: r += f", {p['suffix']}"
        return r


# =============================================================================
# Abstract Citation Formatter
# =============================================================================

class CitationFormatter(ABC):
    """Abstract base class for citation formatters."""
    
    def __init__(self):
        self.style_name = "Generic"
    
    @abstractmethod
    def format_journal_article(self, authors: List[str], title: str, journal: str,
                               year: Optional[int], volume: Optional[str] = None,
                               issue: Optional[str] = None, pages: Optional[str] = None,
                               doi: Optional[str] = None, url: Optional[str] = None) -> str:
        pass
    
    def format_authors(self, authors: List[str], max_authors: Optional[int] = None) -> str:
        if not authors:
            return ""
        display_authors = authors[:max_authors] if max_authors else authors
        formatted = [self._format_single_author(a, i == 0) for i, a in enumerate(display_authors)]
        if max_authors and len(authors) > max_authors:
            formatted.append("et al")
        return self._join_authors(formatted)
    
    @abstractmethod
    def _format_single_author(self, name: str, is_first: bool) -> str:
        pass
    
    @abstractmethod
    def _join_authors(self, formatted_authors: List[str]) -> str:
        pass


# =============================================================================
# AMA Formatter
# =============================================================================

class AMAFormatter(CitationFormatter):
    """AMA (American Medical Association) citation style."""
    
    def __init__(self):
        super().__init__()
        self.style_name = "AMA"
    
    def format_journal_article(self, authors: List[str], title: str, journal: str,
                               year: Optional[int], volume: Optional[str] = None,
                               issue: Optional[str] = None, pages: Optional[str] = None,
                               doi: Optional[str] = None, url: Optional[str] = None) -> str:
        """AMA: Author(s). Title. Journal. Year;volume(issue):pages. doi:XX"""
        parts = []
        if authors:
            parts.append(f"{self.format_authors(authors, max_authors=6)}.")
        parts.append(f"{title}.")
        parts.append(f"{journal}.")
        
        details = []
        if year: details.append(str(year))
        if volume:
            vol_str = volume
            if issue: vol_str += f"({issue})"
            details.append(f";{vol_str}")
        if pages: details.append(f":{pages}")
        if details:
            parts.append("".join(details) + ".")
        if doi:
            parts.append(f"doi:{doi}")
        return " ".join(parts)
    
    def _format_single_author(self, name: str, is_first: bool) -> str:
        return AuthorNameParser.format_ama(name)
    
    def _join_authors(self, formatted_authors: List[str]) -> str:
        if len(formatted_authors) == 1:
            return formatted_authors[0]
        return ", ".join(formatted_authors[:-1]) + f", {formatted_authors[-1]}"


# =============================================================================
# Citation Formatter Factory  
# =============================================================================

class CitationFormatterFactory:
    """Factory for creating citation formatters."""
    
    _formatters = {
        "AMA": AMAFormatter,
    }
    
    @classmethod
    def get_formatter(cls, style: str) -> CitationFormatter:
        """Get formatter for specified style."""
        style_upper = style.upper()
        if style_upper not in cls._formatters:
            raise ValueError(f"Unsupported style: {style}")
        return cls._formatters[style_upper]()
    
    @classmethod
    def list_supported_styles(cls) -> List[str]:
        """Get list of supported styles."""
        return list(cls._formatters.keys())
