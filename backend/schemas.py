"""
Pydantic schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SearchStartRequest(BaseModel):
    """Request to start drug parameter search."""
    inn_en: str = Field(..., description="Drug name in English")
    inn_ru: Optional[str] = Field(None, description="Drug name in Russian")
    dosage: str = Field(..., description="Drug dosage (e.g., '400mg')")
    form: str = Field(..., description="Drug form (e.g., 'tablets')")

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
