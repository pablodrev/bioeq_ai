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
            cells[1].text = project.inn_en
            
            cells = table.rows[1].cells
            cells[0].text = "Лекарственная форма"
            cells[1].text = project.form
            
            cells = table.rows[2].cells
            cells[0].text = "Дозировка"
            cells[1].text = project.dosage
            
            cells = table.rows[3].cells
            cells[0].text = "Тип исследования"
            cells[1].text = "Биоэквивалентность"
            
            cells = table.rows[4].cells
            cells[0].text = "Статус"
            cells[1].text = project.status.replace("_", " ").upper()
            
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
                    cells[0].text = param.parameter
                    cells[1].text = param.value
                    cells[2].text = param.unit or ""
                    cells[3].text = f"PMID: {param.source_pmid}" if param.source_pmid else "Manual"
            else:
                doc.add_paragraph("Параметры не найдены.")
            
            # Design section
            if project.design_parameters:
                doc.add_heading("3. Дизайн исследования", level=2)
                design = project.design_parameters
                
                design_table = doc.add_table(rows=5, cols=2)
                design_table.style = "Light Grid Accent 1"
                
                cells = design_table.rows[0].cells
                cells[0].text = "Дизайн"
                cells[1].text = design.get("design_type", "N/A")
                
                cells = design_table.rows[1].cells
                cells[0].text = "Размер выборки (N)"
                cells[1].text = str(design.get("sample_size", "N/A"))
                
                cells = design_table.rows[2].cells
                cells[0].text = "Статистическая мощность"
                cells[1].text = f"{design.get('power', 0.8) * 100:.0f}%"
                
                cells = design_table.rows[3].cells
                cells[0].text = "CV_intra (%)"
                cells[1].text = str(design.get("critical_parameters", {}).get("CV_intra", "N/A"))
                
                cells = design_table.rows[4].cells
                cells[0].text = "Период отмывания (дней)"
                cells[1].text = str(design.get("washout_days", "N/A"))
            
            # Regulatory status
            if project.regulatory_check:
                doc.add_heading("4. Статус регуляторной проверки", level=2)
                reg = project.regulatory_check
                
                status_para = doc.add_paragraph()
                if reg.get("is_compliant"):
                    status_text = "✓ СООТВЕТСТВУЕТ ТРЕБОВАНИЯМ"
                    status_para.add_run(status_text).font.color.rgb = RGBColor(0, 128, 0)
                else:
                    status_text = "✗ ТРЕБУЕТ ДОРАБОТКИ"
                    status_para.add_run(status_text).font.color.rgb = RGBColor(255, 0, 0)
                
                if reg.get("critical_issues"):
                    doc.add_paragraph("Критические замечания:", style="Heading 3")
                    for issue in reg["critical_issues"]:
                        doc.add_paragraph(issue, style="List Bullet")
                
                if reg.get("warnings"):
                    doc.add_paragraph("Предупреждения:", style="Heading 3")
                    for warning in reg["warnings"]:
                        doc.add_paragraph(warning, style="List Bullet")
            
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
                "file_name": output_path.split("\\")[-1]
            }
        
        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            return {"error": str(e)}
