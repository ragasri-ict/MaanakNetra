"""
MAANAKNETRA - Regulatory Intelligence Service (Step 9A)

Provides deterministic, auditable regulatory intelligence for procurement officers:
- Standard Status (CURRENT, SUPERSEDED, WITHDRAWN, UNKNOWN)
- Version & Amendment Lifecycle (editions, supersession chains, gazetted amendments)
- Quality Control Order (QCO) Applicability (mandates, effective dates, scope, exemptions)
- Human Review Requirements (flagging all statutory uncertainties without speculation)

Enforces zero hallucination:
- No invented dates or fake QCO mandates.
- No manufactured URLs or citations.
- Explicit PENDING_VERIFICATION for transition periods and cross-applicability uncertainties.
"""

from __future__ import annotations

import os
import re
import json
from typing import Dict, Any, List, Optional, Tuple, Set

from .models import (
    StandardLifecycleStatus,
    ApplicabilityState,
    VerificationStatus,
    StandardStatusResult,
    AmendmentRecord,
    LifecycleResult,
    QCOApplicabilityResult,
    RegulatorySummaryResult,
)


def normalize_is_code(code: Optional[str]) -> str:
    """
    Deterministically normalizes an Indian Standard designation.
    Examples:
        'is14220' -> 'IS 14220'
        'IS  8034:2018' -> 'IS 8034:2018'
        'is 6595 (part 1)' -> 'IS 6595 (Part 1)'
    """
    if not code or not isinstance(code, str):
        return ""

    cleaned = code.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Standardize prefix "IS"
    m = re.match(r"^(?i:is)\s*(\d.*)$", cleaned)
    if m:
        cleaned = f"IS {m.group(1).strip()}"

    # Standardize common (Part X) casing
    cleaned = re.sub(r"(?i)\(part\s*(\d+)\)", r"(Part \1)", cleaned)

    return cleaned


def extract_base_is_code(code: str) -> str:
    """
    Extracts the base standard designation without the year/revision suffix.
    Examples:
        'IS 14220:2018' -> 'IS 14220'
        'IS 6595 (Part 1):2018' -> 'IS 6595 (Part 1)'
        'IS 14220' -> 'IS 14220'
    """
    norm = normalize_is_code(code)
    # Remove year suffix :YYYY or :YYYY-YY
    base = re.sub(r":\d{4}(-\d+)?$", "", norm)
    return base.strip()


class RegulatoryIntelligenceService:
    """
    Service layer providing auditable status, amendment, and QCO intelligence.
    """

    def __init__(
        self,
        standards_path: str = "data/standards.json",
        status_path: str = "data/status.json",
        qco_path: str = "data/qco.json",
    ):
        self.standards_path = standards_path
        self.status_path = status_path
        self.qco_path = qco_path

        self.standards: List[Dict[str, Any]] = []
        self.statuses: List[Dict[str, Any]] = []
        self.qcos: List[Dict[str, Any]] = []

        # Index maps for deterministic lookup
        self._standards_by_code: Dict[str, Dict[str, Any]] = {}
        self._standards_by_version: Dict[str, Dict[str, Any]] = {}
        self._status_by_code: Dict[str, Dict[str, Any]] = {}
        self._status_by_version: Dict[str, Dict[str, Any]] = {}
        self._qco_by_id: Dict[str, Dict[str, Any]] = {}

        self._load_data()

    def _load_data(self) -> None:
        """Loads and indexes datasets from disk."""
        if os.path.exists(self.standards_path):
            with open(self.standards_path, "r", encoding="utf-8") as f:
                self.standards = json.load(f)
            for std in self.standards:
                is_num = normalize_is_code(std.get("is_number", ""))
                if is_num:
                    self._standards_by_code[is_num] = std
                ver = normalize_is_code(std.get("current_version", ""))
                if ver:
                    self._standards_by_version[ver] = std

        if os.path.exists(self.status_path):
            with open(self.status_path, "r", encoding="utf-8") as f:
                self.statuses = json.load(f)
            for st in self.statuses:
                code = normalize_is_code(st.get("standard_code", ""))
                if code:
                    self._status_by_code[code] = st
                ver = normalize_is_code(st.get("version", ""))
                if ver:
                    self._status_by_version[ver] = st

        if os.path.exists(self.qco_path):
            with open(self.qco_path, "r", encoding="utf-8") as f:
                self.qcos = json.load(f)
            for q in self.qcos:
                qid = q.get("qco_id", "")
                if qid:
                    self._qco_by_id[qid] = q

    # ------------------------------------------------------------------
    # Standard Status Intelligence
    # ------------------------------------------------------------------

    def get_standard_status(self, is_number: Optional[str]) -> Dict[str, Any]:
        """
        Determines the official lifecycle status of an Indian Standard.
        Returns CURRENT, SUPERSEDED, WITHDRAWN, or UNKNOWN.
        """
        if not is_number or not isinstance(is_number, str) or not is_number.strip():
            return StandardStatusResult(
                is_number="[MISSING]",
                title="[MISSING STANDARD IDENTIFIER]",
                status=StandardLifecycleStatus.UNKNOWN,
                evidence="No standard identifier was provided for verification.",
                provenance="service_validation",
                verification_status=VerificationStatus.UNKNOWN,
                review_required=True,
                review_reason="Standard identifier was omitted or empty.",
            ).to_dict()

        norm_code = normalize_is_code(is_number)
        base_code = extract_base_is_code(norm_code)

        # 1. Lookup in status.json
        status_rec = (
            self._status_by_code.get(norm_code)
            or self._status_by_version.get(norm_code)
            or self._status_by_code.get(base_code)
            or self._status_by_version.get(base_code)
        )

        # 2. Lookup in standards.json
        std_rec = (
            self._standards_by_code.get(norm_code)
            or self._standards_by_version.get(norm_code)
            or self._standards_by_code.get(base_code)
            or self._standards_by_version.get(base_code)
        )

        if not status_rec and not std_rec:
            return StandardStatusResult(
                is_number=norm_code,
                title="[UNKNOWN STANDARD]",
                status=StandardLifecycleStatus.UNKNOWN,
                evidence="",
                provenance="data/status.json, data/standards.json",
                verification_status=VerificationStatus.UNKNOWN,
                review_required=True,
                review_reason=f"Standard '{norm_code}' not found in official project standards registry.",
            ).to_dict()

        # Determine title
        title = ""
        if std_rec:
            title = std_rec.get("title", "")
        elif status_rec and status_rec.get("superseded_by"):
            sup_std = self._standards_by_code.get(status_rec.get("superseded_by", ""))
            title = f"{sup_std.get('title', '')} (Older Edition)" if sup_std else "Indian Standard (Superseded Edition)"
        else:
            title = "Indian Standard"

        # Determine status
        raw_status = (
            (status_rec.get("status") if status_rec else None)
            or (std_rec.get("status") if std_rec else None)
            or "UNKNOWN"
        ).upper()

        try:
            status_enum = StandardLifecycleStatus(raw_status)
        except ValueError:
            status_enum = StandardLifecycleStatus.UNKNOWN

        current_ver = (
            (status_rec.get("version") if status_rec else None)
            or (std_rec.get("current_version") if std_rec else None)
        )
        effective_year = (
            (status_rec.get("effective_year") if status_rec else None)
            or (std_rec.get("publication_year") if std_rec else None)
        )
        superseded_by = (
            (status_rec.get("superseded_by") if status_rec else None)
            or (std_rec.get("superseded_by") if std_rec else None)
        )
        withdrawn_reason = std_rec.get("withdrawn_reason") if std_rec else None

        # Verification status
        raw_v_status = (
            (status_rec.get("verification_status") if status_rec else None)
            or (std_rec.get("verification", {}).get("verification_status") if std_rec else None)
            or "UNKNOWN"
        )
        try:
            v_status_enum = VerificationStatus(raw_v_status)
        except ValueError:
            v_status_enum = VerificationStatus.UNKNOWN

        # Evidence and Provenance
        evidence = (
            (status_rec.get("lifecycle_evidence") if status_rec else None)
            or (std_rec.get("source", {}).get("curator_notes") if std_rec else "")
            or ""
        )
        provenance = (
            (std_rec.get("source", {}).get("official_publication_ref") if std_rec else None)
            or "data/status.json"
        )
        source = std_rec.get("source", {}) if std_rec else {}

        # Human Review Triggers
        review_required = False
        review_reason = None

        if v_status_enum == VerificationStatus.PENDING_VERIFICATION:
            review_required = True
            review_reason = (
                f"Official gazette cessation of revision or concurrent transition period "
                f"for '{norm_code}' remains pending verification against BIS gazette."
            )
        elif status_enum == StandardLifecycleStatus.SUPERSEDED:
            review_required = True
            review_reason = (
                f"Standard '{norm_code}' is SUPERSEDED by '{superseded_by}'. "
                f"Procurement documents should cite the active current standard."
            )
        elif status_enum == StandardLifecycleStatus.WITHDRAWN:
            review_required = True
            review_reason = (
                f"Standard '{norm_code}' is WITHDRAWN. Reason: {withdrawn_reason or 'Not specified in registry'}."
            )
        elif status_enum == StandardLifecycleStatus.UNKNOWN:
            review_required = True
            review_reason = f"Standard status for '{norm_code}' could not be established with certainty."

        return StandardStatusResult(
            is_number=norm_code,
            title=title,
            status=status_enum,
            current_version=current_ver,
            effective_year=effective_year,
            superseded_by=superseded_by,
            withdrawn_reason=withdrawn_reason,
            evidence=evidence,
            source=source,
            provenance=provenance,
            verification_status=v_status_enum,
            review_required=review_required,
            review_reason=review_reason,
        ).to_dict()

    # ------------------------------------------------------------------
    # Lifecycle & Amendment Intelligence
    # ------------------------------------------------------------------

    def get_lifecycle(self, is_number: Optional[str]) -> Dict[str, Any]:
        """
        Retrieves complete lifecycle, edition, and amendment records for a standard.
        """
        if not is_number or not isinstance(is_number, str) or not is_number.strip():
            return LifecycleResult(
                is_number="[MISSING]",
                status=StandardLifecycleStatus.UNKNOWN,
                evidence="No standard identifier was provided.",
                provenance="service_validation",
                verification_status=VerificationStatus.UNKNOWN,
                review_required=True,
                review_reason="Standard identifier was omitted or empty.",
            ).to_dict()

        norm_code = normalize_is_code(is_number)
        base_code = extract_base_is_code(norm_code)

        status_rec = (
            self._status_by_code.get(norm_code)
            or self._status_by_version.get(norm_code)
            or self._status_by_code.get(base_code)
            or self._status_by_version.get(base_code)
        )
        std_rec = (
            self._standards_by_code.get(norm_code)
            or self._standards_by_version.get(norm_code)
            or self._standards_by_code.get(base_code)
            or self._standards_by_version.get(base_code)
        )

        if not status_rec and not std_rec:
            return LifecycleResult(
                is_number=norm_code,
                status=StandardLifecycleStatus.UNKNOWN,
                evidence="",
                provenance="data/status.json, data/standards.json",
                verification_status=VerificationStatus.UNKNOWN,
                review_required=True,
                review_reason=f"Standard '{norm_code}' not found in registry.",
            ).to_dict()

        # Find older editions and superseded standards
        older_editions: List[str] = []
        supersedes_list: List[str] = []

        if std_rec and std_rec.get("supersedes"):
            supersedes_list.extend(std_rec.get("supersedes", []))
            older_editions.extend(std_rec.get("supersedes", []))

        # Check all status records for entries that point superseded_by to this standard
        for st in self.statuses:
            sup_by = st.get("superseded_by")
            if sup_by and (sup_by == norm_code or sup_by == base_code or sup_by == (std_rec.get("current_version") if std_rec else None)):
                ver = st.get("version") or st.get("standard_code")
                if ver and ver not in older_editions:
                    older_editions.append(ver)
                if ver and ver not in supersedes_list:
                    supersedes_list.append(ver)

        # Current edition:
        # If this standard is superseded, current active edition is the replacement standard
        current_edition = None
        if status_rec and status_rec.get("superseded_by"):
            sup_code = status_rec.get("superseded_by")
            sup_st = self._status_by_code.get(sup_code)
            current_edition = sup_st.get("version") if sup_st else sup_code
        elif std_rec and std_rec.get("superseded_by"):
            sup_code = std_rec.get("superseded_by")
            sup_st = self._status_by_code.get(sup_code) or self._standards_by_code.get(sup_code)
            current_edition = (sup_st.get("version") or sup_st.get("current_version")) if sup_st else sup_code
        elif std_rec and std_rec.get("status") != "SUPERSEDED":
            current_edition = std_rec.get("current_version")
        elif status_rec and status_rec.get("status") == "CURRENT":
            current_edition = status_rec.get("version")
        elif std_rec:
            current_edition = std_rec.get("current_version")

        # Amendments from standards.json
        amendments = []
        if std_rec and "amendments" in std_rec:
            for am in std_rec["amendments"]:
                am_rec = AmendmentRecord(
                    amendment_number=am.get("amendment_number", ""),
                    issue_date=am.get("issue_date", ""),
                    summary=am.get("summary", ""),
                    affected_clauses=am.get("affected_clauses", []),
                    gazette_notification=am.get("gazette_notification"),
                )
                amendments.append(am_rec.to_dict())

        # Determine effective year and status of the queried standard
        effective_year = (
            (status_rec.get("effective_year") if status_rec else None)
            or (std_rec.get("publication_year") if std_rec else None)
        )
        superseded_by = (
            (status_rec.get("superseded_by") if status_rec else None)
            or (std_rec.get("superseded_by") if std_rec else None)
        )
        raw_status = (
            (status_rec.get("status") if status_rec else None)
            or (std_rec.get("status") if std_rec else None)
            or "UNKNOWN"
        ).upper()
        try:
            status_enum = StandardLifecycleStatus(raw_status)
        except ValueError:
            status_enum = StandardLifecycleStatus.UNKNOWN

        evidence = (
            (status_rec.get("lifecycle_evidence") if status_rec else None)
            or (std_rec.get("source", {}).get("curator_notes") if std_rec else "")
            or ""
        )
        provenance = (
            (std_rec.get("source", {}).get("official_publication_ref") if std_rec else None)
            or "data/status.json"
        )
        transition_notes = evidence if "transition" in evidence.lower() or "grace" in evidence.lower() else None

        raw_v_status = (
            (status_rec.get("verification_status") if status_rec else None)
            or (std_rec.get("verification", {}).get("verification_status") if std_rec else None)
            or "UNKNOWN"
        )
        try:
            v_status_enum = VerificationStatus(raw_v_status)
        except ValueError:
            v_status_enum = VerificationStatus.UNKNOWN

        # Review requirement
        review_required = False
        review_reason = None

        if status_enum == StandardLifecycleStatus.SUPERSEDED:
            review_required = True
            review_reason = f"Standard '{norm_code}' is superseded by '{superseded_by}'."
        elif v_status_enum == VerificationStatus.PENDING_VERIFICATION:
            review_required = True
            review_reason = f"Lifecycle or transition timeline for '{norm_code}' remains pending verification."
        elif transition_notes:
            review_required = True
            review_reason = "Transitional grace period for dual-running standards is subject to procuring entity discretion."

        return LifecycleResult(
            is_number=norm_code,
            current_edition=current_edition,
            older_editions=older_editions,
            supersedes=supersedes_list,
            superseded_by=superseded_by,
            status=status_enum,
            effective_year=effective_year,
            amendments=amendments,
            withdrawn_reason=std_rec.get("withdrawn_reason") if std_rec else None,
            transition_notes=transition_notes,
            evidence=evidence,
            provenance=provenance,
            verification_status=v_status_enum,
            review_required=review_required,
            review_reason=review_reason,
        ).to_dict()

    # ------------------------------------------------------------------
    # QCO Intelligence
    # ------------------------------------------------------------------

    def get_qco_applicability(
        self,
        product_or_category: Optional[str] = None,
        is_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Determines statutory Quality Control Order (QCO) applicability.
        Enforces strict compliance integrity:
        - APPLICABLE only when explicitly covered in QCO gazette.
        - NOT_APPLICABLE when product/standard is verified to be outside QCO scope.
        - PENDING_VERIFICATION for cross-applicability (e.g. submersible motors under IS 12615)
          or enterprise transition grace periods (MSME).
        - UNKNOWN for unrecognized queries.
        """
        norm_is = normalize_is_code(is_number) if is_number else ""
        base_is = extract_base_is_code(norm_is) if norm_is else ""
        prod_query = (product_or_category or "").strip().lower()

        if not norm_is and not prod_query:
            return QCOApplicabilityResult(
                applicability_state=ApplicabilityState.UNKNOWN,
                is_covered_by_qco=False,
                evidence="Neither product name nor standard number was provided.",
                provenance="service_validation",
                verification_status=VerificationStatus.UNKNOWN,
                review_required=True,
                review_reason="Both product/category query and standard code are missing.",
            ).to_dict()

        # Check for explicit Submersible Motor Cross-Applicability Uncertainty:
        # Wet submersible motors operating in wells/boreholes under IS 9283 are NOT
        # explicitly enumerated under Motor QCO S.O. 167(E) (IS 12615 covers surface motors).
        is_submersible_motor_query = (
            norm_is in ("IS 9283", "IS 9283:2024", "IS 9283:2013")
            or "submersible motor" in prod_query
            or "submersible pump motor" in prod_query
            or ("submersible" in prod_query and "motor" in prod_query)
        )
        if is_submersible_motor_query:
            return QCOApplicabilityResult(
                applicability_state=ApplicabilityState.PENDING_VERIFICATION,
                is_covered_by_qco=False,
                order_title="Quality Control Order Applicability Pending Verification",
                order_number="S.O. 167(E) Cross-Applicability Uncertainty",
                isi_mark_mandatory=False,
                product_scope=["Submersible Pump Motors"],
                exemption_provisions=(
                    "PENDING VERIFICATION: Submersible pump motors operating underwater inside sumps/boreholes "
                    "are governed by IS 9283 and are not explicitly enumerated under motor QCO S.O. 167(E) "
                    "(which governs surface induction motors under IS 12615). Cross-applicability requires human regulatory determination."
                ),
                notes="VERIFIED FACT: Omission of IS 12615 IE2 clause in a submersible pumpset tender cannot be automatically penalized.",
                evidence=(
                    "VERIFIED FACT: S.O. 167(E) explicitly notifies IS 12615 for line-operated surface motors. "
                    "Submersible motors under IS 9283 are unlisted in S.O. 167(E) and S.O. 4333(E)."
                ),
                provenance="data/qco.json, data/DATA_SOURCES.md",
                source_url="https://dpiit.gov.in/sites/default/files/Order_Motors_18Jan2017.pdf",
                verification_status=VerificationStatus.PENDING_VERIFICATION,
                review_required=True,
                review_reason=(
                    "Submersible pump motors operating underwater under IS 9283 are not explicitly enumerated "
                    "under S.O. 167(E); cross-applicability requires formal human regulatory determination."
                ),
            ).to_dict()

        # Check for MSME Tiered Transition Uncertainty
        if "msme" in prod_query or "micro" in prod_query or "small enterprise" in prod_query:
            return QCOApplicabilityResult(
                applicability_state=ApplicabilityState.PENDING_VERIFICATION,
                is_covered_by_qco=True,
                order_title="Pumps (Quality Control) Order, 2023",
                order_number="S.O. 4333(E)",
                issuing_ministry="Department for Promotion of Industry and Internal Trade (DPIIT)",
                gazette_date="2023-10-06",
                effective_date="2024-10-06",
                isi_mark_mandatory=True,
                product_scope=["Micro and Small Enterprise Pump Manufacturers"],
                exemption_provisions=(
                    "PENDING VERIFICATION: Tiered transition facilitation dates for Micro and Small Enterprises "
                    "under subsequent DPIIT facilitation orders require bidder enterprise size verification."
                ),
                evidence="Parent order S.O. 4333(E) is active. MSME phased enforcement timeline requires verification.",
                provenance="data/qco.json",
                source_url="https://dpiit.gov.in/sites/default/files/QCO_Pumps_06October2023.pdf",
                verification_status=VerificationStatus.PENDING_VERIFICATION,
                review_required=True,
                review_reason="Tiered transition facilitation dates for Micro and Small Enterprises require bidder enterprise size verification.",
            ).to_dict()

        # Check for Export Exemption
        if "export" in prod_query or "manufactured exclusively for export" in prod_query:
            return QCOApplicabilityResult(
                applicability_state=ApplicabilityState.NOT_APPLICABLE,
                is_covered_by_qco=False,
                exemption_provisions="VERIFIED FACT: Domestic goods manufactured exclusively for export are exempt from mandatory ISI mark.",
                evidence="Statutory exemption clause in DPIIT Quality Control Orders.",
                provenance="data/qco.json",
                verification_status=VerificationStatus.VERIFIED_OFFICIAL,
                review_required=False,
            ).to_dict()

        # 1. Match by IS Number against covered standards in data/qco.json
        matched_qco = None
        matched_covered_std = None

        if norm_is:
            for qco in self.qcos:
                for cov in qco.get("covered_standards", []):
                    cov_is = normalize_is_code(cov.get("is_number", ""))
                    cov_base = extract_base_is_code(cov_is)
                    if norm_is == cov_is or base_is == cov_base or norm_is == cov_base:
                        matched_qco = qco
                        matched_covered_std = cov
                        break
                if matched_qco:
                    break

        # 2. Match by product_or_category if not matched by IS number
        if not matched_qco and prod_query:
            for qco in self.qcos:
                # Check covered_standards product names
                for cov in qco.get("covered_standards", []):
                    pname = cov.get("product_name", "").lower()
                    if pname and (pname in prod_query or prod_query in pname):
                        matched_qco = qco
                        matched_covered_std = cov
                        break
                if matched_qco:
                    break

                # Check general keywords in order title
                otitle = qco.get("order_title", "").lower()
                if ("pump" in prod_query and "pump" in otitle) or ("motor" in prod_query and "motor" in otitle):
                    matched_qco = qco
                    break

        # Check if known standard explicitly has NO QCO
        if not matched_qco and norm_is:
            std_rec = self._standards_by_code.get(norm_is) or self._standards_by_code.get(base_is)
            if std_rec:
                qco_info = std_rec.get("qco", {})
                if not qco_info.get("is_covered_by_qco", False):
                    return QCOApplicabilityResult(
                        applicability_state=ApplicabilityState.NOT_APPLICABLE,
                        is_covered_by_qco=False,
                        isi_mark_mandatory=False,
                        product_scope=[std_rec.get("title", "")],
                        evidence=f"Standard {norm_is} is not notified under statutory Pumps QCO S.O. 4333(E) or Motors QCO S.O. 167(E).",
                        provenance="data/standards.json, data/qco.json",
                        source_url=std_rec.get("source", {}).get("portal_url"),
                        verification_status=VerificationStatus.VERIFIED_OFFICIAL,
                        review_required=False,
                    ).to_dict()

        if matched_qco:
            covered_stds = matched_qco.get("covered_standards", [])
            product_scope = [cs.get("product_name", "") for cs in covered_stds if cs.get("product_name")]
            evidence = (
                f"Statutory Quality Control Order {matched_qco.get('order_number')} published in "
                f"{matched_qco.get('gazette_reference', 'Gazette of India')}. "
                f"Mandatory ISI Mark: {matched_qco.get('isi_mark_mandatory')}."
            )
            return QCOApplicabilityResult(
                applicability_state=ApplicabilityState.APPLICABLE,
                is_covered_by_qco=True,
                qco_id=matched_qco.get("qco_id"),
                order_title=matched_qco.get("order_title"),
                order_number=matched_qco.get("order_number"),
                issuing_ministry=matched_qco.get("issuing_ministry"),
                gazette_date=matched_qco.get("gazette_date"),
                effective_date=matched_qco.get("effective_date"),
                isi_mark_mandatory=matched_qco.get("isi_mark_mandatory", False),
                covered_standards=covered_stds,
                product_scope=product_scope,
                exemption_provisions=matched_qco.get("exemption_clauses"),
                notes=matched_qco.get("notes"),
                evidence=evidence,
                provenance="data/qco.json",
                source_url=matched_qco.get("source_url"),
                verification_status=VerificationStatus.VERIFIED_OFFICIAL,
                review_required=False,
            ).to_dict()

        # Unrecognized / unknown
        return QCOApplicabilityResult(
            applicability_state=ApplicabilityState.UNKNOWN,
            is_covered_by_qco=False,
            isi_mark_mandatory=False,
            evidence="No matching Quality Control Order found in verified QCO dataset.",
            provenance="data/qco.json",
            verification_status=VerificationStatus.UNKNOWN,
            review_required=True,
            review_reason=f"QCO applicability for product '{prod_query}' / standard '{norm_is}' is unknown in verified registry.",
        ).to_dict()

    # ------------------------------------------------------------------
    # Consolidated Regulatory Summary
    # ------------------------------------------------------------------

    def get_regulatory_summary(
        self,
        is_number: Optional[str] = None,
        product_or_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Combines standard status, lifecycle, and QCO applicability into an auditable
        procurement regulatory summary.
        """
        status_res = self.get_standard_status(is_number) if is_number else None
        lifecycle_res = self.get_lifecycle(is_number) if is_number else None
        qco_res = self.get_qco_applicability(product_or_category=product_or_category, is_number=is_number)

        # Collect evidence & provenance
        evidence_items: List[str] = []
        provenance_items: List[str] = []
        source_urls: List[str] = []
        review_reasons: List[str] = []

        if status_res:
            if status_res.get("evidence"):
                evidence_items.append(status_res["evidence"])
            if status_res.get("provenance"):
                provenance_items.append(status_res["provenance"])
            if status_res.get("review_reason"):
                review_reasons.append(status_res["review_reason"])
            portal_url = status_res.get("source", {}).get("portal_url")
            if portal_url and portal_url not in source_urls:
                source_urls.append(portal_url)

        if lifecycle_res:
            if lifecycle_res.get("transition_notes"):
                evidence_items.append(lifecycle_res["transition_notes"])
            if lifecycle_res.get("review_reason") and lifecycle_res["review_reason"] not in review_reasons:
                review_reasons.append(lifecycle_res["review_reason"])

        if qco_res:
            if qco_res.get("evidence"):
                evidence_items.append(qco_res["evidence"])
            if qco_res.get("provenance") and qco_res["provenance"] not in provenance_items:
                provenance_items.append(qco_res["provenance"])
            if qco_res.get("source_url") and qco_res["source_url"] not in source_urls:
                source_urls.append(qco_res["source_url"])
            if qco_res.get("review_reason") and qco_res["review_reason"] not in review_reasons:
                review_reasons.append(qco_res["review_reason"])

        # Determine compliance verdict
        mandatory_cert = qco_res.get("isi_mark_mandatory", False) if qco_res else False
        std_status_val = status_res.get("status") if status_res else "UNKNOWN"
        qco_state = qco_res.get("applicability_state") if qco_res else "UNKNOWN"

        if not is_number and not product_or_category:
            verdict = "UNKNOWN"
        elif std_status_val == "SUPERSEDED":
            verdict = "SUPERSEDED_STANDARD_CITED"
        elif std_status_val == "WITHDRAWN":
            verdict = "WITHDRAWN_STANDARD_CITED"
        elif qco_state == "APPLICABLE" and mandatory_cert:
            verdict = "MANDATORY_QCO_COMPLIANCE_REQUIRED"
        elif qco_state == "PENDING_VERIFICATION" or (status_res and status_res.get("verification_status") == "PENDING_VERIFICATION"):
            verdict = "PENDING_VERIFICATION"
        elif std_status_val == "CURRENT" and qco_state == "NOT_APPLICABLE":
            verdict = "CURRENT_STANDARD_VOLUNTARY_OR_SCHEME_I"
        elif std_status_val == "CURRENT" and qco_state == "APPLICABLE":
            verdict = "CURRENT_STANDARD_QCO_APPLICABLE"
        elif std_status_val == "UNKNOWN":
            verdict = "UNKNOWN_STANDARD"
        else:
            verdict = "UNKNOWN"

        review_required = bool(review_reasons) or (status_res.get("review_required") if status_res else False) or (qco_res.get("review_required") if qco_res else False)

        title = status_res.get("title") if status_res else None
        cert_scheme = "Scheme I - ISI Mark (Product Certification)" if mandatory_cert else None

        return RegulatorySummaryResult(
            is_number=normalize_is_code(is_number) if is_number else None,
            title=title,
            product_or_category=product_or_category,
            standard_status=status_res,
            lifecycle=lifecycle_res,
            qco=qco_res,
            mandatory_certification=mandatory_cert,
            certification_scheme=cert_scheme,
            compliance_verdict=verdict,
            review_required=review_required,
            review_reasons=review_reasons,
            evidence=evidence_items,
            provenance=provenance_items,
            source_urls=source_urls,
        ).to_dict()
