"""
PubMed API client for searching and extracting abstracts.
"""
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)

class PubMedClient:
    """Client for searching PubMed and fetching abstracts."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    EMAIL = "pharma.mvp@gmail.com"  # Required by NCBI
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)
    
    def search(
        self,
        substances,
        max_results: int = 5,
        sort: str = "relevance",
        focus_terms: Optional[List[str]] = None
    ) -> List[str]:
        """
        Search PubMed for articles about drug pharmacokinetics.
        Can accept either a single substance string or list of substances.
        First substance is treated as mandatory (main INN).
        Additional substances are optional filters.
        Returns list of PMIDs (PubMed IDs).
        """
        # Normalize input to list
        if isinstance(substances, str):
            substances = [substances]
        
        # Build search query with main substance mandatory and additional substances optional
        if len(substances) == 1:
            # Basic search: just main substance
            main_substance = substances[0]
            query = f'"{main_substance}" AND (pharmacokinetics OR bioequivalence OR bioavailability) AND healthy'
        else:
            # Advanced search: main substance mandatory, additional substances optional
            main_substance = substances[0]
            additional = substances[1:]
            additional_query = " OR ".join(additional)
            query = f'"{main_substance}" AND ({additional_query}) AND (pharmacokinetics OR bioequivalence OR bioavailability) AND healthy'

        if focus_terms:
            normalized_focus = [term.strip() for term in focus_terms if term and term.strip()]
            if normalized_focus:
                focus_query = " OR ".join(f'"{term}"' for term in normalized_focus)
                query = f"{query} AND ({focus_query})"
        
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
        
        # Retry logic for transient failures
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.get(f"{self.BASE_URL}/esearch.fcgi", params=params)
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                pmids = data.get("esearchresult", {}).get("idlist", [])
                
                logger.info(f"PubMed search for '{main_substance}': found {len(pmids)} articles")
                return pmids
            
            except (httpx.ConnectError, httpx.TimeoutException, OSError) as e:
                logger.warning(f"PubMed search attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)  # exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"PubMed search error after {self.MAX_RETRIES} attempts: {e}")
                    return []
            
            except Exception as e:
                logger.error(f"PubMed search error: {e}")
                return []
        
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
        
        # Retry logic for transient failures
        for attempt in range(self.MAX_RETRIES):
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
            
            except (httpx.ConnectError, httpx.TimeoutException, OSError) as e:
                logger.warning(f"PubMed fetch attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)  # exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"PubMed fetch error after {self.MAX_RETRIES} attempts: {e}")
                    return []
            
            except Exception as e:
                logger.error(f"PubMed fetch error: {e}")
                return []
        
        return []

    def map_pmids_to_pmcids(self, pmids: List[str]) -> Dict[str, str]:
        """
        Map PubMed IDs to PMCID values using elink.
        Returns dict: {pmid: pmcid}
        """
        if not pmids:
            return {}

        mapping: Dict[str, str] = {}
        for pmid in pmids:
            params = {
                "dbfrom": "pubmed",
                "db": "pmc",
                "id": pmid,
                "retmode": "xml",
                "email": self.EMAIL,
            }
            if self.api_key:
                params["api_key"] = self.api_key

            for attempt in range(self.MAX_RETRIES):
                try:
                    response = self.client.get(f"{self.BASE_URL}/elink.fcgi", params=params)
                    response.raise_for_status()
                    root = ET.fromstring(response.text)
                    pmcid = root.findtext(".//LinkSetDb/Link/Id") or ""
                    if pmcid:
                        mapping[pmid] = pmcid
                    break
                except (httpx.ConnectError, httpx.TimeoutException, OSError) as e:
                    logger.warning(
                        f"PMID->PMCID mapping for {pmid} attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}"
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = self.RETRY_DELAY * (2 ** attempt)
                        time.sleep(wait_time)
                    else:
                        logger.error(f"PMID->PMCID mapping failed for {pmid} after retries: {e}")
                except Exception as e:
                    logger.error(f"PMID->PMCID mapping error for {pmid}: {e}")
                    break

        logger.info(f"Mapped {len(mapping)}/{len(pmids)} PMIDs to PMCIDs")
        return mapping

    def fetch_pmc_fulltexts(self, pmid_to_pmcid: Dict[str, str]) -> Dict[str, str]:
        """
        Fetch full text for PMCID records (when available).
        Returns dict: {pmid: full_text}
        """
        if not pmid_to_pmcid:
            return {}

        # Reverse map for quick PMCID -> PMID lookup
        pmcid_to_pmid = {pmcid: pmid for pmid, pmcid in pmid_to_pmcid.items() if pmcid}
        pmcids = list(pmcid_to_pmid.keys())

        params = {
            "db": "pmc",
            "id": ",".join(pmcids),
            "retmode": "xml",
            "email": self.EMAIL,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.get(f"{self.BASE_URL}/efetch.fcgi", params=params)
                response.raise_for_status()
                root = ET.fromstring(response.text)

                results: Dict[str, str] = {}
                for article in root.findall(".//article"):
                    article_id_nodes = article.findall(".//article-id")
                    pmcid = ""
                    for node in article_id_nodes:
                        pub_id_type = (node.attrib.get("pub-id-type") or "").lower()
                        if pub_id_type in {"pmc", "pmcid"}:
                            pmcid = (node.text or "").strip()
                            break
                    if not pmcid:
                        continue

                    # NCBI efetch usually gives PMCID digits only, normalize possible "PMC" prefix
                    normalized = pmcid[3:] if pmcid.upper().startswith("PMC") else pmcid
                    pmid = pmcid_to_pmid.get(normalized) or pmcid_to_pmid.get(pmcid)
                    if not pmid:
                        continue

                    body_node = article.find(".//body")
                    if body_node is None:
                        continue

                    full_text = " ".join(
                        segment.strip()
                        for segment in body_node.itertext()
                        if segment and segment.strip()
                    )
                    if full_text:
                        results[pmid] = full_text

                logger.info(f"Fetched PMC full texts for {len(results)} articles")
                return results

            except (httpx.ConnectError, httpx.TimeoutException, OSError) as e:
                logger.warning(f"PMC full-text fetch attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    logger.error(f"PMC full-text fetch failed after retries: {e}")
                    return {}
            except Exception as e:
                logger.error(f"PMC full-text fetch error: {e}")
                return {}

        return {}
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
