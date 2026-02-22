"""
Data parsing and collection module.
Orchestrates PubMed search, LLM extraction, and result aggregation.
"""
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from services.pubmed import PubMedClient
from services.llm_client import YandexGPTClient
from models import DBProject, DBDrugParameter
from datetime import datetime

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ParsingModule:
    """Orchestrates drug parameter data collection."""
    
    def __init__(self, db: Session):
        self.db = db
        self.pubmed = PubMedClient()
        self.llm = YandexGPTClient()
    
    def search_and_extract(
        self,
        project_id: str,
        inn: str,
        max_articles: int = 5
    ) -> Dict[str, Any]:
        """
        Full workflow: search PubMed -> extract params via LLM -> save to DB.
        
        Args:
            project_id: Project UUID
            inn: Drug name in English
            max_articles: Max articles to process
        
        Returns:
            Dict with aggregated results
        """
        
        try:
            # Step 1: Search PubMed
            logger.info(f"[{project_id}] Searching PubMed for '{inn}'...")
            pmids = self.pubmed.search(inn, max_results=max_articles)
            
            if not pmids:
                logger.warning(f"[{project_id}] No articles found for '{inn}'")
                return {"error": "No articles found", "parameters": []}
            
            # Step 2: Fetch abstracts
            logger.info(f"[{project_id}] Fetching {len(pmids)} abstracts...")
            articles = self.pubmed.fetch_abstracts(pmids)
            
            if not articles:
                logger.warning(f"[{project_id}] Failed to fetch abstracts")
                return {"error": "Failed to fetch abstracts", "parameters": []}
            
            # Step 3: Extract parameters via LLM
            aggregated_params = {}
            
            for article in articles:
                pmid = article["pmid"]
                title = article["title"]
                abstract = article["abstract"]
                
                logger.info(f"[{project_id}] Extracting from PMID {pmid}...")
                
                # Call LLM
                params = self.llm.extract_parameters(abstract, inn)
                
                # Process extracted parameters
                for param_name, param_data in params.items():
                    if param_data is None or not param_data.get("found"):
                        continue
                    
                    if param_name not in aggregated_params:
                        aggregated_params[param_name] = []
                    
                    aggregated_params[param_name].append({
                        "value": param_data.get("value"),
                        "unit": param_data.get("unit"),
                        "pmid": pmid,
                        "title": title
                    })
            
            # Step 4: Save to database
            logger.info(f"[{project_id}] Saving {len(aggregated_params)} parameter types to DB...")
            
            for param_name, values in aggregated_params.items():
                for value_entry in values:
                    db_param = DBDrugParameter(
                        project_id=project_id,
                        parameter=param_name,
                        value=str(value_entry["value"]),
                        unit=value_entry.get("unit"),
                        source_pmid=value_entry.get("pmid"),
                        source_title=value_entry.get("title"),
                        is_reliable=True
                    )
                    self.db.add(db_param)
            
            self.db.commit()
            
            # Step 5: Update project status
            project = self.db.query(DBProject).filter(
                DBProject.project_id == project_id
            ).first()
            
            if project:
                project.status = "searching_completed"
                project.search_results = {
                    "articles_processed": len(articles),
                    "parameters_found": {
                        k: len(v) for k, v in aggregated_params.items()
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.db.commit()
            
            logger.info(f"[{project_id}] Extraction completed successfully")
            return self._format_results(aggregated_params, articles)
        
        except Exception as e:
            logger.error(f"[{project_id}] Error in search_and_extract: {e}", exc_info=True)
            return {"error": str(e), "parameters": []}
    
    def _format_results(
        self,
        aggregated_params: Dict[str, List[Dict[str, Any]]],
        articles: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Format aggregated results for API response."""
        
        parameters = []
        
        for param_name, values in aggregated_params.items():
            for value_entry in values:
                parameters.append({
                    "parameter": param_name,
                    "value": str(value_entry["value"]),
                    "unit": value_entry.get("unit"),
                    "source": f"PubMed ID: {value_entry.get('pmid')}",
                    "is_reliable": True
                })
        
        return {
            "parameters": parameters,
            "articles_processed": len(articles),
            "error": None
        }
    
    def close(self):
        """Cleanup resources."""
        self.pubmed.close()
        self.llm.close()
