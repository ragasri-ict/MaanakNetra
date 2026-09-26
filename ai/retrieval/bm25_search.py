"""
Sparse Retrieval for MAANAKNETRA using Okapi BM25.
Indexes standards dataset (is_number, title, scope, product types, keywords, clauses)
and scores lexical relevance against extracted tender requirements.
"""

import math
import re
from typing import List, Dict, Any, Tuple


class BM25Searcher:
    """
    In-memory Okapi BM25 search engine for curated Indian Standards.
    Implements standard BM25 formula with document length normalization.
    """

    def __init__(self, standards: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.standards = standards
        self.k1 = k1
        self.b = b
        self.corpus_size = len(standards)
        self.doc_tokens: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.idf_cache: Dict[str, float] = {}

        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase alphanumeric words."""
        if not text:
            return []
        # Support tokens like IS 14220, 14220, 7.5, kw, etc.
        words = re.findall(r"[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*", text.lower())
        return words

    def _extract_document_text(self, std: Dict[str, Any]) -> str:
        """Flattens a standard into an indexable string."""
        parts = [
            std.get("is_number", ""),
            std.get("title", ""),
            std.get("scope", ""),
            std.get("category", ""),
            " ".join(std.get("product_types", [])),
            " ".join(std.get("keywords", [])),
            " ".join(std.get("supersedes", [])),
            std.get("superseded_by") or "",
        ]
        # Include parameter texts
        for p in std.get("structured_parameters", []):
            parts.append(p.get("parameter_name", ""))
            parts.append(p.get("requirement_text", ""))

        return " ".join(filter(None, parts))

    def _build_index(self):
        """Indexes token frequencies and computes Inverse Document Frequencies (IDF)."""
        total_len = 0
        self.doc_tokens = []
        self.doc_lengths = []
        self.doc_freqs = {}

        for std in self.standards:
            doc_str = self._extract_document_text(std)
            tokens = self._tokenize(doc_str)
            self.doc_tokens.append(tokens)
            l = len(tokens)
            self.doc_lengths.append(l)
            total_len += l

            # Track unique term appearances across documents
            seen_in_doc = set(tokens)
            for token in seen_in_doc:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_doc_length = total_len / max(self.corpus_size, 1)

        # Precompute IDF using standard BM25 formula
        for term, df in self.doc_freqs.items():
            # Robertson-Spärck Jones IDF
            self.idf_cache[term] = math.log((self.corpus_size - df + 0.5) / (df + 0.5) + 1.0)

    def score(self, query_text: str) -> List[Tuple[Dict[str, Any], float]]:
        """
        Calculates BM25 score for all indexed standards against query text.
        Returns sorted list of (standard, normalized_score).
        """
        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            return [(std, 0.0) for std in self.standards]

        raw_scores: List[float] = []

        for idx, doc in enumerate(self.standards):
            tokens = self.doc_tokens[idx]
            doc_len = self.doc_lengths[idx]
            score = 0.0

            # Count term frequencies in this document
            tf_map: Dict[str, int] = {}
            for t in tokens:
                tf_map[t] = tf_map.get(t, 0) + 1

            for qt in query_tokens:
                if qt in tf_map:
                    tf = tf_map[qt]
                    idf = self.idf_cache.get(qt, 0.0)
                    # Standard BM25 term weighting
                    denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_length))
                    score += idf * (tf * (self.k1 + 1.0)) / max(denom, 1e-6)

            raw_scores.append(score)

        max_score = max(raw_scores) if raw_scores else 0.0
        results = []
        for std, raw in zip(self.standards, raw_scores):
            # Normalize to 0.0 - 1.0
            norm = (raw / max_score) if max_score > 0 else 0.0
            results.append((std, round(norm, 4)))

        # Sort descending by score
        results.sort(key=lambda x: x[1], reverse=True)
        return results
