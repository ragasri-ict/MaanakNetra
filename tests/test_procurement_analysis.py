"""
Test Suite for MAANAKNETRA Procurement Analysis Orchestrator (Step 9B).

Focuses strictly on Step 9B integration:
1. Complete TenderAnalysisResultDocument structure conforming to contracts/analysis.schema.json.
2. Status flags accurately detect superseded standards.
3. all_standards_current must be False when zero standards are evaluated.
4. Certification flags accurately detect QCO applicability and omitted ISI clauses.
5. Outdated standard citation generates OUTDATED_STANDARD finding.
6. Omitted mandatory ISI mark generates MISSING_CERTIFICATION finding.
7. Findings use only allowed finding_types from contracts/finding.schema.json.
8. Standards BOM contains verified QCO mandate indicators.
9. Corrected clauses link to causal findings.
10. human_review_required accurately set.
"""

import os
import json
import pytest

from ai.procurement_analyzer import ProcurementAnalysisEngine, analyze_procurement_document


ALLOWED_FINDING_TYPES = {
    "OUTDATED_STANDARD",
    "WITHDRAWN_STANDARD",
    "MISSING_ALLIED_STANDARD",
    "MISSING_TEST_STANDARD",
    "MISSING_CERTIFICATION",
    "PARAMETER_CONFLICT",
    "VAGUE_REQUIREMENT",
    "OTHER",
}


@pytest.fixture(scope="module")
def analysis_engine():
    return ProcurementAnalysisEngine()


@pytest.fixture(scope="module")
def sample_analysis(analysis_engine):
    sample_pdf = os.path.join("demo", "sample_tender.pdf")
    assert os.path.exists(sample_pdf), "demo/sample_tender.pdf must exist"
    return analysis_engine.analyze(sample_pdf, top_k=5)


def test_1_analysis_pipeline_produces_all_required_schema_fields(sample_analysis):
    """Output document must contain all 13 required top-level fields of analysis.schema.json."""
    required_fields = [
        "tender_metadata",
        "extracted_requirements",
        "already_cited_standards",
        "recommended_standards",
        "related_standards",
        "graph_summary",
        "status_flags",
        "certification_flags",
        "findings",
        "standards_bom",
        "corrected_clause",
        "risk_indicator",
        "human_review_required",
    ]

    for field_name in required_fields:
        assert field_name in sample_analysis, f"Missing required analysis field: {field_name}"

    # Verify tender_metadata required fields
    meta = sample_analysis["tender_metadata"]
    assert "analysis_id" in meta
    assert "document_title" in meta
    assert "file_name" in meta
    assert "analyzed_at" in meta


def test_2_status_flags_accurately_detects_superseded_standards(sample_analysis):
    """Tender citing IS 14220:1994 must trigger has_superseded_standards and all_standards_current=False."""
    flags = sample_analysis["status_flags"]

    assert flags["has_superseded_standards"] is True
    assert flags["all_standards_current"] is False
    assert flags["superseded_count"] >= 1
    assert flags["has_withdrawn_standards"] is False


def test_3_all_standards_current_is_false_when_zero_standards_evaluated(analysis_engine):
    """all_standards_current must be False when zero standards are evaluated."""
    empty_doc = {
        "tender_metadata": {"file_name": "empty.pdf", "page_count": 1},
        "extracted_requirements": [],
        "already_cited_standards": [],
        "product_context": {},
    }

    result = analysis_engine.analyze(empty_doc, top_k=0)
    flags = result["status_flags"]

    assert flags["all_standards_current"] is False
    assert flags["superseded_count"] == 0
    assert flags["withdrawn_count"] == 0


def test_4_certification_flags_detects_qco_and_omitted_isi_mark(sample_analysis):
    """Openwell pumpset under QCO Pumps 2023 with omitted ISI mark must trigger qco_violation_risk."""
    cert = sample_analysis["certification_flags"]

    assert cert["qco_mandate_applicable"] is True
    assert cert["mandatory_isi_clause_present"] is False
    assert cert["qco_violation_risk"] is True
    assert len(cert["governing_qco_orders"]) >= 1

    qco_order = cert["governing_qco_orders"][0]
    assert qco_order["order_number"] == "S.O. 4333(E)"
    assert "Pumps (Quality Control) Order" in qco_order["order_name"]


def test_5_superseded_standard_generates_outdated_standard_finding(sample_analysis):
    """IS 14220:1994 must generate an OUTDATED_STANDARD finding pointing to IS 14220:2018."""
    findings = sample_analysis["findings"]
    outdated = [f for f in findings if f["finding_type"] == "OUTDATED_STANDARD"]

    assert len(outdated) >= 1
    find = outdated[0]
    assert find["severity"] == "HIGH"
    assert find["affected_standard"]["is_number"] == "IS 14220:1994"
    assert find["affected_standard"]["current_status"] == "SUPERSEDED"
    assert find["affected_standard"]["replacement_standard"] == "IS 14220:2018"
    assert find["source"]["source_type"] == "BIS_CATALOG"
    assert find["requires_human_review"] is True


def test_6_qco_violation_generates_missing_certification_finding(sample_analysis):
    """Mandatory QCO omission must generate a CRITICAL MISSING_CERTIFICATION finding."""
    findings = sample_analysis["findings"]
    missing_cert = [f for f in findings if f["finding_type"] == "MISSING_CERTIFICATION"]

    assert len(missing_cert) >= 1
    find = missing_cert[0]
    assert find["severity"] == "CRITICAL"
    assert find["source"]["source_type"] == "GAZETTE_QCO_ORDER"
    assert "S.O. 4333(E)" in find["evidence"]["qco_order_number"]
    assert find["requires_human_review"] is True


def test_7_findings_use_only_allowed_finding_types(sample_analysis):
    """Every generated finding must belong strictly to the finding.schema.json enum."""
    findings = sample_analysis["findings"]
    assert len(findings) >= 2

    for f in findings:
        f_type = f.get("finding_type")
        assert f_type in ALLOWED_FINDING_TYPES, f"Disallowed finding type found: {f_type}"
        assert "finding_id" in f
        assert "severity" in f
        assert "suggested_fix" in f
        assert "replacement_clause_text" in f["suggested_fix"]


def test_8_standards_bom_structure_and_qco_flags(sample_analysis):
    """Standards BOM must list primary standard with mandatory QCO indicator and outdated status."""
    bom = sample_analysis["standards_bom"]
    assert len(bom) >= 1

    primary_item = bom[0]
    assert primary_item["is_number"] == "IS 14220"
    assert primary_item["role"] == "PRIMARY_PRODUCT_STANDARD"
    assert primary_item["is_mandatory_qco"] is True
    assert primary_item["compliance_status"] == "CITED_BUT_OUTDATED"


def test_9_corrected_clauses_linked_to_findings(sample_analysis):
    """Corrected clauses must provide drop-in text and link to finding IDs."""
    corrections = sample_analysis["corrected_clause"]
    assert len(corrections) >= 2

    for corr in corrections:
        assert "clause_id" in corr
        assert "corrected_text" in corr
        assert len(corr["linked_finding_ids"]) > 0


def test_10_human_review_required_flag(sample_analysis):
    """human_review_required must be True when statutory or superseded discrepancies exist."""
    assert sample_analysis["human_review_required"] is True
    assert sample_analysis["risk_indicator"]["risk_level"] in ["CRITICAL", "HIGH"]
