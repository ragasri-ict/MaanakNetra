"""
MAANAKNETRA — Tender Linter & Procurement Analysis Demo Runner
Runs direct end-to-end analysis on demo/sample_tender.pdf and prints
an explainable audit report with findings and corrected specification clauses.
Saves schema-valid analysis result to demo/tender_analysis_result.json.
"""

import os
import sys
import json
from typing import Dict, Any

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.procurement_analyzer import ProcurementAnalysisEngine


def run_demo():
    sample_pdf = os.path.join("demo", "sample_tender.pdf")
    output_json = os.path.join("demo", "tender_analysis_result.json")

    print("=" * 100)
    print("MAANAKNETRA (SIH26108) — DETERMINISTIC TENDER LINTER & PROCUREMENT AUDIT")
    print("=" * 100)
    print(f"Target Tender Document: {sample_pdf}\n")

    if not os.path.exists(sample_pdf):
        print(f"ERROR: Tender file '{sample_pdf}' not found.")
        sys.exit(1)

    # 1. Initialize Procurement Analysis Engine
    print("1. Initializing Procurement Analysis Engine with Tender Linter...")
    engine = ProcurementAnalysisEngine()

    # 2. Execute End-to-End Analysis
    print("2. Executing deterministic end-to-end audit...")
    analysis_result = engine.analyze(sample_pdf, top_k=3)

    # 3. Print Tender Metadata & Summary
    meta = analysis_result.get("tender_metadata", {})
    status_flags = analysis_result.get("status_flags", {})
    cert_flags = analysis_result.get("certification_flags", {})
    findings = analysis_result.get("findings", [])
    corrected_clauses = analysis_result.get("corrected_clause", []) or analysis_result.get("corrected_clauses", [])
    bom = analysis_result.get("standards_bom", [])

    print("\n" + "-" * 100)
    print(f"TENDER AUDIT SUMMARY: {meta.get('document_title')}")
    print(f"Analysis ID: {meta.get('analysis_id')} | Pages: {meta.get('page_count')} | Dept: {meta.get('procuring_department')}")
    print("-" * 100)

    print("\n[REGULATORY & LIFECYCLE FLAGS]")
    print(f"  • All Standards Current:     {status_flags.get('all_standards_current')}")
    print(f"  • Has Superseded Standards:  {status_flags.get('has_superseded_standards')} (Count: {status_flags.get('superseded_count')})")
    print(f"  • Has Withdrawn Standards:   {status_flags.get('has_withdrawn_standards')} (Count: {status_flags.get('withdrawn_count')})")
    print(f"  • QCO Mandate Applicable:    {cert_flags.get('qco_mandate_applicable')}")
    print(f"  • QCO Violation Risk:        {cert_flags.get('qco_violation_risk')}")
    print(f"  • Mandatory ISI Clause:      {'PRESENT' if cert_flags.get('mandatory_isi_clause_present') else 'OMITTED (DEFICIENT)'}")

    print("\n[STANDARDS BILL OF MATERIALS (BOM)]")
    for item in bom:
        is_num = str(item.get("is_number") or "")
        role = str(item.get("role") or "")
        comp = str(item.get("compliance_status") or "")
        qco_stat = "QCO MANDATED" if item.get("is_mandatory_qco") else "VOLUNTARY"
        print(f"  • [{role:24}] {is_num:12} | Status: {comp:22} | {qco_stat:12} | {item.get('title', '')[:45]}")

    print(f"\n[LINTER FINDINGS ({len(findings)} Total)]")
    for idx, f in enumerate(findings, start=1):
        f_id = f.get("finding_id")
        sev = f.get("severity")
        f_type = f.get("finding_type")
        title = f.get("title")
        t_text = f.get("tender_text")
        rec_action = f.get("suggested_fix", {}).get("recommended_action_summary", "")

        print(f"\n  Finding #{idx}: [{sev}] {f_type}")
        print(f"    ID:       {f_id}")
        print(f"    Title:    {title}")
        print(f"    Evidence: \"{t_text}\"")
        print(f"    Action:   {rec_action}")
        if f.get("affected_standard"):
            print(f"    Standard: {f.get('affected_standard', {}).get('is_number')}")
        print(f"    Source:   {f.get('source', {}).get('source_type')} ({f.get('source', {}).get('rule_id')})")

    print(f"\n[DETERMINISTIC CORRECTED SPECIFICATION CLAUSES ({len(corrected_clauses)} Generated)]")
    for idx, c in enumerate(corrected_clauses, start=1):
        c_id = c.get("clause_id")
        ref = c.get("source_clause_reference")
        orig = c.get("original_tender_text")
        corr = c.get("corrected_text")
        rat = c.get("rationale")

        print(f"\n  Correction #{idx} [{c_id}] -> {ref}")
        print(f"    Original:  \"{orig}\"")
        print(f"    Corrected: \"{corr}\"")
        print(f"    Rationale: {rat}")

    # 4. Save JSON Report
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(analysis_result, f, indent=2)

    print("\n" + "=" * 100)
    print(f"SUCCESS: Analysis complete. JSON artifact exported to: {output_json}")
    print("=" * 100)
    return analysis_result


if __name__ == "__main__":
    run_demo()
