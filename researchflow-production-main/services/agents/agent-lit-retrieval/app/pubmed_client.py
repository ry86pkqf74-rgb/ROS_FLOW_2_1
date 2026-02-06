"""
Pure NCBI Entrez client for PubMed searches.
No BaseAgent dependencies - uses httpx directly.
"""
import os
import asyncio
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class PubMedClient:
    """Minimal PubMed client using NCBI EUtils API."""

    def __init__(self) -> None:
        self.api_key = os.getenv("NCBI_API_KEY")
        self.email = os.getenv("NCBI_EMAIL", "researchflow@example.com")
        self.rate_limit_delay = 0.1 if self.api_key else 0.34

    async def search_pubmed(
        self,
        query: str,
        max_results: int = 25,
    ) -> List[Dict[str, Any]]:
        """Search PubMed and return paper metadata."""
        pmids = await self._esearch(query, max_results)
        if not pmids:
            return []
        await asyncio.sleep(self.rate_limit_delay)
        return await self._efetch(pmids)

    async def _esearch(self, query: str, retmax: int) -> List[str]:
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
        data = response.json()
        esearchresult = data.get("esearchresult", {})
        return esearchresult.get("idlist", [])

    async def _efetch(self, pmids: List[str]) -> List[Dict[str, Any]]:
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
        return self._parse_pubmed_xml(response.text)

    def _parse_pubmed_xml(self, xml_text: str) -> List[Dict[str, Any]]:
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
        try:
            medline = article.find("MedlineCitation")
            if medline is None:
                return None
            pmid_elem = medline.find("PMID")
            pmid = pmid_elem.text if pmid_elem is not None else None
            article_elem = medline.find("Article")
            if article_elem is None:
                return None
            title = ""
            title_elem = article_elem.find("ArticleTitle")
            if title_elem is not None:
                title = "".join(title_elem.itertext()).strip()
            abstract_parts = []
            abstract_elem = article_elem.find("Abstract")
            if abstract_elem is not None:
                for abstract_text in abstract_elem.findall("AbstractText"):
                    text = "".join(abstract_text.itertext()).strip()
                    if text:
                        label = abstract_text.get("Label")
                        abstract_parts.append(f"{label}: {text}" if label else text)
            abstract = " ".join(abstract_parts)
            authors = []
            author_list = article_elem.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last_name = author.find("LastName")
                    fore_name = author.find("ForeName")
                    if last_name is not None:
                        name = last_name.text or ""
                        if fore_name is not None and fore_name.text:
                            name = f"{fore_name.text} {name}"
                        authors.append(name)
            journal = ""
            journal_elem = article_elem.find("Journal/Title")
            if journal_elem is not None:
                journal = "".join(journal_elem.itertext()).strip()
            year = None
            pub_date = article_elem.find("Journal/JournalIssue/PubDate")
            if pub_date is not None:
                year_elem = pub_date.find("Year")
                if year_elem is not None:
                    try:
                        year = int(year_elem.text)
                    except (ValueError, TypeError):
                        pass
            doi = None
            article_id_list = article.find(".//ArticleIdList")
            if article_id_list is not None:
                for aid in article_id_list.findall("ArticleId"):
                    if aid.get("IdType") == "doi":
                        doi = aid.text
                        break
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "journal": journal,
                "year": year,
                "doi": doi,
                "url": url,
                "source": "pubmed",
            }
        except Exception:
            return None
