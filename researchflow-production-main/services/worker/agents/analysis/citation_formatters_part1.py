"""
Citation Formatters - Part 1: Base Classes and Utilities

Author name parsing and abstract formatter base class.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


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
        suffix_patterns = ["Jr.", "Sr.", "II", "III", "IV"]
        for pattern in suffix_patterns:
            if last.endswith(pattern):
                suffix = pattern
                last = last[:-len(pattern)].strip()
                break
        
        return {"first": first, "middle": middle, "last": last, "suffix": suffix}
    
    @staticmethod
    def format_ama(name: str) -> str:
        """Format name for AMA style: Last FM."""
        parsed = AuthorNameParser.parse_full_name(name)
        result = parsed["last"]
        if parsed["first"]:
            result += f" {parsed['first'][0]}"
        if parsed["middle"]:
            result += f"{parsed['middle'][0]}"
        if parsed["suffix"]:
            result += f", {parsed['suffix']}"
        return result


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
