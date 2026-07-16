import json
import logging
import asyncio
from functools import lru_cache
from typing import Any, Dict, List, NamedTuple, Optional

logger = logging.getLogger(__name__)


class TokenCount(NamedTuple):
    count: int
    estimated: bool


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

    @classmethod
    async def get_aggregate_preflight_count(
        cls,
        provider: Any,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None,
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
                    return TokenCount(response.total_tokens, False)
            except Exception as e:
                logger.debug("Failed to query native Gemini count_tokens API: %s", e)
        return None
