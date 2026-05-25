"""
VOXLORE STUDIO — Semantic Similarity Engine (Pure NumPy + SentenceTransformers)

NOTE: faiss-cpu has NO Python 3.13 Windows wheels on PyPI — do NOT install it.
This engine uses sentence-transformers + numpy cosine similarity directly.
No faiss binary required. Works fully on Python 3.13 Windows CPU-only.

Model: all-MiniLM-L6-v2 (~90MB, auto-downloads on first use from HuggingFace)
Falls back to Jaccard keyword overlap if model unavailable.

Used for:
  - Computing similarity between script beat text and Pexels search queries
  - Filtering irrelevant stock footage (threshold 0.82)
"""

import os
import numpy as np
from loguru import logger

# Force CPU — no CUDA
os.environ["CUDA_VISIBLE_DEVICES"] = ""


class FAISSEngine:
    """
    Semantic similarity via SentenceTransformers + numpy cosine similarity.
    Named FAISSEngine for backward compatibility — no faiss binary needed.

    faiss-cpu has no Python 3.13 Windows wheels. This engine does not
    import or require faiss at all. Pure numpy cosine similarity is used.
    """

    MODEL_NAME = "all-MiniLM-L6-v2"   # ~90MB, CPU-friendly
    DIM        = 384                    # Embedding dimension

    def __init__(self):
        self._model        = None
        self._cached_texts = []
        self._cached_vecs  = []
        logger.info("[FAISS] Engine initialized (lazy-load, CPU mode, no faiss binary needed)")

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """
        Returns cosine similarity [0.0–1.0] between two texts.
        Used to filter stock footage (threshold 0.82).
        """
        if not text_a or not text_b:
            return 0.5
        try:
            vec_a = self._encode(text_a.lower().strip())
            vec_b = self._encode(text_b.lower().strip())
            return float(max(0.0, min(1.0, np.dot(vec_a, vec_b))))
        except Exception as e:
            logger.warning(f"[FAISS] Similarity error: {e} — keyword fallback")
            return self._keyword_similarity(text_a, text_b)

    def is_duplicate(self, text: str, threshold: float = 0.82) -> bool:
        """
        True if text is too similar to a previously seen script.
        Prevents repetitive content across videos.
        """
        if not self._cached_vecs:
            self._add_to_cache(text)
            return False
        try:
            vec    = self._encode(text)
            cached = np.array(self._cached_vecs)
            sims   = cached @ vec
            if float(np.max(sims)) >= threshold:
                logger.warning(f"[FAISS] Duplicate: sim={float(np.max(sims)):.3f}")
                return True
            self._add_to_cache(text)
            return False
        except Exception:
            return False

    # ─────────────────────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────────────────────

    def _load(self):
        """Lazy-load SentenceTransformer model on first use."""
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME, device="cpu")
            logger.info(f"[FAISS] Loaded {self.MODEL_NAME} on CPU")
        except ImportError:
            logger.warning("[FAISS] sentence-transformers not available — using keyword fallback")
            self._model = None
        except Exception as e:
            logger.warning(f"[FAISS] Model load failed ({e}) — using keyword fallback")
            self._model = None

    def _encode(self, text: str) -> np.ndarray:
        self._load()
        if self._model is None:
            return self._fallback_vec(text)
        return self._model.encode(
            [text], convert_to_numpy=True, normalize_embeddings=True
        )[0]

    def _add_to_cache(self, text: str):
        vec = self._encode(text)
        self._cached_texts.append(text)
        self._cached_vecs.append(vec)

    def _fallback_vec(self, text: str) -> np.ndarray:
        """Character-hash vector when model unavailable."""
        vec = np.zeros(self.DIM)
        for i, ch in enumerate(text[:self.DIM]):
            vec[i % self.DIM] += ord(ch) / 128.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def _keyword_similarity(self, a: str, b: str) -> float:
        """Jaccard overlap as pure-keyword fallback."""
        wa, wb = set(a.lower().split()), set(b.lower().split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / len(wa | wb)
