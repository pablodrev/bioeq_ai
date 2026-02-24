"""
Report generation module.
Generates DOCX report with study synopsis.
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from models import DBProject, DBDrugParameter
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pathlib import Path
from core.design_module import DesignModule

logger = logging.getLogger(__name__)

class ReportModule:
    """Generates Word documents with study synopsis."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_synopsis(self, project_id: str, output_path: str) -> Dict[str, Any]:
        """
        Generate DOCX document with study synopsis.
        
        Args:
            project_id: Project UUID
            output_path: Path to save DOCX file
        
        Returns:
            Dict with status and file path
        """
        
        try:
            # Fetch project
            project = self.db.query(DBProject).filter(
                DBProject.project_id == project_id
            ).first()
            
            if not project:
                return {"error": "Project not found"}
            
            # Create document
            doc = Document()
            
            # Title
            title = doc.add_heading(
                "Синопсис исследования биоэквивалентности",
                level=1
            )
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Study info
            doc.add_heading("1. Информация о лекарственном препарате", level=2)
            table = doc.add_table(rows=5, cols=2)
            table.style = "Light Grid Accent 1"
            
            cells = table.rows[0].cells
            cells[0].text = "Международное непатентованное название (МНН)"
            cells[1].text = str(project.inn_en or "Unknown")
            
            cells = table.rows[1].cells
            cells[0].text = "Лекарственная форма"
            cells[1].text = str(project.form or "Not specified")
            
            cells = table.rows[2].cells
            cells[0].text = "Дозировка"
            cells[1].text = str(project.dosage or "Not specified")
            
            cells = table.rows[3].cells
            cells[0].text = "Тип исследования"
            cells[1].text = "Биоэквивалентность"
            
            cells = table.rows[4].cells
            cells[0].text = "Статус"
            cells[1].text = str((project.status or "unknown").replace("_", " ").upper())
            
            # Extracted parameters
            doc.add_heading("2. Фармакокинетические параметры", level=2)
            
            params = self.db.query(DBDrugParameter).filter(
                DBDrugParameter.project_id == project_id
            ).all()
            
            if params:
                param_table = doc.add_table(rows=len(params) + 1, cols=4)
                param_table.style = "Light Grid Accent 1"
                
                # Header
                hdr_cells = param_table.rows[0].cells
                hdr_cells[0].text = "Параметр"
                hdr_cells[1].text = "Значение"
                hdr_cells[2].text = "Единица"
                hdr_cells[3].text = "Источник (PMID)"
                
                # Data rows
                for i, param in enumerate(params, 1):
                    cells = param_table.rows[i].cells
                    cells[0].text = str(param.parameter or "")
                    cells[1].text = str(param.value or "")
                    cells[2].text = str(param.unit or "")
                    cells[3].text = f"PMID: {param.source_pmid}" if getattr(param, 'source_pmid', None) else "Manual"
            else:
                doc.add_paragraph("Параметры не найдены.")
            
            # Design section
            # Be defensive: `design_parameters` may be None or not a dict
            design_raw = project.design_parameters
            design = design_raw if isinstance(design_raw, dict) else {}

            # If design not present, attempt to generate it from available parameters
            if not design:
                try:
                    designer = DesignModule(self.db)
                    generated = designer.generate_design(project_id)
                    if isinstance(generated, dict) and not generated.get("error"):
                        design = generated
                    else:
                        logger.info(f"Design generation during report: {generated.get('error') if isinstance(generated, dict) else 'unknown error'}")
                except Exception as e:
                    logger.warning(f"Failed to auto-generate design during report: {e}")

            if design:
                doc.add_heading("3. Дизайн исследования", level=2)

                design_table = doc.add_table(rows=7, cols=2)
                design_table.style = "Light Grid Accent 1"

                cells = design_table.rows[0].cells
                cells[0].text = "Дизайн"
                cells[1].text = str(design.get("design_type", "N/A"))

                cells = design_table.rows[1].cells
                cells[0].text = "Размер выборки (N)"
                cells[1].text = str(design.get("sample_size", "N/A"))

                cells = design_table.rows[2].cells
                cells[0].text = "Размер выборки с учетом выбывания (N)"
                cells[1].text = str(design.get("recruitment_size", design.get("sample_size", "N/A")))

                cells = design_table.rows[3].cells
                cells[0].text = "Статистическая мощность"
                try:
                    power = design.get('power', 0.8)
                    cells[1].text = f"{float(power) * 100:.0f}%"
                except Exception:
                    cells[1].text = str(design.get('power', 'N/A'))

                cells = design_table.rows[4].cells
                cells[0].text = "CV_intra (%)"
                crit = design.get("critical_parameters", {}) or {}
                cells[1].text = str(crit.get("CV_intra", "N/A"))

                cells = design_table.rows[5].cells
                cells[0].text = "Период отмывания (дней)"
                cells[1].text = str(design.get("washout_days", "N/A"))

                cells = design_table.rows[6].cells
                cells[0].text = "Выбывание / Отсев по скринингу (%)"
                dropout = design.get("dropout_rate", 0.0)
                screen_fail = design.get("screen_fail_rate", 0.0)
                cells[1].text = f"{dropout}% / {screen_fail}%"

            
            # Regulatory status
            # Be defensive: `regulatory_check` may be None or not a dict
            reg_raw = project.regulatory_check
            reg = reg_raw if isinstance(reg_raw, dict) else {}

            if reg:
                doc.add_heading("4. Статус регуляторной проверки", level=2)

                status_para = doc.add_paragraph()
                if reg.get("is_compliant") is True:
                    status_text = "✓ СООТВЕТСТВУЕТ ТРЕБОВАНИЯМ"
                    status_para.add_run(status_text).font.color.rgb = RGBColor(0, 128, 0)
                elif reg.get("is_compliant") is False:
                    status_text = "✗ ТРЕБУЕТ ДОРАБОТКИ"
                    status_para.add_run(status_text).font.color.rgb = RGBColor(255, 0, 0)
                else:
                    status_para.add_run("Статус: N/A")

                if reg.get("critical_issues"):
                    doc.add_paragraph("Критические замечания:", style="Heading 3")
                    for issue in reg["critical_issues"]:
                        doc.add_paragraph(str(issue), style="List Bullet")

                if reg.get("warnings"):
                    doc.add_paragraph("Предупреждения:", style="Heading 3")
                    for warning in reg["warnings"]:
                        doc.add_paragraph(str(warning), style="List Bullet")
            
            # Footer
            doc.add_paragraph()
            footer = doc.add_paragraph(
                f"Документ автоматически сгенерирован системой MedDesign MVP\n"
                f"Дата: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            footer.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            footer_format = footer.runs[0].font
            footer_format.size = Pt(9)
            footer_format.italic = True
            
            # Save
            doc.save(output_path)
            logger.info(f"Generated report for {project_id} at {output_path}")

            return {
                "success": True,
                "file_path": output_path,
                "file_name": Path(output_path).name
            }
        
        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            return {"error": str(e)}
