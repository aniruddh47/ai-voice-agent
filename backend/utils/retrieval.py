from dataclasses import dataclass
from typing import List, Optional

import numpy as np

try:
    import faiss  # type: ignore
    FAISS_AVAILABLE = True
except Exception:
    faiss = None
    FAISS_AVAILABLE = False


@dataclass
class RetrievedChunk:
    text: str
    score: float
    idx: int


class SemanticRetriever:
    def __init__(self, similarity_threshold: float = 0.15, debug: bool = True) -> None:
        self.similarity_threshold = similarity_threshold
        self.debug = debug
        self.chunks: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self.index = None
        self.use_faiss = False

    def build(self, chunks: List[str], embeddings: np.ndarray) -> None:
        self.chunks = chunks
        self.embeddings = embeddings.astype(np.float32)

        if FAISS_AVAILABLE and len(chunks) > 0:
            dim = self.embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(self.embeddings)
            self.use_faiss = True
        else:
            self.index = None
            self.use_faiss = False

        if self.debug:
            backend = "FAISS" if self.use_faiss else "NumPy"
            print(f"✅ Retriever index ready ({backend}), chunks={len(chunks)}")

    def _top_candidates(self, query_embedding: np.ndarray, top_k: int) -> List[tuple[int, float]]:
        if self.embeddings is None or len(self.chunks) == 0:
            return []

        q = query_embedding.astype(np.float32).reshape(1, -1)

        if self.use_faiss and self.index is not None:
            scores, indices = self.index.search(q, top_k)
            return [(int(i), float(s)) for i, s in zip(indices[0], scores[0]) if i >= 0]

        all_scores = np.dot(self.embeddings, q[0])
        idxs = np.argsort(all_scores)[-top_k:][::-1]
        return [(int(i), float(all_scores[i])) for i in idxs]

    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> List[RetrievedChunk]:
        candidates = self._top_candidates(query_embedding, top_k=max(top_k, 1))
        if not candidates:
            return []

        filtered: List[RetrievedChunk] = [
            RetrievedChunk(text=self.chunks[idx], score=score, idx=idx)
            for idx, score in candidates
            if score >= self.similarity_threshold
        ]

        # If no chunk crosses threshold, still return top-1 as requested.
        if not filtered:
            idx, score = candidates[0]
            filtered = [RetrievedChunk(text=self.chunks[idx], score=score, idx=idx)]

        if self.debug:
            print("\n🔎 Retrieved RAG Chunks")
            for i, item in enumerate(filtered, start=1):
                preview = item.text[:170].replace("\n", " ")
                print(f"  {i}. score={item.score:.3f} | chunk={item.idx} | {preview}...")

        return filtered

    def build_context(self, items: List[RetrievedChunk], fallback_context: str, max_chars: int = 1200) -> str:
        if not items:
            return fallback_context

        blocks: List[str] = []
        used = 0
        for item in items:
            text = item.text.strip()
            if not text:
                continue
            if used + len(text) > max_chars:
                break
            blocks.append(text)
            used += len(text)

        if not blocks:
            return fallback_context

        context = "\n\n".join(blocks).strip()
        if fallback_context:
            # Always include fallback context as a safety net.
            tail = fallback_context[:220]
            context = f"{context}\n\nFallback: {tail}".strip()
        return context
