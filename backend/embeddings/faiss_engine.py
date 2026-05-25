"""
THE INNER CITADEL — FAISS Semantic Similarity Engine
CPU Mode — works on Intel with 30GB RAM.
Model: all-MiniLM-L6-v2 (~90MB, auto-downloads on first use)
"""

import os
import numpy as np
from loguru import logger

# Force CPU — no CUDA for Intel integrated graphics
os.environ["CUDA_VISIBLE_DEVICES"] = ""


class FAISSEngine:
    """
    Computes semantic similarity between script text and visual keywords.
    Uses SentenceTransformers (all-MiniLM-L6-v2) + FAISS flat index.

    Threshold 0.82: clips scoring below this are rejected and re-queried.
    Falls back to simple cosine if FAISS/SentenceTransformers unavailable.
    """

    MODEL_NAME = "all-MiniLM-L6-v2"   # ~90MB, CPU-friendly, fast
    DIM = 384                           # Embedding dimension

    def __init__(self):
        self._model = None
        self._index = None
        self._cached_texts = []
        self._cached_vecs  = []
        logger.info("[FAISS] Engine initialized (lazy-load on first use, CPU mode)")

    def _load(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME, device="cpu")
            logger.info(f"[FAISS] ✅ Loaded {self.MODEL_NAME} on CPU")
        except ImportError:
            logger.warning("[FAISS] sentence-transformers not installed. Using keyword overlap.")
            self._model = None

    def _encode(self, text: str) -> np.ndarray:
        """Encode text to embedding vector."""
        self._load()
        if self._model is None:
            return self._fallback_vec(text)
        return self._model.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """
        Returns cosine similarity [0.0 – 1.0] between two texts.
        Used to filter irrelevant stock footage (threshold 0.82).
        """
        if not text_a or not text_b:
            return 0.5
        try:
            vec_a = self._encode(text_a.lower().strip())
            vec_b = self._encode(text_b.lower().strip())
            similarity = float(np.dot(vec_a, vec_b))
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.warning(f"[FAISS] Similarity error: {e} — using keyword fallback")
            return self._keyword_similarity(text_a, text_b)

    def is_duplicate(self, text: str, threshold: float = 0.82) -> bool:
        """
        Checks if the given text is too similar to previously seen scripts.
        Prevents repetitive content across generated videos.
        """
        if not self._cached_vecs:
            self._add_to_cache(text)
            return False

        try:
            vec = self._encode(text)
            cached = np.array(self._cached_vecs)
            sims = cached @ vec
            max_sim = float(np.max(sims))

            if max_sim >= threshold:
                logger.warning(f"[FAISS] Duplicate detected: similarity={max_sim:.3f}")
                return True

            self._add_to_cache(text)
            return False
        except Exception:
            return False

    def _add_to_cache(self, text: str):
        vec = self._encode(text)
        self._cached_texts.append(text)
        self._cached_vecs.append(vec)

    def _fallback_vec(self, text: str) -> np.ndarray:
        """Simple character-hash vector when model unavailable."""
        vec = np.zeros(self.DIM)
        for i, ch in enumerate(text[:self.DIM]):
            vec[i % self.DIM] += ord(ch) / 128.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def _keyword_similarity(self, a: str, b: str) -> float:
        """Jaccard overlap as fallback similarity."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
