"""
End-to-End Hybrid Standard Retrieval Pipeline for MAANAKNETRA.
Coordinates BM25 lexical search, dense semantic search, parameter matching,
and hybrid ranking against data/standards.json.
"""

import os
import json
from typing import List, Dict, Any, Optional

from .bm25_search import BM25Searcher
from .semantic_search import SemanticSearcher
from .parameter_matcher import ParameterMatcher
from .ranker import HybridRanker

STANDARDS_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "standards.json"
)


class RetrievalPipeline:
    """
    Coordinates multi-stage retrieval across Indian Standards.
    """

    def __init__(
        self,
        standards_path: Optional[str] = None,
        embedding_model: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        path = standards_path or STANDARDS_DATA_PATH
        with open(path, "r", encoding="utf-8") as f:
            self.standards: List[Dict[str, Any]] = json.load(f)

        self.standards_by_num: Dict[str, Dict[str, Any]] = {
            s["is_number"]: s for s in self.standards
        }

        # Initialize retrieval components
        self.bm25_searcher = BM25Searcher(self.standards)
        self.semantic_searcher = SemanticSearcher(
            self.standards,
            model_name=embedding_model,
            cache_dir=cache_dir
        )
        self.param_matcher = ParameterMatcher()
        self.ranker = HybridRanker()

    def build_query_string(self, requirements_doc: Dict[str, Any], include_citations: bool = True) -> str:
        """
        Builds a rich textual query from extracted tender requirements.
        Allows omitting explicit standard numbers for testing pure requirement-based retrieval.
        """
        parts = []

        # Product context
        p_ctx = requirements_doc.get("product_context", {})
        if p_ctx.get("primary_item_name"):
            parts.append(p_ctx["primary_item_name"])
        if p_ctx.get("category"):
            parts.append(p_ctx["category"])
        if p_ctx.get("summary"):
            parts.append(p_ctx["summary"])

        # Extracted parameters
        for req in requirements_doc.get("extracted_requirements", []):
            cat = req.get("category", "")
            param = req.get("parameter_name", "")
            val = req.get("value", "")
            unit = req.get("unit") or ""
            parts.append(f"{param} {val} {unit}")

        # Citations (optional)
        if include_citations:
            for cit in requirements_doc.get("already_cited_standards", []):
                parts.append(cit.get("standard_code", ""))

        return " ".join(parts)

    def retrieve(
        self,
        requirements_doc: Dict[str, Any],
        top_k: int = 5,
        include_citations_in_query: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k recommended Indian Standards for the given tender requirements.
        """
        product_ctx = requirements_doc.get("product_context", {})
        extracted_reqs = requirements_doc.get("extracted_requirements", [])

        # Construct query text
        query_text = self.build_query_string(
            requirements_doc,
            include_citations=include_citations_in_query
        )

        # Stage 2A: Sparse BM25 retrieval
        bm25_scores = {std["is_number"]: score for std, score in self.bm25_searcher.score(query_text)}

        # Stage 2B: Semantic retrieval
        semantic_scores = {std["is_number"]: score for std, score in self.semantic_searcher.score(query_text)}

        # Stage 3 & 4: Merge & compute parameter fit for all standards
        candidates_data: List[Dict[str, Any]] = []

        primary_domain = product_ctx.get("category", "").lower()
        primary_item = product_ctx.get("primary_item_name", "").lower()

        for std in self.standards:
            is_num = std.get("is_number")
            lex_score = bm25_scores.get(is_num, 0.0)
            sem_score = semantic_scores.get(is_num, 0.0)

            # Evaluate parameter fit
            param_eval = self.param_matcher.evaluate(std, extracted_reqs, product_ctx)

            # Category / product taxonomy alignment score
            std_cat = std.get("category", "").lower()
            std_pts = [p.lower() for p in std.get("product_types", [])]

            cat_match = 0.0
            if any(pt in primary_item or primary_item in pt for pt in std_pts):
                cat_match = 1.0
            elif "pump" in std_cat and "pump" in primary_domain:
                cat_match = 0.7
            elif "motor" in std_cat and "motor" in primary_domain:
                cat_match = 0.6

            candidates_data.append({
                "standard": std,
                "lexical_score": lex_score,
                "semantic_score": sem_score,
                "parameter_eval": param_eval,
                "category_score": cat_match
            })

        # Stage 5: Hybrid ranking
        ranked_results = self.ranker.rank(candidates_data)

        return ranked_results[:top_k]

    def get_embedding_model_info(self) -> Dict[str, Any]:
        """Returns active embedding model metadata."""
        return self.semantic_searcher.get_index_metadata()


def retrieve_standards(
    requirements_doc: Dict[str, Any],
    top_k: int = 5,
    standards_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Convenience function for standard retrieval."""
    pipeline = RetrievalPipeline(standards_path=standards_path)
    return pipeline.retrieve(requirements_doc, top_k=top_k)
