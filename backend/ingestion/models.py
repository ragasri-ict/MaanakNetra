"""
Data models for MAANAKNETRA Document Ingestion Layer.
Strictly maps to contracts/document.schema.json.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json


class FileType(str, Enum):
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"


class ExtractionMethod(str, Enum):
    TEXT = "TEXT"
    OCR = "OCR"
    MIXED = "MIXED"


@dataclass
class TextBlock:
    """A single text block, paragraph, or clause within a document page."""
    text: str
    page_number: int
    block_id: Optional[str] = None
    clause_number: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "clause_number": self.clause_number,
            "text": self.text,
            "page_number": self.page_number,
            "char_start": self.char_start,
            "char_end": self.char_end
        }


@dataclass
class PageObject:
    """A page representation preserving boundary and extraction provenance."""
    page_number: int
    text: str
    extraction_method: ExtractionMethod
    character_count: int
    blocks: List[TextBlock] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "extraction_method": self.extraction_method.value if isinstance(self.extraction_method, ExtractionMethod) else self.extraction_method,
            "character_count": self.character_count,
            "blocks": [b.to_dict() for b in self.blocks]
        }


@dataclass
class DocumentResult:
    """Normalized ingested document output ready for downstream AI analysis."""
    document_id: str
    filename: str
    file_type: str
    page_count: int
    extracted_text: str
    pages: List[PageObject]
    character_count: int = 0
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.character_count:
            self.character_count = len(self.extracted_text)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "page_count": self.page_count,
            "extracted_text": self.extracted_text,
            "character_count": self.character_count,
            "ingested_at": self.ingested_at,
            "metadata": self.metadata,
            "pages": [p.to_dict() for p in self.pages]
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
