"""
Data parsing and collection module.
Orchestrates PubMed search, LLM extraction, and result aggregation.
"""
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Set
from sqlalchemy.orm import Session
from services.pubmed import PubMedClient
from services.llm_client import YandexGPTClient
from services.pdf_utils import PDFProcessor
from models import DBProject, DBDrugParameter
from datetime import datetime

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

CV_FOCUS_TERMS = [
    "intra-subject variability",
    "within-subject variability",
    "intrasubject CV",
    "within-subject CV",
    "coefficient of variation",
    "bioequivalence crossover",
]

PARAM_NAME_ALIASES = {
    "cmax": "Cmax",
    "auc": "AUC",
    "tmax": "Tmax",
    "t1/2": "T1/2",
    "t1_2": "T1/2",
    "half_life": "T1/2",
    "half-life": "T1/2",
    "cv_intra": "CV_intra",
    "cvintra": "CV_intra",
    "intra_subject_cv": "CV_intra",
    "intrasubject_cv": "CV_intra",
    "within_subject_cv": "CV_intra",
    "withinsubject_cv": "CV_intra",
}

class ParsingModule:
    """Orchestrates drug parameter data collection."""
    
    def __init__(self, db: Session):
        self.db = db
        self.pubmed = PubMedClient()
        self.llm = YandexGPTClient()

    @staticmethod
    def _canonicalize_param_name(raw_name: str) -> str:
        key = (raw_name or "").strip()
        if not key:
            return key
        normalized = key.lower().replace(" ", "_")
        return PARAM_NAME_ALIASES.get(normalized, key)

    @staticmethod
    def _is_valid_extracted_param(param_data: Dict[str, Any]) -> bool:
        if param_data is None or not isinstance(param_data, dict):
            return False
        if not param_data.get("found"):
            return False
        value = param_data.get("value")
        try:
            float(value)
        except (TypeError, ValueError):
            return False
        return True

    @staticmethod
    def _merge_aggregated(
        target: Dict[str, List[Dict[str, Any]]],
        source: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        for param_name, values in source.items():
            target.setdefault(param_name, []).extend(values)

    @staticmethod
    def _cv_signal_score(title: str, abstract: str) -> int:
        text = f"{title or ''} {abstract or ''}".lower()
        score = 0
        if "bioequivalence" in text:
            score += 2
        if "crossover" in text or "cross-over" in text:
            score += 2
        if "healthy volunteer" in text or "healthy subjects" in text:
            score += 1
        for marker in ("intra-subject", "within-subject", "intrasubject", "withinsubject"):
            if marker in text:
                score += 3
        if "coefficient of variation" in text:
            score += 2
        if "variability" in text and "inter-individual" not in text:
            score += 1
        return score

    def _extract_params_from_article(
        self,
        article: Dict[str, str],
        inn: str,
        target_only_cv: bool = False
    ) -> Dict[str, List[Dict[str, Any]]]:
        extractor = self.llm.extract_cv_intra if target_only_cv else self.llm.extract_parameters
        params = extractor(article.get("abstract", ""), inn)
        aggregated: Dict[str, List[Dict[str, Any]]] = {}

        for raw_name, param_data in params.items():
            canonical_name = self._canonicalize_param_name(raw_name)
            if target_only_cv and canonical_name != "CV_intra":
                continue
            if not self._is_valid_extracted_param(param_data):
                continue

            aggregated.setdefault(canonical_name, []).append({
                "value": param_data.get("value"),
                "unit": param_data.get("unit"),
                "pmid": article.get("pmid"),
                "title": article.get("title"),
            })
        return aggregated

    def _extract_missing_cv_intra(
        self,
        inn: str,
        substances: List[str],
        max_articles: int,
        already_seen_pmids: Set[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Targeted second pass for CV_intra using focus terms and CV-oriented extraction.
        """
        pmids = self.pubmed.search(
            substances,
            max_results=max(max_articles, 15),
            sort="relevance",
            focus_terms=CV_FOCUS_TERMS,
        )
        new_pmids = [pmid for pmid in pmids if pmid and pmid not in already_seen_pmids]
        if not new_pmids:
            return {}

        articles = self.pubmed.fetch_abstracts(new_pmids)
        if not articles:
            return {}

        scored = sorted(
            articles,
            key=lambda a: self._cv_signal_score(a.get("title", ""), a.get("abstract", "")),
            reverse=True,
        )

        aggregated: Dict[str, List[Dict[str, Any]]] = {}
        for article in scored[:10]:
            already_seen_pmids.add(article.get("pmid", ""))
            extracted = self._extract_params_from_article(article, inn, target_only_cv=True)
            self._merge_aggregated(aggregated, extracted)
        return aggregated
    
    def search_and_extract(
        self,
        project_id: str,
        inn: str,
        max_articles: int = 5,
        additional_substances: List[str] = None
    ) -> Dict[str, Any]:
        """
        Full workflow: search PubMed -> extract params via LLM -> save to DB.
        
        Args:
            project_id: Project UUID
            inn: Drug name in English
            max_articles: Max articles to process
            additional_substances: Optional list of additional substances to include in search
        
        Returns:
            Dict with aggregated results
        """
        
        try:
            # Step 1: Search PubMed
            logger.info(f"[{project_id}] Searching PubMed for '{inn}'...")
            substances = [inn]
            if additional_substances:
                substances.extend(additional_substances)
                logger.info(f"[{project_id}] Including additional substances: {additional_substances}")
            pmids = self.pubmed.search(substances, max_results=max_articles)
            
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
            aggregated_params: Dict[str, List[Dict[str, Any]]] = {}
            processed_pmids: Set[str] = set()
            
            for article in articles:
                pmid = article["pmid"]
                processed_pmids.add(pmid)
                
                logger.info(f"[{project_id}] Extracting from PMID {pmid}...")

                extracted = self._extract_params_from_article(article, inn, target_only_cv=False)
                self._merge_aggregated(aggregated_params, extracted)

            # Step 3b: targeted enrichment for missing critical parameter CV_intra
            if "CV_intra" not in aggregated_params:
                logger.info(f"[{project_id}] CV_intra missing after first pass. Running targeted CV_intra retrieval...")
                cv_only = self._extract_missing_cv_intra(
                    inn=inn,
                    substances=substances,
                    max_articles=max_articles,
                    already_seen_pmids=processed_pmids,
                )
                self._merge_aggregated(aggregated_params, cv_only)
            
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
                    "articles_processed": len(processed_pmids),
                    "parameters_found": {
                        k: len(v) for k, v in aggregated_params.items()
                    },
                    "critical_coverage": {
                        "CV_intra": len(aggregated_params.get("CV_intra", [])) > 0
                    },
                    "missing_critical": [
                        name for name in ["CV_intra"]
                        if len(aggregated_params.get(name, [])) == 0
                    ],
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
    
    def extract_from_pdf(
        self,
        project_id: str,
        pdf_path: str,
        inn: str
    ) -> Dict[str, Any]:
        """
        Extract parameters from a PDF file.
        
        Args:
            project_id: Project UUID
            pdf_path: Path to the PDF file
            inn: Drug name
        
        Returns:
            Dict with extraction results
        """
        try:
            # Step 1: Extract text from PDF
            logger.info(f"[{project_id}] Extracting text from PDF...")
            processor = PDFProcessor()
            pdf_text = processor.extract_text(pdf_path)
            
            if not pdf_text:
                logger.warning(f"[{project_id}] No text extracted from PDF")
                return {"error": "Failed to extract text from PDF", "parameters": []}
            
            # Step 2: Extract parameters via LLM
            logger.info(f"[{project_id}] Extracting parameters from PDF text...")
            params = self.llm.extract_parameters(pdf_text, inn)
            
            if not params:
                logger.warning(f"[{project_id}] LLM returned no parameters")
                return {"error": "No parameters extracted", "parameters": []}
            
            # Step 3: Save to database
            logger.info(f"[{project_id}] Saving parameters to DB...")
            aggregated_params = {}
            
            for param_name, param_data in params.items():
                if param_data is None or not param_data.get("found"):
                    continue
                
                if param_name not in aggregated_params:
                    aggregated_params[param_name] = []
                
                aggregated_params[param_name].append({
                    "value": param_data.get("value"),
                    "unit": param_data.get("unit"),
                    "pmid": None,
                    "title": "Uploaded PDF"
                })
            
            for param_name, values in aggregated_params.items():
                for value_entry in values:
                    db_param = DBDrugParameter(
                        project_id=project_id,
                        parameter=param_name,
                        value=str(value_entry["value"]),
                        unit=value_entry.get("unit"),
                        source_pmid=None,  # PDF upload doesn't have PMID
                        source_title="Uploaded PDF",
                        is_reliable=True
                    )
                    self.db.add(db_param)
            
            self.db.commit()
            
            # Step 4: Update project status
            project = self.db.query(DBProject).filter(
                DBProject.project_id == project_id
            ).first()
            
            if project:
                project.status = "pdf_processed"
                project.search_results = {
                    "source": "PDF file",
                    "parameters_found": {
                        k: len(v) for k, v in aggregated_params.items()
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.db.commit()
            
            logger.info(f"[{project_id}] PDF extraction completed successfully")
            
            # Return formatted results
            parameters = []
            for param_name, values in aggregated_params.items():
                for value_entry in values:
                    parameters.append({
                        "parameter": param_name,
                        "value": str(value_entry["value"]),
                        "unit": value_entry.get("unit"),
                        "source": "Uploaded PDF",
                        "is_reliable": True
                    })
            
            return {
                "parameters": parameters,
                "parameters_count": len(parameters),
                "error": None
            }
        
        except Exception as e:
            logger.error(f"[{project_id}] Error in extract_from_pdf: {e}", exc_info=True)
            return {"error": str(e), "parameters": []}
    
    def close(self):
        """Cleanup resources."""
        self.pubmed.close()
        self.llm.close()
