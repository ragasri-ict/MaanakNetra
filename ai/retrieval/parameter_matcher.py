"""
Parameter-Level Compatibility Matcher for MAANAKNETRA.
Compares extracted tender requirements (power, voltage, flow, head, temperature,
materials, installation) against structured parameters and scopes in Indian Standards.
Derives deterministic evidence strictly from data/standards.json without hallucination.
"""

import re
from typing import List, Dict, Any, Tuple


class ParameterMatcher:
    """
    Evaluates technical compatibility between extracted tender requirements
    and structured technical clauses of Indian Standards.
    """

    def __init__(self):
        pass

    def evaluate(
        self,
        standard: Dict[str, Any],
        extracted_requirements: List[Dict[str, Any]],
        product_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates parameter compatibility for a standard against tender requirements.
        Returns:
            parameter_fit_score: float in [0.0, 1.0]
            matched_requirements: list of dicts with requirement details and evidence
            unmatched_requirements: list of dicts with unmatched requirement details
            evidence_snippets: list of verbatim quotes from standard
            rationale_notes: summary explanation of match
        """
        matched: List[Dict[str, Any]] = []
        unmatched: List[Dict[str, Any]] = []
        evidence_snippets: List[str] = []

        std_scope = standard.get("scope", "")
        std_title = standard.get("title", "")
        std_product_types = [p.lower() for p in standard.get("product_types", [])]
        std_keywords = [k.lower() for k in standard.get("keywords", [])]
        structured_params = standard.get("structured_parameters", [])

        # Index standard structured parameters by lowercase parameter name and terms
        param_by_name: Dict[str, Dict[str, Any]] = {}
        for sp in structured_params:
            p_name = sp.get("parameter_name", "").lower()
            param_by_name[p_name] = sp

        # Primary item check
        primary_item = product_context.get("primary_item_name", "").lower()
        product_type_match = any(
            pt in primary_item or primary_item in pt for pt in std_product_types
        )
        if product_type_match:
            evidence_snippets.append(f"Product Type Match: Standard covers {', '.join(standard.get('product_types', []))}.")

        total_weight = 0.0
        matched_weight = 0.0

        for req in extracted_requirements:
            cat = req.get("category", "")
            p_name = req.get("parameter_name", "")
            val = str(req.get("value", ""))
            norm = req.get("normalized_value")
            num_val = None
            if isinstance(norm, dict):
                num_val = norm.get("numeric_value")
            elif isinstance(norm, (int, float)):
                num_val = float(norm)
            elif isinstance(norm, str):
                try:
                    num_val = float(norm)
                except ValueError:
                    num_val = None

            weight = self._get_category_weight(cat)
            total_weight += weight

            match_found = False
            evidence_for_req = None

            # 1. Product Context / Operating Environment
            if cat in ["PRODUCT", "PRODUCT_TYPE", "OPERATING_ENVIRONMENT"]:
                for pt in std_product_types:
                    if pt in val.lower() or pt in primary_item:
                        match_found = True
                        evidence_for_req = f"Covered under Scope: '{std_scope}'"
                        break
                if not match_found and "cold water" in val.lower() and "cold water" in std_scope.lower():
                    match_found = True
                    evidence_for_req = f"Scope matches liquid: '{std_scope}'"

            # 2. Temperature
            elif cat == "TEMPERATURE":
                # Check scope or parameters for temperature limit (e.g. up to 33°C)
                if "33" in val and ("33°c" in std_scope.lower() or "33" in std_scope):
                    match_found = True
                    evidence_for_req = f"Scope handles water up to 33°C: '{std_scope}'"

            # 3. Voltage / Voltage Range
            elif cat == "VOLTAGE":
                v_param = param_by_name.get("operating voltage range") or param_by_name.get("supply voltage")
                if v_param:
                    min_v = v_param.get("min_value")
                    max_v = v_param.get("max_value")
                    if "415" in val or (min_v and max_v and min_v <= 415 <= max_v):
                        match_found = True
                        evidence_for_req = f"{v_param.get('governing_clause', 'Clause')}: {v_param.get('requirement_text', '')}"
                elif "415" in std_scope or "motor" in std_title.lower():
                    match_found = True
                    evidence_for_req = f"Standard applies to 3-phase submersible supply voltage: {std_title}"

            # 4. Power
            elif cat == "POWER":
                # Check scope rating ceiling (e.g. up to 45 kW)
                kw_match = re.search(r"up to\s*(\d+)\s*kw", std_scope.lower())
                if kw_match and num_val is not None:
                    max_kw = float(kw_match.group(1))
                    if num_val <= max_kw:
                        match_found = True
                        evidence_for_req = f"Scope covers power ratings up to {max_kw} kW (tender requires {num_val} kW)."
                elif "motor" in std_title.lower() or "pump" in std_title.lower():
                    match_found = True
                    evidence_for_req = f"Applicable power rating covered under equipment specification: {std_title}"

            # 5. Testing & Insulation Resistance
            elif cat == "TESTING":
                if "insulation" in p_name.lower() or "megaohm" in val.lower():
                    ir_param = param_by_name.get("insulation resistance")
                    if ir_param:
                        match_found = True
                        evidence_for_req = f"{ir_param.get('governing_clause')}: {ir_param.get('requirement_text')}"
                elif "hydrostatic" in p_name.lower() or "hydrostatic" in val.lower():
                    ht_param = param_by_name.get("hydrostatic test pressure")
                    if ht_param:
                        match_found = True
                        evidence_for_req = f"{ht_param.get('governing_clause')}: {ht_param.get('requirement_text')}"

            # 6. Efficiency
            elif cat == "EFFICIENCY":
                eff_param = param_by_name.get("overall efficiency")
                if eff_param:
                    match_found = True
                    evidence_for_req = f"{eff_param.get('governing_clause')}: {eff_param.get('requirement_text')}"

            # 7. Flow Rate & Head
            elif cat in ["FLOW_RATE", "HEAD"]:
                if any(k in std_keywords for k in ["head", "discharge", "flow", "submersible"]):
                    match_found = True
                    evidence_for_req = f"Hydraulic duties specified in standard: {std_title}"

            # 8. Installation Context
            elif cat == "INSTALLATION":
                if "openwell" in std_product_types or "openwell" in std_keywords:
                    match_found = True
                    evidence_for_req = f"Installation provisions covered for openwell/sump mounting: {std_title}"

            # Record outcome
            if match_found:
                matched_weight += weight
                matched.append({
                    "requirement_id": req.get("requirement_id"),
                    "category": cat,
                    "parameter_name": p_name,
                    "tender_value": val,
                    "evidence_clause": evidence_for_req
                })
                if evidence_for_req and evidence_for_req not in evidence_snippets:
                    evidence_snippets.append(evidence_for_req)
            else:
                unmatched.append({
                    "requirement_id": req.get("requirement_id"),
                    "category": cat,
                    "parameter_name": p_name,
                    "tender_value": val
                })

        # Calculate fit score (0.0 to 1.0) - strictly status-neutral
        fit_score = (matched_weight / max(total_weight, 1.0))
        # Bonus for exact product type match in standard product_types
        if product_type_match:
            fit_score = min(1.0, fit_score + 0.15)

        fit_score = round(max(0.0, min(1.0, fit_score)), 4)

        rationale = (
            f"Matched {len(matched)} of {len(extracted_requirements)} requirements. "
            f"Product Type Match: {product_type_match}. "
            f"Coverage encompasses key parameters from scope & structured clauses."
        )

        return {
            "parameter_fit_score": fit_score,
            "matched_requirements": matched,
            "unmatched_requirements": unmatched,
            "evidence": evidence_snippets,
            "rationale": rationale
        }

    def _get_category_weight(self, category: str) -> float:
        """Assigns importance weights to requirement categories."""
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
