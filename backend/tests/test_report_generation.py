import uuid
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models import DBProject
from core.report_module import ReportModule


def test_generate_report_with_failed_design(tmp_path):
    # Create an isolated SQLite in-memory database for the test
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    project_id = str(uuid.uuid4())
    project = DBProject(
        project_id=project_id,
        inn_en="TestDrug",
        inn_ru=None,
        dosage="10 mg",
        form="tablet",
        status="design_failed",
        design_parameters=None,
        regulatory_check=None
    )
    session.add(project)
    session.commit()

    out_file = tmp_path / f"{project.inn_en}_{project_id[:8]}.docx"

    reporter = ReportModule(session)
    result = reporter.generate_synopsis(project_id, str(out_file))

    assert result.get("success") is True
    assert out_file.exists()

    session.close()
