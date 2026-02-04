"""
Pure NCBI Entrez client for PubMed searches.
No BaseAgent dependencies - uses httpx directly.
"""
import os
import asyncio
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import httpx

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class PubMedClient:
    """Minimal PubMed client using NCBI EUtils API."""
    
    def __init__(self):
        self.api_key = os.getenv("NCBI_API_KEY")
        self.email = os.getenv("NCBI_EMAIL", "researchflow@example.com")
        # Rate limiting: 10 req/sec with API key, 3 req/sec without
        self.rate_limit_delay = 0.1 if self.api_key else 0.34
        
    async def search_pubmed(
        self, 
        query: str, 
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search PubMed and return paper metadata.
        
        Args:
            query: PubMed query string (already formatted with MeSH, filters, etc)
            max_results: Maximum number of results to return
            
        Returns:
            List of paper dictionaries with standardized fields
        """
        # Step 1: ESearch to get PMIDs
        pmids = await self._esearch(query, max_results)
        
        if not pmids:
            return []
        
        # Rate limit between ESearch and EFetch
        await asyncio.sleep(self.rate_limit_delay)
        
        # Step 2: EFetch to get full metadata
        papers = await self._efetch(pmids)
        
        return papers
    
    async def _esearch(self, query: str, retmax: int) -> List[str]:
        """Execute ESearch and return list of PMIDs."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": retmax,
            "retmode": "json",
            "tool": "researchflow",
            "email": self.email,
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(ESEARCH_URL, params=params)
            response.raise_for_status()
            
        # Parse JSON response
        data = response.json()
        esearchresult = data.get("esearchresult", {})
        pmids = esearchresult.get("idlist", [])
        
        return pmids
    
    async def _efetch(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetch full metadata for given PMIDs."""
        if not pmids:
            return []
        
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "tool": "researchflow",
            "email": self.email,
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(EFETCH_URL, params=params)
            response.raise_for_status()
        
        # Parse XML and extract papers
        papers = self._parse_pubmed_xml(response.text)
        return papers
    
    def _parse_pubmed_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse PubMed XML response into normalized paper dictionaries."""
        papers = []
        
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []
        
        for article in root.findall(".//PubmedArticle"):
            paper = self._extract_paper_metadata(article)
            if paper:
                papers.append(paper)
        
        return papers
    
    def _extract_paper_metadata(self, article: ET.Element) -> Optional[Dict[str, Any]]:
        """Extract metadata from a single PubmedArticle XML element."""
        try:
            medline = article.find("MedlineCitation")
            if medline is None:
                return None
            
            pmid_elem = medline.find("PMID")
            pmid = pmid_elem.text if pmid_elem is not None else None
            
            article_elem = medline.find("Article")
            if article_elem is None:
                return None
            
            # Title - use itertext() to handle nested tags
            title = ""
            title_elem = article_elem.find("ArticleTitle")
            if title_elem is not None:
                title = ''.join(title_elem.itertext()).strip()
            
            # Abstract - handle multiple AbstractText parts and nested tags
            abstract_parts = []
            abstract_elem = article_elem.find("Abstract")
            if abstract_elem is not None:
                for abstract_text in abstract_elem.findall("AbstractText"):
                    text = ''.join(abstract_text.itertext()).strip()
                    if text:
                        # Include label if present
                        label = abstract_text.get("Label")
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
            abstract = " ".join(abstract_parts)
            
            # Authors
            authors = []
            author_list = article_elem.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last_name = author.find("LastName")
                    fore_name = author.find("ForeName")
                    if last_name is not None:
                        name = last_name.text
                        if fore_name is not None:
                            name = f"{fore_name.text} {name}"
                        authors.append(name)
            
            # Journal
            journal = ""
            journal_elem = article_elem.find("Journal/Title")
            if journal_elem is not None:
                journal = ''.join(journal_elem.itertext()).strip()
            
            # Publication date
            pub_date = article_elem.find("Journal/JournalIssue/PubDate")
            year = None
            if pub_date is not None:
                year_elem = pub_date.find("Year")
                if year_elem is not None:
                    try:
                        year = int(year_elem.text)
                    except (ValueError, TypeError):
                        pass
            
            # DOI
            doi = None
            article_id_list = article.find(".//ArticleIdList")
            if article_id_list is not None:
                for article_id in article_id_list.findall("ArticleId"):
                    if article_id.get("IdType") == "doi":
                        doi = article_id.text
                        break
            
            # MeSH terms
            mesh_terms = []
            mesh_heading_list = medline.find("MeshHeadingList")
            if mesh_heading_list is not None:
                for mesh_heading in mesh_heading_list.findall("MeshHeading"):
                    descriptor = mesh_heading.find("DescriptorName")
                    if descriptor is not None and descriptor.text:
                        mesh_terms.append(descriptor.text)
            
            # PubMed URL
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
            
            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "year": year,
                "doi": doi,
                "mesh_terms": mesh_terms,
                "url": url,
                "source": "pubmed",
            }
            
        except Exception:
            return None
