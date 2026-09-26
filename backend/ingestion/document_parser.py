"""
Unified Document Ingestion API for MAANAKNETRA.
Main entrypoint: ingest_document(file_path) -> DocumentResult.
Dispatches to format-specific parsers (PDF, DOCX, TXT) and handles edge cases.
"""

import os
import hashlib
from typing import Optional
from .models import DocumentResult, FileType, ExtractionMethod
from .pdf_parser import parse_pdf_file
from .docx_parser import parse_docx_file
from .txt_parser import parse_txt_file
from .ocr_fallback import DEFAULT_OCR_TEXT_THRESHOLD


def detect_file_type(file_path: str) -> FileType:
    """
    Detects file type based on file extension and magic header bytes.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return FileType.PDF
    elif ext == ".docx":
        return FileType.DOCX
    elif ext in [".txt", ".text", ".md"]:
        return FileType.TXT

    # Fallback to magic byte inspection
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
            if header.startswith(b"%PDF"):
                return FileType.PDF
            elif header.startswith(b"PK\x03\x04"):
                return FileType.DOCX
            else:
                return FileType.TXT
    except Exception:
        raise ValueError(f"Unsupported or unreadable file type: {ext} for {file_path}")


def ingest_document(
    file_path: str,
    ocr_threshold: int = DEFAULT_OCR_TEXT_THRESHOLD,
    enable_ocr_fallback: bool = True
) -> DocumentResult:
    """
    API-ready ingestion pipeline for tender documents.
    Converts PDF, DOCX, or TXT into a clean, structured DocumentResult.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    filename = os.path.basename(file_path)

    # Compute SHA-256 for audit traceability
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256_hash.update(chunk)
    file_hash = sha256_hash.hexdigest()
    doc_id = f"doc_{file_hash[:16]}"

    # Handle zero-byte empty document gracefully
    if file_size == 0:
        return DocumentResult(
            document_id=doc_id,
            filename=filename,
            file_type="TXT",
            page_count=1,
            extracted_text="",
            character_count=0,
            pages=[],
            metadata={
                "file_size_bytes": 0,
                "file_hash_sha256": file_hash,
                "status": "EMPTY_DOCUMENT"
            }
        )

    file_type = detect_file_type(file_path)

    # Dispatch to appropriate parser
    if file_type == FileType.PDF:
        pages = parse_pdf_file(
            file_path,
            ocr_threshold=ocr_threshold,
            enable_ocr_fallback=enable_ocr_fallback
        )
    elif file_type == FileType.DOCX:
        pages = parse_docx_file(file_path)
    elif file_type == FileType.TXT:
        pages = parse_txt_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_type}")

    # Build consolidated document text across pages
    page_texts = [p.text for p in pages if p.text.strip()]
    consolidated_text = "\n\n".join(page_texts)

    # Determine overall document-level extraction method
    methods = {p.extraction_method for p in pages}
    if not methods or methods == {ExtractionMethod.TEXT}:
        doc_method = "TEXT"
    elif methods == {ExtractionMethod.OCR}:
        doc_method = "OCR"
    else:
        doc_method = "MIXED"

    return DocumentResult(
        document_id=doc_id,
        filename=filename,
        file_type=file_type.value,
        page_count=len(pages),
        extracted_text=consolidated_text,
        character_count=len(consolidated_text),
        pages=pages,
        metadata={
            "file_size_bytes": file_size,
            "file_hash_sha256": file_hash,
            "extraction_method_summary": doc_method,
            "parser_engine": "PyMuPDF" if file_type == FileType.PDF else ("python-docx" if file_type == FileType.DOCX else "built-in")
        }
    )
