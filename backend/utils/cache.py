import json
import os
import threading
import time
from typing import Dict, List, Optional, Tuple

import numpy as np


class SemanticCache:
    def __init__(
        self,
        cache_path: str,
        threshold: float = 0.90,
        max_entries: int = 800,
        debug: bool = True,
    ) -> None:
        self.cache_path = cache_path
        self.threshold = threshold
        self.max_entries = max_entries
        self.debug = debug
        self._lock = threading.Lock()
        self.entries: List[Dict] = []
        self.matrix: Optional[np.ndarray] = None
        self._load()

    def _rebuild(self) -> None:
        if not self.entries:
            self.matrix = None
            return
        self.matrix = np.asarray([e["embedding"] for e in self.entries], dtype=np.float32)

    def _load(self) -> None:
        if not os.path.exists(self.cache_path):
            return
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            raw = payload.get("entries", []) if isinstance(payload, dict) else []
            self.entries = [
                e for e in raw if isinstance(e, dict) and all(k in e for k in ["query", "response", "embedding"])
            ]
            self._rebuild()
            if self.debug:
                print(f"✅ Loaded cache entries: {len(self.entries)}")
        except Exception as e:
            print(f"⚠️ Cache load failed: {e}")

    def _save(self) -> None:
        tmp = f"{self.cache_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"entries": self.entries}, f, ensure_ascii=True)
        os.replace(tmp, self.cache_path)

    def lookup(self, query_embedding: np.ndarray) -> Tuple[Optional[str], float]:
        with self._lock:
            if self.matrix is None or len(self.entries) == 0:
                return None, 0.0
            scores = np.dot(self.matrix, query_embedding)
            idx = int(np.argmax(scores))
            score = float(scores[idx])
            if self.debug:
                print(f"🧠 Cache best similarity: {score:.3f}")
            if score >= self.threshold:
                if self.debug:
                    print("⚡ Cache hit")
                return self.entries[idx]["response"], score
            return None, score

    def add(self, query: str, response: str, embedding: np.ndarray) -> None:
        if not query or not response:
            return
        item = {
            "query": query,
            "response": response,
            "embedding": np.asarray(embedding, dtype=np.float32).tolist(),
            "ts": time.time(),
        }
        with self._lock:
            self.entries.append(item)
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries :]
            self._rebuild()
            try:
                self._save()
            except Exception as e:
                print(f"⚠️ Cache save failed: {e}")
