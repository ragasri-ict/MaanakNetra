"""
Test Suite for MAANAKNETRA Parameter Intelligence & Compatibility Engine (Step 7A).
Covers:
1. 415 V exact match
2. 350-440 V range comparison
3. 7.5 kW / 10 HP dual-unit handling
4. 33°C upper bound match
5. 18 L/s / 64.8 m³/hr flow rate match
6. 1.5x relative head multiplier handling
7. Missing material data -> NOT_SPECIFIED (no false conflict)
8. Unsupported efficiency table -> NOT_SPECIFIED (guardrail against false 35% comparison)
9. Explicit conflict detection (e.g. 75 kW or 50°C exceeding standard limits)
10. Anti-hallucination check for standard values and evidence
"""

import os
import sys
import json
import unittest

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion import ingest_document
from ai.requirement_extractor import extract_requirements
from ai.parameter_engine import (
    compare_parameter,
    ParameterCompatibilityEngine,
    normalize_unit_and_value
)


class TestParameterMatching(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pdf_path = os.path.join("demo", "sample_tender.pdf")
        cls.standards_path = os.path.join("data", "standards.json")
        assert os.path.exists(cls.pdf_path), "demo/sample_tender.pdf must exist"
        assert os.path.exists(cls.standards_path), "data/standards.json must exist"

        with open(cls.standards_path, "r", encoding="utf-8") as f:
            cls.standards = json.load(f)

        cls.is_14220 = next(s for s in cls.standards if s["is_number"] == "IS 14220")

        # Ingest and extract requirements from sample tender
        cls.doc = ingest_document(cls.pdf_path)
        cls.reqs_doc = extract_requirements(cls.doc)
        cls.extracted_reqs = cls.reqs_doc.get("extracted_requirements", [])

        # Execute parameter compatibility engine
        cls.engine = ParameterCompatibilityEngine()
        cls.eval_result = cls.engine.evaluate_standard_compatibility(
            cls.is_14220,
            cls.extracted_reqs,
            cls.reqs_doc.get("product_context")
        )
        cls.param_results = {r["parameter_name"]: r for r in cls.eval_result["parameter_results"]}

    def test_1_415v_exact_match(self):
        """Verify nominal 415V supply voltage matches standard 3-phase specification."""
        res = self.param_results.get("Rated Supply Voltage")
        self.assertIsNotNone(res)
        self.assertEqual(res["fit_status"], "COMPLIANT")
        self.assertEqual(res["comparison_type"], "EXACT_EQUALITY")
        self.assertIn("415", res["tender_value"])
        self.assertIn("415", res["standard_value"])
        self.assertIn("Clause 6.2", res["evidence"])

    def test_2_350_440v_range(self):
        """Verify 350V to 440V range comparison against standard 352V to 440V variation."""
        res = self.param_results.get("Permissible Voltage Variation Band")
        self.assertIsNotNone(res)
        self.assertIn(res["fit_status"], ["COMPLIANT", "DEVIATING"])
        self.assertEqual(res["comparison_type"], "NUMERIC_RANGE")
        self.assertIn("350V", res["tender_value"])
        self.assertIn("440V", res["tender_value"])
        self.assertIn("352", res["standard_value"])

    def test_3_7_5kw_10hp_dual_unit(self):
        """Verify dual-unit 7.5 kW (10.0 HP) is safely evaluated within standard scope (up to 45 kW)."""
        res = self.param_results.get("Rated Power Output")
        self.assertIsNotNone(res)
        self.assertEqual(res["fit_status"], "COMPLIANT")
        self.assertEqual(res["comparison_type"], "RANGE_CEILING")
        self.assertIn("7.5", res["tender_value"])
        self.assertIn("45", res["standard_value"])

    def test_4_33_deg_c(self):
        """Verify 33°C maximum temperature matches clear cold water scope ceiling."""
        res = self.param_results.get("Maximum Water Temperature")
        self.assertIsNotNone(res)
        self.assertEqual(res["fit_status"], "COMPLIANT")
        self.assertEqual(res["comparison_type"], "LESS_THAN_OR_EQUAL")
        self.assertIn("33", res["tender_value"])
        self.assertIn("33", res["standard_value"])

    def test_5_unsupported_flow_value_is_not_specified(self):
        """Verify discharge rate (18.0 L/s) returns NOT_SPECIFIED because dynamic Table 1 curve is absent."""
        res = self.param_results.get("Discharge Rate at Duty Point")
        self.assertIsNotNone(res)
        self.assertEqual(
            res["fit_status"],
            "NOT_SPECIFIED",
            "Flow rate without numeric Table 1 curves must return NOT_SPECIFIED"
        )
        self.assertEqual(res["comparison_type"], "DUTY_POINT_TABLE_REQUIRED")
        self.assertIn("Table 1", res["evidence"])

    def test_6_unsupported_head_value_is_not_specified(self):
        """Verify rated operating head (32.0m) returns NOT_SPECIFIED because dynamic Table 1 curve is absent."""
        res = self.param_results.get("Rated Operating Head")
        self.assertIsNotNone(res)
        self.assertEqual(
            res["fit_status"],
            "NOT_SPECIFIED",
            "Rated operating head without numeric Table 1 curves must return NOT_SPECIFIED"
        )
        self.assertEqual(res["comparison_type"], "DUTY_POINT_TABLE_REQUIRED")

    def test_7_unsupported_shut_off_head_is_not_specified(self):
        """Verify shut-off head (42.0m) returns NOT_SPECIFIED because dynamic Table 1 curve is absent."""
        res = self.param_results.get("Minimum Shut-off Head")
        self.assertIsNotNone(res)
        self.assertEqual(
            res["fit_status"],
            "NOT_SPECIFIED",
            "Shut-off head without numeric Table 1 curves must return NOT_SPECIFIED"
        )
        self.assertEqual(res["comparison_type"], "DUTY_POINT_TABLE_REQUIRED")

    def test_8_hydrostatic_head_vs_discharge_pressure_is_not_specified(self):
        """Verify 1.5x operating head vs 1.5x discharge pressure returns NOT_SPECIFIED due to physical quantity distinction."""
        # Find hydrostatic parameter in sample tender
        res = next((r for r in self.eval_result["parameter_results"] if "hydrostatic" in r["parameter_name"].lower()), None)
        self.assertIsNotNone(res)
        self.assertEqual(
            res["fit_status"],
            "NOT_SPECIFIED",
            "Hydrostatic head vs discharge pressure must return NOT_SPECIFIED without direct conversion"
        )
        self.assertEqual(res["comparison_type"], "PHYSICAL_QUANTITY_MISMATCH")
        self.assertIn("Different physical quantities; direct equivalence not established", res["notes"])

    def test_9_missing_material_data_is_not_specified(self):
        """Verify missing material details in dataset produce NOT_SPECIFIED, never false NON_COMPLIANT."""
        material_reqs = [r for r in self.eval_result["parameter_results"] if "material" in r["parameter_name"].lower()]
        self.assertGreater(len(material_reqs), 0)
        for m in material_reqs:
            self.assertEqual(
                m["fit_status"],
                "NOT_SPECIFIED",
                f"Missing material data must produce NOT_SPECIFIED, got {m['fit_status']}"
            )
            self.assertNotEqual(m["fit_status"], "NON_COMPLIANT")

    def test_10_unsupported_efficiency_table_is_not_specified(self):
        """Verify efficiency returns NOT_SPECIFIED to prevent false fixed scalar comparisons."""
        res = self.param_results.get("Overall Pumpset Efficiency")
        self.assertIsNotNone(res)
        self.assertEqual(
            res["fit_status"],
            "NOT_SPECIFIED",
            "Efficiency must return NOT_SPECIFIED because dynamic duty-point curve tables are required"
        )
        self.assertEqual(res["comparison_type"], "TABLE_LOOKUP_REQUIRED")
        self.assertIn("Table 1", res["notes"])

    def test_11_explicit_comparable_numeric_conflict(self):
        """Verify that genuine parameter contradictions trigger NON_COMPLIANT."""
        # 1. Temperature exceeding scope limit
        req_hot_water = {
            "requirement_id": "REQ_TEST_HOT",
            "category": "TEMPERATURE",
            "parameter_name": "Maximum Water Temperature",
            "value": "50°C",
            "unit": "deg C",
            "normalized_value": {"numeric_value": 50.0, "unit": "deg C", "operator": "LTE"},
            "source_text": "Water temperature not exceeding 50°C."
        }
        res_temp = compare_parameter(req_hot_water, self.is_14220)
        self.assertEqual(res_temp["fit_status"], "NON_COMPLIANT")
        self.assertIn("exceeds", res_temp["notes"].lower())

        # 2. Power exceeding scope ceiling (45 kW)
        req_high_power = {
            "requirement_id": "REQ_TEST_POWER",
            "category": "POWER",
            "parameter_name": "Rated Power Output",
            "value": "75 kW",
            "unit": "kW",
            "normalized_value": {"numeric_value": 75.0, "unit": "kW", "operator": "EQUAL"},
            "source_text": "75 kW continuous rated output."
        }
        res_power = compare_parameter(req_high_power, self.is_14220)
        self.assertEqual(res_power["fit_status"], "NON_COMPLIANT")
        self.assertIn("exceeds", res_power["notes"].lower())

        # 3. Supply frequency conflict (60 Hz vs standard 50 Hz)
        req_freq_60 = {
            "requirement_id": "REQ_TEST_FREQ",
            "category": "FREQUENCY",
            "parameter_name": "Rated Supply Frequency",
            "value": "60 Hz",
            "unit": "Hz",
            "normalized_value": {"numeric_value": 60.0, "unit": "Hz", "operator": "EQUAL"},
            "source_text": "Rated grid frequency 60 Hz."
        }
        res_freq = compare_parameter(req_freq_60, self.is_14220)
        self.assertEqual(res_freq["fit_status"], "NON_COMPLIANT")

        # 4. Insulation resistance conflict (< 5 MOhm)
        req_ir_low = {
            "requirement_id": "REQ_TEST_IR",
            "category": "TESTING",
            "parameter_name": "Insulation Resistance",
            "value": "2.0 Megaohms",
            "unit": "Megaohms",
            "normalized_value": {"numeric_value": 2.0, "unit": "MOhm", "operator": "GTE"},
            "source_text": "Insulation resistance minimum 2.0 Megaohms."
        }
        res_ir = compare_parameter(req_ir_low, self.is_14220)
        self.assertEqual(res_ir["fit_status"], "NON_COMPLIANT")

    def test_12_explicit_numeric_match(self):
        """Verify explicit verified parameters yield COMPLIANT."""
        # 415 V supply voltage
        res_v = self.param_results.get("Rated Supply Voltage")
        self.assertIsNotNone(res_v)
        self.assertEqual(res_v["fit_status"], "COMPLIANT")

        # 50 Hz frequency
        res_f = self.param_results.get("Rated Supply Frequency")
        self.assertIsNotNone(res_f)
        self.assertEqual(res_f["fit_status"], "COMPLIANT")

        # 5 MOhm insulation resistance
        res_ir = self.param_results.get("Insulation Resistance")
        self.assertIsNotNone(res_ir)
        self.assertEqual(res_ir["fit_status"], "COMPLIANT")


if __name__ == "__main__":
    unittest.main()
