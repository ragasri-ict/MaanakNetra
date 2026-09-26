"""
MAANAKNETRA Document Ingestion Package.
Provides multi-format parsing (PDF, DOCX, TXT) with PyMuPDF, python-docx, and conditional OCR fallback.
"""

from .models import (
    DocumentResult,
    PageObject,
    TextBlock,
    FileType,
    ExtractionMethod
)
from .document_parser import (
    ingest_document,
    detect_file_type
)
from .pdf_parser import parse_pdf_file
from .docx_parser import parse_docx_file
from .txt_parser import parse_txt_file
from .ocr_fallback import should_trigger_ocr, OCRFallbackEngine

__all__ = [
    "ingest_document",
    "detect_file_type",
    "parse_pdf_file",
    "parse_docx_file",
    "parse_txt_file",
    "should_trigger_ocr",
    "OCRFallbackEngine",
    "DocumentResult",
    "PageObject",
    "TextBlock",
    "FileType",
    "ExtractionMethod",
]
