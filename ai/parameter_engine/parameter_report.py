"""
Parameter Matching Report Generator for MAANAKNETRA.
Generates structured JSON report and formatted terminal tables:
PARAMETER | TENDER | STANDARD | RESULT | EVIDENCE
"""

import os
import json
from typing import Dict, Any, List


def format_parameter_table(evaluation_result: Dict[str, Any]) -> str:
    """
    Renders per-parameter comparisons into the exact format:
    PARAMETER | TENDER | STANDARD | RESULT | EVIDENCE
    """
    lines = []
    header = f"{'PARAMETER':<35} | {'TENDER':<25} | {'STANDARD':<34} | {'RESULT':<14} | {'EVIDENCE'}"
    separator = "-" * 175
    lines.append(separator)
    lines.append(header)
    lines.append(separator)

    for item in evaluation_result.get("parameter_results", []):
        param = item.get("parameter_name", "")[:33]
        t_val = str(item.get("tender_value", ""))[:23]
        s_val = str(item.get("standard_value") or "-")[:32]
        status = item.get("fit_status", "")
        ev = item.get("evidence", "")[:60] + ("..." if len(item.get("evidence", "")) > 60 else "")

        line = f"{param:<35} | {t_val:<25} | {s_val:<34} | {status:<14} | {ev}"
        lines.append(line)

    lines.append(separator)
    summary = evaluation_result.get("parameter_summary", {})
    lines.append(
        f"Summary: Matched={summary.get('matched_count', 0)}, "
        f"Conflicts={summary.get('conflict_count', 0)}, "
        f"Not Specified={summary.get('not_specified_count', 0)}, "
        f"Fit Score={evaluation_result.get('parameter_fit_score', 0.0):.4f}"
    )
    lines.append(separator)
    return "\n".join(lines)


def generate_json_report(
    evaluation_result: Dict[str, Any],
    standard: Dict[str, Any],
    tender_meta: Dict[str, Any],
    output_path: str = "demo/parameter_matching_report.json"
) -> Dict[str, Any]:
    """
    Saves and returns the complete parameter matching report to JSON.
    """
    report = {
        "report_metadata": {
            "title": "MAANAKNETRA Parameter-Level Standard Matching Report",
            "tender_document": tender_meta.get("file_name", "sample_tender.pdf"),
            "evaluated_standard": standard.get("is_number"),
            "standard_title": standard.get("title"),
            "standard_status": standard.get("status")
        },
        "parameter_fit_score": evaluation_result.get("parameter_fit_score"),
        "parameter_summary": evaluation_result.get("parameter_summary"),
        "matched_requirements": evaluation_result.get("matched_requirements"),
        "conflicting_requirements": evaluation_result.get("conflicting_requirements"),
        "not_specified_requirements": evaluation_result.get("not_specified_requirements"),
        "parameter_results": evaluation_result.get("parameter_results")
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report
