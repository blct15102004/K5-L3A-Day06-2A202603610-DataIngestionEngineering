"""Choose a real embedding provider (API or local) and implement this contract."""
import json
import os
import time
import urllib.request
import urllib.error
import hashlib
from pathlib import Path
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Gemini API embedding adapter with rate-limit handling and disk cache."""

    def __init__(self, model_name: str = "models/gemini-embedding-001", api_key: str | None = None,
                 cache_dir: Path | None = None) -> None:
        self.model_name = model_name
        self.dimensions = 768
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or constructor.")
        
        self.cache_dir = cache_dir or Path(__file__).resolve().parents[1] / ".cache" / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache(self, text: str) -> list[float] | None:
        key = hashlib.sha256((self.model_name + ":" + text).encode("utf-8")).hexdigest()
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _set_cache(self, text: str, vec: list[float]) -> None:
        key = hashlib.sha256((self.model_name + ":" + text).encode("utf-8")).hexdigest()
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(vec, f)
        except Exception:
            pass

    def _embed_single(self, text: str, max_retries: int = 8) -> list[float]:
        cached = self._get_cache(text)
        if cached is not None:
            return cached

        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:embedContent?key={self.api_key}"
        payload = {
            "model": self.model_name,
            "content": {"parts": [{"text": text[:4000]}]},
            "outputDimensionality": self.dimensions
        }
        data = json.dumps(payload).encode("utf-8")

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    vec = res.get("embedding", {}).get("values", [])
                    if len(vec) == self.dimensions:
                        self._set_cache(text, vec)
                        return vec
                    raise ValueError(f"Expected {self.dimensions} dimensions, got {len(vec)}")
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    sleep_time = 5.0 * (attempt + 1)
                    time.sleep(sleep_time)
                elif attempt == max_retries - 1:
                    raise
                else:
                    time.sleep(2.0)
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2.0)
        raise RuntimeError("Failed to embed text after retries.")

    def embed_documents(self, texts: list[str], batch_size: int = 20) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        results: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_vectors: list[list[float]] = []
            uncached_items = []
            uncached_indices = []

            for idx, txt in enumerate(batch):
                cached = self._get_cache(txt)
                if cached is not None:
                    batch_vectors.append(cached)
                else:
                    uncached_items.append(txt)
                    uncached_indices.append(idx)
                    batch_vectors.append([])  # placeholder

            if uncached_items:
                url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:batchEmbedContents?key={self.api_key}"
                req_list = [
                    {
                        "model": self.model_name,
                        "content": {"parts": [{"text": t[:4000]}]},
                        "outputDimensionality": self.dimensions
                    }
                    for t in uncached_items
                ]
                payload = json.dumps({"requests": req_list}).encode("utf-8")

                success = False
                for attempt in range(5):
                    try:
                        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            res = json.loads(resp.read().decode("utf-8"))
                            embs = res.get("embeddings", [])
                            for u_idx, emb in enumerate(embs):
                                vec = emb.get("values", [])
                                orig_idx = uncached_indices[u_idx]
                                batch_vectors[orig_idx] = vec
                                self._set_cache(uncached_items[u_idx], vec)
                            success = True
                            break
                    except urllib.error.HTTPError as e:
                        if e.code == 429:
                            time.sleep((2 ** attempt) + 1.5)
                        elif attempt == 4:
                            break
                        else:
                            time.sleep(1.0)
                    except Exception:
                        if attempt == 4:
                            break
                        time.sleep(1.0)

                # Fallback to single requests if batch failed
                if not success:
                    for u_idx, txt in enumerate(uncached_items):
                        orig_idx = uncached_indices[u_idx]
                        vec = self._embed_single(txt)
                        batch_vectors[orig_idx] = vec

            results.extend(batch_vectors)
            time.sleep(0.2)  # Polite pause between batches

        return results

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        return self._embed_single(question)
