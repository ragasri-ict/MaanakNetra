"""
Requirement Extraction Engine for MAANAKNETRA.
Consumes DocumentResult from backend.ingestion and extracts:
1. Product & Procurement Context
2. Explicitly Cited Indian Standards (AlreadyCitedStandard)
3. Technical Specifications & Tolerances (RequirementItem)
Strictly adheres to contracts/requirements.schema.json.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from .extraction_rules import (
    extract_cited_standards,
    is_requirement_mandatory,
    normalize_numeric_value,
    clean_character_encoding,
    is_heading_only,
    extract_voltage_range,
    extract_dual_power,
    extract_dual_flow,
    extract_relative_parameter,
    PARAMETER_PATTERNS
)

# Specific domain keyword hints for category classification
CATEGORY_KEYWORD_MAP = {
    "EFFICIENCY": ["efficiency", "wire-to-water", "overall efficiency"],
    "FLOW_RATE": ["discharge", "flow rate", "l/sec", "lps", "m3/hr", "m³/hr"],
    "HEAD": ["head", "dynamic head", "shut-off", "meters head", "total head"],
    "POWER": ["power", "kw", "hp", "output rating", "capacity"],
    "VOLTAGE": ["voltage", "volts", "supply voltage", "3-phase", "415 v"],
    "FREQUENCY": ["frequency", "hz", "cycles"],
    "TEMPERATURE": ["temperature", "water temperature", "ambient", "°c", "deg c"],
    "MATERIAL": ["material", "casing", "impeller", "shaft", "stainless steel", "cast iron", "bronze"],
    "INSTALLATION": ["mounting", "bed", "pedestal", "suspension", "flanged", "delivery bore"],
    "TESTING": ["test", "testing", "megger", "insulation resistance", "hydrostatic", "routine test"],
    "SAFETY": ["safety", "protection", "thermal overload", "grounding", "earthing"]
}


def extract_requirements(document_result: Any) -> Dict[str, Any]:
    """
    Primary requirement extraction pipeline entry point.
    Consumes DocumentResult (or dict) and returns structured requirements document
    conforming strictly to contracts/requirements.schema.json.
    """
    if hasattr(document_result, "to_dict"):
        doc_data = document_result.to_dict()
    elif isinstance(document_result, dict):
        doc_data = document_result
    else:
        doc_data = {
            "document_id": getattr(document_result, "document_id", "DOC_UNKNOWN"),
            "filename": getattr(document_result, "filename", "unknown"),
            "page_count": getattr(document_result, "page_count", 1),
            "extracted_text": getattr(document_result, "extracted_text", ""),
            "pages": getattr(document_result, "pages", [])
        }

    full_text = clean_character_encoding(doc_data.get("extracted_text", ""))
    pages = doc_data.get("pages", [])

    meta = _extract_document_metadata(doc_data, full_text)
    product_ctx = _extract_product_context(full_text)
    already_cited_standards = _extract_all_cited_standards(pages, full_text)
    extracted_requirements = _extract_technical_requirements(pages, product_ctx["primary_item_name"])

    return {
        "document_metadata": meta,
        "product_context": product_ctx,
        "extracted_requirements": extracted_requirements,
        "already_cited_standards": already_cited_standards
    }


def _extract_document_metadata(doc_data: Dict[str, Any], full_text: str) -> Dict[str, Any]:
    title = "Tender Specification"
    procuring_entity = None

    for line in full_text.splitlines():
        line_clean = line.strip()
        if "SUBJECT:" in line_clean.upper():
            title = re.sub(r"^SUBJECT:\s*", "", line_clean, flags=re.IGNORECASE).strip()
            break
        elif "TENDER NOTICE" in line_clean.upper() and len(line_clean) > 20:
            title = line_clean

    for line in full_text.splitlines():
        line_clean = line.strip()
        if "DEPARTMENT:" in line_clean.upper() or "PROCURING AUTHORITY:" in line_clean.upper():
            procuring_entity = re.sub(r"^(DEPARTMENT|PROCURING AUTHORITY):\s*", "", line_clean, flags=re.IGNORECASE).strip()
            break

    return {
        "document_id": doc_data.get("document_id", "DOC_UNKNOWN"),
        "document_title": title,
        "file_name": doc_data.get("filename", "unknown"),
        "page_count": doc_data.get("page_count", 1),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "procuring_entity": procuring_entity
    }


def _extract_product_context(full_text: str) -> Dict[str, Any]:
    lower_text = full_text.lower()

    if "openwell submersible" in lower_text or "openwell pumpset" in lower_text:
        item = "Openwell Submersible Pumpsets"
        cat = "Mechanical / Water Supply & Pumping Systems"
        summary = "Procurement of electric motor-driven openwell submersible pumpsets for community drinking water."
    elif "submersible pumpset" in lower_text or "borehole pump" in lower_text:
        item = "Submersible Pumpsets"
        cat = "Mechanical / Deepwell Pumps"
        summary = "Procurement of borehole / deepwell submersible pumpsets."
    elif "monobloc" in lower_text or "monoset" in lower_text:
        item = "Monoset Pumps"
        cat = "Mechanical / Agricultural Pumps"
        summary = "Procurement of monoset centrifugal pumps for clear, cold water."
    else:
        item = "General Industrial Equipment"
        cat = "Engineering & Procurement"
        summary = "Technical specification for procurement."

    return {
        "primary_item_name": item,
        "category": cat,
        "summary": summary
    }


def _extract_all_cited_standards(pages: List[Dict[str, Any]], full_text: str) -> List[Dict[str, Any]]:
    citations: List[Dict[str, Any]] = []
    seen = set()

    for page in pages:
        p_num = page.get("page_number", 1)
        p_text = clean_character_encoding(page.get("text", ""))
        page_citations = extract_cited_standards(p_text, page_number=p_num)

        for c in page_citations:
            key = (c["standard_code"], c["year_cited"])
            if key not in seen:
                seen.add(key)
                citations.append(c)

    if not citations:
        citations = extract_cited_standards(full_text, page_number=1)

    return citations


def _extract_technical_requirements(pages: List[Dict[str, Any]], product_name: str) -> List[Dict[str, Any]]:
    requirements: List[Dict[str, Any]] = []
    req_counter = 1

    for page in pages:
        p_num = page.get("page_number", 1)
        raw_blocks = page.get("blocks", [])

        # Decompose blocks into granular clauses if multiple clause headers exist in one block
        atomic_blocks = []
        for b in raw_blocks:
            b_text = clean_character_encoding(b.get("text", "").strip())
            # Split if block contains multiple numbered sub-clauses (e.g. \n1.2 or \n2.1)
            sub_clauses = re.split(r"\n(?=\d+\.\d+|\bClause\s+\d+)", b_text)
            for sc in sub_clauses:
                clean_sc = sc.strip()
                if clean_sc:
                    c_match = re.match(r"^(\d+\.\d+|Clause\s+\d+(\.\d+)*|SECTION\s+\d+)", clean_sc, re.IGNORECASE)
                    c_num = c_match.group(1) if c_match else b.get("clause_number")
                    atomic_blocks.append({
                        "clause_number": c_num,
                        "text": clean_sc,
                        "page_number": p_num,
                        "char_start": b.get("char_start"),
                        "char_end": b.get("char_end")
                    })

        for block in atomic_blocks:
            b_text = block.get("text", "").strip()
            if not b_text or len(b_text) < 10:
                continue

            # 1. Heading check: exclude pure section/part headers
            if is_heading_only(b_text):
                continue

            # Ignore non-specification header and footer banners
            if any(k in b_text.lower() for k in ["end of synthetic", "demonstration data", "tender notice ref"]):
                continue

            clause_num = block.get("clause_number")
            is_mand = is_requirement_mandatory(b_text)
            char_s = block.get("char_start")
            char_e = block.get("char_end")

            matched_in_block = False
            consumed_spans = []

            def is_span_consumed(start: int, end: int) -> bool:
                for cs, ce in consumed_spans:
                    if max(start, cs) < min(end, ce):
                        return True
                return False

            # Priority 1: Check Continuous Voltage Variation Range
            volt_range = extract_voltage_range(b_text)
            if volt_range:
                requirements.append({
                    "requirement_id": f"REQ_{req_counter:03d}",
                    "field": volt_range["field"],
                    "category": volt_range["category"],
                    "parameter_name": volt_range["parameter_name"],
                    "value": volt_range["value"],
                    "unit": volt_range["unit"],
                    "normalized_value": volt_range["normalized_value"],
                    "product_category_context": product_name,
                    "is_mandatory": is_mand,
                    "source_text": b_text,
                    "source_location": {
                        "source_page": p_num,
                        "clause_number": clause_num,
                        "line_number": None,
                        "table_identifier": None,
                        "char_start": char_s,
                        "char_end": char_e,
                        "bounding_box": None
                    },
                    "extraction_confidence": 0.95,
                    "notes": volt_range["notes"]
                })
                req_counter += 1
                matched_in_block = True
                consumed_spans.append(volt_range["span"])

            # Priority 2: Check Dual-Unit Power (e.g. 7.5 kW (10.0 HP))
            dual_power = extract_dual_power(b_text)
            if dual_power:
                requirements.append({
                    "requirement_id": f"REQ_{req_counter:03d}",
                    "field": dual_power["field"],
                    "category": dual_power["category"],
                    "parameter_name": dual_power["parameter_name"],
                    "value": dual_power["value"],
                    "unit": dual_power["unit"],
                    "normalized_value": dual_power["normalized_value"],
                    "product_category_context": product_name,
                    "is_mandatory": is_mand,
                    "source_text": b_text,
                    "source_location": {
                        "source_page": p_num,
                        "clause_number": clause_num,
                        "line_number": None,
                        "table_identifier": None,
                        "char_start": char_s,
                        "char_end": char_e,
                        "bounding_box": None
                    },
                    "extraction_confidence": 0.95,
                    "notes": dual_power["notes"]
                })
                req_counter += 1
                matched_in_block = True
                consumed_spans.append(dual_power["span"])

            # Priority 3: Check Dual-Unit Flow (e.g. 18.0 Litres per Second (64.8 m³/hr))
            dual_flow = extract_dual_flow(b_text)
            if dual_flow:
                requirements.append({
                    "requirement_id": f"REQ_{req_counter:03d}",
                    "field": dual_flow["field"],
                    "category": dual_flow["category"],
                    "parameter_name": dual_flow["parameter_name"],
                    "value": dual_flow["value"],
                    "unit": dual_flow["unit"],
                    "normalized_value": dual_flow["normalized_value"],
                    "product_category_context": product_name,
                    "is_mandatory": is_mand,
                    "source_text": b_text,
                    "source_location": {
                        "source_page": p_num,
                        "clause_number": clause_num,
                        "line_number": None,
                        "table_identifier": None,
                        "char_start": char_s,
                        "char_end": char_e,
                        "bounding_box": None
                    },
                    "extraction_confidence": 0.95,
                    "notes": dual_flow["notes"]
                })
                req_counter += 1
                matched_in_block = True
                consumed_spans.append(dual_flow["span"])

            # Priority 4: Check Relative Parameter Multiplier (e.g. 1.5 times the maximum operating head)
            rel_param = extract_relative_parameter(b_text)
            if rel_param:
                requirements.append({
                    "requirement_id": f"REQ_{req_counter:03d}",
                    "field": rel_param["field"],
                    "category": rel_param["category"],
                    "parameter_name": rel_param["parameter_name"],
                    "value": rel_param["value"],
                    "unit": rel_param["unit"],
                    "normalized_value": rel_param["normalized_value"],
                    "product_category_context": product_name,
                    "is_mandatory": is_mand,
                    "source_text": b_text,
                    "source_location": {
                        "source_page": p_num,
                        "clause_number": clause_num,
                        "line_number": None,
                        "table_identifier": None,
                        "char_start": char_s,
                        "char_end": char_e,
                        "bounding_box": None
                    },
                    "extraction_confidence": 0.95,
                    "notes": rel_param["notes"]
                })
                req_counter += 1
                matched_in_block = True
                consumed_spans.append(rel_param["span"])

            # 5. Match against remaining parameter patterns (skipping consumed spans)
            for pat in PARAMETER_PATTERNS:
                matches = list(pat["regex"].finditer(b_text))
                for m in matches:
                    if is_span_consumed(m.start(), m.end()):
                        continue

                    val_str = m.group(1)
                    matched_unit = m.group(2) if len(m.groups()) > 1 else pat["default_unit"]

                    norm_val = normalize_numeric_value(val_str, matched_unit, b_text)

                    # Distinct parameter naming for special cases
                    param_name = pat["parameter_name"]
                    if "shut-off" in b_text.lower() and pat["category"] == "HEAD":
                        param_name = "Minimum Shut-off Head"
                    elif "dynamic head" in b_text.lower() and pat["category"] == "HEAD":
                        param_name = "Rated Operating Head"
                    elif "submergence depth" in b_text.lower() and pat["category"] == "HEAD":
                        param_name = "Maximum Submergence Depth"
                    elif "operating" in b_text.lower() and pat["category"] == "VOLTAGE" and "band" in b_text.lower():
                        param_name = "Permissible Voltage Variation Band"
                    elif "megger" in b_text.lower() and pat["category"] == "VOLTAGE":
                        param_name = "Megger Test Voltage"

                    requirements.append({
                        "requirement_id": f"REQ_{req_counter:03d}",
                        "field": pat["field"],
                        "category": pat["category"],
                        "parameter_name": param_name,
                        "value": m.group(0),
                        "unit": matched_unit,
                        "normalized_value": norm_val,
                        "product_category_context": product_name,
                        "is_mandatory": is_mand,
                        "source_text": b_text,
                        "source_location": {
                            "source_page": p_num,
                            "clause_number": clause_num,
                            "line_number": None,
                            "table_identifier": None,
                            "char_start": char_s,
                            "char_end": char_e,
                            "bounding_box": None
                        },
                        "extraction_confidence": 0.95,
                        "notes": f"Deterministic regex extraction ({pat['category']})."
                    })
                    req_counter += 1
                    matched_in_block = True
                    consumed_spans.append(m.span())

            # 6. Detect Qualitative / Vague Requirements or Installation clauses
            if not matched_in_block:
                category_detected, field_name = _classify_qualitative_clause(b_text)
                if category_detected:
                    requirements.append({
                        "requirement_id": f"REQ_{req_counter:03d}",
                        "field": field_name,
                        "category": category_detected,
                        "parameter_name": f"{category_detected.title()} Requirement",
                        "value": b_text[:120] + ("..." if len(b_text) > 120 else ""),
                        "unit": None,
                        "normalized_value": {
                            "numeric_value": None,
                            "min_value": None,
                            "max_value": None,
                            "unit": None,
                            "operator": "TEXT_EXACT",
                            "text_value": b_text
                        },
                        "product_category_context": product_name,
                        "is_mandatory": is_mand,
                        "source_text": b_text,
                        "source_location": {
                            "source_page": p_num,
                            "clause_number": clause_num,
                            "line_number": None,
                            "table_identifier": None,
                            "char_start": char_s,
                            "char_end": char_e,
                            "bounding_box": None
                        },
                        "extraction_confidence": 0.88,
                        "notes": "Qualitative specification clause."
                    })
                    req_counter += 1

    return requirements


def _classify_qualitative_clause(text: str) -> Tuple[Optional[str], str]:
    """
    Classifies a non-numeric clause into one of the controlled categories
    or returns OTHER_TECHNICAL_PARAMETER.
    """
    lower = text.lower()

    if any(k in lower for k in ["end of synthetic", "demonstration data", "tender notice ref"]):
        return None, "Document Metadata"
    elif any(k in lower for k in ["mounting", "pedestal", "suspension", "flanged"]):
        return "INSTALLATION", "Mechanical / Civil"
    elif any(k in lower for k in ["workmanship", "corrosion resistance", "commercial grade", "materials shall"]):
        return "MATERIAL", "Material Quality"
    elif any(k in lower for k in ["submerged", "drinking water", "ambient", "drawdown"]):
        return "OPERATING_ENVIRONMENT", "Environmental"
    elif any(k in lower for k in ["test certificate", "inspection officer", "witness", "routine test"]):
        return "TESTING", "Quality Assurance"
    elif "is 14220" in lower or "indian standard" in lower:
        return "EXISTING_IS_REFERENCE", "Compliance"
    elif len(text) > 25 and ("shall" in lower or "must" in lower):
        return "OTHER_TECHNICAL_PARAMETER", "General Specification"
    else:
        return None, "General"
