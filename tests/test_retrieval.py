"""
Test Suite for MAANAKNETRA Hybrid Standard Retrieval Engine (Step 6B - Status-Neutral).
Covers:
1. Semantic query finds the primary pump standard (IS 14220).
2. BM25 recognizes exact IS terminology.
3. Retrieval is strictly status-neutral (no lifecycle penalty for CURRENT, SUPERSEDED, WITHDRAWN).
4. Technical relevance and parameter matching determine candidate ranking.
5. Irrelevant standards rank lower based on engineering criteria.
6. Every recommendation contains evidence and official source.
7. Scores remain within 0.0 - 1.0.
8. Retrieval works even when an exact IS number is not present in the tender.
"""

import os
import sys
import json
import unittest

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion import ingest_document
from ai.requirement_extractor import extract_requirements
from ai.retrieval.retrieval_pipeline import RetrievalPipeline
from ai.retrieval.bm25_search import BM25Searcher
from ai.retrieval.semantic_search import SemanticSearcher
from ai.retrieval.parameter_matcher import ParameterMatcher
from ai.retrieval.ranker import HybridRanker


class TestStandardRetrieval(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tender_pdf = os.path.join("demo", "sample_tender.pdf")
        cls.standards_path = os.path.join("data", "standards.json")
        cls.expected_path = os.path.join("demo", "retrieval_expected.json")

        assert os.path.exists(cls.tender_pdf), "demo/sample_tender.pdf must exist"
        assert os.path.exists(cls.standards_path), "data/standards.json must exist"
        assert os.path.exists(cls.expected_path), "demo/retrieval_expected.json must exist"

        with open(cls.expected_path, "r", encoding="utf-8") as f:
            cls.expected = json.load(f)

        with open(cls.standards_path, "r", encoding="utf-8") as f:
            cls.standards = json.load(f)

        # Ingest and extract requirements from sample tender
        cls.doc = ingest_document(cls.tender_pdf)
        cls.reqs_doc = extract_requirements(cls.doc)

        # Initialize retrieval pipeline
        cls.pipeline = RetrievalPipeline(standards_path=cls.standards_path)
        cls.results = cls.pipeline.retrieve(cls.reqs_doc, top_k=5)

    def test_1_semantic_query_finds_primary_pump_standard(self):
        """Semantic search alone should identify IS 14220 from pump specification query."""
        searcher = self.pipeline.semantic_searcher
        query = "Openwell Submersible Pumpsets for clear cold water in village open wells up to 33 deg C"
        scores = searcher.score(query)
        top_std, top_score = scores[0]

        # Top semantic candidate should be IS 14220
        self.assertIn("14220", top_std["is_number"])
        self.assertGreater(top_score, 0.40)

    def test_2_bm25_recognizes_exact_is_terminology(self):
        """BM25 sparse search should score IS 14220 highest when exact standard code is queried."""
        searcher = self.pipeline.bm25_searcher
        scores = searcher.score("Openwell Submersible Pumpset IS 14220")
        top_std, top_score = scores[0]

        self.assertIn("IS 14220", top_std["is_number"])
        self.assertGreaterEqual(top_score, 0.80)

    def test_3_retrieval_is_status_neutral(self):
        """Verify that retrieval scores are strictly status-neutral (CURRENT, SUPERSEDED, WITHDRAWN do not alter scores)."""
        matcher = ParameterMatcher()
        p_ctx = self.reqs_doc.get("product_context", {})
        reqs = self.reqs_doc.get("extracted_requirements", [])

        is_14220 = next(s for s in self.standards if s["is_number"] == "IS 14220")

        # Test that changing standard status has zero impact on parameter fit
        std_current = dict(is_14220, status="CURRENT")
        std_superseded = dict(is_14220, status="SUPERSEDED")
        std_withdrawn = dict(is_14220, status="WITHDRAWN")

        fit_curr = matcher.evaluate(std_current, reqs, p_ctx)["parameter_fit_score"]
        fit_super = matcher.evaluate(std_superseded, reqs, p_ctx)["parameter_fit_score"]
        fit_withd = matcher.evaluate(std_withdrawn, reqs, p_ctx)["parameter_fit_score"]

        self.assertEqual(fit_curr, fit_super, "Parameter fit must be status-neutral for SUPERSEDED")
        self.assertEqual(fit_curr, fit_withd, "Parameter fit must be status-neutral for WITHDRAWN")

        # Test that ranker produces identical applicability scores regardless of status
        mock_eval = {"parameter_fit_score": 0.85, "rationale": "Neutral test", "evidence": []}
        candidate_curr = {
            "standard": std_current,
            "lexical_score": 0.70,
            "semantic_score": 0.80,
            "parameter_eval": mock_eval,
            "category_score": 1.0
        }
        candidate_super = dict(candidate_curr, standard=std_superseded)
        candidate_withd = dict(candidate_curr, standard=std_withdrawn)

        ranker = HybridRanker()
        score_curr = ranker.rank([candidate_curr])[0]["applicability_score"]
        score_super = ranker.rank([candidate_super])[0]["applicability_score"]
        score_withd = ranker.rank([candidate_withd])[0]["applicability_score"]

        self.assertEqual(score_curr, score_super, "Ranker applicability score must be identical regardless of SUPERSEDED status")
        self.assertEqual(score_curr, score_withd, "Ranker applicability score must be identical regardless of WITHDRAWN status")

    def test_4_technical_relevance_determines_ranking(self):
        """Technical parameter fit and relevance determine candidate ranking without status bias."""
        matcher = ParameterMatcher()
        p_ctx = self.reqs_doc.get("product_context", {})
        reqs = self.reqs_doc.get("extracted_requirements", [])

        is_14220 = next(s for s in self.standards if s["is_number"] == "IS 14220")
        is_12615 = next(s for s in self.standards if s["is_number"] == "IS 12615")

        eval_14220 = matcher.evaluate(is_14220, reqs, p_ctx)
        eval_12615 = matcher.evaluate(is_12615, reqs, p_ctx)

        fit_14220 = eval_14220["parameter_fit_score"]
        fit_12615 = eval_12615["parameter_fit_score"]

        self.assertGreater(
            fit_14220,
            fit_12615,
            f"IS 14220 fit ({fit_14220}) must be greater than IS 12615 fit ({fit_12615})"
        )
        self.assertGreaterEqual(len(eval_14220["matched_requirements"]), 5)

        # IS 14220 ranks #1 purely due to comprehensive technical clause alignment (16 parameters matched)
        top_result = self.results[0]
        self.assertEqual(top_result["is_number"], "IS 14220")

    def test_5_irrelevant_standards_rank_lower(self):
        """Irrelevant standards (e.g. IS 996 small motors, IS 12615 line motors) rank lower than pumpsets."""
        all_results = self.pipeline.retrieve(self.reqs_doc, top_k=len(self.standards))
        ranks = {r["is_number"]: idx for idx, r in enumerate(all_results)}

        # IS 14220 must rank before general industrial motors
        self.assertLess(ranks["IS 14220"], ranks["IS 12615"])
        self.assertLess(ranks["IS 14220"], ranks["IS 996"])

    def test_6_every_recommendation_contains_evidence_and_source(self):
        """Every recommended standard must include factual evidence and an official source reference."""
        for r in self.results:
            self.assertIn("evidence", r)
            self.assertIsInstance(r["evidence"], list)
            self.assertGreater(len(r["evidence"]), 0, f"Standard {r['is_number']} missing evidence")

            self.assertIn("source", r)
            self.assertTrue(len(str(r["source"])) > 5, f"Standard {r['is_number']} missing valid source")

            self.assertIn("status", r)
            self.assertIn("verification_status", r)

    def test_7_scores_remain_within_zero_to_one(self):
        """All component and final scores must be strictly bounded in [0.0, 1.0]."""
        for r in self.results:
            for score_key in ["applicability_score", "semantic_score", "lexical_score", "parameter_fit_score"]:
                val = r[score_key]
                self.assertIsInstance(val, (int, float))
                self.assertGreaterEqual(val, 0.0, f"{score_key} < 0.0 for {r['is_number']}")
                self.assertLessEqual(val, 1.0, f"{score_key} > 1.0 for {r['is_number']}")

    def test_8_retrieval_works_without_exact_is_number_in_tender(self):
        """Retrieval must correctly identify IS 14220 even when no IS citations exist in tender text."""
        # Create synthetic requirements doc with zero citations
        reqs_no_cite = json.loads(json.dumps(self.reqs_doc))
        reqs_no_cite["already_cited_standards"] = []
        # Filter out any extracted requirement with IS citation in value
        reqs_no_cite["extracted_requirements"] = [
            r for r in reqs_no_cite["extracted_requirements"]
            if "14220" not in r["value"] and r["category"] != "EXISTING_IS_REFERENCE"
        ]

        results_no_cite = self.pipeline.retrieve(
            reqs_no_cite,
            top_k=5,
            include_citations_in_query=False
        )

        top_std = results_no_cite[0]
        self.assertEqual(
            top_std["is_number"],
            "IS 14220",
            f"Pure parameter/text retrieval should rank IS 14220 first (got {top_std['is_number']})"
        )


if __name__ == "__main__":
    unittest.main()
