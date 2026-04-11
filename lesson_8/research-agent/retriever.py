"""Hybrid retrieval: semantic (FAISS) + BM25, with cross-encoder reranking."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder

from config import (
    EMBEDDING_MODEL,
    RERANKER_MODEL,
    VECTOR_STORE_DIR,
    TOP_K_SEMANTIC,
    TOP_K_BM25,
    TOP_K_RERANKED,
)


class HybridRetriever:
    """Hybrid semantic + BM25 retriever with cross-encoder reranking."""

    def __init__(self):
        self._loaded = False
        self._embedder: SentenceTransformer | None = None
        self._reranker: CrossEncoder | None = None
        self._index: faiss.Index | None = None
        self._chunks: list[dict] = []
        self._bm25: BM25Okapi | None = None

    def _load(self):
        """Lazy-load index and models on first query."""
        if self._loaded:
            return

        index_path = VECTOR_STORE_DIR / "index.faiss"
        chunks_path = VECTOR_STORE_DIR / "chunks.json"
        bm25_path = VECTOR_STORE_DIR / "bm25_corpus.pkl"

        if not index_path.exists():
            raise FileNotFoundError(
                "Vector store not found. Run `python ingest.py` first."
            )

        # Load FAISS index
        self._index = faiss.read_index(str(index_path))

        # Load chunk metadata
        with open(chunks_path, encoding="utf-8") as f:
            self._chunks = json.load(f)

        # Load BM25 corpus
        with open(bm25_path, "rb") as f:
            tokenized_corpus = pickle.load(f)
        self._bm25 = BM25Okapi(tokenized_corpus)

        # Load models
        self._embedder = SentenceTransformer(EMBEDDING_MODEL)
        self._reranker = CrossEncoder(RERANKER_MODEL)

        self._loaded = True

    def search(self, query: str) -> list[dict]:
        """Run hybrid search + reranking. Returns top-k results.

        Each result: {"text": ..., "source": ..., "score": ..., "method": ...}
        """
        self._load()

        # ── 1. Semantic search (FAISS) ────────────────────────
        q_emb = self._embedder.encode(
            [query], normalize_embeddings=True
        ).astype("float32")
        scores_sem, indices_sem = self._index.search(q_emb, TOP_K_SEMANTIC)

        semantic_results = {}
        for score, idx in zip(scores_sem[0], indices_sem[0]):
            if idx < 0:
                continue
            semantic_results[idx] = {
                **self._chunks[idx],
                "score_semantic": float(score),
            }

        # ── 2. BM25 search ───────────────────────────────────
        tokenized_query = query.lower().split()
        bm25_scores = self._bm25.get_scores(tokenized_query)
        top_bm25_indices = np.argsort(bm25_scores)[::-1][:TOP_K_BM25]

        bm25_results = {}
        for idx in top_bm25_indices:
            idx = int(idx)
            if bm25_scores[idx] > 0:
                bm25_results[idx] = {
                    **self._chunks[idx],
                    "score_bm25": float(bm25_scores[idx]),
                }

        # ── 3. Merge candidates (union) ──────────────────────
        all_indices = set(semantic_results.keys()) | set(bm25_results.keys())
        candidates = []
        for idx in all_indices:
            entry = self._chunks[idx].copy()
            entry["score_semantic"] = semantic_results.get(idx, {}).get("score_semantic", 0.0)
            entry["score_bm25"] = bm25_results.get(idx, {}).get("score_bm25", 0.0)
            # RRF-style fusion: simple weighted sum (semantic weight > bm25)
            entry["score_fused"] = 0.6 * entry["score_semantic"] + 0.4 * min(entry["score_bm25"] / 10, 1.0)
            candidates.append((idx, entry))

        if not candidates:
            return []

        # ── 4. Cross-encoder reranking ───────────────────────
        pairs = [(query, c["text"]) for _, c in candidates]
        rerank_scores = self._reranker.predict(pairs)

        for i, (idx, entry) in enumerate(candidates):
            entry["score_rerank"] = float(rerank_scores[i])

        # Sort by rerank score descending
        candidates.sort(key=lambda x: x[1]["score_rerank"], reverse=True)

        # ── 5. Return top-k ──────────────────────────────────
        results = []
        for _, entry in candidates[:TOP_K_RERANKED]:
            results.append({
                "text": entry["text"],
                "source": entry["source"],
                "chunk_id": entry.get("chunk_id", ""),
                "score_rerank": round(entry["score_rerank"], 4),
                "score_semantic": round(entry["score_semantic"], 4),
                "score_bm25": round(entry["score_bm25"], 4),
            })

        return results


# Module-level singleton (lazy-loaded on first use)
_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
