import os
import json
import pytest
from fastapi.testclient import TestClient

from backend.app import app, get_catalogue_metadata
from ai.procurement_analyzer import ProcurementAnalysisEngine
from ai.standards_graph.graph_builder import StandardsGraphBuilder

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def client():
    return TestClient(app)


def test_zero_unresolved_references_in_catalogue():
    """Fails if any relation points to a standard not in standards.json."""
    builder = StandardsGraphBuilder(
        standards_path=os.path.join(WORKSPACE_ROOT, "data", "standards.json"),
        relations_path=os.path.join(WORKSPACE_ROOT, "data", "relations.json")
    )
    unresolved = builder.get_unresolved_references()
    assert len(unresolved) == 0, f"Unresolved references found: {unresolved}"


def test_is11346_and_is5120_present_and_verified():
    """Authoritatively verified IS 11346 and IS 5120 must exist in standards.json."""
    standards_path = os.path.join(WORKSPACE_ROOT, "data", "standards.json")
    with open(standards_path, "r", encoding="utf-8") as f:
        standards = json.load(f)
    
    stds_by_num = {s["is_number"]: s for s in standards}
    assert "IS 11346" in stds_by_num
    assert "IS 5120" in stds_by_num
    
    is11346 = stds_by_num["IS 11346"]
    assert is11346["current_version"] == "IS 11346:2002"
    assert is11346["status"] == "CURRENT"
    assert is11346["verification"]["verification_status"] == "VERIFIED_OFFICIAL"
    
    is5120 = stds_by_num["IS 5120"]
    assert is5120["current_version"] == "IS 5120:1977"
    assert is5120["status"] == "CURRENT"
    assert is5120["verification"]["verification_status"] == "VERIFIED_OFFICIAL"


def test_health_endpoint(client):
    """GET /health must return status healthy, model status, and catalogue size."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "catalogue_size" in data
    assert data["catalogue_size"] >= 30
    assert "covered_categories_count" in data


def test_catalogue_stats_endpoint(client):
    """GET /api/catalogue/stats must return accurate counts and zero unresolved references."""
    res = client.get("/api/catalogue/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["standards_count"] >= 30
    assert data["unresolved_references"] == 0
    assert data["categories_count"] >= 4
    assert len(data["categories"]) == data["categories_count"]


def test_officer_decisions_persistence(client):
    """POST and GET /api/decisions must store and retrieve officer audit decisions."""
    analysis_id = "ANALYSIS_TEST_AUDIT_001"
    finding_id = "FIND_001"
    
    # Save decision
    payload = {
        "analysis_id": analysis_id,
        "finding_id": finding_id,
        "decision": "ACCEPTED",
        "notes": "Verified against BIS Product Manual Annexure B."
    }
    post_res = client.post("/api/decisions", json=payload)
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["status"] == "success"
    assert post_data["decision"] == "ACCEPTED"
    
    # Retrieve decisions
    get_res = client.get(f"/api/decisions/{analysis_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert finding_id in get_data["decisions"]
    assert get_data["decisions"][finding_id]["decision"] == "ACCEPTED"
    
    # Test invalid decision rejection
    bad_payload = {
        "analysis_id": analysis_id,
        "finding_id": finding_id,
        "decision": "UNKNOWN_ACTION"
    }
    bad_res = client.post("/api/decisions", json=bad_payload)
    assert bad_res.status_code == 400
    assert bad_res.json()["error_code"] == "INVALID_DECISION_VALUE"


def test_upload_validation_unsupported_format(client):
    """Uploading unsupported file formats must return 400 with structured error."""
    files = {"file": ("malicious.exe", b"MZ\x90\x00BinaryContent", "application/octet-stream")}
    res = client.post("/api/analyze", files=files)
    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "UNSUPPORTED_FILE_TYPE"
    assert "stage" in data


def test_upload_validation_empty_file(client):
    """Uploading empty (0 bytes) file must return 422 with structured error."""
    files = {"file": ("empty_tender.pdf", b"", "application/pdf")}
    res = client.post("/api/analyze", files=files)
    assert res.status_code == 422
    data = res.json()
    assert data["error_code"] == "EMPTY_FILE"
    assert "stage" in data


def test_upload_validation_oversized_file(client):
    """Uploading file larger than 25MB must return 413 with structured error."""
    # Create 26MB dummy stream without writing 26MB to disk
    import io
    big_stream = io.BytesIO(b"A" * (26 * 1024 * 1024))
    files = {"file": ("huge_tender.pdf", big_stream, "application/pdf")}
    res = client.post("/api/analyze", files=files)
    assert res.status_code == 413
    data = res.json()
    assert data["error_code"] == "FILE_TOO_LARGE"


def test_outside_coverage_handling():
    """Tender with completely out-of-scope domain returns outside_coverage."""
    engine = ProcurementAnalysisEngine()
    unrelated_tender = {
        "tender_metadata": {"document_title": "Procurement of Commercial Boeing Aircraft Fuel", "page_count": 1},
        "extracted_requirements": [
            {
                "requirement_id": "REQ_001",
                "parameter_name": "Jet Fuel Aviation Density",
                "source_text": "Aviation turbine fuel JET-A1 density 0.804 kg/l at 15 degrees Celsius",
                "normalized_value": "0.804",
                "unit": "kg/l",
                "governing_clause": "Clause 1.1",
                "page": 1,
                "confidence": 0.95
            }
        ],
        "already_cited_standards": [],
        "product_context": {"primary_item_name": "Aviation Turbine Fuel", "category": "Petroleum Aviation"},
        "raw_text": "Aviation turbine fuel procurement."
    }
    result = engine.analyze(unrelated_tender, top_k=3)
    assert result["status"] == "outside_coverage"
    # Must not recommend unrelated water pumps
    assert len(result["recommended_standards"]) == 0
    assert any(f["finding_id"] == "FIND_OUTSIDE_COVERAGE" for f in result["findings"])


def test_sample_tender_output_unchanged():
    """Canonical sample_tender.pdf analysis must produce consistent high quality findings."""
    sample_pdf = os.path.join(WORKSPACE_ROOT, "demo", "sample_tender.pdf")
    if os.path.exists(sample_pdf):
        engine = ProcurementAnalysisEngine()
        result = engine.analyze(sample_pdf, top_k=5)
        assert result["status"] == "completed"
        assert len(result["findings"]) >= 6
        # Must detect superseded IS 14220:1994
        has_superseded_finding = any(
            f.get("finding_type") == "OUTDATED_STANDARD"
            and "14220" in f.get("title", "")
            for f in result["findings"]
        )
        assert has_superseded_finding
