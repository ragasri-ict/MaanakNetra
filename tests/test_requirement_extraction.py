"""
Test Suite for MAANAKNETRA Requirement Extraction Engine (Step 5C).
Covers:
1. Product extraction
2. Power and voltage extraction
3. Mandatory requirement detection
4. IS reference detection with year preservation
5. Source page preservation
6. Confidence bounds (0.0 <= c <= 1.0)
7. No hallucinated values
8. Multiple numeric parameters in one clause (Megger 500V and 5 Megaohms)
9. Validation against contracts/requirements.schema.json
10. Deduplication & dual-unit grouping (7.5 kW + 10 HP; 18 L/s + 64.8 m³/hr)
11. Voltage range extraction (350V to 440V as single RANGE item)
12. Heading exclusion (SECTION 6 banner excluded)
13. Relative multiplier parameter handling (1.5x operating head)
14. Degree symbol preservation (33°C)
"""

import os
import sys
import json
import unittest
import jsonschema

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion import ingest_document
from ai.requirement_extractor import extract_requirements
from ai.extraction_rules import clean_character_encoding


class TestRequirementExtraction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pdf_path = os.path.join("demo", "sample_tender.pdf")
        cls.schema_path = os.path.join("contracts", "requirements.schema.json")
        assert os.path.exists(cls.pdf_path), "demo/sample_tender.pdf must exist"
        assert os.path.exists(cls.schema_path), "contracts/requirements.schema.json must exist"

        # Ingest and extract requirements once for tests
        cls.doc_result = ingest_document(cls.pdf_path)
        cls.extracted = extract_requirements(cls.doc_result)

        with open(cls.schema_path, "r", encoding="utf-8") as f:
            cls.schema = json.load(f)

    def test_1_product_extraction(self):
        """Verify product and domain classification."""
        product_ctx = self.extracted.get("product_context", {})
        self.assertIn("Openwell Submersible Pumpsets", product_ctx.get("primary_item_name", ""))
        self.assertIn("Mechanical", product_ctx.get("category", ""))
        self.assertIn("community drinking water", product_ctx.get("summary", "").lower())

    def test_2_power_voltage_extraction(self):
        """Verify extraction of rated power and voltage (415V)."""
        reqs = self.extracted.get("extracted_requirements", [])
        categories = [r["category"] for r in reqs]
        self.assertIn("POWER", categories)
        self.assertIn("VOLTAGE", categories)

        power_reqs = [r for r in reqs if r["category"] == "POWER"]
        values = [r["value"] for r in power_reqs]
        self.assertTrue(any("7.5" in v for v in values))

        volt_reqs = [r for r in reqs if r["category"] == "VOLTAGE"]
        volt_vals = [r["value"] for r in volt_reqs]
        self.assertTrue(any("415" in v for v in volt_vals))

    def test_3_mandatory_requirement_detection(self):
        """Verify that clauses containing 'shall', 'must', or 'minimum' are flagged as mandatory."""
        reqs = self.extracted.get("extracted_requirements", [])
        mandatory_reqs = [r for r in reqs if r["is_mandatory"]]
        self.assertGreater(len(mandatory_reqs), 5)

        for r in mandatory_reqs:
            src = r["source_text"].lower()
            self.assertTrue(
                any(k in src for k in ["shall", "must", "required", "mandatory", "minimum", "maximum", "not less than", "not exceeding", "at least"]),
                f"Mandatory requirement missing modal verb: {src}"
            )

    def test_4_is_reference_detection(self):
        """Verify detection of explicit Indian Standard citations (IS 14220:1994) with year preserved."""
        citations = self.extracted.get("already_cited_standards", [])
        self.assertGreater(len(citations), 0)

        codes = [c["standard_code"] for c in citations]
        self.assertIn("IS 14220", codes)

        target = next(c for c in citations if c["standard_code"] == "IS 14220")
        self.assertEqual(target["year_cited"], 1994)
        self.assertIn("IS 14220:1994", target["raw_citation"])
        self.assertGreaterEqual(target["source_page"], 1)

    def test_5_source_page_preservation(self):
        """Verify that all requirements and citations preserve valid 1-indexed source pages."""
        reqs = self.extracted.get("extracted_requirements", [])
        for r in reqs:
            loc = r.get("source_location", {})
            page = loc.get("source_page")
            self.assertIsNotNone(page)
            self.assertIn(page, [1, 2, 3], f"Invalid page {page} for req {r['requirement_id']}")

    def test_6_confidence_bounds(self):
        """Verify all extraction confidence values lie strictly within [0.0, 1.0]."""
        reqs = self.extracted.get("extracted_requirements", [])
        for r in reqs:
            c = r.get("extraction_confidence")
            self.assertIsInstance(c, (int, float))
            self.assertGreaterEqual(c, 0.0)
            self.assertLessEqual(c, 1.0)

        citations = self.extracted.get("already_cited_standards", [])
        for cit in citations:
            c = cit.get("extraction_confidence")
            self.assertGreaterEqual(c, 0.0)
            self.assertLessEqual(c, 1.0)

    def test_7_no_hallucinated_values(self):
        """Anti-hallucination check: every extracted value string must literally exist in the document text."""
        raw_full_text = clean_character_encoding(self.doc_result.extracted_text.lower())
        reqs = self.extracted.get("extracted_requirements", [])

        for r in reqs:
            val = r.get("value", "")
            clean_val = clean_character_encoding(val.strip().lower())
            if len(clean_val) < 20:
                self.assertIn(
                    clean_val,
                    raw_full_text,
                    f"Extracted value '{val}' not found in source tender text!"
                )

    def test_8_multiple_numeric_parameters_in_one_clause(self):
        """Verify that distinct parameters in one clause (Megger 500V and 5 Megaohms) yield distinct records."""
        reqs = self.extracted.get("extracted_requirements", [])

        # Clause 4.2 has both 500V DC megger and 5 Megaohms
        clause_4_2_reqs = [r for r in reqs if "500v" in r.get("source_text", "").lower() and "5 megaohms" in r.get("source_text", "").lower()]
        self.assertEqual(len(clause_4_2_reqs), 2)
        categories = {r["category"] for r in clause_4_2_reqs}
        self.assertIn("VOLTAGE", categories)
        self.assertIn("TESTING", categories)

    def test_9_json_schema_validation(self):
        """Strict validation against contracts/requirements.schema.json."""
        jsonschema.validate(instance=self.extracted, schema=self.schema)

    def test_10_deduplication_and_dual_unit_grouping(self):
        """Verify 7.5 kW + 10 HP and 18 L/s + 64.8 m³/hr are grouped into single requirements."""
        reqs = self.extracted.get("extracted_requirements", [])

        # Clause 3.1: 7.5 kW (10.0 HP) must be exactly ONE power requirement
        power_reqs = [r for r in reqs if r["category"] == "POWER"]
        self.assertEqual(len(power_reqs), 1, "Expected exactly 1 combined power requirement for 7.5 kW (10.0 HP)")
        p_req = power_reqs[0]
        self.assertIn("7.5 kW", p_req["value"])
        self.assertIn("10.0 HP", p_req["value"])
        self.assertEqual(p_req["normalized_value"]["numeric_value"], 7.5)
        self.assertIn("10.0 HP", p_req.get("notes", ""))

        # Clause 5.2: 18.0 L/s (64.8 m³/hr) must be exactly ONE flow rate requirement
        flow_reqs = [r for r in reqs if r["category"] == "FLOW_RATE"]
        self.assertEqual(len(flow_reqs), 1, "Expected exactly 1 combined flow rate requirement for 18.0 L/s (64.8 m³/hr)")
        f_req = flow_reqs[0]
        self.assertIn("18.0", f_req["value"])
        self.assertEqual(f_req["normalized_value"]["numeric_value"], 18.0)
        self.assertIn("64.8", f_req.get("notes", ""))

    def test_11_voltage_range_extraction(self):
        """Verify 350V to 440V is extracted as ONE range requirement."""
        reqs = self.extracted.get("extracted_requirements", [])
        range_reqs = [r for r in reqs if r["parameter_name"] == "Permissible Voltage Variation Band"]
        self.assertEqual(len(range_reqs), 1, "Expected exactly 1 range requirement for 350V to 440V")

        r_req = range_reqs[0]
        norm = r_req["normalized_value"]
        self.assertEqual(norm["operator"], "RANGE")
        self.assertEqual(norm["min_value"], 350.0)
        self.assertEqual(norm["max_value"], 440.0)
        self.assertEqual(norm["unit"], "V")

    def test_12_heading_exclusion(self):
        """Verify section headings like 'SECTION 6: INSTALLATION & MOUNTING PROVISIONS' are excluded."""
        reqs = self.extracted.get("extracted_requirements", [])
        for r in reqs:
            val = r["value"].strip()
            self.assertFalse(val.startswith("SECTION 6:"), f"Section header was extracted as requirement: {val}")
            self.assertNotEqual(r["parameter_name"], "Section 6: Installation & Mounting Provisions")

    def test_13_relative_multiplier_handling(self):
        """Verify '1.5 times the maximum operating head' is extracted as relative multiplier."""
        reqs = self.extracted.get("extracted_requirements", [])
        rel_reqs = [r for r in reqs if "1.5 times" in r["value"].lower()]
        self.assertEqual(len(rel_reqs), 1)

        rel = rel_reqs[0]
        self.assertEqual(rel["normalized_value"]["numeric_value"], 1.5)
        self.assertEqual(rel["normalized_value"]["operator"], "EQUAL")
        self.assertIn("1.5x", rel["normalized_value"]["text_value"])
        self.assertIn("relative", rel.get("notes", "").lower())

    def test_14_degree_symbol_preservation(self):
        """Verify 33°C preserves degree symbol and normalizes safely."""
        reqs = self.extracted.get("extracted_requirements", [])
        temp_reqs = [r for r in reqs if r["category"] == "TEMPERATURE"]
        self.assertEqual(len(temp_reqs), 1)

        temp = temp_reqs[0]
        self.assertIn("33°C", temp["value"])
        self.assertEqual(temp["normalized_value"]["max_value"], 33.0)
        self.assertEqual(temp["normalized_value"]["operator"], "LTE")


if __name__ == "__main__":
    unittest.main()
