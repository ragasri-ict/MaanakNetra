"""
PDF Document Parser for MAANAKNETRA.
Primary engine: PyMuPDF (fitz).
Fallback engine: PaddleOCR (triggered ONLY when page has little/no extractable text).
Never silently replaces readable digital text with OCR.
"""

import os
import re
import logging
from typing import List, Tuple
from .models import PageObject, TextBlock, ExtractionMethod
from .ocr_fallback import should_trigger_ocr, OCRFallbackEngine, DEFAULT_OCR_TEXT_THRESHOLD

logger = logging.getLogger(__name__)

CLAUSE_REGEX = re.compile(r"^(\d+(\.\d+)*|[A-Z](\.\d+)*|Clause\s+\d+(\.\d+)*|SECTION\s+\d+)", re.IGNORECASE)


def parse_pdf_file(
    file_path: str,
    ocr_threshold: int = DEFAULT_OCR_TEXT_THRESHOLD,
    enable_ocr_fallback: bool = True
) -> List[PageObject]:
    """
    Parses a PDF file into structured PageObjects with TextBlocks.
    Uses PyMuPDF as the primary digital text extractor.
    Enforces strict fallback guardrail: Triggers OCR only if extracted digital text < ocr_threshold.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        import pymupdf
    except ImportError:
        raise RuntimeError("PyMuPDF is not installed. Install via pip install pymupdf")

    try:
        doc = pymupdf.open(file_path)
    except Exception as e:
        raise ValueError(f"Corrupted or invalid PDF document {file_path}: {e}")

    ocr_engine = OCRFallbackEngine() if enable_ocr_fallback else None
    pages: List[PageObject] = []

    MAX_BOUNDED_PAGES = 50
    total_pages = len(doc)
    pages_to_process = min(total_pages, MAX_BOUNDED_PAGES)
    if total_pages > MAX_BOUNDED_PAGES:
        logger.warning(
            f"Document {file_path} contains {total_pages} pages. "
            f"Analyzing first {MAX_BOUNDED_PAGES} pages to respect memory and latency bounds."
        )

    for page_idx in range(pages_to_process):
        page_num = page_idx + 1
        try:
            page = doc[page_idx]

            # 1. Primary Extraction: PyMuPDF digital text blocks
            # get_text("blocks") returns tuples: (x0, y0, x1, y1, "text", block_no, block_type)
            # block_type 0 is text, 1 is image
            raw_blocks = page.get_text("blocks")
            text_blocks_raw = [b[4] for b in raw_blocks if b[6] == 0 and b[4].strip()]
            digital_page_text = "\n\n".join(text_blocks_raw).strip()

            # 2. Check if page contains sufficient readable digital text
            if not should_trigger_ocr(digital_page_text, threshold=ocr_threshold):
                # Page has sufficient digital text: NEVER run OCR
                clean_text, structured_blocks = _structure_blocks(text_blocks_raw, page_num)
                pages.append(PageObject(
                    page_number=page_num,
                    text=clean_text,
                    extraction_method=ExtractionMethod.TEXT,
                    character_count=len(clean_text),
                    blocks=structured_blocks
                ))
            else:
                # Page is scanned, image-only, or has near-empty text
                logger.info(
                    f"Page {page_num} of {file_path} contains only {len(digital_page_text)} chars "
                    f"(< threshold {ocr_threshold}). Triggering OCR fallback evaluation."
                )

                ocr_text = ""
                ocr_blocks: List[TextBlock] = []

                if ocr_engine:
                    try:
                        # Render page to high-resolution image for OCR
                        pix = page.get_pixmap(dpi=150)
                        image_bytes = pix.tobytes("png")
                        ocr_text, ocr_blocks = ocr_engine.extract_text_from_image(image_bytes, page_num)
                    except Exception as ocr_err:
                        logger.warning(f"OCR execution failed on page {page_num}: {ocr_err}")

                if ocr_text.strip():
                    pages.append(PageObject(
                        page_number=page_num,
                        text=ocr_text,
                        extraction_method=ExtractionMethod.OCR,
                        character_count=len(ocr_text),
                        blocks=ocr_blocks
                    ))
                else:
                    # If OCR produced nothing or was unavailable, retain whatever digital text existed
                    clean_text, structured_blocks = _structure_blocks(text_blocks_raw, page_num)
                    pages.append(PageObject(
                        page_number=page_num,
                        text=clean_text,
                        extraction_method=ExtractionMethod.TEXT,
                        character_count=len(clean_text),
                        blocks=structured_blocks
                    ))

        except Exception as page_err:
            logger.error(f"Error processing page {page_num} in {file_path}: {page_err}")
            # Do not crash the entire document; record unreadable page
            pages.append(PageObject(
                page_number=page_num,
                text="",
                extraction_method=ExtractionMethod.TEXT,
                character_count=0,
                blocks=[]
            ))

    doc.close()

    if not pages:
        pages.append(PageObject(
            page_number=1,
            text="",
            extraction_method=ExtractionMethod.TEXT,
            character_count=0,
            blocks=[]
        ))

    return pages


def _structure_blocks(raw_blocks: List[str], page_number: int) -> Tuple[str, List[TextBlock]]:
    blocks: List[TextBlock] = []
    normalized_parts: List[str] = []
    current_char_offset = 0

    for idx, text in enumerate(raw_blocks, start=1):
        clean_text = text.strip()
        if not clean_text:
            continue

        clause_match = CLAUSE_REGEX.match(clean_text)
        clause_num = clause_match.group(1) if clause_match else None

        char_start = current_char_offset
        char_end = char_start + len(clean_text)

        blocks.append(TextBlock(
            block_id=f"p{page_number}_b{idx}",
            clause_number=clause_num,
            text=clean_text,
            page_number=page_number,
            char_start=char_start,
            char_end=char_end
        ))

        normalized_parts.append(clean_text)
        current_char_offset = char_end + 2

    full_text = "\n\n".join(normalized_parts)
    return full_text, blocks
