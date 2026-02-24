"""
FastAPI application for pharmaceutical study design automation.
Main entry point with all API endpoints.
"""
import logging
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import tempfile
import shutil

from database import SessionLocal, init_db, get_db
from schemas import (
    SearchStartRequest, SearchStartResponse, SearchResultsResponse,
    ParameterSchema, PDFUploadResponse, DesignCalculateRequest, 
    DesignResultResponse, CriticalParametersResponse, SamplingPlanResponse
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3003",
        "http://localhost:3004",
        "http://127.0.0.1:3004",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
            inn=request.inn_en,
            additional_substances=request.additional_substances
        )
        
        return SearchStartResponse(
            project_id=project_id,
            status="searching",
            message="Search started. Please poll /api/v1/search/results/{project_id} for updates"
        )
    
    except Exception as e:
        logger.error(f"Error in start_search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/v1/upload/pdf",
    response_model=PDFUploadResponse,
    tags=["Upload"]
)
async def upload_pdf(
    file: UploadFile = File(...),
    inn_en: str = None,
    inn_ru: str = None,
    dosage: str = None,
    form: str = None,
    db: Session = Depends(get_db)
):
    """
    Upload a PDF file and extract drug parameters from it.
    
    Parameters are extracted using the same LLM process as PubMed abstracts.
    
    Query parameters:
    - inn_en: Drug name in English (optional, but recommended)
    - inn_ru: Drug name in Russian (optional)
    - dosage: Drug dosage (optional)
    - form: Drug form (optional)
    """
    try:
        # Validate file is PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Use generic or provided drug name
        drug_name = inn_en or "unknown drug"
        
        # Create project
        project_id = str(uuid.uuid4())
        project = DBProject(
            project_id=project_id,
            inn_en=inn_en or "Unknown",
            inn_ru=inn_ru,
            dosage=dosage or "Not specified",
            form=form or "Not specified",
            status="uploading"
        )
        db.add(project)
        db.commit()
        
        logger.info(f"Created project {project_id} for PDF upload: {file.filename}")
        
        # Save uploaded file to temp location
        temp_dir = tempfile.mkdtemp()
        temp_pdf_path = Path(temp_dir) / file.filename
        
        try:
            # Save file
            with open(temp_pdf_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            logger.info(f"Saved uploaded PDF to {temp_pdf_path}")
            
            # Extract parameters
            parser = ParsingModule(db)
            result = parser.extract_from_pdf(project_id, str(temp_pdf_path), drug_name)
            
            parameters_found = len(result.get("parameters", []))
            
            if result.get("error"):
                logger.error(f"Error extracting from PDF: {result['error']}")
                project.status = "upload_failed"
                db.commit()
                
                return PDFUploadResponse(
                    project_id=project_id,
                    status="upload_failed",
                    message=f"Failed to extract parameters: {result['error']}",
                    parameters_found=0
                )
            
            return PDFUploadResponse(
                project_id=project_id,
                status="completed",
                message=f"PDF processed successfully. {parameters_found} parameters extracted.",
                parameters_found=parameters_found
            )
        
        finally:
            # Cleanup temp file
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_pdf: {e}", exc_info=True)
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
    "/api/v1/design/calculate",
    response_model=DesignResultResponse,
    tags=["Design"]
)
async def calculate_design(
    request: DesignCalculateRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate study design parameters based on drug pharmacokinetic parameters.
    
    This endpoint calculates design parameters with adjustment for dropout and screen failure rates.
    If project_id is provided, results are stored to the project database.
    
    Parameters:
    - cv_intra: Required. Intra-individual coefficient of variation (%)
    - tmax: Optional. Time to maximum concentration (hours)
    - t_half: Optional. Terminal half-life (hours)
    - power: Statistical power (default 0.80)
    - alpha: Significance level (default 0.05)
    - dropout_rate: Expected dropout rate % (default 0.0)
    - screen_fail_rate: Expected screen failure rate % (default 0.0)
    - project_id: Optional. Project UUID to store results
    """
    try:
        from services.calculator import BioeEquivalenceCalculator
        
        logger.info(f"Calculating design with CV_intra={request.cv_intra}%, dropout={request.dropout_rate}%, screen_fail={request.screen_fail_rate}%")
        
        calc = BioeEquivalenceCalculator()
        
        # Calculate sample size
        sample_size, design_type = calc.calculate_sample_size(
            cv_intra=request.cv_intra,
            power=request.power,
            alpha=request.alpha
        )
        
        # Adjust for dropout and screen failure
        recruitment_size = calc.calculate_recruitment_sample_size(
            sample_size=sample_size,
            dropout_rate=request.dropout_rate,
            screen_fail_rate=request.screen_fail_rate
        )
        
        # Calculate washout period if half-life provided
        washout_days = None
        if request.t_half:
            washout_days = calc.estimate_washout_period(request.t_half)
        
        # Estimate blood sampling plan if both Tmax and T1/2 provided
        sampling_plan_dict = None
        if request.tmax and request.t_half:
            sampling_plan_dict = calc.estimate_blood_sampling(
                request.tmax, 
                request.t_half
            )
        
        # Prepare response
        critical_params = CriticalParametersResponse(
            cv_intra=request.cv_intra,
            tmax=request.tmax,
            t_half=request.t_half
        )
        
        sampling_plan = None
        if sampling_plan_dict:
            sampling_plan = SamplingPlanResponse(**sampling_plan_dict)
        
        result = DesignResultResponse(
            sample_size=sample_size,
            recruitment_size=recruitment_size,
            design_type=design_type,
            cv_intra=request.cv_intra,
            power=request.power,
            alpha=request.alpha,
            dropout_rate=request.dropout_rate,
            screen_fail_rate=request.screen_fail_rate,
            washout_days=washout_days,
            critical_parameters=critical_params,
            sampling_plan=sampling_plan
        )
        
        # Save calculations to project if project_id is provided
        if request.project_id:
            project = db.query(DBProject).filter(
                DBProject.project_id == request.project_id
            ).first()
            
            if project:
                project.design_parameters = {
                    "sample_size": sample_size,
                    "recruitment_size": recruitment_size,
                    "design_type": design_type,
                    "cv_intra": request.cv_intra,
                    "power": request.power,
                    "alpha": request.alpha,
                    "dropout_rate": request.dropout_rate,
                    "screen_fail_rate": request.screen_fail_rate,
                    "washout_days": washout_days,
                    "critical_parameters": {
                        "CV_intra": request.cv_intra,
                        "Tmax": request.tmax,
                        "T1/2": request.t_half,
                    },
                    "sampling_plan": sampling_plan_dict
                }
                db.commit()
                logger.info(f"Design results saved to project {request.project_id}")
        
        logger.info(f"Design calculated: n={sample_size}, recruitment_n={recruitment_size}, type={design_type}")
        return result
    
    except ValueError as e:
        logger.error(f"Validation error in calculate_design: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in calculate_design: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/design/{project_id}",
    response_model=DesignResultResponse,
    tags=["Design"]
)
async def get_design_results(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get calculated design results for a specific project.
    
    Retrieves previously calculated design parameters from the database.
    These results are used when generating the project report.
    """
    try:
        logger.info(f"Fetching design results for project {project_id}")
        
        project = db.query(DBProject).filter(
            DBProject.project_id == project_id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project.design_parameters:
            raise HTTPException(
                status_code=404, 
                detail="Design parameters not found. Calculate design first."
            )
        
        # Extract design parameters from stored JSON
        design_data = project.design_parameters
        critical_params_data = design_data.get("critical_parameters", {})
        sampling_plan_data = design_data.get("sampling_plan")
        
        critical_params = CriticalParametersResponse(
            cv_intra=critical_params_data.get("CV_intra"),
            tmax=critical_params_data.get("Tmax"),
            t_half=critical_params_data.get("T1/2")
        )
        
        sampling_plan = None
        if sampling_plan_data:
            sampling_plan = SamplingPlanResponse(**sampling_plan_data)
        
        result = DesignResultResponse(
            sample_size=design_data.get("sample_size"),
            recruitment_size=design_data.get("recruitment_size", design_data.get("sample_size")),
            design_type=design_data.get("design_type"),
            cv_intra=critical_params_data.get("CV_intra"),
            power=design_data.get("power"),
            alpha=design_data.get("alpha"),
            dropout_rate=design_data.get("dropout_rate", 0.0),
            screen_fail_rate=design_data.get("screen_fail_rate", 0.0),
            washout_days=design_data.get("washout_days"),
            critical_parameters=critical_params,
            sampling_plan=sampling_plan
        )
        
        logger.info(f"Retrieved design for project {project_id}")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_design_results: {e}", exc_info=True)
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
        
        # Allow report generation regardless of project status.
        # Previously this endpoint rejected projects that weren't
        # in the "completed" state; keep behavior permissive but
        # log a warning so callers are aware.
        if project.status != "completed":
            logger.warning(
                f"Generating report for project {project_id} with status '{project.status}'"
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

def _run_full_pipeline(project_id: str, inn: str, additional_substances: list = None):
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
        search_results = parser.search_and_extract(
            project_id, inn, max_articles=10,
            additional_substances=additional_substances
        )
        
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
