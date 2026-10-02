"""Edge Small Language Model (SLM) Inference Engine (Phase 110).

Aligned with Universal Coding Agent Development Protocol v3.8.0 and ADR-006.

Provides ultra-low latency, zero-cloud-token local model execution via Ollama / vLLM,
with automatic health checking, latency telemetry, and hermetic offline test modes.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Callable, Optional
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger("EdgeSLMEngine")


class EdgeSLMResponse(BaseModel):
    """Execution telemetry and completion output from local Edge SLM."""

    model_config = ConfigDict(extra="ignore")

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    is_offline_mock: bool = False
    cloud_egress_prevented: bool = True


class EdgeSLMEngine:
    """Manages low-latency interaction with local quantized models (e.g. Qwen 2.5 Coder, DeepSeek-R1-8B)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "qwen2.5-coder:7b",
        timeout: float = 10.0,
        mock_handler: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("LAS_SLM_BASE_URL")
            or os.environ.get("OLLAMA_BASE_URL")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.model = model
        self.timeout = timeout
        self.mock_handler = mock_handler

    async def health_check(self) -> bool:
        """Probes the local SLM service for readiness."""
        if self.mock_handler is not None:
            return True
        try:
            import httpx

            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception as e:
            logger.debug("Edge SLM health probe failed: %s", e)
            return False

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: str = "You are a specialized low-latency edge coding model.",
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> EdgeSLMResponse:
        """Executes a completion request against the local model."""
        start_time = time.perf_counter()

        # Hermetic mock execution for tests and air-gapped simulation
        if self.mock_handler is not None:
            content = self.mock_handler(prompt, system_prompt)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return EdgeSLMResponse(
                content=content,
                model=self.model,
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(content.split()),
                total_tokens=len(prompt.split()) + len(content.split()),
                latency_ms=round(latency_ms, 2),
                is_offline_mock=True,
                cloud_egress_prevented=True,
            )

        try:
            import httpx

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                res.raise_for_status()
                data = res.json()

            latency_ms = (time.perf_counter() - start_time) * 1000.0
            content = data.get("message", {}).get("content", "")
            prompt_tokens = data.get("prompt_eval_count", 0) or len(prompt.split())
            completion_tokens = data.get("eval_count", 0) or len(content.split())

            return EdgeSLMResponse(
                content=content,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=round(latency_ms, 2),
                is_offline_mock=False,
                cloud_egress_prevented=True,
            )
        except Exception as exc:
            logger.error("Edge SLM generation error: %s", exc)
            raise RuntimeError(f"Edge SLM endpoint unreachable ({self.base_url}): {exc}") from exc
