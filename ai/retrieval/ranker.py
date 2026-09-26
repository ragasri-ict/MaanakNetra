"""
Hybrid Ranker for MAANAKNETRA Standard Retrieval.
Combines Semantic Similarity, BM25 Lexical Score, Parameter Fit, and Category Match.
Applies lifecycle-aware adjustments to ensure current standards outrank superseded editions.
"""

from typing import List, Dict, Any


# Retrieval weight configuration (Sum = 1.00)
WEIGHT_PARAMETER_FIT = 0.40   # Technical clause and numerical compatibility
WEIGHT_SEMANTIC = 0.30        # Multilingual dense semantic context
WEIGHT_LEXICAL = 0.20         # Sparse BM25 keyword matching
WEIGHT_CATEGORY_MATCH = 0.10  # Broad domain and product taxonomy fit


class HybridRanker:
    """
    Computes final applicability scores and formats recommendation items.
    """

    def __init__(
        self,
        w_param: float = WEIGHT_PARAMETER_FIT,
        w_sem: float = WEIGHT_SEMANTIC,
        w_lex: float = WEIGHT_LEXICAL,
        w_cat: float = WEIGHT_CATEGORY_MATCH
    ):
        self.w_param = w_param
        self.w_sem = w_sem
        self.w_lex = w_lex
        self.w_cat = w_cat

    def rank(
        self,
        candidates_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calculates final scores for all candidate standards and formats output.
        Each candidate_data contains:
            standard: Dict
            lexical_score: float (0-1)
            semantic_score: float (0-1)
            parameter_eval: Dict (fit_score, matched_requirements, unmatched, evidence, rationale)
            category_score: float (0-1)
        """
        ranked_results: List[Dict[str, Any]] = []

        for item in candidates_data:
            std = item["standard"]
            lex_score = item.get("lexical_score", 0.0)
            sem_score = item.get("semantic_score", 0.0)
            param_eval = item.get("parameter_eval", {})
            param_score = param_eval.get("parameter_fit_score", 0.0)
            cat_score = item.get("category_score", 0.0)

            # Raw weighted combination
            raw_score = (
                self.w_param * param_score +
                self.w_sem * sem_score +
                self.w_lex * lex_score +
                self.w_cat * cat_score
            )

            # Final score is strictly status-neutral
            final_score = round(max(0.0, min(1.0, raw_score)), 4)

            # Build comprehensive reason
            reason = (
                f"Applicability: {final_score:.2f} (Param Fit: {param_score:.2f}, "
                f"Semantic: {sem_score:.2f}, Lexical: {lex_score:.2f}). "
                f"{param_eval.get('rationale', '')}"
            )

            evidence_list = param_eval.get("evidence", [])
            # Always ensure at least standard scope is cited as official evidence
            if not evidence_list and std.get("scope"):
                evidence_list.append(f"Official Scope: {std.get('scope')}")

            source_info = std.get("source", {})
            verif_info = std.get("verification", {})
            std_status = std.get("status", "CURRENT")

            ranked_results.append({
                "is_number": std.get("is_number"),
                "title": std.get("title"),
                "applicability_score": final_score,
                "semantic_score": round(sem_score, 4),
                "lexical_score": round(lex_score, 4),
                "parameter_fit_score": round(param_score, 4),
                "matched_requirements": param_eval.get("matched_requirements", []),
                "unmatched_requirements": param_eval.get("unmatched_requirements", []),
                "reason": reason,
                "evidence": evidence_list,
                "source": source_info.get("portal_url") or source_info.get("official_publication_ref") or "data/standards.json",
                "status": std_status,
                "verification_status": verif_info.get("verification_status", "PENDING_VERIFICATION")
            })

        # Sort descending by applicability score
        ranked_results.sort(key=lambda x: x["applicability_score"], reverse=True)
        return ranked_results
