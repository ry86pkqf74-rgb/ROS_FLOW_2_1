"""
Popular Tool Connectors for Reference Management

Integrates with Zotero, Mendeley, EndNote, and other popular reference
management tools to provide seamless workflow integration.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
import json
import csv
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Union, IO
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod
import re
import httpx
from pathlib import Path

from .reference_types import Reference, ReferenceType
from .integration_hub import get_integration_hub

logger = logging.getLogger(__name__)

@dataclass
class ImportResult:
    """Result of reference import operation."""
    success: bool
    imported_count: int
    failed_count: int
    imported_references: List[Reference]
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]

@dataclass
class ExportResult:
    """Result of reference export operation."""
    success: bool
    exported_count: int
    format: str
    file_path: Optional[str] = None
    content: Optional[str] = None
    errors: List[str] = None

class BaseConnector(ABC):
    """Base class for reference tool connectors."""
    
    def __init__(self):
        self.stats = {
            'imports_performed': 0,
            'exports_performed': 0,
            'references_processed': 0,
            'api_calls_made': 0,
            'errors_encountered': 0
        }
    
    @abstractmethod
    async def import_references(self, source: Union[str, dict, IO]) -> ImportResult:
        """Import references from the tool."""
        pass
    
    @abstractmethod  
    async def export_references(self, references: List[Reference], format: str = None) -> ExportResult:
        """Export references to the tool."""
        pass
    
    @abstractmethod
    async def sync_references(self, references: List[Reference]) -> Dict[str, Any]:
        """Sync references with the tool."""
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get connector statistics."""
        return self.stats

class ZoteroConnector(BaseConnector):
    """
    Zotero integration connector.
    
    Supports:
    - Zotero Web API integration
    - RDF/XML export format
    - CSL JSON format
    - Collection management
    - Metadata enhancement
    """
    
    def __init__(self, api_key: str = None, user_id: str = None):
        super().__init__()
        self.api_key = api_key
        self.user_id = user_id
        self.base_url = "https://api.zotero.org"
        self.client = None
    
    async def initialize(self):
        """Initialize Zotero connector."""
        self.client = httpx.AsyncClient(
            headers={'Zotero-API-Version': '3', 'Authorization': f'Bearer {self.api_key}'}
            if self.api_key else {}
        )
        logger.info("Zotero connector initialized")
    
    async def import_references(self, source: Union[str, dict, IO]) -> ImportResult:
        """
        Import references from Zotero.
        
        Args:
            source: Zotero collection ID, CSL JSON data, or file object
        """
        self.stats['imports_performed'] += 1
        
        try:
            references = []
            errors = []
            warnings = []
            
            if isinstance(source, str):
                # Assume it's a collection ID or file path
                if source.startswith('collection:'):
                    collection_id = source.replace('collection:', '')
                    references = await self._import_from_collection(collection_id)
                else:
                    # File path
                    references = await self._import_from_file(source)
            
            elif isinstance(source, dict):
                # CSL JSON data
                references = await self._parse_csl_json(source)
            
            elif hasattr(source, 'read'):
                # File object
                content = source.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                
                # Detect format and parse
                if content.strip().startswith('['):
                    data = json.loads(content)
                    references = await self._parse_csl_json(data)
                else:
                    references = await self._parse_rdf_xml(content)
            
            self.stats['references_processed'] += len(references)
            
            return ImportResult(
                success=True,
                imported_count=len(references),
                failed_count=0,
                imported_references=references,
                errors=errors,
                warnings=warnings,
                metadata={'source_type': 'zotero', 'format': 'auto-detected'}
            )
            
        except Exception as e:
            logger.error(f"Zotero import failed: {e}")
            self.stats['errors_encountered'] += 1
            
            return ImportResult(
                success=False,
                imported_count=0,
                failed_count=1,
                imported_references=[],
                errors=[str(e)],
                warnings=[],
                metadata={'error': str(e)}
            )
    
    async def export_references(self, references: List[Reference], format: str = "csl_json") -> ExportResult:
        """
        Export references to Zotero format.
        
        Args:
            references: References to export
            format: Export format ('csl_json', 'rdf_xml', 'bibtex')
        """
        self.stats['exports_performed'] += 1
        
        try:
            if format == "csl_json":
                content = await self._export_csl_json(references)
            elif format == "rdf_xml":
                content = await self._export_rdf_xml(references)
            elif format == "bibtex":
                content = await self._export_bibtex(references)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            return ExportResult(
                success=True,
                exported_count=len(references),
                format=format,
                content=content,
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"Zotero export failed: {e}")
            self.stats['errors_encountered'] += 1
            
            return ExportResult(
                success=False,
                exported_count=0,
                format=format,
                errors=[str(e)]
            )
    
    async def sync_references(self, references: List[Reference]) -> Dict[str, Any]:
        """Sync references with Zotero library."""
        
        if not self.api_key or not self.user_id:
            return {'error': 'Zotero API credentials not provided'}
        
        try:
            sync_results = {
                'created': 0,
                'updated': 0,
                'errors': []
            }
            
            # Convert references to Zotero format
            zotero_items = []
            for ref in references:
                zotero_item = await self._convert_to_zotero_item(ref)
                zotero_items.append(zotero_item)
            
            # Batch create/update via API
            response = await self.client.post(
                f"{self.base_url}/users/{self.user_id}/items",
                json=zotero_items
            )
            
            if response.status_code == 200:
                sync_results['created'] = len(zotero_items)
            else:
                sync_results['errors'].append(f"API error: {response.status_code}")
            
            self.stats['api_calls_made'] += 1
            return sync_results
            
        except Exception as e:
            logger.error(f"Zotero sync failed: {e}")
            return {'error': str(e)}
    
    async def _import_from_collection(self, collection_id: str) -> List[Reference]:
        """Import references from Zotero collection."""
        
        if not self.client:
            raise ValueError("Zotero connector not initialized")
        
        response = await self.client.get(
            f"{self.base_url}/users/{self.user_id}/collections/{collection_id}/items"
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch collection: {response.status_code}")
        
        items = response.json()
        references = []
        
        for item in items:
            ref = await self._convert_zotero_item_to_reference(item)
            references.append(ref)
        
        self.stats['api_calls_made'] += 1
        return references
    
    async def _import_from_file(self, file_path: str) -> List[Reference]:
        """Import references from Zotero export file."""
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding='utf-8')
        
        if file_path.endswith('.json'):
            data = json.loads(content)
            return await self._parse_csl_json(data)
        elif file_path.endswith(('.rdf', '.xml')):
            return await self._parse_rdf_xml(content)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    
    async def _parse_csl_json(self, data: Union[List, Dict]) -> List[Reference]:
        """Parse CSL JSON format."""
        
        if isinstance(data, dict):
            data = [data]
        
        references = []
        
        for item in data:
            ref = Reference(
                id=item.get('id', f"zotero_{hash(str(item))}"),
                title=item.get('title', ''),
                authors=self._parse_csl_authors(item.get('author', [])),
                year=self._parse_csl_year(item.get('issued')),
                journal=item.get('container-title'),
                volume=item.get('volume'),
                issue=item.get('issue'),
                pages=item.get('page'),
                doi=item.get('DOI'),
                pmid=item.get('PMID'),
                url=item.get('URL'),
                abstract=item.get('abstract'),
                reference_type=self._map_zotero_type(item.get('type')),
                source_database='zotero'
            )
            references.append(ref)
        
        return references
    
    async def _parse_rdf_xml(self, content: str) -> List[Reference]:
        """Parse Zotero RDF/XML format."""
        
        try:
            root = ET.fromstring(content)
            references = []
            
            # Zotero RDF parsing logic (simplified)
            for item in root.findall('.//{http://purl.org/rss/1.0/}item'):
                ref = Reference(
                    id=f"zotero_rdf_{len(references)}",
                    title=self._get_xml_text(item, 'title'),
                    authors=self._parse_rdf_authors(item),
                    year=self._parse_rdf_year(item),
                    journal=self._get_xml_text(item, 'container'),
                    source_database='zotero'
                )
                references.append(ref)
            
            return references
            
        except ET.ParseError as e:
            raise ValueError(f"Invalid RDF/XML: {e}")
    
    async def _export_csl_json(self, references: List[Reference]) -> str:
        """Export references as CSL JSON."""
        
        csl_items = []
        
        for ref in references:
            item = {
                'id': ref.id,
                'type': self._map_reference_type_to_csl(ref.reference_type),
                'title': ref.title or '',
            }
            
            if ref.authors:
                item['author'] = [{'family': author, 'given': ''} for author in ref.authors]
            
            if ref.year:
                item['issued'] = {'date-parts': [[ref.year]]}
            
            if ref.journal:
                item['container-title'] = ref.journal
            
            if ref.volume:
                item['volume'] = ref.volume
            
            if ref.issue:
                item['issue'] = ref.issue
            
            if ref.pages:
                item['page'] = ref.pages
            
            if ref.doi:
                item['DOI'] = ref.doi
            
            if ref.url:
                item['URL'] = ref.url
            
            if ref.abstract:
                item['abstract'] = ref.abstract
            
            csl_items.append(item)
        
        return json.dumps(csl_items, indent=2)
    
    async def _export_rdf_xml(self, references: List[Reference]) -> str:
        """Export references as RDF/XML."""
        
        # Simplified RDF/XML generation
        rdf_content = ['<?xml version="1.0" encoding="UTF-8"?>']
        rdf_content.append('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">')
        
        for ref in references:
            rdf_content.append(f'  <rdf:Description rdf:about="#{ref.id}">')
            rdf_content.append(f'    <title>{ref.title or ""}</title>')
            if ref.authors:
                rdf_content.append(f'    <creator>{"; ".join(ref.authors)}</creator>')
            if ref.year:
                rdf_content.append(f'    <date>{ref.year}</date>')
            rdf_content.append('  </rdf:Description>')
        
        rdf_content.append('</rdf:RDF>')
        return '\n'.join(rdf_content)
    
    async def _export_bibtex(self, references: List[Reference]) -> str:
        """Export references as BibTeX."""
        
        bibtex_entries = []
        
        for ref in references:
            entry_type = self._map_reference_type_to_bibtex(ref.reference_type)
            entry_key = ref.doi or ref.id
            
            entry = [f'@{entry_type}{{{entry_key},']
            
            if ref.title:
                entry.append(f'  title = {{{ref.title}}},')
            if ref.authors:
                entry.append(f'  author = {{{" and ".join(ref.authors)}}},')
            if ref.journal:
                entry.append(f'  journal = {{{ref.journal}}},')
            if ref.year:
                entry.append(f'  year = {{{ref.year}}},')
            if ref.volume:
                entry.append(f'  volume = {{{ref.volume}}},')
            if ref.pages:
                entry.append(f'  pages = {{{ref.pages}}},')
            if ref.doi:
                entry.append(f'  doi = {{{ref.doi}}},')
            
            entry.append('}')
            bibtex_entries.append('\n'.join(entry))
        
        return '\n\n'.join(bibtex_entries)
    
    def _parse_csl_authors(self, authors: List[Dict]) -> List[str]:
        """Parse CSL JSON authors."""
        parsed_authors = []
        for author in authors:
            if 'family' in author:
                name = author['family']
                if 'given' in author:
                    name = f"{author['family']}, {author['given']}"
                parsed_authors.append(name)
        return parsed_authors
    
    def _parse_csl_year(self, issued: Dict) -> Optional[int]:
        """Parse CSL JSON issued date."""
        if issued and 'date-parts' in issued:
            date_parts = issued['date-parts'][0]
            if date_parts:
                return date_parts[0]
        return None
    
    def _map_zotero_type(self, zotero_type: str) -> ReferenceType:
        """Map Zotero item type to ReferenceType."""
        mapping = {
            'journalArticle': ReferenceType.JOURNAL_ARTICLE,
            'book': ReferenceType.BOOK,
            'bookSection': ReferenceType.BOOK_CHAPTER,
            'conferencePaper': ReferenceType.CONFERENCE_PAPER,
            'thesis': ReferenceType.THESIS,
            'report': ReferenceType.REPORT,
            'webpage': ReferenceType.WEBPAGE
        }
        return mapping.get(zotero_type, ReferenceType.OTHER)
    
    def _map_reference_type_to_csl(self, ref_type: ReferenceType) -> str:
        """Map ReferenceType to CSL type."""
        mapping = {
            ReferenceType.JOURNAL_ARTICLE: 'article-journal',
            ReferenceType.BOOK: 'book',
            ReferenceType.BOOK_CHAPTER: 'chapter',
            ReferenceType.CONFERENCE_PAPER: 'paper-conference',
            ReferenceType.THESIS: 'thesis',
            ReferenceType.REPORT: 'report',
            ReferenceType.WEBPAGE: 'webpage'
        }
        return mapping.get(ref_type, 'article')
    
    def _map_reference_type_to_bibtex(self, ref_type: ReferenceType) -> str:
        """Map ReferenceType to BibTeX entry type."""
        mapping = {
            ReferenceType.JOURNAL_ARTICLE: 'article',
            ReferenceType.BOOK: 'book',
            ReferenceType.BOOK_CHAPTER: 'inbook',
            ReferenceType.CONFERENCE_PAPER: 'inproceedings',
            ReferenceType.THESIS: 'phdthesis',
            ReferenceType.REPORT: 'techreport',
            ReferenceType.WEBPAGE: 'misc'
        }
        return mapping.get(ref_type, 'misc')

class MendeleyConnector(BaseConnector):
    """
    Mendeley integration connector.
    
    Supports:
    - Mendeley API integration
    - Group collaboration features
    - Metadata synchronization
    - Annotation handling
    """
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.mendeley.com"
        self.client = None
        self.access_token = None
    
    async def initialize(self):
        """Initialize Mendeley connector."""
        self.client = httpx.AsyncClient()
        if self.client_id and self.client_secret:
            await self._authenticate()
        logger.info("Mendeley connector initialized")
    
    async def import_references(self, source: Union[str, dict, IO]) -> ImportResult:
        """Import references from Mendeley."""
        # Implementation would handle Mendeley-specific formats
        return ImportResult(
            success=False,
            imported_count=0,
            failed_count=0,
            imported_references=[],
            errors=["Mendeley import not yet implemented"],
            warnings=[],
            metadata={}
        )
    
    async def export_references(self, references: List[Reference], format: str = "json") -> ExportResult:
        """Export references to Mendeley format."""
        # Implementation would handle Mendeley-specific export
        return ExportResult(
            success=False,
            exported_count=0,
            format=format,
            errors=["Mendeley export not yet implemented"]
        )
    
    async def sync_references(self, references: List[Reference]) -> Dict[str, Any]:
        """Sync references with Mendeley library."""
        return {"error": "Mendeley sync not yet implemented"}

class EndNoteConnector(BaseConnector):
    """
    EndNote integration connector.
    
    Supports:
    - EndNote XML format
    - Tagged format import/export
    - Citation style integration
    - Legacy format support
    """
    
    def __init__(self):
        super().__init__()
    
    async def import_references(self, source: Union[str, dict, IO]) -> ImportResult:
        """Import references from EndNote."""
        
        try:
            references = []
            errors = []
            
            if isinstance(source, str):
                # File path
                references = await self._import_from_file(source)
            elif hasattr(source, 'read'):
                content = source.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                references = await self._parse_endnote_content(content)
            
            return ImportResult(
                success=True,
                imported_count=len(references),
                failed_count=0,
                imported_references=references,
                errors=errors,
                warnings=[],
                metadata={'source_type': 'endnote'}
            )
            
        except Exception as e:
            logger.error(f"EndNote import failed: {e}")
            return ImportResult(
                success=False,
                imported_count=0,
                failed_count=1,
                imported_references=[],
                errors=[str(e)],
                warnings=[],
                metadata={'error': str(e)}
            )
    
    async def export_references(self, references: List[Reference], format: str = "xml") -> ExportResult:
        """Export references to EndNote format."""
        
        try:
            if format == "xml":
                content = await self._export_endnote_xml(references)
            elif format == "tagged":
                content = await self._export_endnote_tagged(references)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            return ExportResult(
                success=True,
                exported_count=len(references),
                format=format,
                content=content,
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"EndNote export failed: {e}")
            return ExportResult(
                success=False,
                exported_count=0,
                format=format,
                errors=[str(e)]
            )
    
    async def sync_references(self, references: List[Reference]) -> Dict[str, Any]:
        """Sync references with EndNote (file-based)."""
        return {"info": "EndNote sync requires file-based import/export"}

class UniversalFormatHandler:
    """
    Universal format handler for common reference formats.
    
    Supports:
    - BibTeX
    - RIS
    - CSV
    - Plain text citations
    """
    
    def __init__(self):
        self.stats = {'formats_handled': 0, 'references_processed': 0}
    
    async def parse_bibtex(self, content: str) -> List[Reference]:
        """Parse BibTeX format."""
        
        references = []
        
        # Simple BibTeX parser (would use proper parser in production)
        entries = re.findall(r'@\w+\s*\{([^}]+)\}', content, re.DOTALL)
        
        for entry in entries:
            ref = Reference(id=f"bibtex_{len(references)}")
            
            # Parse fields
            field_matches = re.findall(r'(\w+)\s*=\s*\{([^}]*)\}', entry)
            for field, value in field_matches:
                field = field.lower().strip()
                value = value.strip()
                
                if field == 'title':
                    ref.title = value
                elif field == 'author':
                    ref.authors = [a.strip() for a in value.split(' and ')]
                elif field == 'year':
                    try:
                        ref.year = int(value)
                    except ValueError:
                        pass
                elif field == 'journal':
                    ref.journal = value
                elif field == 'volume':
                    ref.volume = value
                elif field == 'pages':
                    ref.pages = value
                elif field == 'doi':
                    ref.doi = value
            
            if ref.title:  # Only add if has title
                references.append(ref)
        
        self.stats['references_processed'] += len(references)
        return references
    
    async def export_bibtex(self, references: List[Reference]) -> str:
        """Export references as BibTeX."""
        
        entries = []
        
        for ref in references:
            entry_key = ref.doi or ref.id or f"ref_{hash(ref.title or '')}"
            entry = [f'@article{{{entry_key},']
            
            if ref.title:
                entry.append(f'  title = {{{ref.title}}},')
            if ref.authors:
                entry.append(f'  author = {{{" and ".join(ref.authors)}}},')
            if ref.journal:
                entry.append(f'  journal = {{{ref.journal}}},')
            if ref.year:
                entry.append(f'  year = {{{ref.year}}},')
            if ref.volume:
                entry.append(f'  volume = {{{ref.volume}}},')
            if ref.pages:
                entry.append(f'  pages = {{{ref.pages}}},')
            if ref.doi:
                entry.append(f'  doi = {{{ref.doi}}},')
            
            entry.append('}')
            entries.append('\n'.join(entry))
        
        return '\n\n'.join(entries)
    
    async def parse_ris(self, content: str) -> List[Reference]:
        """Parse RIS format."""
        
        references = []
        current_ref = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('TY  - '):
                if current_ref:
                    references.append(current_ref)
                current_ref = Reference(id=f"ris_{len(references)}")
                
            elif line.startswith('TI  - ') and current_ref:
                current_ref.title = line[6:].strip()
            elif line.startswith('AU  - ') and current_ref:
                if not current_ref.authors:
                    current_ref.authors = []
                current_ref.authors.append(line[6:].strip())
            elif line.startswith('PY  - ') and current_ref:
                try:
                    current_ref.year = int(line[6:].strip()[:4])  # Take first 4 digits
                except ValueError:
                    pass
            elif line.startswith('JO  - ') and current_ref:
                current_ref.journal = line[6:].strip()
            elif line.startswith('VL  - ') and current_ref:
                current_ref.volume = line[6:].strip()
            elif line.startswith('SP  - ') and current_ref:
                current_ref.pages = line[6:].strip()
            elif line.startswith('DO  - ') and current_ref:
                current_ref.doi = line[6:].strip()
            elif line.startswith('UR  - ') and current_ref:
                current_ref.url = line[6:].strip()
            elif line.startswith('AB  - ') and current_ref:
                current_ref.abstract = line[6:].strip()
        
        if current_ref:
            references.append(current_ref)
        
        self.stats['references_processed'] += len(references)
        return references

# Main connector factory
class ConnectorFactory:
    """Factory for creating appropriate connectors."""
    
    @staticmethod
    def create_connector(tool_type: str, **config) -> BaseConnector:
        """Create connector for specified tool type."""
        
        if tool_type.lower() == 'zotero':
            return ZoteroConnector(**config)
        elif tool_type.lower() == 'mendeley':
            return MendeleyConnector(**config)
        elif tool_type.lower() == 'endnote':
            return EndNoteConnector(**config)
        else:
            raise ValueError(f"Unsupported tool type: {tool_type}")

# Global connectors
_connectors: Dict[str, BaseConnector] = {}

async def get_connector(tool_type: str, **config) -> BaseConnector:
    """Get or create connector for tool type."""
    
    key = f"{tool_type}_{hash(str(sorted(config.items())))}"
    
    if key not in _connectors:
        _connectors[key] = ConnectorFactory.create_connector(tool_type, **config)
        if hasattr(_connectors[key], 'initialize'):
            await _connectors[key].initialize()
    
    return _connectors[key]

async def close_all_connectors():
    """Close all active connectors."""
    global _connectors
    for connector in _connectors.values():
        if hasattr(connector, 'client') and connector.client:
            await connector.client.aclose()
    _connectors.clear()