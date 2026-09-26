"""
Standard-Level Parameter Compatibility Engine for MAANAKNETRA.
Iterates over tender requirements, executes deterministic clause comparisons,
and computes parameter summary metrics (fit score, matched, conflicts, not specified).
"""

from typing import Dict, Any, List, Optional
from .comparator import compare_parameter


class ParameterCompatibilityEngine:
    """
    Evaluates end-to-end technical compatibility between tender requirements
    and an Indian Standard record from data/standards.json.
    """

    def __init__(self):
        pass

    def evaluate_standard_compatibility(
        self,
        standard: Dict[str, Any],
        extracted_requirements: List[Dict[str, Any]],
        product_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes parameter-level comparison for a candidate standard.
        Returns:
            standard_id: str
            parameter_fit_score: float in [0.0, 1.0]
            parameter_results: list of per-parameter comparison dicts
            matched_requirements: list of compliant/deviating items
            unmatched_requirements: list of unmapped items
            conflicting_requirements: list of non-compliant/conflicting items
            not_specified_requirements: list of not-specified items
            parameter_summary: dict of summary metrics
        """
        std_id = standard.get("is_number", "IS_UNKNOWN")
        results: List[Dict[str, Any]] = []

        matched_list: List[Dict[str, Any]] = []
        conflicting_list: List[Dict[str, Any]] = []
        not_specified_list: List[Dict[str, Any]] = []
        unmatched_list: List[Dict[str, Any]] = []

        total_reqs = len(extracted_requirements)
        if total_reqs == 0:
            return {
                "standard_id": std_id,
                "parameter_fit_score": 0.0,
                "parameter_results": [],
                "matched_requirements": [],
                "unmatched_requirements": [],
                "conflicting_requirements": [],
                "not_specified_requirements": [],
                "parameter_summary": {
                    "matched_count": 0,
                    "conflict_count": 0,
                    "not_specified_count": 0,
                    "coverage_ratio": 0.0
                }
            }

        total_score_weight = 0.0
        earned_score = 0.0

        for req in extracted_requirements:
            res = compare_parameter(req, standard, all_tender_reqs=extracted_requirements)
            results.append(res)

            status = res["fit_status"]
            cat = req.get("category", "")
            weight = self._get_weight(cat)
            total_score_weight += weight

            if status == "COMPLIANT":
                matched_list.append(res)
                earned_score += weight
            elif status == "DEVIATING":
                matched_list.append(res)
                earned_score += weight * 0.85
            elif status == "NON_COMPLIANT":
                conflicting_list.append(res)
            elif status == "NOT_SPECIFIED":
                not_specified_list.append(res)
            else:
                unmatched_list.append(res)

        # Calculate normalized fit score [0.0, 1.0]
        fit_score = (earned_score / max(total_score_weight, 1.0))
        # If there are explicit conflicts, reduce fit score proportionally
        if conflicting_list:
            fit_score = max(0.0, fit_score - 0.20 * len(conflicting_list))

        fit_score = round(max(0.0, min(1.0, fit_score)), 4)
        coverage_ratio = round((len(matched_list) + len(conflicting_list)) / total_reqs, 4)

        return {
            "standard_id": std_id,
            "parameter_fit_score": fit_score,
            "parameter_results": results,
            "matched_requirements": matched_list,
            "unmatched_requirements": unmatched_list,
            "conflicting_requirements": conflicting_list,
            "not_specified_requirements": not_specified_list,
            "parameter_summary": {
                "matched_count": len(matched_list),
                "conflict_count": len(conflicting_list),
                "not_specified_count": len(not_specified_list),
                "coverage_ratio": coverage_ratio
            }
        }

    def _get_weight(self, category: str) -> float:
        weights = {
            "PRODUCT": 3.0,
            "PRODUCT_TYPE": 3.0,
            "POWER": 2.5,
            "VOLTAGE": 2.5,
            "HEAD": 2.0,
            "FLOW_RATE": 2.0,
            "EFFICIENCY": 2.0,
            "TESTING": 1.5,
            "TEMPERATURE": 1.5,
            "OPERATING_ENVIRONMENT": 1.5,
            "INSTALLATION": 1.0,
            "MATERIAL": 1.0,
            "SIZE/DIMENSION": 1.0,
            "QUANTITY": 0.2,
            "EXISTING_IS_REFERENCE": 0.5,
            "OTHER_TECHNICAL_PARAMETER": 0.5
        }
        return weights.get(category, 1.0)
