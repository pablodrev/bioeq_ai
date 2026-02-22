"""
Regulatory module.
Quick regulatory compliance check based on study parameters.
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models import DBProject

logger = logging.getLogger(__name__)

class RegulatoryModule:
    """Checks regulatory compliance for proposed study design."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_compliance(self, project_id: str) -> Dict[str, Any]:
        """
        Quick regulatory compliance check.
        Based on Russian Decision #85 and EMA guidelines.
        
        Args:
            project_id: Project UUID
        
        Returns:
            Dict with compliance status and issues
        """
        
        try:
            # Fetch project with design parameters
            project = self.db.query(DBProject).filter(
                DBProject.project_id == project_id
            ).first()
            
            if not project:
                return {"error": "Project not found"}
            
            if not project.design_parameters:
                return {"error": "Design parameters not generated yet"}
            
            design = project.design_parameters
            issues = []
            warnings = []
            
            # Check 1: Minimum sample size
            min_n = 12  # Russian guideline minimum
            if design.get("sample_size", 0) < min_n:
                issues.append(
                    f"Sample size ({design['sample_size']}) is below minimum of {min_n}"
                )
            
            # Check 2: CV_intra reasonable range
            cv = design.get("critical_parameters", {}).get("CV_intra")
            if cv:
                if cv > 50:
                    warnings.append(
                        f"High intra-individual variability ({cv}%). "
                        f"Consider replicate design for more accurate BE assessment."
                    )
                if cv < 5:
                    warnings.append(
                        f"Very low variability ({cv}%). Verify data source."
                    )
            
            # Check 3: Design type appropriateness
            design_type = design.get("design_type")
            if cv and cv > 30 and design_type == "2x2 crossover":
                warnings.append(
                    "High variability with 2x2 crossover. "
                    "Consider 2x2x4 or parallel design."
                )
            
            # Check 4: Washout period
            washout = design.get("washout_days")
            if washout:
                if washout > 90:
                    warnings.append(
                        f"Very long washout period ({washout} days). "
                        f"Ensure practical feasibility and volunteer retention."
                    )
            
            # Regulatory status
            is_compliant = len(issues) == 0
            
            result = {
                "is_compliant": is_compliant,
                "status": "APPROVED" if is_compliant else "REJECTED WITH ISSUES",
                "critical_issues": issues,
                "warnings": warnings,
                "design_summary": {
                    "sample_size": design.get("sample_size"),
                    "design_type": design.get("design_type"),
                    "cv_intra": cv,
                    "washout_days": washout,
                }
            }
            
            logger.info(f"Regulatory check for {project_id}: {result['status']}")
            return result
        
        except Exception as e:
            logger.error(f"Error in check_compliance: {e}", exc_info=True)
            return {"error": str(e)}
