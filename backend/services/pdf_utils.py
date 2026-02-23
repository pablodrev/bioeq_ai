"""
PDF processing utility for extracting text from PDF files.
"""
import logging
from typing import Optional
import pdfplumber

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Extract text from PDF files."""
    
    @staticmethod
    def extract_text(pdf_path: str) -> Optional[str]:
        """
        Extract all text from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            Concatenated text from all pages, or None if extraction fails
        """
        try:
            text_content = []
            
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"Processing PDF with {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(page_text)
                        logger.debug(f"Extracted text from page {page_num}")
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num}: {e}")
                        continue
            
            full_text = "\n\n".join(text_content)
            
            if not full_text.strip():
                logger.warning("No text content extracted from PDF")
                return None
            
            logger.info(f"Successfully extracted {len(full_text)} characters from PDF")
            return full_text
        
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return None
