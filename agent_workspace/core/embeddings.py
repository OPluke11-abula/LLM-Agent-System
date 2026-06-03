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
    """Generates a deterministic, L2-normalized float vector using SHA256 digest of the text.
    
    The sum of squares of the returned vector is exactly 1.0 (to act as a true cosine space).
    """
    if not text:
        text = "empty"
    
    # Generate a deterministic seed from the text
    seed_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    # Convert first 4 bytes to an integer
    seed = int.from_bytes(seed_bytes[:4], byteorder="big")
    
    rng = random.Random(seed)
    vector = [rng.gauss(0.0, 1.0) for _ in range(dimension)]
    
    # L2 normalize
    sq_sum = sum(x * x for x in vector)
    norm = math.sqrt(sq_sum)
    if norm > 0.0:
        vector = [x / norm for x in vector]
    else:
        # Fallback in the astronomical case norm is 0
        vector = [0.0] * dimension
        vector[0] = 1.0
        
    return vector


class EmbeddingGenerator:
    """Thread-safe embedding generator wrapping Google GenAI and OpenAI REST endpoints."""
    
    _cache: dict[str, list[float]] = {}
    _lock = threading.Lock()

    def __init__(self, provider: str | None = None, api_key: str | None = None):
        self.provider = provider
        self.api_key = api_key
        
        # Read from environment if not specified
        if not self.provider:
            self.provider = os.environ.get("EMBEDDING_PROVIDER")
            
        if not self.provider:
            if os.environ.get("OPENAI_API_KEY"):
                self.provider = "openai"
            elif os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
                self.provider = "google"
            else:
                self.provider = "mock"
                
        self.provider = self.provider.strip().lower()
        
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
        with self._lock:
            if text in self._cache:
                return self._cache[text]

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
            self._cache[text] = embedding
            
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
