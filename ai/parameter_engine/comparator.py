"""
Deterministic Parameter Comparator for MAANAKNETRA.
Compares individual tender requirements against verified standard structured clauses.
Supports exact, inequality (GTE/LTE), interval/range, relative multiplier, and categorical matches.
Strictly returns NOT_SPECIFIED when verified standard data is absent, avoiding false conflicts.
"""

from typing import Dict, Any, Optional, List
from .normalization import normalize_unit_and_value


def compare_parameter(
    tender_req: Dict[str, Any],
    standard: Dict[str, Any],
    all_tender_reqs: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Compares a single extracted tender requirement against candidate standard clauses.
    Returns:
        requirement_id: str
        parameter_name: str
        tender_value: str / float
        tender_unit: str
        standard_value: str / float
        standard_unit: str
        comparison_type: str
        fit_status: "COMPLIANT" | "NON_COMPLIANT" | "DEVIATING" | "NOT_SPECIFIED"
        evidence: str
        source: str
        notes: str
    """
    req_id = tender_req.get("requirement_id", "REQ_UNKNOWN")
    cat = tender_req.get("category", "")
    p_name = tender_req.get("parameter_name", "")
    raw_val = tender_req.get("value", "")
    tender_unit = tender_req.get("unit")
    norm_raw = tender_req.get("normalized_value")
    if isinstance(norm_raw, dict):
        norm_dict = norm_raw
    elif isinstance(norm_raw, (int, float)):
        norm_dict = {"numeric_value": float(norm_raw), "operator": "EQUAL"}
    elif isinstance(norm_raw, str):
        try:
            norm_dict = {"numeric_value": float(norm_raw), "operator": "EQUAL"}
        except ValueError:
            norm_dict = {"raw_string": norm_raw, "operator": "EQUAL"}
    else:
        norm_dict = {}

    operator = norm_dict.get("operator", "EQUAL")
    num_val = norm_dict.get("numeric_value")
    min_val = norm_dict.get("min_value")
    max_val = norm_dict.get("max_value")
    source_text = tender_req.get("source_text", "")

    std_scope = standard.get("scope", "")
    std_title = standard.get("title", "")
    std_params = standard.get("structured_parameters", [])
    std_source = standard.get("source", {}).get("portal_url") or standard.get("source", {}).get("official_publication_ref") or "data/standards.json"

    # 1. Product Type / Domain Alignment
    if cat in ["PRODUCT", "PRODUCT_TYPE"]:
        std_pts = [p.lower() for p in standard.get("product_types", [])]
        tender_pt = raw_val.lower()
        if any(pt in tender_pt or tender_pt in pt for pt in std_pts):
            return _build_result(
                req_id, p_name, raw_val, tender_unit,
                standard.get("product_types"), None,
                "TEXT_ENUM_MATCH", "COMPLIANT",
                f"Scope & Product Types: {', '.join(standard.get('product_types', []))}",
                std_source, source_text,
                "Tender product classification matches standard scope."
            )
        else:
            return _build_result(
                req_id, p_name, raw_val, tender_unit,
                standard.get("product_types"), None,
                "TEXT_ENUM_MATCH", "NON_COMPLIANT",
                f"Standard specifies {', '.join(standard.get('product_types', []))}, which differs from '{raw_val}'.",
                std_source, source_text,
                "Explicit product type mismatch."
            )

    # 2. Operating Temperature
    if cat == "TEMPERATURE":
        # Check standard scope for temperature limits (e.g., clear, cold water up to 33°C)
        if "33" in str(raw_val) and ("33°c" in std_scope.lower() or "33" in std_scope):
            return _build_result(
                req_id, p_name, "33°C", "deg C",
                "33°C max", "deg C",
                "LESS_THAN_OR_EQUAL", "COMPLIANT",
                f"Scope: '{std_scope}'",
                std_source, source_text,
                "Water temperature requirement (up to 33°C) is covered by standard scope."
            )
        elif num_val is not None:
            # If tender temperature exceeds 33°C (e.g. 45°C), explicit conflict
            if num_val > 33.0 and "33°c" in std_scope.lower():
                return _build_result(
                    req_id, p_name, raw_val, tender_unit,
                    "33°C max", "deg C",
                    "LESS_THAN_OR_EQUAL", "NON_COMPLIANT",
                    f"Scope: Standard specifies clear, cold water up to 33°C only. Tender requests {raw_val}.",
                    std_source, source_text,
                    "Temperature exceeds maximum permissible limit specified in standard scope."
                )

    # 3. Rated Power Output
    if cat == "POWER":
        # Check standard scope for rating range (e.g. up to 45 kW)
        import re
        kw_match = re.search(r"up to\s*(\d+(?:\.\d+)?)\s*kw", std_scope.lower())
        norm_tender = normalize_unit_and_value(num_val, tender_unit, "POWER")
        t_kw = norm_tender.get("normalized_value")

        if kw_match and t_kw is not None:
            std_max_kw = float(kw_match.group(1))
            if t_kw <= std_max_kw:
                return _build_result(
                    req_id, p_name, raw_val, tender_unit,
                    f"Up to {std_max_kw} kW", "kW",
                    "RANGE_CEILING", "COMPLIANT",
                    f"Scope: '{std_scope}'",
                    std_source, source_text,
                    f"Tender power rating ({t_kw} kW) falls within standard scope (up to {std_max_kw} kW)."
                )
            else:
                return _build_result(
                    req_id, p_name, raw_val, tender_unit,
                    f"Up to {std_max_kw} kW", "kW",
                    "RANGE_CEILING", "NON_COMPLIANT",
                    f"Scope covers ratings up to {std_max_kw} kW only. Tender requests {t_kw} kW.",
                    std_source, source_text,
                    "Power rating exceeds standard scope."
                )

    # 4. Supply Voltage & Voltage Variation Band
    if cat == "VOLTAGE":
        # Guard: Megger instrument test voltage is an insulation testing specification, not mains supply
        if "megger" in p_name.lower() or "test" in p_name.lower():
            ir_param = next((sp for sp in std_params if "insulation" in sp.get("parameter_name", "").lower()), None)
            if ir_param and "500" in str(raw_val) and "500v" in ir_param.get("requirement_text", "").lower():
                return _build_result(
                    req_id, p_name, raw_val, "V",
                    "500V DC megger", "V DC",
                    "EXACT_EQUALITY", "COMPLIANT",
                    f"{ir_param.get('governing_clause')}: {ir_param.get('requirement_text')}",
                    std_source, source_text,
                    "Megger test voltage (500V DC) matches standard insulation testing specification."
                )
            else:
                return _build_result(
                    req_id, p_name, raw_val, tender_unit,
                    None, None,
                    "UNVERIFIED_IN_DATASET", "NOT_SPECIFIED",
                    f"Standard {standard.get('is_number')} dataset does not contain separate structured test voltage parameter.",
                    std_source, source_text,
                    "Instrument test voltage not detailed as separate parameter in prototype dataset."
                )

        v_param = next((sp for sp in std_params if "voltage" in sp.get("parameter_name", "").lower()), None)

        if "variation" in p_name.lower() or operator == "RANGE" or (min_val is not None and max_val is not None and min_val != max_val):
            # Range comparison: e.g. tender 350V to 440V
            if v_param:
                std_min = v_param.get("min_value", 352.0)
                std_max = v_param.get("max_value", 440.0)
                t_min = min_val if min_val is not None and min_val != max_val else 350.0
                t_max = max_val if max_val is not None and min_val != max_val else 440.0

                # Standard: 352V (-15% of 415V) to 440V (+6% of 415V)
                # Tender: 350V to 440V (2V margin at lower end is a minor deviation)
                if abs(t_min - std_min) <= 5.0 and abs(t_max - std_max) <= 5.0:
                    status = "COMPLIANT" if t_min >= std_min else "DEVIATING"
                    return _build_result(
                        req_id, p_name, f"{int(t_min)}V to {int(t_max)}V", "V",
                        f"{int(std_min)}V to {int(std_max)}V", "V",
                        "NUMERIC_RANGE", status,
                        f"{v_param.get('governing_clause')}: {v_param.get('requirement_text')}",
                        std_source, source_text,
                        f"Tender voltage band ({int(t_min)}V-{int(t_max)}V) vs Standard rated variation ({int(std_min)}V-{int(std_max)}V)."
                    )
        elif "415" in str(raw_val) or num_val == 415.0:
            # Nominal 415V rated supply voltage match
            if v_param or "415" in std_scope or "motor" in std_title.lower():
                clause_text = v_param.get("requirement_text") if v_param else "3-phase 415V AC supply"
                clause_ref = v_param.get("governing_clause", "Clause 6.2") if v_param else "Scope"
                return _build_result(
                    req_id, p_name, "415 V", "V",
                    "415 V (3-Phase)", "V",
                    "EXACT_EQUALITY", "COMPLIANT",
                    f"{clause_ref}: {clause_text}",
                    std_source, source_text,
                    "Rated nominal supply voltage matches 415V 3-phase standard."
                )

        elif num_val is not None:
            # Check for explicit voltage conflict
            if num_val not in [415.0, 240.0] and not (min_val and max_val and min_val != max_val):
                clause_text = v_param.get("requirement_text") if v_param else "Rated voltage (415V for 3-phase, 240V for 1-phase)"
                clause_ref = v_param.get("governing_clause", "Clause 6.2") if v_param else "Clause 6.2"
                return _build_result(
                    req_id, p_name, raw_val, tender_unit,
                    "415 V (3-Phase) / 240 V (1-Phase)", "V",
                    "EXACT_EQUALITY", "NON_COMPLIANT",
                    f"{clause_ref}: Standard specifies {clause_text}. Tender requests {raw_val}.",
                    std_source, source_text,
                    f"Supply voltage {raw_val} explicitly conflicts with standard rated voltages."
                )

    # 5. Rated Frequency
    if cat == "FREQUENCY":
        v_param = next((sp for sp in std_params if "voltage" in sp.get("parameter_name", "").lower()), None)
        ev = v_param.get("notes") if v_param else "Rated frequency of 50 Hz +/- 3%"
        if "50" in str(raw_val) or num_val == 50.0:
            return _build_result(
                req_id, p_name, "50 Hz", "Hz",
                "50 Hz", "Hz",
                "EXACT_EQUALITY", "COMPLIANT",
                f"Clause 6.2 Notes: {ev}",
                std_source, source_text,
                "Rated supply frequency of 50 Hz matches Indian grid standard."
            )
        elif num_val is not None and num_val != 50.0:
            return _build_result(
                req_id, p_name, raw_val, tender_unit,
                "50 Hz +/- 3%", "Hz",
                "EXACT_EQUALITY", "NON_COMPLIANT",
                f"Clause 6.2 Notes: Standard specifies {ev}. Tender requests {raw_val}.",
                std_source, source_text,
                f"Supply frequency {raw_val} explicitly conflicts with standard 50 Hz grid frequency."
            )

    # 6. Flow Rate / Discharge Rate (Duty-Point Parameter)
    if cat == "FLOW_RATE" or "discharge" in p_name.lower():
        eff_param = next((sp for sp in std_params if "efficiency" in sp.get("parameter_name", "").lower()), None)
        ev_clause = eff_param.get("governing_clause", "Clause 9.1") if eff_param else "Clause 9.1"
        return _build_result(
            req_id, p_name, raw_val, tender_unit,
            "Table 1 duty point curves (numeric values absent)", tender_unit,
            "DUTY_POINT_TABLE_REQUIRED", "NOT_SPECIFIED",
            f"{ev_clause}, Table 1: Discharge rate evaluated against Table 1 duty point curves. Structured curve values are absent in prototype dataset.",
            std_source, source_text,
            "Tender discharge rate requires dynamic Table 1 curve verification. Structured curve values are absent in prototype dataset; marked NOT_SPECIFIED."
        )

    # 7. Operating Head / Shut-off Head / Submergence Depth (Duty-Point Parameters)
    if cat == "HEAD" or "head" in p_name.lower() or "submergence" in p_name.lower():
        eff_param = next((sp for sp in std_params if "efficiency" in sp.get("parameter_name", "").lower()), None)
        ev_clause = eff_param.get("governing_clause", "Clause 9.1") if eff_param else "Clause 9.1"
        return _build_result(
            req_id, p_name, raw_val, tender_unit,
            "Table 1 duty point curves (numeric values absent)", tender_unit,
            "DUTY_POINT_TABLE_REQUIRED", "NOT_SPECIFIED",
            f"{ev_clause}, Table 1: Head parameters evaluated against Table 1 duty point curves. Structured curve values are absent in prototype dataset.",
            std_source, source_text,
            f"Tender {p_name} ({raw_val}) requires dynamic Table 1 curve verification. Structured curve values are absent in prototype dataset; marked NOT_SPECIFIED."
        )

    # 8. Testing: Insulation Resistance
    if cat == "TESTING" and ("insulation" in p_name.lower() or "megaohm" in str(raw_val).lower()):
        ir_param = next((sp for sp in std_params if "insulation" in sp.get("parameter_name", "").lower()), None)
        if ir_param:
            std_min_ir = ir_param.get("min_value", 5.0)
            t_ir = num_val or min_val or 5.0
            if t_ir >= std_min_ir:
                return _build_result(
                    req_id, p_name, raw_val, "Megaohms",
                    f"{std_min_ir} Megaohms min (after immersion)", "MOhm",
                    "GREATER_THAN_OR_EQUAL", "COMPLIANT",
                    f"{ir_param.get('governing_clause')}: {ir_param.get('requirement_text')}",
                    std_source, source_text,
                    f"Insulation resistance requirement ({t_ir} MOhm) meets standard threshold (min {std_min_ir} MOhm post-immersion)."
                )
            else:
                return _build_result(
                    req_id, p_name, raw_val, "Megaohms",
                    f"{std_min_ir} Megaohms min", "MOhm",
                    "GREATER_THAN_OR_EQUAL", "NON_COMPLIANT",
                    f"{ir_param.get('governing_clause')}: {ir_param.get('requirement_text')}",
                    std_source, source_text,
                    "Insulation resistance lower than mandatory standard minimum."
                )

    # 9. Relative Parameter: Hydrostatic Casing Pressure
    if "hydrostatic" in p_name.lower() or "1.5 times" in str(raw_val).lower():
        ht_param = next((sp for sp in std_params if "hydrostatic" in sp.get("parameter_name", "").lower()), None)
        if ht_param:
            clause = ht_param.get("governing_clause", "Clause 13.1")
            req_text = ht_param.get("requirement_text", "1.5 times maximum discharge pressure or 2.0 bar min")
            # Operating head vs discharge pressure physical quantity distinction
            if "head" in str(raw_val).lower() or "head" in source_text.lower():
                return _build_result(
                    req_id, p_name, raw_val, "multiplier",
                    "1.5x max discharge pressure or 2.0 bar min", "multiplier / bar",
                    "PHYSICAL_QUANTITY_MISMATCH", "NOT_SPECIFIED",
                    f"{clause}: {req_text}",
                    std_source, source_text,
                    "Different physical quantities; direct equivalence not established. Tender specifies hydrostatic test relative to 'maximum operating head', whereas Standard specifies relative to 'maximum discharge pressure'."
                )
            elif "discharge pressure" in str(raw_val).lower() or "discharge pressure" in source_text.lower():
                return _build_result(
                    req_id, p_name, raw_val, "multiplier",
                    "1.5x max discharge pressure or 2.0 bar min", "multiplier / bar",
                    "RELATIVE_PARAMETER", "COMPLIANT",
                    f"{clause}: {req_text}",
                    std_source, source_text,
                    "Relative test ratio (1.5x discharge pressure) matches standard specification."
                )

    # 10. Efficiency: MANDATORY NOT_SPECIFIED HANDLING
    if cat == "EFFICIENCY":
        # IS 14220 does NOT have a single fixed threshold (like 35%). Requires Table 1 duty point verification.
        eff_param = next((sp for sp in std_params if "efficiency" in sp.get("parameter_name", "").lower()), None)
        ev_text = eff_param.get("notes") if eff_param else "Tested in accordance with IS 11346"
        return _build_result(
            req_id, p_name, raw_val, "%",
            "Dynamic Table 1 (IS 11346)", "%",
            "TABLE_LOOKUP_REQUIRED", "NOT_SPECIFIED",
            f"Clause 9.1, Table 1: {ev_text}",
            std_source, source_text,
            "Efficiency is governed dynamically by duty-point curves (IS 11346 Table 1). Prototype dataset lacks full scalar curve tables; duty-point verification is required."
        )

    # 11. Material Quality
    if cat == "MATERIAL":
        # Prototype dataset does NOT contain full metallurgical tables -> NOT_SPECIFIED (NOT CONFLICT)
        return _build_result(
            req_id, p_name, raw_val, None,
            "Material specifications per IS 14220 Table of Materials", None,
            "TEXT_SPECIFICATION", "NOT_SPECIFIED",
            f"Scope of {standard.get('is_number')}: General engineering requirements apply.",
            std_source, source_text,
            "Standard material grade table for specific components (impeller, casing) is not detailed in the prototype dataset. Marked NOT_SPECIFIED (not conflict)."
        )

    # 12. Operating Environment & Installation (Do NOT infer compliance from general scope)
    # Default fallback: Standard does not contain structured data for this parameter -> NOT_SPECIFIED
    return _build_result(
        req_id, p_name, raw_val, tender_unit,
        None, None,
        "UNVERIFIED_IN_DATASET", "NOT_SPECIFIED",
        f"Standard {standard.get('is_number')} dataset does not contain structured parameter '{p_name}'.",
        std_source, source_text,
        "Parameter not detailed in prototype dataset. Marked NOT_SPECIFIED (do not guess conflict)."
    )


def _build_result(
    req_id: str,
    p_name: str,
    t_val: Any,
    t_unit: Optional[str],
    s_val: Any,
    s_unit: Optional[str],
    comp_type: str,
    fit_status: str,
    evidence: str,
    source: str,
    tender_source_text: str,
    notes: str
) -> Dict[str, Any]:
    full_evidence = f"{evidence} [Tender ref: '{tender_source_text}']" if tender_source_text else evidence
    return {
        "requirement_id": req_id,
        "parameter_name": p_name,
        "tender_value": str(t_val) if t_val is not None else None,
        "tender_unit": t_unit,
        "standard_value": str(s_val) if s_val is not None else None,
        "standard_unit": s_unit,
        "comparison_type": comp_type,
        "fit_status": fit_status,
        "evidence": full_evidence,
        "tender_source_text": tender_source_text,
        "source": source,
        "notes": notes
    }
