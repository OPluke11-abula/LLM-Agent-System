"""
core/providers.py - lightweight LLM provider abstraction.

The router talks to BaseLLMProvider only. Vendor-specific SDKs and HTTP
payloads stay in this module so the agent loop does not care which model
backend is being used.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

try:
    from observability import LLM_CALL_COUNT, LLM_CALL_LATENCY, Timer, tracer, TRACING_AVAILABLE
except ImportError:
    from agent_workspace.observability import LLM_CALL_COUNT, LLM_CALL_LATENCY, Timer, tracer, TRACING_AVAILABLE

ProviderResult = tuple[str, Any]
Message = dict[str, Any]
ToolSchema = dict[str, Any]


class BaseLLMProvider(ABC):
    """Unified provider contract for LAS.

    `complete()` and `stream()` are the canonical interface. The existing
    `generate_content()` names are retained for AgentRouter compatibility.
    """

    async def generate_content(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ) -> ProviderResult:
        provider_label = type(self).__name__
        with tracer.start_as_current_span("llm_generate") as span:
            span.set_attribute("provider", provider_label)
            if config.get("model"):
                span.set_attribute("model", config["model"])
                
            with Timer(LLM_CALL_LATENCY, labels={"provider": provider_label}):
                result = await self.complete(system_prompt, messages, tool_schemas, config)
            
            status = "error" if result[0] == "error" else "success"
            span.set_attribute("status", status)
            if status == "error":
                if TRACING_AVAILABLE:
                    import opentelemetry.trace as otel_trace
                    span.set_status(otel_trace.Status(otel_trace.StatusCode.ERROR))
            
            LLM_CALL_COUNT.labels(provider=provider_label, status=status).inc()
            return result

    async def generate_content_stream(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ):
        provider_label = type(self).__name__
        with tracer.start_as_current_span("llm_generate_stream") as span:
            span.set_attribute("provider", provider_label)
            if config.get("model"):
                span.set_attribute("model", config["model"])
            
            async for event in self.stream(system_prompt, messages, tool_schemas, config):
                yield event

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ) -> ProviderResult:
        """Return `(response_type, response_data)`.

        response_type is `text`, `tool_calls`, or `error`.
        """

    async def stream(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ):
        """Default streaming fallback.

        Providers can override this for native token streaming. The fallback is
        intentionally conservative: it keeps every provider usable by the API
        and CLI stream paths even before vendor-specific streaming is tuned.
        """
        yield await self.complete(system_prompt, messages, tool_schemas, config)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required for this provider")
    return value


def parse_json_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if raw in (None, ""):
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def openai_tools(tool_schemas: list[ToolSchema]) -> list[dict[str, Any]] | None:
    if not tool_schemas:
        return None
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description") or "",
                "parameters": tool.get("input_schema") or {"type": "object", "properties": {}},
            },
        }
        for tool in tool_schemas
    ]


def openai_messages(system_prompt: str, messages: list[Message]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    tool_call_ids: dict[str, str] = {}
    call_index = 0

    for message in messages:
        role = message.get("role")
        if role == "user":
            result.append({"role": "user", "content": message.get("content", "")})
        elif role == "assistant" and "content" in message:
            result.append({"role": "assistant", "content": message.get("content", "")})
        elif role == "assistant" and "tool_call" in message:
            call_index += 1
            tool_call = message["tool_call"]
            tool_name = tool_call.get("name", "")
            call_id = f"call_{call_index}_{tool_name}"
            tool_call_ids[tool_name] = call_id
            result.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_call.get("arguments", {}), ensure_ascii=False),
                            },
                        }
                    ],
                }
            )
        elif role == "tool":
            tool_name = message.get("name", "")
            result.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_ids.get(tool_name, f"call_unknown_{tool_name}"),
                    "content": message.get("content", ""),
                }
            )
    return result


class GoogleGenAIProvider(BaseLLMProvider):
    """Google Gemini provider using the official google-genai SDK."""

    def __init__(self):
        try:
            from google import genai
        except ImportError as error:
            raise ImportError("google-genai SDK is required for GoogleGenAIProvider.") from error
        self.client = genai.Client()

    def _build_google_contents(self, messages: list[Message], types: Any) -> list[Any]:
        contents = []
        for msg in messages:
            if msg["role"] == "user":
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=msg["content"])]))
            elif msg["role"] == "assistant" and "content" in msg:
                contents.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))
            elif msg["role"] == "assistant" and "tool_call" in msg:
                tool_call = msg["tool_call"]
                contents.append(
                    types.Content(
                        role="model",
                        parts=[
                            types.Part.from_function_call(
                                name=tool_call["name"],
                                args=tool_call.get("arguments", {}),
                            )
                        ],
                    )
                )
            elif msg["role"] == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=msg["name"],
                                response={"result": msg["content"]},
                            )
                        ],
                    )
                )
        return contents

    def _build_google_tools(self, tool_schemas: list[ToolSchema], types: Any) -> list[Any] | None:
        if not tool_schemas:
            return None
        declarations = [
            types.FunctionDeclaration(
                name=tool["name"],
                description=(tool.get("description") or "").strip(),
                parameters=tool.get("input_schema", {}),
            )
            for tool in tool_schemas
        ]
        return [types.Tool(function_declarations=declarations)]

    async def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ) -> ProviderResult:
        try:
            from google.genai import types

            model = config.get("model", "gemini-2.5-flash")
            output_schema = config.get("output_schema")
            req_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=config.get("temperature", 0.0),
                max_output_tokens=config.get("max_tokens", 4096),
                tools=self._build_google_tools(tool_schemas, types),
                response_mime_type="application/json" if output_schema else None,
                response_schema=output_schema,
            )
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model,
                contents=self._build_google_contents(messages, types),
                config=req_config,
            )
            return self._parse_response(response)
        except Exception as error:
            logger.error("Google GenAI API call failed: %s", error)
            return "error", str(error)

    async def stream(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ):
        try:
            from google.genai import types

            model = config.get("model", "gemini-2.5-flash")
            output_schema = config.get("output_schema")
            req_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=config.get("temperature", 0.0),
                max_output_tokens=config.get("max_tokens", 4096),
                tools=self._build_google_tools(tool_schemas, types),
                response_mime_type="application/json" if output_schema else None,
                response_schema=output_schema,
            )
            response_stream = await self.client.aio.models.generate_content_stream(
                model=model,
                contents=self._build_google_contents(messages, types),
                config=req_config,
            )
            async for chunk in response_stream:
                yield self._parse_response(chunk)
        except Exception as error:
            logger.error("Google GenAI API stream failed: %s", error)
            yield "error", str(error)

    def _parse_response(self, response: Any) -> ProviderResult:
        try:
            candidate = response.candidates[0]
            parts = candidate.content.parts
            tool_calls = []
            for part in parts:
                if hasattr(part, "function_call") and part.function_call:
                    function_call = part.function_call
                    tool_calls.append(
                        {
                            "name": function_call.name,
                            "arguments": dict(function_call.args) if function_call.args else {},
                        }
                    )
            if tool_calls:
                return "tool_calls", tool_calls
            return "text", response.text if hasattr(response, "text") else ""
        except (AttributeError, IndexError, TypeError) as error:
            logger.warning("Error parsing Google response: %s", error)
            return "error", str(error)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Chat Completions provider using direct HTTP."""

    async def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ) -> ProviderResult:
        try:
            import httpx

            api_key = require_env("OPENAI_API_KEY")
            base_url = config.get("base_url") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            payload: dict[str, Any] = {
                "model": config.get("model", "gpt-4.1-mini"),
                "messages": openai_messages(system_prompt, messages),
                "temperature": config.get("temperature", 0.0),
                "max_tokens": config.get("max_tokens", 4096),
            }
            tools = openai_tools(tool_schemas)
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            async with httpx.AsyncClient(timeout=config.get("timeout", 120.0)) as client:
                response = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                return "tool_calls", [
                    {
                        "name": call["function"]["name"],
                        "arguments": parse_json_arguments(call["function"].get("arguments")),
                    }
                    for call in tool_calls
                ]
            return "text", message.get("content") or ""
        except Exception as error:
            logger.error("OpenAI API call failed: %s", error)
            return "error", str(error)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Messages API provider using direct HTTP."""

    def _messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role")
            if role == "user":
                result.append({"role": "user", "content": message.get("content", "")})
            elif role == "assistant" and "content" in message:
                result.append({"role": "assistant", "content": message.get("content", "")})
            elif role == "assistant" and "tool_call" in message:
                tool_call = message["tool_call"]
                result.append(
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": f"toolu_{tool_call.get('name', 'tool')}",
                                "name": tool_call.get("name", ""),
                                "input": tool_call.get("arguments", {}),
                            }
                        ],
                    }
                )
            elif role == "tool":
                result.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": f"toolu_{message.get('name', 'tool')}",
                                "content": message.get("content", ""),
                            }
                        ],
                    }
                )
        return result

    async def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ) -> ProviderResult:
        try:
            import httpx

            api_key = require_env("ANTHROPIC_API_KEY")
            payload: dict[str, Any] = {
                "model": config.get("model", "claude-3-5-haiku-latest"),
                "system": system_prompt,
                "messages": self._messages(messages),
                "temperature": config.get("temperature", 0.0),
                "max_tokens": config.get("max_tokens", 4096),
            }
            if tool_schemas:
                payload["tools"] = [
                    {
                        "name": tool["name"],
                        "description": tool.get("description") or "",
                        "input_schema": tool.get("input_schema") or {"type": "object", "properties": {}},
                    }
                    for tool in tool_schemas
                ]

            async with httpx.AsyncClient(timeout=config.get("timeout", 120.0)) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": config.get("anthropic_version", "2023-06-01"),
                    },
                    json=payload,
                )
                response.raise_for_status()
            data = response.json()
            tool_calls = []
            text_parts = []
            for block in data.get("content", []):
                if block.get("type") == "tool_use":
                    tool_calls.append({"name": block.get("name", ""), "arguments": block.get("input", {})})
                elif block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            if tool_calls:
                return "tool_calls", tool_calls
            return "text", "".join(text_parts)
        except Exception as error:
            logger.error("Anthropic API call failed: %s", error)
            return "error", str(error)


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider using the /api/chat endpoint."""

    async def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ) -> ProviderResult:
        try:
            import httpx

            base_url = config.get("base_url") or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
            payload: dict[str, Any] = {
                "model": config.get("model", "llama3.1"),
                "messages": openai_messages(system_prompt, messages),
                "stream": False,
                "options": {
                    "temperature": config.get("temperature", 0.0),
                    "num_predict": config.get("max_tokens", 4096),
                },
            }
            tools = openai_tools(tool_schemas)
            if tools:
                payload["tools"] = tools

            async with httpx.AsyncClient(timeout=config.get("timeout", 120.0)) as client:
                response = await client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
                response.raise_for_status()
            data = response.json()
            message = data.get("message", {})
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                return "tool_calls", [
                    {
                        "name": call.get("function", {}).get("name", ""),
                        "arguments": parse_json_arguments(call.get("function", {}).get("arguments")),
                    }
                    for call in tool_calls
                ]
            return "text", message.get("content") or data.get("response", "")
        except Exception as error:
            logger.error("Ollama API call failed: %s", error)
            return "error", str(error)


class ProviderFactory:
    """Factory for configured LLM providers."""

    _providers = {
        "google-genai": GoogleGenAIProvider,
        "gemini": GoogleGenAIProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> BaseLLMProvider:
        normalized_name = provider_name.strip().lower()
        provider_cls = cls._providers.get(normalized_name)
        if not provider_cls:
            supported = ", ".join(sorted(cls._providers))
            raise ValueError(f"Unsupported LLM provider: {provider_name!r}. Supported providers: {supported}")
        return provider_cls()
