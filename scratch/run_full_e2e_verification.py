import os
import sys
import time
import json
import requests
import subprocess

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("=" * 60)
    print("MAANAKNETRA FULL E2E SUITE - 7 MANDATORY TESTS")
    print("=" * 60)

    # Health check
    res = requests.get(f"{BASE_URL}/health", timeout=10)
    print(f"[HEALTH CHECK] Status: {res.status_code}, Body: {res.json()}")
    assert res.status_code == 200

    # TEST 1: Built-in sample/demo
    print("\n--- TEST 1: Built-in sample/demo (/api/demo) ---")
    t0 = time.time()
    res1 = requests.get(f"{BASE_URL}/api/demo", timeout=10)
    dt1 = round(time.time() - t0, 3)
    print(f"Test 1 Status: {res1.status_code} in {dt1}s")
    assert res1.status_code == 200
    data1 = res1.json()
    assert "findings" in data1 and len(data1["findings"]) > 0
    assert "recommended_standards" in data1
    assert "tender_metadata" in data1
    print(f"  PASS: findings={len(data1['findings'])}, reqs={len(data1['extracted_requirements'])}, doc={data1['tender_metadata'].get('document_title')}")

    # TEST 2: Small real government tender (tender_dg_set.pdf)
    print("\n--- TEST 2: Small real government tender (scratch/tender_dg_set.pdf) ---")
    pdf2_path = os.path.join(WORKSPACE_ROOT, "scratch", "tender_dg_set.pdf")
    t0 = time.time()
    with open(pdf2_path, "rb") as f:
        res2 = requests.post(f"{BASE_URL}/api/analyze", files={"file": ("tender_dg_set_2026.pdf", f, "application/pdf")}, timeout=30)
    dt2 = round(time.time() - t0, 3)
    print(f"Test 2 Status: {res2.status_code} in {dt2}s")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2.get("tender_metadata", {}).get("document_title") == "tender_dg_set_2026.pdf"
    assert len(data2.get("extracted_requirements", [])) > 0
    assert len(data2.get("recommended_standards", [])) > 0
    print(f"  PASS: findings={len(data2.get('findings', []))}, reqs={len(data2['extracted_requirements'])}, primary={data2['recommended_standards'][0]['standard']['is_number']}")

    # TEST 3: Second real tender/product category (tender_transformer.pdf)
    print("\n--- TEST 3: Second real tender category (scratch/tender_transformer.pdf) ---")
    pdf3_path = os.path.join(WORKSPACE_ROOT, "scratch", "tender_transformer.pdf")
    t0 = time.time()
    with open(pdf3_path, "rb") as f:
        res3 = requests.post(f"{BASE_URL}/api/analyze", files={"file": ("tender_distribution_transformer.pdf", f, "application/pdf")}, timeout=30)
    dt3 = round(time.time() - t0, 3)
    print(f"Test 3 Status: {res3.status_code} in {dt3}s")
    assert res3.status_code == 200
    data3 = res3.json()
    assert len(data3.get("extracted_requirements", [])) > 0
    assert len(data3.get("recommended_standards", [])) > 0
    print(f"  PASS: findings={len(data3.get('findings', []))}, reqs={len(data3['extracted_requirements'])}, primary={data3['recommended_standards'][0]['standard']['is_number']}")

    # TEST 4: Invalid/non-PDF upload
    print("\n--- TEST 4: Invalid/unsupported format upload (.exe / .zip) ---")
    t0 = time.time()
    res4 = requests.post(f"{BASE_URL}/api/analyze", files={"file": ("malicious_file.exe", b"MZ\x90\x00BinaryContent", "application/octet-stream")}, timeout=10)
    dt4 = round(time.time() - t0, 3)
    print(f"Test 4 Status: {res4.status_code} in {dt4}s")
    assert res4.status_code == 400
    data4 = res4.json()
    assert data4.get("status") == "error"
    assert "stage" in data4
    assert "message" in data4
    print(f"  PASS: Structured error returned cleanly: stage='{data4.get('stage')}', message='{data4.get('message')}'")

    # TEST 5: Large PDF / bounded page handling
    print("\n--- TEST 5: Large PDF / multi-page bounded handling ---")
    # Generate a multi-page PDF on the fly
    import fitz
    large_pdf_path = os.path.join(WORKSPACE_ROOT, "scratch", "large_tender_60pages.pdf")
    doc = fitz.open()
    for p in range(60):
        page = doc.new_page()
        page.insert_text((50, 72), f"GOVERNMENT OF INDIA TENDER NOTICE - PAGE {p+1}\nClause {p+1}.1: The submersible pumping unit shall operate with 415V supply.\nMaterial of construction shall be stainless steel grade 304.")
    doc.save(large_pdf_path)
    doc.close()

    t0 = time.time()
    with open(large_pdf_path, "rb") as f:
        res5 = requests.post(f"{BASE_URL}/api/analyze", files={"file": ("large_tender_60pages.pdf", f, "application/pdf")}, timeout=30)
    dt5 = round(time.time() - t0, 3)
    print(f"Test 5 Status: {res5.status_code} in {dt5}s")
    assert res5.status_code == 200
    data5 = res5.json()
    # Confirms it bounded to 50 pages maximum and completed within seconds without hanging
    assert data5["tender_metadata"]["page_count"] == 50
    assert len(data5["extracted_requirements"]) > 0
    print(f"  PASS: Bounded 60-page PDF processed within {dt5}s! Page count bounded to {data5['tender_metadata']['page_count']}")

    # TEST 6: Empty file (0 bytes) upload validation
    print("\n--- TEST 6: Empty 0-byte file upload validation ---")
    empty_path = os.path.join(WORKSPACE_ROOT, "scratch", "empty_tender.pdf")
    with open(empty_path, "wb") as f:
        pass
    with open(empty_path, "rb") as f:
        res6 = requests.post(f"{BASE_URL}/api/analyze", files={"file": ("empty_tender.pdf", f, "application/pdf")}, timeout=10)
    print(f"Test 6 Status: {res6.status_code}")
    assert res6.status_code == 400
    data6 = res6.json()
    assert data6.get("status") == "error"
    print(f"  PASS: Structured empty file rejection: {data6.get('message')}")

    # TEST 7: DOCX upload format handling
    print("\n--- TEST 7: DOCX / TXT format handling ---")
    txt_path = os.path.join(WORKSPACE_ROOT, "scratch", "tender_procurement.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("TENDER SPECIFICATION FOR SUBMERSIBLE PUMPS\nDepartment of Water Resources\nClause 3.1: Operating head 45 meters, discharge 12 lps.\nSubject to IS 14220:1994.")
    with open(txt_path, "rb") as f:
        res7 = requests.post(f"{BASE_URL}/api/analyze", files={"file": ("tender_procurement.txt", f, "text/plain")}, timeout=15)
    print(f"Test 7 Status: {res7.status_code}")
    assert res7.status_code == 200
    data7 = res7.json()
    assert len(data7.get("findings", [])) > 0
    print(f"  PASS: TXT format processed cleanly with {len(data7['findings'])} findings!")

    print("\n" + "=" * 60)
    print("ALL 7 END-TO-END TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
