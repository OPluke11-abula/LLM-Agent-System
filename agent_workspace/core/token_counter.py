import json
import logging
import asyncio
import threading
from collections import OrderedDict
from functools import lru_cache
from typing import Any, Dict, List, NamedTuple, Optional

logger = logging.getLogger(__name__)


class TokenCount(NamedTuple):
    count: int
    estimated: bool


class TokenCountMemo:
    def __init__(self, max_entries: int = 16):
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or max_entries < 1:
            raise ValueError("max_entries must be a positive integer")
        self.max_entries = max_entries
        self._entries: OrderedDict[tuple[Any, ...], TokenCount] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: tuple[Any, ...]) -> tuple[bool, TokenCount | None]:
        with self._lock:
            try:
                value = self._entries.pop(key)
            except KeyError:
                return False, None
            self._entries[key] = value
            return True, value

    def set(self, key: tuple[Any, ...], value: TokenCount) -> None:
        with self._lock:
            self._entries.pop(key, None)
            self._entries[key] = value
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


class TokenCounter:
    """Utility for counting and estimating prompt tokens across different providers."""

    @staticmethod
    @lru_cache(maxsize=32)
    def get_encoding(model_name: Optional[str] = None):
        """Retrieve tiktoken encoding safely, fallback to cl100k_base if it fails."""
        try:
            import tiktoken
            if model_name:
                try:
                    return tiktoken.encoding_for_model(model_name)
                except KeyError:
                    pass
            return tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken not installed, falling back to character approximation.")
            return None

    @classmethod
    def count_text(cls, text: str, model_name: Optional[str] = None) -> TokenCount:
        """Count tokens for a raw string. Always estimated=True for component pre-flight."""
        if not text:
            return TokenCount(0, True)
        if not isinstance(text, str):
            text = str(text)

        encoding = cls.get_encoding(model_name)
        if encoding is not None:
            return TokenCount(len(encoding.encode(text)), True)

        # Fallback to character approximation: 1 token ≈ 4 characters
        return TokenCount(len(text) // 4, True)

    @classmethod
    def count_messages(cls, messages: List[Dict[str, Any]], model_name: Optional[str] = None) -> TokenCount:
        """Estimate tokens for a list of message dicts. Always estimated=True."""
        total = 0
        for msg in messages:
            content = msg.get("content") or ""
            if isinstance(content, list):
                serialized = json.dumps(content, ensure_ascii=False)
                total += cls.count_text(serialized, model_name).count
            else:
                total += cls.count_text(str(content), model_name).count

            # Add message overhead metadata counts
            for k, v in msg.items():
                if k != "content" and v:
                    total += cls.count_text(f"{k}:{v}", model_name).count
        return TokenCount(total, True)

    @classmethod
    def count_tool_schemas(cls, tool_schemas: List[Dict[str, Any]], model_name: Optional[str] = None) -> TokenCount:
        """Estimate tokens for a list of tool schema dicts. Always estimated=True."""
        if not tool_schemas:
            return TokenCount(0, True)
        serialized = json.dumps(tool_schemas, ensure_ascii=False)
        return TokenCount(cls.count_text(serialized, model_name).count, True)

    @classmethod
    def estimate_components(
        cls,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        memory_context: Optional[str] = None,
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Estimate prompt tokens split by components.
        All component pre-flight estimates are flagged as estimated=True.
        """
        sys_count = cls.count_text(system_prompt or "", model_name).count
        msg_count = cls.count_messages(messages or [], model_name).count
        mem_count = cls.count_text(memory_context or "", model_name).count
        tool_count = cls.count_tool_schemas(tool_schemas or [], model_name).count

        return {
            "system_prompt": {"count": sys_count, "estimated": True},
            "messages": {"count": msg_count, "estimated": True},
            "memory_context": {"count": mem_count, "estimated": True},
            "tool_schemas": {"count": tool_count, "estimated": True},
        }

    @staticmethod
    def _preflight_cache_key(
        provider: Any,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tool_schemas: Optional[List[Dict[str, Any]]],
        model: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[tuple[Any, ...]]:
        payload = {
            "model": model,
            "provider_type": f"{type(provider).__module__}.{type(provider).__qualname__}",
            "system_prompt": system_prompt or "",
            "messages": messages or [],
            "tool_schemas": tool_schemas or [],
            "config": config or {},
        }
        try:
            serialized = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError):
            return None
        return (
            type(provider).__module__,
            type(provider).__qualname__,
            serialized,
        )

    @classmethod
    async def get_aggregate_preflight_count(
        cls,
        provider: Any,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
        memo: Optional[TokenCountMemo] = None,
    ) -> Optional[TokenCount]:
        """
        Gemini specific: Query native count_tokens API on the complete final payload if online.
        Flagged as estimated=False since it is a direct API response for the payload.
        """
        provider_name = type(provider).__name__
        if "GoogleGenAI" not in provider_name:
            return None

        if hasattr(provider, "client") and provider.client:
            try:
                from google.genai import types
                model = (config or {}).get("model", "gemini-2.5-flash")
                cache_key = cls._preflight_cache_key(
                    provider,
                    system_prompt,
                    messages,
                    tool_schemas,
                    model,
                    config,
                )
                if memo is not None and cache_key is not None:
                    found, cached = memo.get(cache_key)
                    if found:
                        return cached

                # Build contents and config using provider helpers
                contents = provider._build_google_contents(messages, types)
                google_config = types.GenerateContentConfig()
                if system_prompt:
                    google_config.system_instruction = system_prompt

                google_tools = provider._build_google_tools(tool_schemas or [], types)
                if google_tools:
                    google_config.tools = google_tools

                # Run synchronous GenAI Client call in executor to avoid blocking event loop
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: provider.client.models.count_tokens(
                        model=model,
                        contents=contents,
                        config=google_config
                    )
                )
                if hasattr(response, "total_tokens"):
                    result = TokenCount(response.total_tokens, False)
                    if memo is not None and cache_key is not None:
                        memo.set(cache_key, result)
                    return result
            except Exception as e:
                logger.debug("Failed to query native Gemini count_tokens API: %s", e)
        return None
