"""
MAANAKNETRA - Tender Linter Engine (Step 10)

Executes deterministic procurement compliance, specification quality, and regulatory audits:
- Rule 1: Cited IS is SUPERSEDED or WITHDRAWN (OUTDATED_STANDARD, WITHDRAWN_STANDARD)
- Rule 2: Relevant normative / test reference omitted from tender (MISSING_TEST_STANDARD, MISSING_ALLIED_STANDARD)
- Rule 3: Mandatory QCO / ISI mark omitted from tender (MISSING_CERTIFICATION)
- Rule 4: Vague / subjective specification phrasing (VAGUE_REQUIREMENT)
- Rule 5: Parameter conflicts with verified standard data (PARAMETER_CONFLICT)
- Rule 6: Alternative current standard citation (OTHER)

Produces schema-compliant findings strictly adhering to contracts/finding.schema.json.
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple, Set

from ai.regulatory_intelligence import (
    RegulatoryIntelligenceService,
    normalize_is_code,
    extract_base_is_code,
)
from ai.parameter_engine.compatibility import ParameterCompatibilityEngine
from ai.standards_graph.graph_queries import StandardsGraphQueryEngine
from .rules import (
    LinterFinding,
    FindingType,
    FindingSeverity,
    SourceType,
    ResolutionStatus,
    VAGUE_PATTERNS,
)


class TenderLinter:
    """
    Deterministic rule-based compliance and quality linter for procurement documents.
    """

    def __init__(
        self,
        regulatory_service: RegulatoryIntelligenceService,
        standards_by_num: Dict[str, Dict[str, Any]],
        graph_query: Optional[StandardsGraphQueryEngine] = None,
        parameter_engine: Optional[ParameterCompatibilityEngine] = None,
    ):
        self.reg_service = regulatory_service
        self.standards_by_num = standards_by_num
        self.graph_query = graph_query
        self.param_engine = parameter_engine or ParameterCompatibilityEngine()

    def lint(
        self,
        extracted_requirements: List[Dict[str, Any]],
        already_cited_standards: List[Dict[str, Any]],
        product_context: Dict[str, Any],
        primary_standard_id: Optional[str] = None,
        raw_tender_text: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Runs all linter rules and returns:
        (findings_list, corrected_clauses_list)
        """
        findings: List[Dict[str, Any]] = []
        corrected_clauses: List[Dict[str, Any]] = []

        primary_is = primary_standard_id or "IS 14220"
        primary_std_rec = self.standards_by_num.get(primary_is, {})

        # Collect all tender text for keyword matching
        text_snippets = []
        if raw_tender_text:
            text_snippets.append(raw_tender_text)
        for req in extracted_requirements:
            text_snippets.append(req.get("source_text", ""))
        for cit in already_cited_standards:
            text_snippets.append(cit.get("verbatim_citation", ""))
            text_snippets.append(cit.get("source_text", ""))
        full_tender_text = " ".join(filter(None, text_snippets))

        # ------------------------------------------------------------------
        # Rule 1: Cited IS is SUPERSEDED or WITHDRAWN
        # ------------------------------------------------------------------
        for cited in already_cited_standards:
            raw_cite = cited.get("raw_citation")
            code = cited.get("standard_code", "")
            year_cited = cited.get("year_cited")
            verbatim = cited.get("verbatim_citation") or cited.get("source_text") or f"Governing Standard: {code}"
            clause_ref = (
                cited.get("clause_number")
                or cited.get("clause_reference")
                or (f"Page {cited['source_page']}" if cited.get("source_page") else None)
            )

            full_code = raw_cite or (f"{code}:{year_cited}" if year_cited else code)
            if not full_code:
                continue

            status_res = self.reg_service.get_standard_status(full_code)
            st_val = status_res.get("status")

            if st_val == "SUPERSEDED":
                rep_std = status_res.get("superseded_by") or "active revision"
                find_id = f"FIND_SUPERSEDED_{full_code.replace(' ', '_').replace(':', '_')}"

                finding = LinterFinding(
                    finding_id=find_id,
                    severity=FindingSeverity.HIGH,
                    finding_type=FindingType.OUTDATED_STANDARD,
                    title=f"Superseded Indian Standard Cited: {full_code}",
                    tender_text=verbatim,
                    affected_standard={
                        "is_number": full_code,
                        "version_cited": str(year_cited) if year_cited else cited.get("edition_or_year"),
                        "current_status": "SUPERSEDED",
                        "replacement_standard": rep_std,
                    },
                    explanation=(
                        f"The tender cites '{full_code}', which has been officially superseded by '{rep_std}'. "
                        f"Procurement specifications citing obsolete standard editions violate public procurement rules "
                        f"and lead to rejection during technical and audit inspections."
                    ),
                    evidence={
                        "standard_clause_reference": clause_ref,
                        "factual_summary": status_res.get("evidence", "Superseded edition identified in official BIS catalog."),
                    },
                    source={
                        "source_type": SourceType.BIS_CATALOG.value,
                        "rule_id": f"RULE_SUPERSEDED_{full_code.replace(' ', '_').replace(':', '_')}",
                        "official_url": status_res.get("source", {}).get("portal_url"),
                    },
                    suggested_fix={
                        "replacement_clause_text": f"The equipment shall strictly comply with active Indian Standard {rep_std}.",
                        "recommended_action_summary": f"Replace obsolete reference '{full_code}' with active standard '{rep_std}'.",
                    },
                    confidence=1.0,
                    requires_human_review=True,
                    resolution_status=ResolutionStatus.PENDING,
                )
                findings.append(finding.to_dict())

                corr_id = f"CORR_{len(corrected_clauses) + 1:03d}"
                corrected_clauses.append({
                    "clause_id": corr_id,
                    "source_clause_reference": clause_ref or "Section 4: Governing Standards",
                    "original_tender_text": verbatim,
                    "corrected_text": f"The equipment shall strictly comply with the design, manufacturing, and performance requirements of {rep_std}.",
                    "rationale": f"Replaces superseded {full_code} with active revision {rep_std} as confirmed in official BIS Product Manual.",
                    "governing_rules": [f"RULE_SUPERSEDED_{full_code.replace(' ', '_')}"],
                    "linked_finding_ids": [find_id],
                })

            elif st_val == "WITHDRAWN":
                find_id = f"FIND_WITHDRAWN_{full_code.replace(' ', '_').replace(':', '_')}"
                finding = LinterFinding(
                    finding_id=find_id,
                    severity=FindingSeverity.CRITICAL,
                    finding_type=FindingType.WITHDRAWN_STANDARD,
                    title=f"Withdrawn Standard Cited: {full_code}",
                    tender_text=verbatim,
                    affected_standard={
                        "is_number": full_code,
                        "current_status": "WITHDRAWN",
                    },
                    explanation=f"The standard '{full_code}' cited in the tender has been officially withdrawn.",
                    evidence={
                        "standard_clause_reference": clause_ref,
                        "factual_summary": status_res.get("withdrawn_reason") or "Standard officially withdrawn by BIS.",
                    },
                    source={
                        "source_type": SourceType.BIS_CATALOG.value,
                        "rule_id": f"RULE_WITHDRAWN_{full_code.replace(' ', '_').replace(':', '_')}",
                    },
                    suggested_fix={
                        "replacement_clause_text": "Update the specification to remove or replace the withdrawn standard.",
                        "recommended_action_summary": "Remove citation of withdrawn standard.",
                    },
                    confidence=1.0,
                    requires_human_review=True,
                    resolution_status=ResolutionStatus.PENDING,
                )
                findings.append(finding.to_dict())

        # ------------------------------------------------------------------
        # Rule 2: Relevant Normative / Test / Safety Reference Omitted
        # ------------------------------------------------------------------
        # Test standards required by governing standard (e.g. IS 11346 for pumpsets)
        test_standards = primary_std_rec.get("test_standards", [])
        for t_code in test_standards:
            # Check if t_code is cited or mentioned in full tender text
            if t_code.lower() not in full_tender_text.lower():
                t_clean = t_code.replace(" ", "_")
                find_id = f"FIND_MISSING_TEST_{t_clean}"
                t_std_rec = self.standards_by_num.get(t_code, {})
                t_title = t_std_rec.get("title", f"Test Standard {t_code}")

                finding = LinterFinding(
                    finding_id=find_id,
                    severity=FindingSeverity.MEDIUM,
                    finding_type=FindingType.MISSING_TEST_STANDARD,
                    title=f"Standard-Required Acceptance Test Standard Omitted: {t_code}",
                    tender_text="Section 7: Quality Assurance & Inspection (Test method standard absent)",
                    affected_standard={
                        "is_number": t_code,
                        "current_status": "CURRENT",
                    },
                    explanation=(
                        f"The governing product standard {primary_is} explicitly stipulates that hydraulic performance, "
                        f"tolerances, and acceptance tests shall be conducted in accordance with {t_code} ({t_title}). "
                        f"Omitting this standard leaves test methodologies and tolerance bands legally unanchored."
                    ),
                    evidence={
                        "standard_clause_reference": f"{primary_is} Clause 9.1 & Clause 13",
                        "factual_summary": f"Standard {primary_is} requires testing according to {t_code}. Absent from tender.",
                    },
                    source={
                        "source_type": SourceType.STANDARDS_GRAPH.value,
                        "rule_id": f"RULE_MISSING_TEST_{t_clean}",
                        "official_url": t_std_rec.get("source", {}).get("portal_url"),
                    },
                    suggested_fix={
                        "replacement_clause_text": f"Performance and hydrostatic testing shall be conducted strictly in accordance with {t_code}.",
                        "recommended_action_summary": f"Incorporate standard-required test method {t_code} into inspection clauses.",
                    },
                    confidence=1.0,
                    requires_human_review=False,
                    resolution_status=ResolutionStatus.PENDING,
                )
                findings.append(finding.to_dict())

                corr_id = f"CORR_{len(corrected_clauses) + 1:03d}"
                corrected_clauses.append({
                    "clause_id": corr_id,
                    "source_clause_reference": "Section 7: Quality Assurance & Inspection (Clause 7.1)",
                    "original_tender_text": "Manufacturer must furnish internal routine test certificates... before dispatch.",
                    "corrected_text": (
                        f"Manufacturer must furnish test certificates strictly complying with {t_code} "
                        f"acceptance testing protocols, covering head-discharge, overall efficiency, and hydrostatic pressure characteristics."
                    ),
                    "rationale": f"Explicitly anchors factory and site acceptance testing to {t_code} as required by {primary_is}.",
                    "governing_rules": [f"RULE_MISSING_TEST_{t_clean}"],
                    "linked_finding_ids": [find_id],
                })

        # ------------------------------------------------------------------
        # Rule 3: Mandatory QCO / ISI Mark Requirement Omitted
        # ------------------------------------------------------------------
        primary_item = product_context.get("primary_item_name", "")
        primary_cat = product_context.get("category", "")
        qco_res = self.reg_service.get_qco_applicability(
            product_or_category=primary_item or primary_cat,
            is_number=primary_is,
        )

        qco_applicable = (
            qco_res.get("applicability_state") == "APPLICABLE"
            and qco_res.get("is_covered_by_qco", False)
            and qco_res.get("isi_mark_mandatory", False)
        )

        isi_patterns = [
            r"\bisi\b",
            r"\bbis\s+mark\b",
            r"\bstandard\s+mark\b",
            r"\bscheme\s+i\b",
            r"\bcompulsory\s+registration\b",
        ]
        has_isi_clause = any(
            re.search(pat, full_tender_text, re.IGNORECASE) is not None for pat in isi_patterns
        )

        if qco_applicable and not has_isi_clause:
            qco_id = qco_res.get("qco_id", "QCO_PUMPS_2023")
            find_id = f"FIND_QCO_MISSING_{qco_id}"

            finding = LinterFinding(
                finding_id=find_id,
                severity=FindingSeverity.CRITICAL,
                finding_type=FindingType.MISSING_CERTIFICATION,
                title=f"Mandatory BIS ISI Mark Omitted under {qco_res.get('order_title')}",
                tender_text="The tender specification does not stipulate mandatory BIS Standard Mark (ISI mark) licensing for the equipment.",
                affected_standard={
                    "is_number": primary_is,
                    "current_status": "CURRENT",
                },
                explanation=(
                    f"Under statutory order {qco_res.get('order_number')} ({qco_res.get('order_title')}) "
                    f"issued by the {qco_res.get('issuing_ministry')}, it is legally mandatory that goods "
                    f"cannot be manufactured, imported, or procured without a valid BIS Standard Mark (ISI mark) under Scheme I. "
                    f"Omitting this requirement creates legal non-compliance and permits uncertified equipment."
                ),
                evidence={
                    "factual_summary": qco_res.get("evidence", "Statutory QCO mandates ISI mark."),
                    "qco_order_number": qco_res.get("order_number"),
                    "gazette_date": qco_res.get("gazette_date"),
                },
                source={
                    "source_type": SourceType.GAZETTE_QCO_ORDER.value,
                    "rule_id": f"RULE_QCO_{qco_id}",
                    "official_url": qco_res.get("source_url"),
                },
                suggested_fix={
                    "replacement_clause_text": (
                        f"Bidders must possess a valid Bureau of Indian Standards (BIS) Standard Mark (ISI mark) license "
                        f"under Scheme I of BIS (Conformity Assessment) Regulations 2018 for {primary_is} "
                        f"as mandated by {qco_res.get('order_title')}."
                    ),
                    "recommended_action_summary": "Mandate compulsory BIS ISI certification in technical eligibility and delivery terms.",
                },
                confidence=1.0,
                requires_human_review=True,
                resolution_status=ResolutionStatus.PENDING,
            )
            findings.append(finding.to_dict())

            corr_id = f"CORR_{len(corrected_clauses) + 1:03d}"
            corrected_clauses.append({
                "clause_id": corr_id,
                "source_clause_reference": "Quality Assurance & Certification Clause",
                "original_tender_text": "[Mandatory BIS ISI Mark Certification Clause Omitted in Original Tender]",
                "corrected_text": (
                    f"The contractor must possess a valid BIS Standard Mark (ISI mark) license under Scheme I "
                    f"for {primary_is} as mandated by {qco_res.get('order_title')} ({qco_res.get('order_number')}). "
                    f"Tenders lacking verified BIS license certificates shall be summarily rejected."
                ),
                "rationale": f"Enforces compliance with statutory Quality Control Order {qco_res.get('order_number')} effective {qco_res.get('effective_date')}.",
                "governing_rules": [f"RULE_QCO_{qco_id}"],
                "linked_finding_ids": [find_id],
            })

        # ------------------------------------------------------------------
        # Rule 4: Vague Procurement Language
        # ------------------------------------------------------------------
        seen_vague_phrases: Set[str] = set()

        for vague_def in VAGUE_PATTERNS:
            phrase = vague_def["phrase"]
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)

            # Search in extracted requirements or text
            matching_req = None
            for req in extracted_requirements:
                req_text = req.get("source_text", "")
                if pattern.search(req_text):
                    matching_req = req
                    break

            if pattern.search(full_tender_text) and phrase not in seen_vague_phrases:
                seen_vague_phrases.add(phrase)
                phrase_slug = phrase.replace(" ", "_")
                find_id = f"FIND_VAGUE_{phrase_slug[:30]}"

                matched_text = matching_req.get("source_text") if matching_req else f"Specification contains phrase: '{phrase}'"
                clause_loc = (
                    matching_req.get("source_location", {}).get("clause_number")
                    if matching_req
                    else "Specification Clause"
                )

                finding = LinterFinding(
                    finding_id=find_id,
                    severity=FindingSeverity.MEDIUM,
                    finding_type=FindingType.VAGUE_REQUIREMENT,
                    title=f"Ambiguous / Qualitative Specification Phrase: '{phrase}'",
                    tender_text=matched_text,
                    affected_standard={
                        "is_number": primary_is,
                        "current_status": "CURRENT",
                    },
                    explanation=(
                        f"The clause uses the unquantified phrase '{phrase}'. Subjective specification language "
                        f"creates audit ambiguity, prevents objective lab testing, and can lead to supplier disputes."
                    ),
                    evidence={
                        "standard_clause_reference": clause_loc,
                        "factual_summary": f"Unquantified qualitative requirement '{phrase}' without objective standard reference.",
                    },
                    source={
                        "source_type": SourceType.DETERMINISTIC_RULE_ENGINE.value,
                        "rule_id": f"RULE_VAGUE_{phrase_slug[:30]}",
                    },
                    suggested_fix={
                        "replacement_clause_text": f"[Draft Replacement]: Replace '{phrase}' with explicit parameters per {vague_def['guidance']}.",
                        "recommended_action_summary": f"Replace ambiguous phrasing with quantifiable requirements ({vague_def['guidance']}).",
                    },
                    confidence=0.95,
                    requires_human_review=True,
                    resolution_status=ResolutionStatus.PENDING,
                    affected_requirement={
                        "requirement_id": matching_req.get("requirement_id") if matching_req else None,
                        "parameter_name": matching_req.get("parameter_name") if matching_req else f"{vague_def['category']} Requirement",
                        "tender_clause": clause_loc,
                    } if matching_req else None,
                )
                findings.append(finding.to_dict())

                corr_id = f"CORR_{len(corrected_clauses) + 1:03d}"
                corrected_clauses.append({
                    "clause_id": corr_id,
                    "source_clause_reference": clause_loc or "Technical Specifications",
                    "original_tender_text": matched_text,
                    "corrected_text": f"[Corrected Draft]: {vague_def['guidance']}",
                    "rationale": f"Replaces ambiguous phrase '{phrase}' with objective BIS criteria.",
                    "governing_rules": [f"RULE_VAGUE_{phrase_slug[:30]}"],
                    "linked_finding_ids": [find_id],
                })

        # ------------------------------------------------------------------
        # Rule 5: Tender Parameter Explicitly Conflicts with Verified Standard
        # ------------------------------------------------------------------
        compat_eval = self.param_engine.evaluate_standard_compatibility(
            standard=primary_std_rec,
            extracted_requirements=extracted_requirements,
            product_context=product_context,
        )

        conflicts = compat_eval.get("conflicting_requirements", [])
        for conf in conflicts:
            p_name = conf.get("parameter_name", "")
            t_val = conf.get("tender_value", "")
            ev_str = conf.get("evidence", "")
            gov_clause = conf.get("governing_clause", "")
            req_id = conf.get("requirement_id", "REQ_PARAM")

            p_slug = p_name.replace(" ", "_")
            find_id = f"FIND_PARAM_CONFLICT_{p_slug}"

            finding = LinterFinding(
                finding_id=find_id,
                severity=FindingSeverity.HIGH,
                finding_type=FindingType.PARAMETER_CONFLICT,
                title=f"Parameter Specification Conflict: {p_name}",
                tender_text=f"Tender stipulates {p_name} = {t_val}",
                affected_standard={
                    "is_number": primary_is,
                    "current_status": "CURRENT",
                },
                explanation=(
                    f"Tender specification for '{p_name}' ({t_val}) explicitly conflicts with {primary_is} "
                    f"prescribed limits ({ev_str})."
                ),
                evidence={
                    "standard_clause_reference": gov_clause,
                    "factual_summary": ev_str,
                },
                source={
                    "source_type": SourceType.DETERMINISTIC_RULE_ENGINE.value,
                    "rule_id": f"RULE_PARAM_CONFLICT_{p_slug}",
                },
                suggested_fix={
                    "replacement_clause_text": f"{p_name} shall comply strictly with {primary_is} {gov_clause}: {ev_str}.",
                    "recommended_action_summary": f"Align tender parameter '{p_name}' with verified standard limits.",
                },
                confidence=1.0,
                requires_human_review=True,
                resolution_status=ResolutionStatus.PENDING,
                affected_requirement={
                    "requirement_id": req_id,
                    "parameter_name": p_name,
                    "tender_clause": gov_clause,
                },
            )
            findings.append(finding.to_dict())

            corr_id = f"CORR_{len(corrected_clauses) + 1:03d}"
            corrected_clauses.append({
                "clause_id": corr_id,
                "source_clause_reference": gov_clause or "Technical Parameter Clause",
                "original_tender_text": f"Specified {p_name}: {t_val}",
                "corrected_text": f"{p_name} shall be manufactured and tested strictly to comply with {primary_is} {gov_clause}.",
                "rationale": f"Resolves explicit conflict with verified limit in {primary_is}.",
                "governing_rules": [f"RULE_PARAM_CONFLICT_{p_slug}"],
                "linked_finding_ids": [find_id],
            })

        # ------------------------------------------------------------------
        # Rule 6: Tender Citation is Current but Differs from Recommended
        # ------------------------------------------------------------------
        for cited in already_cited_standards:
            code = cited.get("standard_code", "")
            base_cited = extract_base_is_code(code)
            base_primary = extract_base_is_code(primary_is)

            if base_cited and base_primary and base_cited != base_primary:
                status_res = self.reg_service.get_standard_status(code)
                # If current and not superseded
                if status_res.get("status") == "CURRENT":
                    find_id = f"FIND_ALT_CURRENT_{base_cited.replace(' ', '_')}"
                    finding = LinterFinding(
                        finding_id=find_id,
                        severity=FindingSeverity.LOW,
                        finding_type=FindingType.OTHER,
                        title=f"Alternative Current Standard Cited: {code}",
                        tender_text=cited.get("verbatim_citation") or f"Governing Standard: {code}",
                        affected_standard={
                            "is_number": code,
                            "current_status": "CURRENT",
                        },
                        explanation=(
                            f"The tender cites '{code}', which is active and current. However, hybrid retrieval and "
                            f"technical requirements indicate that '{primary_is}' represents the primary specification "
                            f"for {product_context.get('primary_item_name', 'the equipment')}. Officer review is recommended."
                        ),
                        evidence={
                            "standard_clause_reference": cited.get("clause_number"),
                            "factual_summary": f"Standard {code} is active, but {primary_is} was identified as the closest technical match.",
                        },
                        source={
                            "source_type": SourceType.DETERMINISTIC_RULE_ENGINE.value,
                            "rule_id": f"RULE_ALT_CURRENT_{base_cited.replace(' ', '_')}",
                            "official_url": status_res.get("source", {}).get("portal_url"),
                        },
                        suggested_fix={
                            "replacement_clause_text": f"Verify whether procurement scope is intended for {code} or {primary_is}.",
                            "recommended_action_summary": f"Officer advisory: Check suitability between {code} and {primary_is}.",
                        },
                        confidence=0.85,
                        requires_human_review=True,
                        resolution_status=ResolutionStatus.PENDING,
                    )
                    findings.append(finding.to_dict())

        return findings, corrected_clauses


def lint_tender_document(
    extracted_requirements: List[Dict[str, Any]],
    already_cited_standards: List[Dict[str, Any]],
    product_context: Dict[str, Any],
    primary_standard_id: Optional[str] = None,
    regulatory_service: Optional[RegulatoryIntelligenceService] = None,
    standards_path: str = "data/standards.json",
    raw_tender_text: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Convenience helper to run the tender linter."""
    reg_svc = regulatory_service or RegulatoryIntelligenceService(standards_path=standards_path)
    with open(standards_path, "r", encoding="utf-8") as f:
        standards = json.load(f)
    standards_by_num = {s["is_number"]: s for s in standards}

    linter = TenderLinter(
        regulatory_service=reg_svc,
        standards_by_num=standards_by_num,
    )
    return linter.lint(
        extracted_requirements=extracted_requirements,
        already_cited_standards=already_cited_standards,
        product_context=product_context,
        primary_standard_id=primary_standard_id,
        raw_tender_text=raw_tender_text,
    )
