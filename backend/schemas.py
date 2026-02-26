"""
Pydantic schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchStartRequest(BaseModel):
    """Request to start drug parameter search."""
    inn_en: str = Field(..., description="Drug name in English")
    inn_ru: Optional[str] = Field(None, description="Drug name in Russian")
    dosage: str = Field(..., description="Drug dosage (e.g., '400mg')")
    form: str = Field(..., description="Drug form (e.g., 'tablets')")
    additional_substances: Optional[List[str]] = Field(
        None,
        description="Optional list of additional substances to include in search query"
    )

class ParameterSchema(BaseModel):
    """Individual drug parameter from literature."""
    parameter: str
    value: str  # Store as string to preserve precision
    unit: Optional[str] = None
    source: str
    is_reliable: bool = True

class SearchResultsResponse(BaseModel):
    """Response with search results and parameters."""
    project_id: str
    status: str
    parameters: List[ParameterSchema]
    sources_count: int
    created_at: datetime
    updated_at: datetime
    
class DesignParametersSchema(BaseModel):
    """Study design parameters for bioequivalence."""
    sample_size: int
    design_type: str  # "2x2 crossover", "parallel", etc.
    cv_intra: float
    power: float
    alpha: float

class SearchStartResponse(BaseModel):
    """Response to search start request."""
    project_id: str
    status: str
    message: str

class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    details: Optional[str] = None

class PDFUploadResponse(BaseModel):
    """Response to PDF upload request."""
    project_id: str
    status: str
    message: str
    parameters_found: int


class DrugParameterInput(BaseModel):
    """Input for drug parameter in design calculation."""
    parameter: str
    value: float
    unit: Optional[str] = None


class DesignCalculateRequest(BaseModel):
    """Request to calculate study design parameters."""
    cv_intra: float = Field(..., description="Intra-individual coefficient of variation (%)")
    tmax: Optional[float] = Field(None, description="Time to maximum concentration (hours)")
    t_half: Optional[float] = Field(None, description="Terminal half-life (hours)")
    power: float = Field(0.80, description="Statistical power (0.0-1.0)")
    alpha: float = Field(0.05, description="Significance level (0.0-1.0)")
    dropout_rate: float = Field(0.0, description="Expected dropout rate (%)")
    screen_fail_rate: float = Field(0.0, description="Expected screen failure rate (%)")
    project_id: Optional[str] = Field(None, description="Optional project ID to store results")
    desired_design: Optional[str] = Field(
        None,
        description="Optional desired study design: '2x2 crossover', '3-way replicate', '4-way replicate', or 'Параллельный'"
    )
    drug_name_t: Optional[str] = Field(None, description="Test drug name for report")
    drug_name_r: Optional[str] = Field(None, description="Reference drug name for report")


class CriticalParametersResponse(BaseModel):
    """Critical parameters used for design calculation."""
    cv_intra: float  # Intra-individual coefficient of variation (%), reflects variability within subjects
    tmax: Optional[float] = None  # Time to maximum plasma concentration (hours), indicates absorption rate
    t_half: Optional[float] = None  # Terminal elimination half-life (hours), describes drug clearance


class DesignResultResponse(BaseModel):
    """Response with calculated study design parameters."""
    sample_size: int  # Number of subjects required for statistical power
    recruitment_size: int  # Total subjects to recruit (accounts for dropout and screen failure)
    design_type: str  # Study design (e.g., '2x2 crossover', 'parallel')
    cv_intra: float  # Intra-individual coefficient of variation (%)
    power: float  # Desired statistical power (probability of detecting true effect)
    alpha: float  # Significance level (probability of Type I error)
    dropout_rate: float  # Expected dropout rate (%) during study
    screen_fail_rate: float  # Expected screen failure rate (%) at screening
    randomization_scheme: Optional[str] = None  # Description of subject randomization (e.g., block, stratified)
    washout_days: Optional[float] = None  # Washout period between study periods (days)
    critical_parameters: CriticalParametersResponse  # Key pharmacokinetic parameters used in design
    design_explanation: Optional[str] = None  # Textual explanation of design choices and calculations
