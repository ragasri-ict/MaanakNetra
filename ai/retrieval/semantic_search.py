"""
Semantic Search & Neural Vector Indexing for MAANAKNETRA Indian Standards.
Uses SentenceTransformers (configurable via EMBEDDING_MODEL environment variable)
with local disk caching and FAISS / cosine similarity.
"""

import os
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Configurable embedding model name (Default: practical multilingual model for CPU laptops)
DEFAULT_EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2"
)

INDEX_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", ".cache", "standards_embeddings.npz"
)
INDEX_META_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", ".cache", "standards_index_meta.json"
)


from ai.memory_utils import log_memory

class SemanticSearcher:
    """
    Computes dense vector representations of Indian Standards and
    performs semantic similarity matching against tender queries.
    """

    def __init__(
        self,
        standards: List[Dict[str, Any]],
        model_name: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        self.standards = standards
        self.model_name = model_name or os.environ.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        self.cache_npz = os.path.join(cache_dir, "standards_embeddings.npz") if cache_dir else INDEX_CACHE_PATH
        self.cache_meta = os.path.join(cache_dir, "standards_index_meta.json") if cache_dir else INDEX_META_PATH

        self.model = None
        self.embeddings: Optional[np.ndarray] = None
        self.use_fallback = False
        self.fallback_vectorizer = None

        self._init_encoder()
        self._build_or_load_index()

    def _init_encoder(self):
        """Initializes the SentenceTransformer model or falls back gracefully."""
        log_memory("Semantic model init start")
        if os.environ.get("RENDER") == "true" or os.environ.get("USE_TFIDF_ONLY") == "true":
            logger.info("Render/low-memory environment detected. Enforcing TF-IDF semantic proxy to prevent OOM.")
            self._init_fallback_vectorizer()
            return

        try:
            import torch
            torch.set_num_threads(1)
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name, device="cpu")
            self.model.eval()
            self.use_fallback = False
            log_memory("Semantic model init complete")
        except Exception as e:
            logger.warning(
                f"SentenceTransformer not available for '{self.model_name}' ({e}). "
                f"Falling back to character/subword TF-IDF semantic proxy."
            )
            self._init_fallback_vectorizer()

    def _init_fallback_vectorizer(self):
        """Initializes the TF-IDF vectorizer fallback."""
        self.use_fallback = True
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.fallback_vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            max_features=4096
        )
        log_memory("Semantic model fallback ready")

    def _prepare_document_texts(self) -> List[str]:
        """Creates semantic search representations for all standards."""
        texts = []
        for std in self.standards:
            parts = [
                f"Indian Standard: {std.get('is_number', '')}",
                f"Title: {std.get('title', '')}",
                f"Scope: {std.get('scope', '')}",
                f"Category: {std.get('category', '')}",
                f"Product Types: {', '.join(std.get('product_types', []))}",
                f"Keywords: {', '.join(std.get('keywords', []))}"
            ]
            for p in std.get("structured_parameters", []):
                parts.append(f"{p.get('parameter_name', '')}: {p.get('requirement_text', '')}")
            texts.append(" | ".join(parts))
        return texts

    def _build_or_load_index(self):
        """Loads cached index or computes and saves new embeddings."""
        import hashlib
        log_memory("Index load/build start")
        doc_texts = self._prepare_document_texts()
        content_hash = hashlib.sha256("".join(doc_texts).encode("utf-8")).hexdigest()

        # Check if cache is valid
        if os.path.exists(self.cache_meta) and os.path.exists(self.cache_npz):
            try:
                with open(self.cache_meta, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                if (
                    meta.get("model_name") == self.model_name
                    and meta.get("doc_count") == len(self.standards)
                    and meta.get("content_hash") == content_hash
                    and not self.use_fallback
                ):
                    data = np.load(self.cache_npz)
                    self.embeddings = data["embeddings"]
                    log_memory("Index loaded from cache")
                    return
            except Exception as e:
                logger.warning(f"Failed to read index cache ({e}), rebuilding.")

        # Build index
        os.makedirs(os.path.dirname(self.cache_npz), exist_ok=True)

        if not self.use_fallback and self.model is not None:
            try:
                import torch
                with torch.inference_mode():
                    raw_embs = self.model.encode(doc_texts, convert_to_numpy=True, show_progress_bar=False)
            except Exception as enc_err:
                logger.warning(f"Error encoding document texts ({enc_err}). Reverting to TF-IDF.")
                self.use_fallback = True
                from sklearn.feature_extraction.text import TfidfVectorizer
                self.fallback_vectorizer = TfidfVectorizer(ngram_range=(1, 3), sublinear_tf=True, max_features=4096)
                matrix = self.fallback_vectorizer.fit_transform(doc_texts).toarray()
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                norms = np.where(norms == 0, 1e-12, norms)
                self.embeddings = matrix / norms
                log_memory("Index build fallback complete")
                return

            # Normalize for cosine similarity
            norms = np.linalg.norm(raw_embs, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1e-12, norms)
            self.embeddings = raw_embs / norms

            # Cache to disk
            np.savez_compressed(self.cache_npz, embeddings=self.embeddings)
            with open(self.cache_meta, "w", encoding="utf-8") as f:
                json.dump({
                    "model_name": self.model_name,
                    "doc_count": len(self.standards),
                    "content_hash": content_hash,
                    "dimensions": int(self.embeddings.shape[1]),
                    "standards_indexed": [s.get("is_number") for s in self.standards]
                }, f, indent=2)
            log_memory("Index build complete and cached")
        else:
            # Fallback vectorizer
            if self.fallback_vectorizer is None:
                from sklearn.feature_extraction.text import TfidfVectorizer
                self.fallback_vectorizer = TfidfVectorizer(ngram_range=(1, 3), sublinear_tf=True, max_features=4096)
            matrix = self.fallback_vectorizer.fit_transform(doc_texts).toarray()
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1e-12, norms)
            self.embeddings = matrix / norms
            log_memory("Index build fallback complete")

    def score(self, query_text: str) -> List[Tuple[Dict[str, Any], float]]:
        """
        Computes semantic cosine similarity between query and all indexed standards.
        Returns list of (standard, normalized_similarity_score) sorted descending.
        """
        if not query_text or self.embeddings is None:
            return [(std, 0.0) for std in self.standards]

        sims = None
        if not self.use_fallback and self.model is not None:
            try:
                import torch
                with torch.inference_mode():
                    q_emb = self.model.encode([query_text], convert_to_numpy=True, show_progress_bar=False)
                norm = np.linalg.norm(q_emb)
                if norm > 0:
                    q_emb = q_emb / norm
                # Cosine similarity (dot product on normalized vectors)
                sims = np.dot(self.embeddings, q_emb.T).flatten()
            except Exception as e:
                logger.warning(f"Error in SentenceTransformer score ({e}). Using TF-IDF fallback.")
                sims = None

        if sims is None:
            if self.fallback_vectorizer is None:
                from sklearn.feature_extraction.text import TfidfVectorizer
                self.fallback_vectorizer = TfidfVectorizer(ngram_range=(1, 3), sublinear_tf=True, max_features=4096)
                self.fallback_vectorizer.fit(self._prepare_document_texts())
            q_vec = self.fallback_vectorizer.transform([query_text]).toarray()
            norm = np.linalg.norm(q_vec)
            if norm > 0:
                q_vec = q_vec / norm
            sims = np.dot(self.embeddings, q_vec.T).flatten()

        results = []
        for std, sim in zip(self.standards, sims):
            # Clip between 0.0 and 1.0
            score = float(np.clip(sim, 0.0, 1.0))
            results.append((std, round(score, 4)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def get_index_metadata(self) -> Dict[str, Any]:
        """Returns metadata about the active embedding model and cache."""
        return {
            "model_name": self.model_name,
            "is_fallback": self.use_fallback,
            "indexed_standards_count": len(self.standards),
            "vector_dimension": int(self.embeddings.shape[1]) if self.embeddings is not None else 0
        }
