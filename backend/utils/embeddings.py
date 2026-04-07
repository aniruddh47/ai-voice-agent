import os
import threading
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def preload(self) -> None:
        self.get_model()

    def get_model(self) -> SentenceTransformer:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        print("⏳ Loading embedding model...")
                        # Use cache_folder to store model locally
                        cache_dir = os.path.join(os.path.expanduser("~"), ".sentence_transformers")
                        os.makedirs(cache_dir, exist_ok=True)
                        self._model = SentenceTransformer(
                            self.model_name,
                            cache_folder=cache_dir,
                            trust_remote_code=True
                        )
                    except Exception as e:
                        print(f"⚠️ Failed to load embedding model: {e}")
                        print("⚠️ Using fallback embeddings")
                        self._model = None
        return self._model

    def encode(self, text: str) -> np.ndarray:
        normalized = (text or "").strip() or "general admission query"
        model = self.get_model()
        
        if model is None:
            # Fallback: simple hash-based embedding
            import hashlib
            hash_bytes = hashlib.sha256(normalized.encode()).digest()
            emb = np.frombuffer(hash_bytes, dtype=np.float32)
            emb = np.pad(emb, (0, 384 - len(emb)), mode='constant')[:384]
            return emb / (np.linalg.norm(emb) + 1e-8)
        
        emb = model.encode(normalized, normalize_embeddings=True)
        return np.asarray(emb, dtype=np.float32)

    def encode_many(self, texts: Iterable[str]) -> np.ndarray:
        items = list(texts)
        if not items:
            return np.zeros((0, 384), dtype=np.float32)
        
        model = self.get_model()
        
        if model is None:
            # Fallback: hash-based embeddings for all texts
            import hashlib
            embeddings = []
            for text in items:
                hash_bytes = hashlib.sha256(text.encode()).digest()
                emb = np.frombuffer(hash_bytes, dtype=np.float32)
                emb = np.pad(emb, (0, 384 - len(emb)), mode='constant')[:384]
                emb = emb / (np.linalg.norm(emb) + 1e-8)
                embeddings.append(emb)
            return np.asarray(embeddings, dtype=np.float32)
        
        arr = model.encode(items, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(arr, dtype=np.float32)
