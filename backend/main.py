"""
FastAPI application for pharmaceutical study design automation.
Main entry point with all API endpoints.
"""
import logging
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime

from database import SessionLocal, init_db, get_db
from schemas import (
    SearchStartRequest, SearchStartResponse, SearchResultsResponse,
    ParameterSchema
)
from models import DBProject, DBDrugParameter
from core.parsing_module import ParsingModule
from core.design_module import DesignModule
from core.regulatory_module import RegulatoryModule
from core.report_module import ReportModule

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create reports directory
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: Initialize database.
    Shutdown: Cleanup.
    """
    logger.info("Starting up: Initializing database...")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="MedDesign MVP",
    description="AI-powered pharmaceutical study design automation",
    version="0.1.0",
    lifespan=lifespan
)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post(
    "/api/v1/search/start",
    response_model=SearchStartResponse,
    tags=["Search"]
)
async def start_search(
    request: SearchStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start drug parameter search (async background task).
    
    Returns project_id immediately (202 Accepted pattern).
    """
    try:
        # Create project
        project_id = str(uuid.uuid4())
        project = DBProject(
            project_id=project_id,
            inn_en=request.inn_en,
            inn_ru=request.inn_ru,
            dosage=request.dosage,
            form=request.form,
            status="searching"
        )
        db.add(project)
        db.commit()
        
        logger.info(f"Created project {project_id} for {request.inn_en}")
        
        # Schedule background tasks
        background_tasks.add_task(
            _run_full_pipeline,
            project_id=project_id,
            inn=request.inn_en
        )
        
        return SearchStartResponse(
            project_id=project_id,
            status="searching",
            message="Search started. Please poll /api/v1/search/results/{project_id} for updates"
        )
    
    except Exception as e:
        logger.error(f"Error in start_search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/v1/search/results/{project_id}",
    response_model=SearchResultsResponse,
    tags=["Search"]
)
async def get_results(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get search results and design parameters for a project.
    Returns current status and available data.
    """
    try:
        project = db.query(DBProject).filter(
            DBProject.project_id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Fetch parameters
        params = db.query(DBDrugParameter).filter(
            DBDrugParameter.project_id == project_id
        ).all()
        
        parameter_schemas = [
            ParameterSchema(
                parameter=p.parameter,
                value=p.value,
                unit=p.unit,
                source=f"PMID: {p.source_pmid}" if p.source_pmid else "Manual",
                is_reliable=p.is_reliable
            )
            for p in params
        ]
        
        return SearchResultsResponse(
            project_id=project_id,
            status=project.status,
            parameters=parameter_schemas,
            sources_count=len(set(p.source_pmid for p in params if p.source_pmid)),
            created_at=project.created_at,
            updated_at=project.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/v1/projects/{project_id}",
    tags=["Projects"]
)
async def get_project_details(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Get full project details including design and regulatory status."""
    try:
        project = db.query(DBProject).filter(
            DBProject.project_id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "project_id": project.project_id,
            "inn_en": project.inn_en,
            "inn_ru": project.inn_ru,
            "dosage": project.dosage,
            "form": project.form,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "design_parameters": project.design_parameters,
            "regulatory_check": project.regulatory_check,
            "search_results": project.search_results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_project_details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/v1/reports/{project_id}/generate",
    tags=["Reports"]
)
async def generate_report(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate DOCX report for project."""
    try:
        project = db.query(DBProject).filter(
            DBProject.project_id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if we have necessary data
        if project.status != "completed":
            raise HTTPException(
                status_code=400,
                detail="Project not yet completed. Cannot generate report."
            )
        
        # Generate filename
        report_filename = f"{project.inn_en}_{project_id[:8]}.docx"
        report_path = REPORTS_DIR / report_filename
        
        # Schedule report generation
        background_tasks.add_task(
            _generate_report_task,
            project_id=project_id,
            output_path=str(report_path)
        )
        
        return {
            "message": "Report generation started",
            "project_id": project_id,
            "expected_file": report_filename
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/v1/reports/{project_id}/download",
    tags=["Reports"]
)
async def download_report(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Download generated report."""
    try:
        project = db.query(DBProject).filter(
            DBProject.project_id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Find report file
        report_filename = f"{project.inn_en}_{project_id[:8]}.docx"
        report_path = REPORTS_DIR / report_filename
        
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found. Generate it first.")
        
        return FileResponse(
            path=report_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=report_filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

def _run_full_pipeline(project_id: str, inn: str):
    """
    Full pipeline: search -> design -> regulatory check -> report.
    Runs as background task.
    """
    db = SessionLocal()
    project = db.query(DBProject).filter(
        DBProject.project_id == project_id
    ).first()
    
    try:
        logger.info(f"[{project_id}] Starting full pipeline for {inn}")
        
        # Step 1: Search and extract parameters
        logger.info(f"[{project_id}] Step 1: Searching PubMed...")
        parser = ParsingModule(db)
        search_results = parser.search_and_extract(project_id, inn, max_articles=10)
        
        if search_results.get("error"):
            logger.warning(f"[{project_id}] Search error: {search_results['error']}")
            project.status = "search_failed"
            db.commit()
            return
        
        # Step 2: Generate design
        logger.info(f"[{project_id}] Step 2: Generating design...")
        designer = DesignModule(db)
        design = designer.generate_design(project_id)
        
        if design.get("error"):
            logger.warning(f"[{project_id}] Design generation error: {design['error']}")
            project.status = "design_failed"
            db.commit()
            return
        
        # Step 3: Regulatory check
        logger.info(f"[{project_id}] Step 3: Regulatory compliance check...")
        regulator = RegulatoryModule(db)
        reg_check = regulator.check_compliance(project_id)
        
        if reg_check.get("error"):
            logger.warning(f"[{project_id}] Regulatory check error: {reg_check['error']}")
            project.status = "regulatory_check_failed"
            db.commit()
            return
        
        # Save regulatory check
        project.regulatory_check = reg_check
        
        # Step 4: Update status
        project.status = "completed"
        db.commit()
        
        logger.info(f"[{project_id}] Pipeline completed successfully")
        
        # Auto-generate report
        _generate_report_task(project_id, str(REPORTS_DIR / f"{inn}_{project_id[:8]}.docx"))
    
    except Exception as e:
        logger.error(f"[{project_id}] Pipeline error: {e}", exc_info=True)
        project.status = "failed"
        db.commit()
    
    finally:
        db.close()

def _generate_report_task(project_id: str, output_path: str):
    """Generate report as background task."""
    db = SessionLocal()
    
    try:
        logger.info(f"[{project_id}] Generating report...")
        
        reporter = ReportModule(db)
        result = reporter.generate_synopsis(project_id, output_path)
        
        if result.get("error"):
            logger.error(f"[{project_id}] Report generation error: {result['error']}")
        else:
            logger.info(f"[{project_id}] Report generated: {output_path}")
    
    except Exception as e:
        logger.error(f"[{project_id}] Report task error: {e}", exc_info=True)
    
    finally:
        db.close()

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
