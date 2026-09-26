"""
Data models and typed structures for MAANAKNETRA Regulatory Intelligence Layer (Step 9A).
Defines representations for Standard Status, Lifecycle/Amendments, QCO Applicability,
and Consolidated Regulatory Summaries.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class StandardLifecycleStatus(str, Enum):
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"
    UNDER_REVISION = "UNDER_REVISION"
    UNKNOWN = "UNKNOWN"


class ApplicabilityState(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(str, Enum):
    VERIFIED_OFFICIAL = "VERIFIED_OFFICIAL"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    UNKNOWN = "UNKNOWN"


@dataclass
class StandardStatusResult:
    """Status details for an Indian Standard."""
    is_number: str
    title: str
    status: StandardLifecycleStatus
    current_version: Optional[str] = None
    effective_year: Optional[int] = None
    superseded_by: Optional[str] = None
    withdrawn_reason: Optional[str] = None
    evidence: str = ""
    source: Dict[str, Any] = field(default_factory=dict)
    provenance: str = ""
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    review_required: bool = False
    review_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_number": self.is_number,
            "title": self.title,
            "status": self.status.value if isinstance(self.status, StandardLifecycleStatus) else self.status,
            "current_version": self.current_version,
            "effective_year": self.effective_year,
            "superseded_by": self.superseded_by,
            "withdrawn_reason": self.withdrawn_reason,
            "evidence": self.evidence,
            "source": self.source,
            "provenance": self.provenance,
            "verification_status": self.verification_status.value if isinstance(self.verification_status, VerificationStatus) else self.verification_status,
            "review_required": self.review_required,
            "review_reason": self.review_reason,
        }


@dataclass
class AmendmentRecord:
    """Amendment information for an Indian Standard."""
    amendment_number: str
    issue_date: str
    summary: str
    affected_clauses: List[str] = field(default_factory=list)
    gazette_notification: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amendment_number": self.amendment_number,
            "issue_date": self.issue_date,
            "summary": self.summary,
            "affected_clauses": self.affected_clauses,
            "gazette_notification": self.gazette_notification,
        }


@dataclass
class LifecycleResult:
    """Lifecycle and edition lineage for an Indian Standard."""
    is_number: str
    current_edition: Optional[str] = None
    older_editions: List[str] = field(default_factory=list)
    supersedes: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None
    status: StandardLifecycleStatus = StandardLifecycleStatus.UNKNOWN
    effective_year: Optional[int] = None
    amendments: List[Dict[str, Any]] = field(default_factory=list)
    withdrawn_reason: Optional[str] = None
    transition_notes: Optional[str] = None
    evidence: str = ""
    provenance: str = ""
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    review_required: bool = False
    review_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_number": self.is_number,
            "current_edition": self.current_edition,
            "older_editions": self.older_editions,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "status": self.status.value if isinstance(self.status, StandardLifecycleStatus) else self.status,
            "effective_year": self.effective_year,
            "amendments": self.amendments,
            "withdrawn_reason": self.withdrawn_reason,
            "transition_notes": self.transition_notes,
            "evidence": self.evidence,
            "provenance": self.provenance,
            "verification_status": self.verification_status.value if isinstance(self.verification_status, VerificationStatus) else self.verification_status,
            "review_required": self.review_required,
            "review_reason": self.review_reason,
        }


@dataclass
class QCOApplicabilityResult:
    """Quality Control Order applicability analysis."""
    applicability_state: ApplicabilityState
    is_covered_by_qco: bool
    qco_id: Optional[str] = None
    order_title: Optional[str] = None
    order_number: Optional[str] = None
    issuing_ministry: Optional[str] = None
    gazette_date: Optional[str] = None
    effective_date: Optional[str] = None
    isi_mark_mandatory: bool = False
    covered_standards: List[Dict[str, str]] = field(default_factory=list)
    product_scope: List[str] = field(default_factory=list)
    exemption_provisions: Optional[str] = None
    notes: Optional[str] = None
    evidence: str = ""
    provenance: str = ""
    source_url: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    review_required: bool = False
    review_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applicability_state": self.applicability_state.value if isinstance(self.applicability_state, ApplicabilityState) else self.applicability_state,
            "is_covered_by_qco": self.is_covered_by_qco,
            "qco_id": self.qco_id,
            "order_title": self.order_title,
            "order_number": self.order_number,
            "issuing_ministry": self.issuing_ministry,
            "gazette_date": self.gazette_date,
            "effective_date": self.effective_date,
            "isi_mark_mandatory": self.isi_mark_mandatory,
            "covered_standards": self.covered_standards,
            "product_scope": self.product_scope,
            "exemption_provisions": self.exemption_provisions,
            "notes": self.notes,
            "evidence": self.evidence,
            "provenance": self.provenance,
            "source_url": self.source_url,
            "verification_status": self.verification_status.value if isinstance(self.verification_status, VerificationStatus) else self.verification_status,
            "review_required": self.review_required,
            "review_reason": self.review_reason,
        }


@dataclass
class RegulatorySummaryResult:
    """Consolidated deterministic regulatory and compliance summary."""
    is_number: Optional[str] = None
    title: Optional[str] = None
    product_or_category: Optional[str] = None
    standard_status: Optional[Dict[str, Any]] = None
    lifecycle: Optional[Dict[str, Any]] = None
    qco: Optional[Dict[str, Any]] = None
    mandatory_certification: bool = False
    certification_scheme: Optional[str] = None
    compliance_verdict: str = "UNKNOWN"
    review_required: bool = False
    review_reasons: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    provenance: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_number": self.is_number,
            "title": self.title,
            "product_or_category": self.product_or_category,
            "standard_status": self.standard_status,
            "lifecycle": self.lifecycle,
            "qco": self.qco,
            "mandatory_certification": self.mandatory_certification,
            "certification_scheme": self.certification_scheme,
            "compliance_verdict": self.compliance_verdict,
            "review_required": self.review_required,
            "review_reasons": self.review_reasons,
            "evidence": self.evidence,
            "provenance": self.provenance,
            "source_urls": self.source_urls,
        }
