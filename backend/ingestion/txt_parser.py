"""
TXT Document Parser for MAANAKNETRA.
Parses plain text files, normalizes whitespace, extracts clause numbers, and handles page markers.
"""

import os
import re
from typing import List, Tuple
from .models import PageObject, TextBlock, ExtractionMethod

CLAUSE_REGEX = re.compile(r"^(\d+(\.\d+)*|[A-Z](\.\d+)*|Clause\s+\d+(\.\d+)*|SECTION\s+\d+)", re.IGNORECASE)


def parse_txt_file(file_path: str) -> List[PageObject]:
    """
    Parses a plain text file into structured PageObjects with TextBlocks.
    Preserves explicit form-feed page breaks (\x0c) or logical page pagination.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read with encoding fallbacks
    raw_content = None
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=enc) as f:
                raw_content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if raw_content is None:
        raise ValueError(f"Could not decode text file: {file_path}")

    # Check for form-feed characters (\x0c)
    raw_pages = raw_content.split("\x0c") if "\x0c" in raw_content else [raw_content]

    # If document is large and has no page breaks, paginate logically every ~3500 chars at paragraph boundary
    final_page_texts: List[str] = []
    for p in raw_pages:
        if len(p) > 5000 and "\n\n" in p:
            paragraphs = p.split("\n\n")
            current_chunk = []
            current_len = 0
            for para in paragraphs:
                current_chunk.append(para)
                current_len += len(para)
                if current_len >= 3000:
                    final_page_texts.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_len = 0
            if current_chunk:
                final_page_texts.append("\n\n".join(current_chunk))
        else:
            final_page_texts.append(p)

    pages: List[PageObject] = []

    for page_idx, page_raw in enumerate(final_page_texts, start=1):
        clean_page_text, blocks = _extract_blocks_from_text(page_raw, page_idx)
        pages.append(PageObject(
            page_number=page_idx,
            text=clean_page_text,
            extraction_method=ExtractionMethod.TEXT,
            character_count=len(clean_page_text),
            blocks=blocks
        ))

    return pages


def _extract_blocks_from_text(raw_text: str, page_number: int) -> Tuple[str, List[TextBlock]]:
    """
    Normalizes whitespace and extracts paragraphs/clauses with char offsets.
    """
    lines = raw_text.splitlines()
    paragraphs: List[str] = []
    current_para: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
        else:
            # Check if this line looks like a new clause start
            if CLAUSE_REGEX.match(stripped) and current_para:
                paragraphs.append(" ".join(current_para))
                current_para = [stripped]
            else:
                current_para.append(stripped)

    if current_para:
        paragraphs.append(" ".join(current_para))

    blocks: List[TextBlock] = []
    normalized_full_text_parts: List[str] = []
    current_char_offset = 0

    for idx, para in enumerate(paragraphs, start=1):
        clean_para = para.strip()
        if not clean_para:
            continue

        # Detect clause number if present
        clause_match = CLAUSE_REGEX.match(clean_para)
        clause_num = clause_match.group(1) if clause_match else None

        char_start = current_char_offset
        char_end = char_start + len(clean_para)

        blocks.append(TextBlock(
            block_id=f"p{page_number}_b{idx}",
            clause_number=clause_num,
            text=clean_para,
            page_number=page_number,
            char_start=char_start,
            char_end=char_end
        ))

        normalized_full_text_parts.append(clean_para)
        current_char_offset = char_end + 2  # accounted for \n\n

    full_normalized_text = "\n\n".join(normalized_full_text_parts)
    return full_normalized_text, blocks
