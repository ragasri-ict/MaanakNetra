"""
Tender Linter Rules & Schema-Conformant Models (Step 10).
Strictly adheres to contracts/finding.schema.json.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingType(str, Enum):
    OUTDATED_STANDARD = "OUTDATED_STANDARD"
    WITHDRAWN_STANDARD = "WITHDRAWN_STANDARD"
    MISSING_ALLIED_STANDARD = "MISSING_ALLIED_STANDARD"
    MISSING_TEST_STANDARD = "MISSING_TEST_STANDARD"
    MISSING_CERTIFICATION = "MISSING_CERTIFICATION"
    PARAMETER_CONFLICT = "PARAMETER_CONFLICT"
    VAGUE_REQUIREMENT = "VAGUE_REQUIREMENT"
    OTHER = "OTHER"


class SourceType(str, Enum):
    BIS_CATALOG = "BIS_CATALOG"
    GAZETTE_QCO_ORDER = "GAZETTE_QCO_ORDER"
    DETERMINISTIC_RULE_ENGINE = "DETERMINISTIC_RULE_ENGINE"
    STANDARDS_GRAPH = "STANDARDS_GRAPH"


class ResolutionStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"


# Controlled dictionary of subjective / unquantified phrases to flag under Rule 4
VAGUE_PATTERNS = [
    {
        "phrase": "superior engineering workmanship",
        "category": "WORKMANSHIP",
        "guidance": "Specify standard workmanship clauses from IS 14220 Clause 6 or relevant BIS code.",
    },
    {
        "phrase": "standard commercial grade",
        "category": "MATERIAL",
        "guidance": "Specify exact metallurgical grades conforming to IS 14220 Table 2 (e.g. FG 200 for grey iron, AISI 410 for shaft).",
    },
    {
        "phrase": "heavy duty",
        "category": "DURABILITY",
        "guidance": "Replace 'heavy duty' with explicit continuous rating, temperature rise limits, and bearing L10h life.",
    },
    {
        "phrase": "good quality",
        "category": "QUALITY",
        "guidance": "Replace 'good quality' with explicit test acceptance standards and tolerance limits.",
    },
    {
        "phrase": "high-grade durable components",
        "category": "MATERIAL",
        "guidance": "Specify exact material standards conforming to IS 14220 / IS 5120 specifications.",
    },
    {
        "phrase": "suitable for water contact",
        "category": "MATERIAL",
        "guidance": "Specify corrosion-resistant metallurgy (e.g. Bronze Grade LTB 2 or Stainless Steel Grade CF8M).",
    },
    {
        "phrase": "best industry practice",
        "category": "PROCESS",
        "guidance": "Cite relevant BIS code of practice or ISO 9001 certified manufacturing protocols.",
    },
    {
        "phrase": "reputed make",
        "category": "VENDOR_NEUTRALITY",
        "guidance": "Replace restrictive 'reputed make' clause with objective technical standards under public procurement guidelines.",
    },
]


@dataclass
class LinterFinding:
    """Represents a single finding conforming to contracts/finding.schema.json."""
    finding_id: str
    severity: FindingSeverity
    finding_type: FindingType
    title: str
    tender_text: str
    affected_standard: Dict[str, Any]
    explanation: str
    evidence: Dict[str, Any]
    source: Dict[str, Any]
    suggested_fix: Dict[str, Any]
    confidence: float = 1.0
    requires_human_review: bool = True
    resolution_status: ResolutionStatus = ResolutionStatus.PENDING
    affected_requirement: Optional[Dict[str, Any]] = None
    officer_justification: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes finding strictly according to finding.schema.json."""
        d = {
            "finding_id": self.finding_id,
            "severity": self.severity.value if isinstance(self.severity, FindingSeverity) else self.severity,
            "finding_type": self.finding_type.value if isinstance(self.finding_type, FindingType) else self.finding_type,
            "title": self.title,
            "tender_text": self.tender_text,
            "affected_standard": self.affected_standard,
            "explanation": self.explanation,
            "evidence": self.evidence,
            "source": self.source,
            "suggested_fix": self.suggested_fix,
            "confidence": self.confidence,
            "requires_human_review": self.requires_human_review,
            "resolution_status": self.resolution_status.value if isinstance(self.resolution_status, ResolutionStatus) else self.resolution_status,
        }
        if self.affected_requirement is not None:
            d["affected_requirement"] = self.affected_requirement
        if self.officer_justification is not None:
            d["officer_justification"] = self.officer_justification
        if self.resolved_by is not None:
            d["resolved_by"] = self.resolved_by
        if self.resolved_at is not None:
            d["resolved_at"] = self.resolved_at
        return d
