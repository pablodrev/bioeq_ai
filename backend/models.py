"""
SQLAlchemy models for the database.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, UUID, Boolean
from database import Base

class DBProject(Base):
    """Project - represents a drug investigation plan."""
    __tablename__ = "projects"
    
    project_id: str = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    inn_en: str = Column(String, nullable=False)  # Drug name in English
    inn_ru: str = Column(String, nullable=True)   # Drug name in Russian
    dosage: str = Column(String, nullable=False)
    shape: str = Column(String, nullable=True)  # Drug form/shape from search
    drug_name_t: str = Column(String, nullable=True)  # Test drug name from design
    drug_name_r: str = Column(String, nullable=True)  # Reference drug name from design
    
    status: str = Column(String, default="searching")  # searching, completed, failed
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Store aggregated results as JSON
    search_results: dict = Column(JSON, nullable=True)
    design_parameters: dict = Column(JSON, nullable=True)
    regulatory_check: dict = Column(JSON, nullable=True)


class DBDrugParameter(Base):
    """Individual drug parameter extracted from literature."""
    __tablename__ = "drug_parameters"
    
    param_id: str = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: str = Column(UUID(as_uuid=False), nullable=False)
    
    parameter: str = Column(String, nullable=False)  # CV_intra, T1/2, AUC, Cmax, etc.
    value: float = Column(String, nullable=False)
    unit: str = Column(String, nullable=True)
    
    source_pmid: str = Column(String, nullable=True)
    source_title: str = Column(String, nullable=True)
    is_reliable: bool = Column(Boolean, default=True)
    
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
