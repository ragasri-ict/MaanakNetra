"""
Script to execute Parameter-Level Standard Matching for demo/sample_tender.pdf
against the top retrieved Indian Standard (IS 14220:2018).
Generates demo/parameter_matching_report.json and prints concise terminal summary table.
"""

import os
import sys
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion import ingest_document
from ai.requirement_extractor import extract_requirements
from ai.parameter_engine import ParameterCompatibilityEngine, format_parameter_table, generate_json_report


def main():
    tender_path = "demo/sample_tender.pdf"
    standards_path = "data/standards.json"
    output_path = "demo/parameter_matching_report.json"

    print("=" * 120)
    print("MAANAKNETRA - STEP 7A: PARAMETER-LEVEL STANDARD MATCHING PIPELINE")
    print("=" * 120)

    # 1. Ingest tender & extract requirements
    print(f"1. Ingesting tender: {tender_path}")
    tender_doc = ingest_document(tender_path)
    reqs_doc = extract_requirements(tender_doc)
    extracted_reqs = reqs_doc.get("extracted_requirements", [])
    product_context = reqs_doc.get("product_context", "")
    print(f"   -> Extracted {len(extracted_reqs)} structured requirements.")

    # 2. Load top candidate standard (IS 14220:2018)
    print(f"2. Loading standard dataset from {standards_path}")
    with open(standards_path, "r", encoding="utf-8") as f:
        standards = json.load(f)
    
    top_standard = next((s for s in standards if s.get("is_number") == "IS 14220"), standards[0])
    print(f"   -> Top candidate standard: {top_standard.get('is_number')} - {top_standard.get('title')}")

    # 3. Evaluate parameter-level compatibility
    print("3. Evaluating deterministic parameter compatibility...")
    engine = ParameterCompatibilityEngine()
    result = engine.evaluate_standard_compatibility(
        top_standard,
        extracted_reqs,
        product_context
    )

    # 4. Generate JSON report
    report = generate_json_report(
        evaluation_result=result,
        standard=top_standard,
        tender_meta={"file_name": os.path.basename(tender_path)},
        output_path=output_path
    )
    print(f"   -> Saved JSON report to: {output_path}")

    # 5. Print summary table
    print("\n" + "=" * 120)
    print("PARAMETER COMPATIBILITY MATRIX")
    print("=" * 120)
    table_str = format_parameter_table(result)
    print(table_str)


if __name__ == "__main__":
    main()
