"""
Study design module.
Calculates bioequivalence design parameters based on extracted drug data.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from services.calculator import BioeEquivalenceCalculator
from models import DBProject, DBDrugParameter

logger = logging.getLogger(__name__)

class DesignModule:
    """Generates study design based on drug parameters."""
    
    def __init__(self, db: Session):
        self.db = db
        self.calc = BioeEquivalenceCalculator()
    
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
            
            # Calculate sample size
            sample_size, design_type = self.calc.calculate_sample_size(
                cv_intra=cv_intra,
                power=0.80,
                alpha=0.05
            )
            
            # Calculate other design parameters
            washout_days = None
            if t_half:
                washout_days = self.calc.estimate_washout_period(t_half)
            
            sampling_plan = None
            if tmax and t_half:
                sampling_plan = self.calc.estimate_blood_sampling(tmax, t_half)
            
            design_params = {
                "sample_size": sample_size,
                "design_type": design_type,
                "cv_intra": cv_intra,
                "power": 0.80,
                "alpha": 0.05,
                "washout_days": washout_days,
                "critical_parameters": {
                    "CV_intra": cv_intra,
                    "Tmax": tmax,
                    "T1/2": t_half,
                },
                "sampling_plan": sampling_plan
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
            if p.parameter == param_name and p.is_reliable
        ]
        
        if not values:
            return None
        
        if param_name == "CV_intra":
            # Worst case: highest variability
            return max(values)
        else:
            # For Tmax, T1/2, etc.: use maximum (conservative)
            return max(values)
