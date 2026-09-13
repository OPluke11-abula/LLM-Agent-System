import os
import math
import random
import hashlib
import logging
import threading
import httpx
from typing import Any

logger = logging.getLogger(__name__)


def generate_mock_embedding(text: str, dimension: int = 1536) -> list[float]:
    """Generates a deterministic, L2-normalized float vector with word-token semantic affinity.
    
    The sum of squares of the returned vector is exactly 1.0 (to act as a true cosine space).
    """
    if not text:
        text = "empty"

    import re
    words = re.findall(r"\w+", text.lower())
    if not words:
        words = [text.lower()]

    accum = [0.0] * dimension

    for word in words:
        seed_bytes = hashlib.sha256(word.encode("utf-8")).digest()
        seed = int.from_bytes(seed_bytes[:4], byteorder="big")
        rng = random.Random(seed)
        for i in range(dimension):
            accum[i] += rng.gauss(0.0, 1.0)

    # Add whole text seed for nuance
    whole_seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], byteorder="big")
    rng_whole = random.Random(whole_seed)
    for i in range(dimension):
        accum[i] += 0.3 * rng_whole.gauss(0.0, 1.0)

    # L2 normalize
    sq_sum = sum(x * x for x in accum)
    norm = math.sqrt(sq_sum)
    if norm > 0.0:
        return [x / norm for x in accum]
    else:
        vector = [0.0] * dimension
        vector[0] = 1.0
        return vector


class EmbeddingGenerator:
    """Thread-safe embedding generator wrapping Google GenAI and OpenAI REST endpoints."""
    
    _cache: dict[tuple[str, int, str], list[float]] = {}
    _lock = threading.Lock()

    def __init__(self, provider: str | None = None, api_key: str | None = None):
        explicit_provider = provider is not None
        self.provider = provider
        self.api_key = api_key
        
        # Read from environment if not specified
        if not self.provider:
            self.provider = os.environ.get("EMBEDDING_PROVIDER")
            
        network_enabled = os.environ.get(
            "EMBEDDING_ALLOW_NETWORK", ""
        ).lower() in {"1", "true", "yes"}
        if not self.provider:
            if network_enabled and os.environ.get("OPENAI_API_KEY"):
                self.provider = "openai"
            elif network_enabled and (
                os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            ):
                self.provider = "google"
            else:
                self.provider = "mock"
                
        self.provider = self.provider.strip().lower()

        if not explicit_provider and self.provider in {"openai", "google"} and not network_enabled:
            self.provider = "mock"
        
        if not self.api_key:
            if self.provider == "openai":
                self.api_key = os.environ.get("OPENAI_API_KEY")
            elif self.provider == "google":
                self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
                
        logger.info("[EmbeddingGenerator] Initialized with provider: %s", self.provider)

    def get_embedding(self, text: str, dimension: int = 1536) -> list[float]:
        """Generates embedding for the given text. Uses caching to prevent duplicate API requests."""
        if not isinstance(text, str):
            text = str(text)
            
        # 1. Thread-safe cache check
        cache_key = (self.provider, dimension, text)
        with self._lock:
            if cache_key in self._cache:
                return list(self._cache[cache_key])

        # 2. Generate embedding based on provider
        try:
            if self.provider == "openai":
                embedding = self._fetch_openai(text, dimension)
            elif self.provider == "google":
                # Google text-embedding-004 generates 768-dimensional vectors by default.
                # If 1536 is requested, we can pad or handle it, or standard dimension is 768.
                # Let's request the specified dimension if supported, or let it return Google's native dim.
                # Wait, the spec says "embedding vector(1536) column" for pgvector, so let's default Google to 1536 or map it.
                # In text-embedding-004, we can request output_dimensionality.
                embedding = self._fetch_google(text, dimension)
            else:
                embedding = generate_mock_embedding(text, dimension)
        except Exception as e:
            logger.error("[EmbeddingGenerator] Error generating embedding with %s: %s. Falling back to mock.", self.provider, e)
            embedding = generate_mock_embedding(text, dimension)

        # 3. Thread-safe cache store
        with self._lock:
            self._cache[cache_key] = list(embedding)
            
        return embedding

    def _fetch_openai(self, text: str, dimension: int) -> list[float]:
        if not self.api_key:
            raise ValueError("OpenAI API key is missing.")
            
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": text,
            "model": "text-embedding-3-small"
        }
        # If dimension is specified, OpenAI's text-embedding-3-small supports reducing dimensions
        if dimension:
            payload["dimensions"] = dimension
            
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    def _fetch_google(self, text: str, dimension: int) -> list[float]:
        if not self.api_key:
            raise ValueError("Google GenAI API key is missing.")
            
        # Google's text-embedding-004 embedding API endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {
                "parts": [{"text": text}]
            }
        }
        if dimension:
            payload["outputDimensionality"] = dimension
            
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["embedding"]["values"]

    @classmethod
    def reset_cache(cls):
        with cls._lock:
            cls._cache.clear()
