"""
Study design module.
Calculates bioequivalence design parameters based on extracted drug data.
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from services.calculator import BioeEquivalenceCalculator
from models import DBProject, DBDrugParameter

logger = logging.getLogger(__name__)

PARAM_NAME_ALIASES = {
    "cv_intra": "CV_intra",
    "cvintra": "CV_intra",
    "intra_subject_cv": "CV_intra",
    "intrasubject_cv": "CV_intra",
    "within_subject_cv": "CV_intra",
    "withinsubject_cv": "CV_intra",
    "t1_2": "T1/2",
    "half_life": "T1/2",
    "half-life": "T1/2",
}

class DesignModule:
    """Generates study design based on drug parameters."""
    
    def __init__(self, db: Session):
        self.db = db
        self.calc = BioeEquivalenceCalculator()

    @staticmethod
    def _canonicalize_param_name(raw_name: str) -> str:
        key = (raw_name or "").strip()
        if not key:
            return key
        normalized = key.lower().replace(" ", "_")
        return PARAM_NAME_ALIASES.get(normalized, key)
    
    def generate_design(self, project_id: str) -> Dict[str, Any]:
        """
        Generate study design for bioequivalence testing.
        
        Args:
            project_id: Project UUID
        
        Returns:
            Dict with design parameters
        """
        
        try:
            # Fetch project
            project = self.db.query(DBProject).filter(
                DBProject.project_id == project_id
            ).first()
            
            if not project:
                logger.error(f"Project {project_id} not found")
                return {"error": "Project not found"}
            
            # Fetch drug parameters
            params = self.db.query(DBDrugParameter).filter(
                DBDrugParameter.project_id == project_id
            ).all()
            
            if not params:
                logger.error(f"No parameters found for project {project_id}")
                return {"error": "No parameters found"}
            
            # Extract critical values
            cv_intra = self._get_most_conservative_value(params, "CV_intra")
            tmax = self._get_most_conservative_value(params, "Tmax")
            t_half = self._get_most_conservative_value(params, "T1/2")
            
            if cv_intra is None:
                logger.error(f"CV_intra not found for project {project_id}")
                return {"error": "CV_intra not found - cannot calculate sample size"}
            
            # Decide design type using the same rules as the API
            design_type = self.calc.choose_design_type(cv_intra, t_half)

            # Calculate sample size for the chosen design
            sample_size, design_type = self.calc.calculate_sample_size_for_design(
                cv_intra=cv_intra,
                design_type=design_type,
                power=0.80,
                alpha=0.05
            )
            
            # Calculate other design parameters
            washout_days = None
            if t_half:
                washout_days = self.calc.estimate_washout_period(t_half)
            
            # sampling_plan removed: no longer estimating blood sampling schedule here
            
            design_params = {
                "sample_size": sample_size,
                "recruitment_size": sample_size,
                "design_type": design_type,
                "cv_intra": cv_intra,
                "power": 0.80,
                "alpha": 0.05,
                "dropout_rate": 0.0,
                "screen_fail_rate": 0.0,
                    "washout_days": washout_days,
                    "design_explanation": self.calc.design_explanation(cv_intra, t_half, design_type),
                    "randomization_scheme": self.calc.randomization_scheme(design_type),
                "critical_parameters": {
                    "CV_intra": cv_intra,
                    "Tmax": tmax,
                    "T1/2": t_half,
                },
                # sampling_plan removed
            }
            
            # Save to DB
            project.design_parameters = design_params
            self.db.commit()
            
            logger.info(f"Generated design for {project_id}: N={sample_size}, CV={cv_intra}%")
            return design_params
        
        except Exception as e:
            logger.error(f"Error in generate_design: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _get_most_conservative_value(
        self,
        params: List[DBDrugParameter],
        param_name: str
    ) -> Optional[float]:
        """
        Get most conservative value for a parameter.
        - For CV_intra: highest value (worst case)
        - For others: use mean or median
        """
        
        values = [
            float(p.value) for p in params 
            if self._canonicalize_param_name(p.parameter) == param_name and p.is_reliable
        ]
        
        if not values:
            return None
        
        if param_name == "CV_intra":
            # Worst case: highest variability
            return max(values)
        else:
            # For Tmax, T1/2, etc.: use maximum (conservative)
            return max(values)
