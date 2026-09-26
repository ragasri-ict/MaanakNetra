"""
Engineering Unit Normalization and Conversion Utility for MAANAKNETRA.
Provides deterministic, mathematically safe conversions between procurement units
and standard SI/engineering units while strictly preserving original values.
"""

from typing import Dict, Any, Optional, Tuple


# Conversion factors to canonical SI/engineering units
# Power -> kW
POWER_CONVERSIONS = {
    "kw": (1.0, "kW"),
    "w": (0.001, "kW"),
    "mw": (1000.0, "kW"),
    "hp": (0.7457, "kW"),
    "bhp": (0.7457, "kW"),
}

# Voltage -> V
VOLTAGE_CONVERSIONS = {
    "v": (1.0, "V"),
    "volt": (1.0, "V"),
    "volts": (1.0, "V"),
    "kv": (1000.0, "V"),
    "mv": (0.001, "V"),
}

# Flow Rate -> L/sec
FLOW_CONVERSIONS = {
    "l/sec": (1.0, "L/sec"),
    "lps": (1.0, "L/sec"),
    "litres per second": (1.0, "L/sec"),
    "litre per second": (1.0, "L/sec"),
    "litres/second": (1.0, "L/sec"),
    "m3/hr": (1.0 / 3.6, "L/sec"),
    "m³/hr": (1.0 / 3.6, "L/sec"),
    "m3/h": (1.0 / 3.6, "L/sec"),
    "m³/h": (1.0 / 3.6, "L/sec"),
}

# Pressure -> bar
PRESSURE_CONVERSIONS = {
    "bar": (1.0, "bar"),
    "mpa": (10.0, "bar"),
    "kpa": (0.01, "bar"),
    "kg/cm2": (0.980665, "bar"),
    "kg/cm²": (0.980665, "bar"),
}

# Insulation Resistance -> MOhm
RESISTANCE_CONVERSIONS = {
    "mohm": (1.0, "MOhm"),
    "megaohm": (1.0, "MOhm"),
    "megaohms": (1.0, "MOhm"),
    "mω": (1.0, "MOhm"),
    "kohm": (0.001, "MOhm"),
    "ohm": (1e-6, "MOhm"),
}


def normalize_unit_and_value(
    value: Optional[float],
    unit: Optional[str],
    category: str
) -> Dict[str, Any]:
    """
    Normalizes a numerical value and unit into standard engineering units.
    Preserves original value and notes any conversion formula applied.
    """
    if value is None or not unit:
        return {
            "original_value": value,
            "original_unit": unit,
            "normalized_value": value,
            "normalized_unit": unit,
            "conversion_ratio": 1.0,
            "conversion_applied": None
        }

    clean_unit = unit.strip().lower()
    cat_upper = category.upper()

    conv_table = {}
    if cat_upper == "POWER":
        conv_table = POWER_CONVERSIONS
    elif cat_upper == "VOLTAGE":
        conv_table = VOLTAGE_CONVERSIONS
    elif cat_upper == "FLOW_RATE":
        conv_table = FLOW_CONVERSIONS
    elif cat_upper == "PRESSURE":
        conv_table = PRESSURE_CONVERSIONS
    elif cat_upper == "TESTING" and any(u in clean_unit for u in ["ohm", "ω"]):
        conv_table = RESISTANCE_CONVERSIONS

    if clean_unit in conv_table:
        factor, target_unit = conv_table[clean_unit]
        norm_val = round(value * factor, 4)
        conversion_applied = f"{value} {unit} * {factor} = {norm_val} {target_unit}"
        return {
            "original_value": value,
            "original_unit": unit,
            "normalized_value": norm_val,
            "normalized_unit": target_unit,
            "conversion_ratio": factor,
            "conversion_applied": conversion_applied
        }

    # Default if no specific conversion rule
    return {
        "original_value": value,
        "original_unit": unit,
        "normalized_value": value,
        "normalized_unit": unit,
        "conversion_ratio": 1.0,
        "conversion_applied": None
    }
