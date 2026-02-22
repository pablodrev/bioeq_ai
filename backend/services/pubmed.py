"""
PubMed API client for searching and extracting abstracts.
"""
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PubMedClient:
    """Client for searching PubMed and fetching abstracts."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    EMAIL = "pharma.mvp@gmail.com"  # Required by NCBI
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)
    
    def search(
        self,
        inn: str,
        max_results: int = 5,
        sort: str = "relevance"
    ) -> List[str]:
        """
        Search PubMed for articles about drug pharmacokinetics.
        Returns list of PMIDs (PubMed IDs).
        """
        # Build search query
        query = f"{inn} AND (pharmacokinetics OR bioequivalence OR bioavailability) AND healthy"
        
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": sort,
            "email": self.EMAIL,
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = self.client.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])
            
            logger.info(f"PubMed search for '{inn}': found {len(pmids)} articles")
            return pmids
        
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return []
    
    def fetch_abstracts(self, pmids: List[str]) -> List[Dict[str, str]]:
        """
        Fetch full abstracts for given PMIDs.
        Returns list of dicts with 'pmid', 'title', 'abstract'.
        """
        if not pmids:
            return []
        
        # EFetch API: request XML and parse it
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "retmax": len(pmids),
            "email": self.EMAIL,
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = self.client.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
            response.raise_for_status()
            
            text = response.text
            if not text:
                logger.error("Empty response from PubMed efetch")
                return []

            try:
                root = ET.fromstring(text)
            except ET.ParseError as pe:
                logger.error(f"Failed parsing PubMed XML: {pe}")
                return []

            results: List[Dict[str, str]] = []
            # Iterate over PubmedArticle elements
            for article in root.findall('.//PubmedArticle'):
                pmid = article.findtext('.//MedlineCitation/PMID') or ""
                title = article.findtext('.//Article/ArticleTitle') or ""

                # Collect abstract text parts
                abstract_parts: List[str] = []
                for at in article.findall('.//Article/Abstract/AbstractText'):
                    # AbstractText may contain nested text or attribution
                    part_text = ''.join(at.itertext()).strip()
                    if part_text:
                        abstract_parts.append(part_text)

                abstract = " ".join(abstract_parts)

                results.append({
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                })

            logger.info(f"Fetched {len(results)} abstracts")
            return results
        
        except Exception as e:
            logger.error(f"PubMed fetch error: {e}")
            return []
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
