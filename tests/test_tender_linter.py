"""
Test Suite for MAANAKNETRA Tender Linter (Step 10).

Covers all Mandatory Rules and Finding Requirements:
1. Rule 1: Superseded citation produces OUTDATED_STANDARD finding.
2. Rule 1: Withdrawn citation produces WITHDRAWN_STANDARD finding.
3. Rule 2: Missing normative / test reference produces MISSING_TEST_STANDARD finding.
4. Rule 3: Missing mandatory QCO / ISI mark produces MISSING_CERTIFICATION finding.
5. Rule 4: Vague specification phrasing produces VAGUE_REQUIREMENT finding.
6. Rule 5: Verified parameter conflict produces PARAMETER_CONFLICT with affected_requirement.
7. Rule 5: Unsupported parameter does NOT become a conflict.
8. Corrected clauses contain only supported facts without invented numbers.
9. Evidence and provenance are preserved across all findings.
10. All findings strictly adhere to contracts/finding.schema.json allowed enums.
11. Rule 6: Alternative current citation classified as OTHER (advisory), not fatal error.
12. End-to-end linting on demo/sample_tender.pdf.
"""

import os
import json
import pytest

from ai.regulatory_intelligence import RegulatoryIntelligenceService
from ai.tender_linter import (
    TenderLinter,
    FindingType,
    FindingSeverity,
    VAGUE_PATTERNS,
)
from ai.parameter_engine.compatibility import ParameterCompatibilityEngine


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

ALLOWED_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


@pytest.fixture(scope="module")
def linter():
    reg_svc = RegulatoryIntelligenceService(
        standards_path="data/standards.json",
        status_path="data/status.json",
        qco_path="data/qco.json",
    )
    with open("data/standards.json", "r", encoding="utf-8") as f:
        standards = json.load(f)
    standards_by_num = {s["is_number"]: s for s in standards}

    return TenderLinter(
        regulatory_service=reg_svc,
        standards_by_num=standards_by_num,
    )


def test_1_superseded_citation(linter):
    """Rule 1: Superseded citation (IS 14220:1994) produces OUTDATED_STANDARD with replacement."""
    cited = [{
        "raw_citation": "IS 14220:1994",
        "standard_code": "IS 14220",
        "year_cited": 1994,
        "verbatim_citation": "IS 14220:1994 Openwell Submersible Pumpsets",
        "clause_number": "Clause 4.1",
    }]

    findings, corrected = linter.lint(
        extracted_requirements=[],
        already_cited_standards=cited,
        product_context={"primary_item_name": "Openwell Submersible Pumpset"},
        primary_standard_id="IS 14220",
    )

    outdated = [f for f in findings if f["finding_type"] == "OUTDATED_STANDARD"]
    assert len(outdated) == 1
    f = outdated[0]

    assert f["severity"] == "HIGH"
    assert f["affected_standard"]["is_number"] == "IS 14220:1994"
    assert f["affected_standard"]["current_status"] == "SUPERSEDED"
    assert f["affected_standard"]["replacement_standard"] == "IS 14220:2018"
    assert f["source"]["source_type"] == "BIS_CATALOG"
    assert f["requires_human_review"] is True
    assert "IS 14220:2018" in f["suggested_fix"]["replacement_clause_text"]


def test_2_withdrawn_citation(linter):
    """Rule 1: Withdrawn citation produces WITHDRAWN_STANDARD finding."""
    # Test with standard marked WITHDRAWN
    linter.reg_service._status_by_code["IS 99999"] = {
        "standard_code": "IS 99999",
        "status": "WITHDRAWN",
        "withdrawn_reason": "Withdrawn by Sectional Committee without replacement.",
        "verification_status": "VERIFIED_OFFICIAL",
    }

    cited = [{
        "raw_citation": "IS 99999",
        "standard_code": "IS 99999",
        "verbatim_citation": "IS 99999 Obsolete Code",
        "clause_number": "Clause 1.2",
    }]

    findings, _ = linter.lint(
        extracted_requirements=[],
        already_cited_standards=cited,
        product_context={},
        primary_standard_id="IS 14220",
    )

    withdrawn = [f for f in findings if f["finding_type"] == "WITHDRAWN_STANDARD"]
    assert len(withdrawn) == 1
    f = withdrawn[0]
    assert f["severity"] == "CRITICAL"
    assert f["affected_standard"]["current_status"] == "WITHDRAWN"


def test_3_missing_normative_test_reference(linter):
    """Rule 2: Essential acceptance test standard (IS 11346) omitted from tender produces MISSING_TEST_STANDARD."""
    findings, corrected = linter.lint(
        extracted_requirements=[],
        already_cited_standards=[{"standard_code": "IS 14220", "raw_citation": "IS 14220"}],
        product_context={"primary_item_name": "Openwell Submersible Pumpset"},
        primary_standard_id="IS 14220",
        raw_tender_text="Equipment shall comply with IS 14220.",  # Omits IS 11346
    )

    missing_test = [f for f in findings if f["finding_type"] == "MISSING_TEST_STANDARD"]
    assert len(missing_test) >= 1
    is_11346_findings = [f for f in missing_test if "11346" in f["affected_standard"]["is_number"]]
    assert len(is_11346_findings) == 1

    f = is_11346_findings[0]
    assert f["severity"] == "MEDIUM"
    assert f["source"]["source_type"] == "STANDARDS_GRAPH"
    assert "IS 11346" in f["suggested_fix"]["replacement_clause_text"]


def test_4_missing_mandatory_qco_certification(linter):
    """Rule 3: Pumps QCO 2023 ISI mark requirement omitted produces MISSING_CERTIFICATION."""
    findings, corrected = linter.lint(
        extracted_requirements=[],
        already_cited_standards=[],
        product_context={"primary_item_name": "Openwell Submersible Pumpset"},
        primary_standard_id="IS 14220",
        raw_tender_text="The contractor shall deliver 150 units of openwell pumpsets.",  # No ISI mention
    )

    qco_findings = [f for f in findings if f["finding_type"] == "MISSING_CERTIFICATION"]
    assert len(qco_findings) == 1
    f = qco_findings[0]

    assert f["severity"] == "CRITICAL"
    assert f["source"]["source_type"] == "GAZETTE_QCO_ORDER"
    assert "S.O. 4333(E)" in f["evidence"]["qco_order_number"]
    assert f["requires_human_review"] is True


def test_5_vague_specification_phrase(linter):
    """Rule 4: Qualitative phrases like 'superior engineering workmanship' produce VAGUE_REQUIREMENT."""
    reqs = [
        {
            "requirement_id": "REQ_VAGUE_1",
            "parameter_name": "Workmanship",
            "source_text": "The entire assembly shall be manufactured with superior engineering workmanship and durable components.",
            "source_location": {"clause_number": "Clause 6.4"},
        },
        {
            "requirement_id": "REQ_VAGUE_2",
            "parameter_name": "Material Quality",
            "source_text": "All pump materials shall be of standard commercial grade and suitable for water contact.",
            "source_location": {"clause_number": "Clause 7.2"},
        },
    ]

    findings, corrected = linter.lint(
        extracted_requirements=reqs,
        already_cited_standards=[],
        product_context={"primary_item_name": "Openwell Submersible Pumpset"},
        primary_standard_id="IS 14220",
    )

    vague_findings = [f for f in findings if f["finding_type"] == "VAGUE_REQUIREMENT"]
    assert len(vague_findings) >= 2

    phrases = [f["title"] for f in vague_findings]
    assert any("superior engineering workmanship" in p for p in phrases)
    assert any("standard commercial grade" in p for p in phrases)

    for vf in vague_findings:
        assert vf["severity"] == "MEDIUM"
        assert vf["source"]["source_type"] == "DETERMINISTIC_RULE_ENGINE"
        assert vf["requires_human_review"] is True


def test_6_verified_parameter_conflict(linter):
    """Rule 5: Explicitly deviating parameter produces PARAMETER_CONFLICT with affected_requirement."""
    # IS 14220 rated power output scope is up to 45 kW.
    # Tender specifying 75 kW continuous rated output represents an explicit conflict.
    reqs = [{
        "requirement_id": "REQ_POWER_CONFLICT",
        "category": "POWER",
        "field": "Rated Power Output",
        "parameter_name": "Rated Power Output",
        "value": "75 kW",
        "unit": "kW",
        "normalized_value": {
            "numeric_value": 75.0,
            "unit": "kW",
            "operator": "EQUAL",
        },
        "source_text": "Rated continuous motor power output shall be 75 kW.",
        "source_location": {"clause_number": "Clause 3.2"},
    }]

    findings, corrected = linter.lint(
        extracted_requirements=reqs,
        already_cited_standards=[],
        product_context={"primary_item_name": "Openwell Submersible Pumpset"},
        primary_standard_id="IS 14220",
    )

    param_conflicts = [f for f in findings if f["finding_type"] == "PARAMETER_CONFLICT"]
    assert len(param_conflicts) >= 1
    f = param_conflicts[0]

    assert f["severity"] == "HIGH"
    assert f["affected_requirement"] is not None
    assert f["affected_requirement"]["requirement_id"] == "REQ_POWER_CONFLICT"
    assert f["source"]["source_type"] == "DETERMINISTIC_RULE_ENGINE"


def test_7_unsupported_parameter_does_not_become_conflict(linter):
    """Rule 5: Duty-point dependent efficiency or missing parameters must NOT become a PARAMETER_CONFLICT."""
    # Overall efficiency in IS 14220 Table 1 is dynamic and has min_value=null
    reqs = [{
        "requirement_id": "REQ_EFF_001",
        "category": "EFFICIENCY",
        "field": "Overall Efficiency",
        "parameter_name": "Overall Efficiency",
        "value": "48%",
        "unit": "%",
        "normalized_value": {
            "min_value": 48.0,
            "max_value": None,
            "numeric_value": 48.0,
            "unit": "%",
            "operator": "GREATER_THAN_OR_EQUAL",
        },
        "source_text": "Overall efficiency of the complete pumpset shall be not less than 48.0%.",
        "source_location": {"clause_number": "Clause 5.3"},
    }]

    findings, _ = linter.lint(
        extracted_requirements=reqs,
        already_cited_standards=[],
        product_context={"primary_item_name": "Openwell Submersible Pumpset"},
        primary_standard_id="IS 14220",
    )

    # Must NOT generate PARAMETER_CONFLICT for dynamic/unsupported efficiency limit
    eff_conflicts = [
        f for f in findings
        if f["finding_type"] == "PARAMETER_CONFLICT" and "Efficiency" in f["title"]
    ]
    assert len(eff_conflicts) == 0


def test_8_corrected_clause_contains_only_supported_facts(linter):
    """Corrected clauses must not invent speculative numbers and must link to causal findings."""
    cited = [{
        "raw_citation": "IS 14220:1994",
        "standard_code": "IS 14220",
        "year_cited": 1994,
        "verbatim_citation": "Conforms to IS 14220:1994",
        "clause_number": "Clause 4.1",
    }]

    findings, corrected_clauses = linter.lint(
        extracted_requirements=[],
        already_cited_standards=cited,
        product_context={"primary_item_name": "Openwell Submersible Pumpset"},
        primary_standard_id="IS 14220",
        raw_tender_text="Conforms to IS 14220:1994.",
    )

    assert len(corrected_clauses) >= 1
    for corr in corrected_clauses:
        assert "clause_id" in corr
        assert "corrected_text" in corr
        assert "rationale" in corr
        assert len(corr["linked_finding_ids"]) > 0
        # No placeholders or hallucinatory strings
        assert "TODO" not in corr["corrected_text"]
        assert "None" not in corr["corrected_text"]


def test_9_evidence_and_provenance_preserved(linter):
    """Every finding must preserve exact evidence, provenance, and rule_id."""
    findings, _ = linter.lint(
        extracted_requirements=[],
        already_cited_standards=[{"raw_citation": "IS 14220:1994", "standard_code": "IS 14220", "year_cited": 1994}],
        product_context={"primary_item_name": "Openwell Submersible Pumpset"},
        primary_standard_id="IS 14220",
    )

    for f in findings:
        assert "evidence" in f
        assert "factual_summary" in f["evidence"]
        assert "source" in f
        assert "source_type" in f["source"]
        assert "rule_id" in f["source"]
        assert len(f["source"]["rule_id"]) > 0


def test_10_schema_valid_output_and_allowed_enums(linter):
    """All findings must use only allowed finding_types and severities from finding.schema.json."""
    sample_pdf = os.path.join("demo", "sample_tender.pdf")
    from backend.ingestion import ingest_document
    from ai.requirement_extractor import extract_requirements

    doc = ingest_document(sample_pdf)
    reqs_doc = extract_requirements(doc)

    findings, corrected = linter.lint(
        extracted_requirements=reqs_doc.get("extracted_requirements", []),
        already_cited_standards=reqs_doc.get("already_cited_standards", []),
        product_context=reqs_doc.get("product_context", {}),
        primary_standard_id="IS 14220",
        raw_tender_text=doc.extracted_text,
    )

    assert len(findings) >= 3
    for f in findings:
        assert f["finding_type"] in ALLOWED_FINDING_TYPES
        assert f["severity"] in ALLOWED_SEVERITIES
        assert f["resolution_status"] in ["PENDING", "ACCEPTED", "REJECTED", "OVERRIDDEN"]
        assert "suggested_fix" in f
        assert "replacement_clause_text" in f["suggested_fix"]
        assert "recommended_action_summary" in f["suggested_fix"]


def test_11_alternative_current_standard_not_called_error(linter):
    """Rule 6: Active current standard citation differing from recommended is classified as OTHER advisory."""
    cited = [{
        "standard_code": "IS 9079",  # Monoset pump standard, active & current
        "verbatim_citation": "Pumps shall conform to IS 9079:2018.",
        "clause_number": "Clause 2.1",
    }]

    findings, _ = linter.lint(
        extracted_requirements=[],
        already_cited_standards=cited,
        product_context={"primary_item_name": "Openwell Submersible Pumpset"},
        primary_standard_id="IS 14220",  # Recommended is IS 14220
        raw_tender_text="Pumps shall conform to IS 9079:2018.",
    )

    alt_findings = [f for f in findings if f["finding_type"] == "OTHER"]
    assert len(alt_findings) == 1
    f = alt_findings[0]

    assert f["severity"] == "LOW"
    assert f["requires_human_review"] is True
    assert "IS 9079" in f["title"]
    assert "Alternative Current Standard" in f["title"]
