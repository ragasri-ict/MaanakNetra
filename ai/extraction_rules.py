"""
Deterministic Extraction Rules & Pattern Matchers for MAANAKNETRA.
Provides strict regex-based parameter extraction, IS reference parsing,
unit normalization, dual-unit handling, range detection, and mandatory clause classification.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

# Indian Standard Citation Regex: matches IS 14220, IS 14220:1994, IS 6595 (Part 1):2018, IS:694, etc.
IS_REFERENCE_REGEX = re.compile(
    r"\b(IS\s*:?\s*(\d{3,5}(?:\s*\([A-Za-z0-9/ ]+\))?)(?:\s*:\s*(\d{4}))?(?:\s+[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)?)?)\b",
    re.IGNORECASE
)

# Mandatory phrasing indicators
MANDATORY_REGEX = re.compile(
    r"\b(shall|must|required|mandatory|minimum|maximum|not less than|not exceeding|at least|strictly)\b",
    re.IGNORECASE
)

# Operator detection patterns
OP_GTE_REGEX = re.compile(r"\b(minimum|min|not less than|at least|no less than|>=)\b", re.IGNORECASE)
OP_LTE_REGEX = re.compile(r"\b(maximum|max|not exceeding|up to|not more than|<=)\b", re.IGNORECASE)
OP_RANGE_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*(?:V|kW|m|mm)?\s*(?:to|-)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)

# Technical parameter pattern specifications: (category, field, parameter_name, regex, default_unit, operator_hint)
PARAMETER_PATTERNS = [
    {
        "category": "POWER",
        "field": "Electrical",
        "parameter_name": "Rated Power Output",
        "regex": re.compile(r"\b(\d+(?:\.\d+)?)\s*(kW|HP|BHP|MW|W)\b", re.IGNORECASE),
        "default_unit": "kW"
    },
    {
        "category": "VOLTAGE",
        "field": "Electrical",
        "parameter_name": "Rated Supply Voltage",
        "regex": re.compile(r"\b(\d{3,4})\s*(?:V|Volts?)\b", re.IGNORECASE),
        "default_unit": "V"
    },
    {
        "category": "FREQUENCY",
        "field": "Electrical",
        "parameter_name": "Rated Supply Frequency",
        "regex": re.compile(r"\b(\d{2}(?:\.\d+)?)\s*(?:Hz)\b", re.IGNORECASE),
        "default_unit": "Hz"
    },
    {
        "category": "FLOW_RATE",
        "field": "Mechanical / Hydraulic",
        "parameter_name": "Discharge Rate at Duty Point",
        "regex": re.compile(r"\b(\d+(?:\.\d+)?)\s*(L/sec|Lps|litres?\s*per\s*second|m3/hr|m³/hr|m3/h|m³/h)\b", re.IGNORECASE),
        "default_unit": "L/sec"
    },
    {
        "category": "HEAD",
        "field": "Mechanical / Hydraulic",
        "parameter_name": "Operating Head / Dynamic Head",
        "regex": re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:Meters?|m)\s*(?:Head|Total Dynamic Head|TDH|shut-off)?\b", re.IGNORECASE),
        "default_unit": "m"
    },
    {
        "category": "EFFICIENCY",
        "field": "Performance",
        "parameter_name": "Overall Pumpset Efficiency",
        "regex": re.compile(r"\b(\d+(?:\.\d+)?)\s*(%|percent)(?![a-zA-Z0-9])", re.IGNORECASE),
        "default_unit": "%"
    },
    {
        "category": "TEMPERATURE",
        "field": "Operating Environment",
        "parameter_name": "Maximum Water Temperature",
        "regex": re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:°|º|\ufffd)?\s*(?:C|deg\s*C|degrees?\s*Celsius)\b", re.IGNORECASE),
        "default_unit": "deg C"
    },
    {
        "category": "TESTING",
        "field": "Electrical / Insulation",
        "parameter_name": "Insulation Resistance",
        "regex": re.compile(r"\b(\d+(?:\.\d+)?)\s*(Megaohms?|MOhm|Mohm|MΩ)\b", re.IGNORECASE),
        "default_unit": "MOhm"
    },
    {
        "category": "SIZE/DIMENSION",
        "field": "Mechanical",
        "parameter_name": "Nominal Delivery Bore",
        "regex": re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:mm)\s*(?:nominal bore|NB)?\b", re.IGNORECASE),
        "default_unit": "mm"
    },
    {
        "category": "QUANTITY",
        "field": "Commercial / Supply",
        "parameter_name": "Procurement Quantity",
        "regex": re.compile(r"\b(\d+)\s*(?:units?|nos?|numbers?|sets?)\b", re.IGNORECASE),
        "default_unit": "units"
    }
]

# Dual-unit pattern matchers
DUAL_POWER_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(kW|MW|W)\s*\(\s*(\d+(?:\.\d+)?)\s*(HP|BHP)\s*\)",
    re.IGNORECASE
)
DUAL_POWER_INVERTED_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(HP|BHP)\s*\(\s*(\d+(?:\.\d+)?)\s*(kW|MW|W)\s*\)",
    re.IGNORECASE
)

DUAL_FLOW_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(L/sec|Lps|litres?\s*per\s*second)\s*\(\s*(\d+(?:\.\d+)?)\s*(m3/hr|m³/hr|m3/h|m³/h)\s*\)",
    re.IGNORECASE
)
DUAL_FLOW_INVERTED_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(m3/hr|m³/hr|m3/h|m³/h)\s*\(\s*(\d+(?:\.\d+)?)\s*(L/sec|Lps|litres?\s*per\s*second)\s*\)",
    re.IGNORECASE
)

# Voltage Range pattern matcher
VOLTAGE_RANGE_REGEX = re.compile(
    r"\b(?:voltage\s*band\s*of\s*)?(\d{3,4})\s*(?:V|Volts?)?\s*(?:to|-)\s*(\d{3,4})\s*(?:V|Volts?)\b",
    re.IGNORECASE
)

# Relative multiplier parameter matcher
RELATIVE_PARAM_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*times\s+(?:the\s+)?(maximum|minimum|rated|operating)?\s*([a-zA-Z\s]+?)(?=[.,;\n]|$)",
    re.IGNORECASE
)


def clean_character_encoding(text: str) -> str:
    """
    Cleans font encoding artifacts like replacement characters (U+FFFD or '?')
    in place of the degree symbol '°' in temperature contexts.
    """
    if not text:
        return text
    # Replace \ufffd or ? before C with °
    text = re.sub(r"(\d+(?:\.\d+)?)\s*[\ufffd\?]\s*C\b", r"\1°C", text)
    text = text.replace("\ufffdC", "°C").replace("\ufffd C", "°C")
    return text


def is_heading_only(text: str) -> bool:
    """
    Detects whether a text block is exclusively a section/clause heading
    without normative requirement statements or technical specifications.
    """
    clean = text.strip()
    if not clean:
        return False
    # Explicit section/part/chapter/annexure headers
    if re.match(r"^(SECTION|PART|CHAPTER|ANNEXURE|APPENDIX)\s+[0-9A-Z]+(\s*[:.-]\s*.*)?$", clean, re.IGNORECASE):
        # If it does not contain mandatory requirement modal verbs, it is a standalone header
        if not MANDATORY_REGEX.search(clean):
            return True
    # Short uppercase single line without modal verbs or digits
    lines = clean.splitlines()
    if len(lines) == 1 and len(clean.split()) <= 8 and clean.isupper():
        if not MANDATORY_REGEX.search(clean) and not re.search(r"\d", clean):
            return True
    return False


def extract_voltage_range(text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts continuous voltage operating band as a single RANGE requirement.
    Matches e.g. "350V to 440V" or "voltage band of 350V to 440V".
    """
    match = VOLTAGE_RANGE_REGEX.search(text)
    if not match:
        return None
    min_v = float(match.group(1))
    max_v = float(match.group(2))
    return {
        "category": "VOLTAGE",
        "field": "Electrical",
        "parameter_name": "Permissible Voltage Variation Band",
        "value": f"{int(min_v)}V to {int(max_v)}V",
        "unit": "V",
        "normalized_value": {
            "numeric_value": None,
            "min_value": min_v,
            "max_value": max_v,
            "unit": "V",
            "operator": "RANGE",
            "text_value": f"{min_v} to {max_v} V"
        },
        "notes": f"Continuous voltage variation band: {int(min_v)}V to {int(max_v)}V.",
        "span": match.span()
    }


def extract_dual_power(text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts dual-unit power specification (e.g., '7.5 kW (10.0 HP)') as ONE requirement.
    Preserves original, primary normalized value (kW), and alternate value/unit.
    """
    match = DUAL_POWER_REGEX.search(text)
    if match:
        kw_val = float(match.group(1))
        hp_val = float(match.group(3))
        kw_unit = match.group(2)
        hp_unit = match.group(4)
        return {
            "category": "POWER",
            "field": "Electrical",
            "parameter_name": "Rated Power Output",
            "value": match.group(0),
            "unit": kw_unit,
            "normalized_value": {
                "numeric_value": kw_val,
                "min_value": kw_val,
                "max_value": kw_val,
                "unit": kw_unit,
                "operator": "EQUAL",
                "text_value": f"{kw_val} {kw_unit}"
            },
            "notes": f"Dual-unit specification: {kw_val} {kw_unit} primary (alternate: {hp_val} {hp_unit}).",
            "span": match.span()
        }

    inv_match = DUAL_POWER_INVERTED_REGEX.search(text)
    if inv_match:
        hp_val = float(inv_match.group(1))
        kw_val = float(inv_match.group(3))
        hp_unit = inv_match.group(2)
        kw_unit = inv_match.group(4)
        return {
            "category": "POWER",
            "field": "Electrical",
            "parameter_name": "Rated Power Output",
            "value": inv_match.group(0),
            "unit": kw_unit,
            "normalized_value": {
                "numeric_value": kw_val,
                "min_value": kw_val,
                "max_value": kw_val,
                "unit": kw_unit,
                "operator": "EQUAL",
                "text_value": f"{kw_val} {kw_unit}"
            },
            "notes": f"Dual-unit specification: {kw_val} {kw_unit} primary (alternate: {hp_val} {hp_unit}).",
            "span": inv_match.span()
        }
    return None


def extract_dual_flow(text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts dual-unit flow rate specification (e.g., '18.0 Litres per Second (64.8 m³/hr)') as ONE requirement.
    Preserves original, primary normalized value (L/sec), and alternate value/unit.
    """
    match = DUAL_FLOW_REGEX.search(text)
    if match:
        lps_val = float(match.group(1))
        m3_val = float(match.group(3))
        lps_unit = match.group(2)
        m3_unit = match.group(4)
        return {
            "category": "FLOW_RATE",
            "field": "Mechanical / Hydraulic",
            "parameter_name": "Discharge Rate at Duty Point",
            "value": match.group(0),
            "unit": "L/sec",
            "normalized_value": {
                "numeric_value": lps_val,
                "min_value": lps_val,
                "max_value": lps_val,
                "unit": "L/sec",
                "operator": "EQUAL",
                "text_value": f"{lps_val} L/sec"
            },
            "notes": f"Dual-unit specification: {lps_val} L/sec primary (alternate: {m3_val} {m3_unit}).",
            "span": match.span()
        }

    inv_match = DUAL_FLOW_INVERTED_REGEX.search(text)
    if inv_match:
        m3_val = float(inv_match.group(1))
        lps_val = float(inv_match.group(3))
        m3_unit = inv_match.group(2)
        lps_unit = inv_match.group(4)
        return {
            "category": "FLOW_RATE",
            "field": "Mechanical / Hydraulic",
            "parameter_name": "Discharge Rate at Duty Point",
            "value": inv_match.group(0),
            "unit": "L/sec",
            "normalized_value": {
                "numeric_value": lps_val,
                "min_value": lps_val,
                "max_value": lps_val,
                "unit": "L/sec",
                "operator": "EQUAL",
                "text_value": f"{lps_val} L/sec"
            },
            "notes": f"Dual-unit specification: {lps_val} L/sec primary (alternate: {m3_val} {m3_unit}).",
            "span": inv_match.span()
        }
    return None


def extract_relative_parameter(text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts relative multiplier parameters (e.g. '1.5 times the maximum operating head').
    Preserves relative relationship without fabricating an absolute scalar pressure.
    """
    match = RELATIVE_PARAM_REGEX.search(text)
    if not match:
        return None
    multiplier = float(match.group(1))
    target_rel = (match.group(2) or "").strip() + " " + match.group(3).strip()
    target_clean = re.sub(r"\s+", " ", target_rel).strip()

    if "operating head" in text.lower() or "head" in text.lower():
        cat = "TESTING"
        field = "Mechanical / Testing"
        param_name = "Casing Hydrostatic Test Pressure Multiplier"
    else:
        cat = "OTHER_TECHNICAL_PARAMETER"
        field = "General Technical"
        param_name = f"Relative Parameter Multiplier ({target_clean.title()})"

    return {
        "category": cat,
        "field": field,
        "parameter_name": param_name,
        "value": match.group(0).strip(),
        "unit": "x multiplier",
        "normalized_value": {
            "numeric_value": multiplier,
            "min_value": multiplier,
            "max_value": multiplier,
            "unit": "x multiplier",
            "operator": "EQUAL",
            "text_value": f"{multiplier}x {target_clean}"
        },
        "notes": f"Relative multiplier: {multiplier}x {target_clean}. Traceable relative specification.",
        "span": match.span()
    }


def extract_cited_standards(text: str, page_number: int = 1) -> List[Dict[str, Any]]:
    """
    Extracts all explicit Indian Standard citations from raw text.
    Preserves raw citation, normalized standard code, edition year, and confidence.
    """
    citations = []
    seen = set()

    for match in IS_REFERENCE_REGEX.finditer(text):
        raw_match = match.group(1).strip()
        is_code_num = match.group(2).strip()
        year_str = match.group(3)

        # Normalize IS code: e.g. "IS: 14220" -> "IS 14220"
        clean_num = re.sub(r"IS\s*:?\s*", "", is_code_num, flags=re.IGNORECASE).strip()
        normalized_code = f"IS {clean_num}"
        year_val = int(year_str) if year_str and year_str.isdigit() else None

        key = (normalized_code, year_val)
        if key in seen:
            continue
        seen.add(key)

        # Find enclosing sentence
        sentence = _extract_enclosing_sentence(text, match.start(), match.end())

        citations.append({
            "citation_id": f"CITE_{len(citations) + 1:03d}",
            "raw_citation": raw_match,
            "standard_code": normalized_code,
            "part_number": None,
            "year_cited": year_val,
            "clause_reference": None,
            "source_text": sentence,
            "source_page": page_number,
            "extraction_confidence": 0.98
        })

    return citations


def is_requirement_mandatory(text: str) -> bool:
    """
    Evaluates whether a technical clause represents a mandatory requirement.
    Checks for presence of modal verbs 'shall', 'must', 'mandatory', 'minimum', etc.
    """
    return bool(MANDATORY_REGEX.search(text))


def normalize_numeric_value(val_str: str, unit: Optional[str], context_text: str) -> Dict[str, Any]:
    """
    Converts extracted string representation into a normalized machine-readable value object.
    Identifies bounds, operators (GTE, LTE, RANGE, EQUAL), and SI units.
    """
    # Check for range: e.g. "350V to 440V"
    range_match = OP_RANGE_REGEX.search(context_text)
    if range_match and ("to" in context_text.lower() or "band" in context_text.lower()):
        try:
            min_v = float(range_match.group(1))
            max_v = float(range_match.group(2))
            return {
                "numeric_value": None,
                "min_value": min_v,
                "max_value": max_v,
                "unit": unit,
                "operator": "RANGE",
                "text_value": f"{min_v} to {max_v} {unit or ''}".strip()
            }
        except (ValueError, TypeError):
            pass

    # Single numeric conversion
    try:
        clean_num = re.sub(r"[^\d.]", "", val_str)
        num_val = float(clean_num) if clean_num else None
    except ValueError:
        num_val = None

    if num_val is None:
        return {
            "numeric_value": None,
            "min_value": None,
            "max_value": None,
            "unit": unit,
            "operator": "TEXT_EXACT",
            "text_value": val_str.strip()
        }

    # Determine operator from context
    if OP_GTE_REGEX.search(context_text):
        return {
            "numeric_value": num_val,
            "min_value": num_val,
            "max_value": None,
            "unit": unit,
            "operator": "GTE",
            "text_value": f">={num_val} {unit or ''}".strip()
        }
    elif OP_LTE_REGEX.search(context_text):
        return {
            "numeric_value": num_val,
            "min_value": None,
            "max_value": num_val,
            "unit": unit,
            "operator": "LTE",
            "text_value": f"<={num_val} {unit or ''}".strip()
        }
    else:
        return {
            "numeric_value": num_val,
            "min_value": num_val,
            "max_value": num_val,
            "unit": unit,
            "operator": "EQUAL",
            "text_value": f"{num_val} {unit or ''}".strip()
        }


def _extract_enclosing_sentence(text: str, start: int, end: int) -> str:
    """Extracts the complete sentence containing the match offsets."""
    start_pos = text.rfind("\n", 0, start)
    if start_pos == -1:
        start_pos = 0
    else:
        start_pos += 1

    end_pos = text.find("\n", end)
    if end_pos == -1:
        end_pos = len(text)

    snippet = text[start_pos:end_pos].strip()
    return snippet if snippet else text[start:end]
