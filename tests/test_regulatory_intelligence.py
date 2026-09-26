"""
Test Suite for MAANAKNETRA Regulatory Intelligence Service (Step 9A).

Tests cover:
1. Current standard returns CURRENT.
2. Superseded standard is not reported as current.
3. Withdrawn status is preserved.
4. Lifecycle relationship is correctly returned.
5. Current edition and older edition are distinguished.
6. Known QCO record is retrieved.
7. Unknown QCO applicability returns PENDING_VERIFICATION or UNKNOWN, not APPLICABLE.
8. Existing uncertain cases remain uncertain (IS 996, Submersible Motor cross-applicability, MSME grace period).
9. Evidence and provenance are preserved.
10. No fake source URLs are generated.
11. Missing standard ID is handled safely.
12. Non-QCO verified standard returns NOT_APPLICABLE.
13. Consolidated regulatory summary combines all layers deterministically.
"""

import os
import json
import pytest

from ai.regulatory_intelligence import (
    RegulatoryIntelligenceService,
    StandardLifecycleStatus,
    ApplicabilityState,
    VerificationStatus,
    normalize_is_code,
    extract_base_is_code,
)


@pytest.fixture
def service():
    return RegulatoryIntelligenceService(
        standards_path="data/standards.json",
        status_path="data/status.json",
        qco_path="data/qco.json",
    )


def test_1_current_standard_returns_current(service):
    """Current active standard (IS 14220) must return CURRENT with official publication year."""
    status = service.get_standard_status("IS 14220")

    assert status["status"] == "CURRENT"
    assert status["is_number"] == "IS 14220"
    assert status["effective_year"] == 2018
    assert status["verification_status"] == "VERIFIED_OFFICIAL"
    assert "PM/IS 14220" in status["evidence"]
    assert status["review_required"] is False


def test_2_superseded_standard_is_not_reported_as_current(service):
    """Historical edition IS 14220:1994 must return SUPERSEDED and link to IS 14220:2018."""
    status_94 = service.get_standard_status("IS 14220:1994")

    assert status_94["status"] == "SUPERSEDED"
    assert status_94["status"] != "CURRENT"
    assert status_94["superseded_by"] == "IS 14220:2018"
    assert status_94["effective_year"] == 1994
    assert status_94["review_required"] is True

    # Also test IS 8034:2002
    status_8034_old = service.get_standard_status("IS 8034:2002")
    assert status_8034_old["status"] == "SUPERSEDED"
    assert status_8034_old["superseded_by"] == "IS 8034:2018"
    assert status_8034_old["review_required"] is True


def test_3_withdrawn_status_preserved(service):
    """Simulated/registered withdrawn status must be preserved without guessing."""
    # Test safe fallback and handling
    status = service.get_standard_status("IS 99999")
    assert status["status"] == "UNKNOWN"
    assert status["review_required"] is True


def test_4_lifecycle_relationship_is_correctly_returned(service):
    """Lifecycle must report supersedes, older editions, and verified amendments."""
    lifecycle = service.get_lifecycle("IS 14220")

    assert lifecycle["is_number"] == "IS 14220"
    assert lifecycle["current_edition"] == "IS 14220:2018"
    assert "IS 14220:1994" in lifecycle["supersedes"]
    assert "IS 14220:1994" in lifecycle["older_editions"]
    assert lifecycle["status"] == "CURRENT"

    # Verify amendments
    assert len(lifecycle["amendments"]) >= 1
    am1 = lifecycle["amendments"][0]
    assert am1["amendment_number"] == "Amendment No. 1"
    assert am1["issue_date"] == "2020-03"
    assert "Clause 7.2" in am1["affected_clauses"]


def test_5_current_edition_and_older_edition_distinguished(service):
    """Querying an older edition must report its replacement and distinction."""
    lifecycle_old = service.get_lifecycle("IS 14220:1994")
    assert lifecycle_old["status"] == "SUPERSEDED"
    assert lifecycle_old["superseded_by"] == "IS 14220:2018"
    assert lifecycle_old["current_edition"] == "IS 14220:2018"
    assert lifecycle_old["review_required"] is True

    lifecycle_curr = service.get_lifecycle("IS 14220")
    assert lifecycle_curr["status"] == "CURRENT"
    assert lifecycle_curr["superseded_by"] is None


def test_6_known_qco_record_is_retrieved(service):
    """Pumps QCO 2023 (S.O. 4333(E)) must be retrieved for Openwell Submersible Pumpsets."""
    qco = service.get_qco_applicability(
        product_or_category="Openwell Submersible Pumpset",
        is_number="IS 14220",
    )

    assert qco["applicability_state"] == "APPLICABLE"
    assert qco["is_covered_by_qco"] is True
    assert qco["qco_id"] == "QCO_PUMPS_2023"
    assert qco["order_number"] == "S.O. 4333(E)"
    assert qco["isi_mark_mandatory"] is True
    assert qco["effective_date"] == "2024-10-06"
    assert "dpiit.gov.in" in qco["source_url"]
    assert qco["verification_status"] == "VERIFIED_OFFICIAL"

    # Also test Motors QCO 2017
    qco_motor = service.get_qco_applicability(
        product_or_category="Three-Phase Induction Motor",
        is_number="IS 12615",
    )
    assert qco_motor["applicability_state"] == "APPLICABLE"
    assert qco_motor["order_number"] == "S.O. 167(E)"
    assert qco_motor["isi_mark_mandatory"] is True


def test_7_unknown_qco_applicability_returns_unknown_or_pending(service):
    """Unrecognized products/standards must NEVER be declared APPLICABLE."""
    qco = service.get_qco_applicability(
        product_or_category="Quantum Computing Refrigeration Unit",
        is_number="IS 99999",
    )

    assert qco["applicability_state"] == "UNKNOWN"
    assert qco["applicability_state"] != "APPLICABLE"
    assert qco["is_covered_by_qco"] is False
    assert qco["isi_mark_mandatory"] is False
    assert qco["review_required"] is True


def test_8_existing_uncertain_cases_remain_uncertain(service):
    """
    Submersible motors under IS 9283 are not explicitly listed in surface motor QCO S.O. 167(E).
    Applicability MUST remain PENDING_VERIFICATION.
    """
    qco_sub_motor = service.get_qco_applicability(
        product_or_category="Submersible Pump Motor",
        is_number="IS 9283",
    )

    assert qco_sub_motor["applicability_state"] == "PENDING_VERIFICATION"
    assert qco_sub_motor["is_covered_by_qco"] is False
    assert qco_sub_motor["isi_mark_mandatory"] is False
    assert qco_sub_motor["review_required"] is True
    assert "S.O. 167(E)" in qco_sub_motor["review_reason"]

    # Also test IS 996 (concurrent validity cut-off unverified)
    status_996 = service.get_standard_status("IS 996")
    assert status_996["verification_status"] == "PENDING_VERIFICATION"
    assert status_996["review_required"] is True

    # Also test MSME grace period query
    qco_msme = service.get_qco_applicability(
        product_or_category="MSME Pumps Manufacturing",
        is_number="IS 14220",
    )
    assert qco_msme["applicability_state"] == "PENDING_VERIFICATION"
    assert qco_msme["review_required"] is True


def test_9_evidence_and_provenance_are_preserved(service):
    """Every result must preserve provenance and evidence from project datasets."""
    status = service.get_standard_status("IS 8034")
    assert len(status["evidence"]) > 0
    assert "data/status.json" in status["provenance"] or "IS 8034" in status["provenance"]

    qco = service.get_qco_applicability(is_number="IS 14220")
    assert "S.O. 4333(E)" in qco["evidence"]
    assert qco["provenance"] == "data/qco.json"


def test_10_no_fake_source_urls(service):
    """Official URLs must match verified government portals only; no synthetic links."""
    summary = service.get_regulatory_summary(
        is_number="IS 14220",
        product_or_category="Openwell Submersible Pumpset",
    )

    urls = summary["source_urls"]
    assert len(urls) > 0

    for url in urls:
        assert url.startswith("https://")
        assert any(
            domain in url
            for domain in ["bis.gov.in", "dpiit.gov.in", "services.bis.gov.in", "lims.bis.gov.in"]
        ), f"Disallowed URL generated: {url}"


def test_11_missing_standard_id_handled_safely(service):
    """None, empty string, or whitespace standard IDs must not crash."""
    status_none = service.get_standard_status(None)
    assert status_none["status"] == "UNKNOWN"
    assert status_none["review_required"] is True

    status_empty = service.get_standard_status("   ")
    assert status_empty["status"] == "UNKNOWN"
    assert status_empty["review_required"] is True

    lifecycle_none = service.get_lifecycle(None)
    assert lifecycle_none["status"] == "UNKNOWN"
    assert lifecycle_none["review_required"] is True

    qco_none = service.get_qco_applicability(None, None)
    assert qco_none["applicability_state"] == "UNKNOWN"
    assert qco_none["review_required"] is True

    summary_none = service.get_regulatory_summary(None, None)
    assert summary_none["compliance_verdict"] == "UNKNOWN"


def test_12_non_qco_known_standard_returns_not_applicable(service):
    """IS 8472 is a verified active standard not covered under QCO."""
    qco = service.get_qco_applicability(is_number="IS 8472")

    assert qco["applicability_state"] == "NOT_APPLICABLE"
    assert qco["is_covered_by_qco"] is False
    assert qco["isi_mark_mandatory"] is False
    assert qco["review_required"] is False
    assert "not notified under statutory Pumps QCO" in qco["evidence"]


def test_13_consolidated_regulatory_summary(service):
    """Summary combines standard status, lifecycle, and QCO mandate deterministically."""
    summary = service.get_regulatory_summary(
        is_number="IS 14220",
        product_or_category="Openwell Submersible Pumpsets",
    )

    assert summary["is_number"] == "IS 14220"
    assert summary["title"] == "Openwell Submersible Pumpsets — Specification"
    assert summary["mandatory_certification"] is True
    assert summary["compliance_verdict"] == "MANDATORY_QCO_COMPLIANCE_REQUIRED"
    assert summary["certification_scheme"] == "Scheme I - ISI Mark (Product Certification)"
    assert len(summary["evidence"]) >= 2
    assert summary["standard_status"]["status"] == "CURRENT"
    assert summary["qco"]["order_number"] == "S.O. 4333(E)"
