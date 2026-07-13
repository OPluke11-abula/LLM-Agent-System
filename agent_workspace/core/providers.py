"""
core/providers.py - lightweight LLM provider abstraction.

The router talks to BaseLLMProvider only. Vendor-specific SDKs and HTTP
payloads stay in this module so the agent loop does not care which model
backend is being used.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any

import anyio

logger = logging.getLogger(__name__)

from agent_workspace.observability import LLM_CALL_COUNT, LLM_CALL_LATENCY, Timer, tracer, TRACING_AVAILABLE


class ProviderResponse(tuple):
    def __new__(cls, response_type: str, response_data: Any, usage: dict[str, Any] | None = None):
        obj = super().__new__(cls, (response_type, response_data))
        obj.usage = usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        return obj


ProviderResult = tuple[str, Any]
Message = dict[str, Any]
ToolSchema = dict[str, Any]


class ProviderTransientError(RuntimeError):
    pass


class ProviderStreamTimeoutError(TimeoutError):
    pass


class BaseLLMProvider(ABC):
    """Unified provider contract for LAS.

    `complete()` and `stream()` are the canonical interface. The existing
    `generate_content()` names are retained for AgentRouter compatibility.
    """

    @staticmethod
    def _transient_failure(value: Any) -> bool:
        text = str(value).lower()
        if any(
            marker in text
            for marker in (
                "unauthorized",
                "forbidden",
                "authentication",
                "invalid api key",
                "subscription",
                "billing",
                "quota",
                "offline",
                "cancelled",
                "canceled",
            )
        ):
            return False
        return any(
            marker in text
            for marker in (
                "timeout",
                "timed out",
                "connection",
                "connection reset",
                "temporarily unavailable",
                "http 500",
                "http 502",
                "http 503",
                "http 504",
                "rate limit",
                "http 429",
            )
        )

    def _fallback(self, config: dict[str, Any], provider_label: str, error: Any):
        from agent_workspace.core.account_manager import AccountManager

        workspace_dir = os.environ.get("AGENT_WORKSPACE_DIR") or os.getcwd()
        account_manager = AccountManager(workspace_dir)
        active_account = account_manager.get_active_account()
        fallback_account = None
        for account in account_manager.list_accounts():
            if active_account and account["id"] == active_account["id"]:
                continue
            budget = account.get("token_budget", -1)
            used = account.get("tokens_used", 0)
            if budget == -1 or used < budget:
                fallback_account = account
                break
        if fallback_account is None:
            return None

        from agent_workspace.core.audit_ledger import AuditLedger

        session_id = config.get("session_id", "default-session")
        tenant_id = account_manager.get_session_tenant(session_id) or "default_tenant"
        AuditLedger(workspace_dir).record_event(
            "system_call",
            {
                "event": "sla_failover",
                "original_account_id": active_account["id"] if active_account else "unknown",
                "original_provider": provider_label,
                "fallback_account_id": fallback_account["id"],
                "fallback_provider": fallback_account["provider"],
                "fallback_model": fallback_account["model"],
                "markup_multiplier": 1.8,
                "error": str(error),
            },
            tenant_id=tenant_id,
        )
        if active_account:
            account_manager.register_failover(active_account["id"], fallback_account["id"], 1.8)
        fallback_provider = ProviderFactory.get_provider(
            fallback_account["provider"],
            api_key=account_manager.resolve_api_key(fallback_account),
            base_url=fallback_account.get("base_url"),
        )
        fallback_config = dict(config)
        fallback_config["model"] = fallback_account["model"]
        if fallback_account.get("base_url"):
            fallback_config["base_url"] = fallback_account["base_url"]
        return fallback_provider, fallback_config

    async def _close_stream(self, stream: Any) -> None:
        close = getattr(stream, "aclose", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    async def _iter_with_timeout(self, stream: Any, timeout: float):
        try:
            with anyio.fail_after(timeout):
                async for event in stream:
                    yield event
        except TimeoutError as error:
            raise ProviderStreamTimeoutError("provider stream timeout") from error

    async def aclose(self) -> None:
        client = getattr(self, "_client", None)
        if client is None:
            return
        close = getattr(client, "aclose", None) or getattr(client, "close", None)
        if close is not None:
            result = close()
            if inspect.isawaitable(result):
                await result
        self._client = None

    def _http_client(self, timeout: float):
        client = getattr(self, "_client", None)
        if client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=timeout)
            client = self._client
        return client

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
            from agent_workspace.core.account_manager import AccountManager
            from agent_workspace.core.billing import TenantRateLimiter
            from agent_workspace.core.ledger import FinancialLedger

            workspace_dir = os.environ.get("AGENT_WORKSPACE_DIR") or os.getcwd()
            account_manager = AccountManager(workspace_dir)
            session_id = config.get("session_id", "default-session")
            tenant_id = account_manager.get_session_tenant(session_id) or "default_tenant"
            TenantRateLimiter(FinancialLedger(workspace_dir)).check_rate_limit(tenant_id)

            try:
                with Timer(LLM_CALL_LATENCY, labels={"provider": provider_label}):
                    result = await self.complete(system_prompt, messages, tool_schemas, config)
                if result[0] != "error":
                    LLM_CALL_COUNT.labels(provider=provider_label, status="success").inc()
                    return result
                error = result[1]
            except asyncio.CancelledError:
                raise
            except Exception as error:
                result = ProviderResponse("error", str(error))

            if not self._transient_failure(error):
                LLM_CALL_COUNT.labels(provider=provider_label, status="error").inc()
                return result
            fallback = self._fallback(config, provider_label, error)
            if fallback is None:
                LLM_CALL_COUNT.labels(provider=provider_label, status="error").inc()
                return result
            fallback_provider, fallback_config = fallback
            try:
                fallback_result = await fallback_provider.complete(
                    system_prompt, messages, tool_schemas, fallback_config
                )
            finally:
                await fallback_provider.aclose()
            LLM_CALL_COUNT.labels(provider=provider_label, status="recovered").inc()
            return fallback_result

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
            from agent_workspace.core.account_manager import AccountManager
            from agent_workspace.core.billing import TenantRateLimiter
            from agent_workspace.core.ledger import FinancialLedger

            workspace_dir = os.environ.get("AGENT_WORKSPACE_DIR") or os.getcwd()
            account_manager = AccountManager(workspace_dir)
            session_id = config.get("session_id", "default-session")
            tenant_id = account_manager.get_session_tenant(session_id) or "default_tenant"
            TenantRateLimiter(FinancialLedger(workspace_dir)).check_rate_limit(tenant_id)

            stream = self.stream(system_prompt, messages, tool_schemas, config)
            emitted = False
            seen_usage: tuple[int, int, int] | None = None
            timeout = config.get("stream_timeout", config.get("timeout", 120.0))
            try:
                timeout = float(timeout)
            except (TypeError, ValueError):
                timeout = 120.0
            try:
                async for event in self._iter_with_timeout(stream, timeout):
                    if event[0] == "error":
                        error = event[1]
                        if emitted or not self._transient_failure(error):
                            yield event
                            return
                        raise ProviderTransientError(str(error))
                    usage = getattr(event, "usage", None)
                    if usage:
                        signature = (
                            usage.get("prompt_tokens", 0),
                            usage.get("completion_tokens", 0),
                            usage.get("total_tokens", 0),
                        )
                        if signature == seen_usage:
                            event = ProviderResponse(event[0], event[1])
                        else:
                            seen_usage = signature
                    emitted = True
                    yield event
            except asyncio.CancelledError:
                raise
            except Exception as error:
                if emitted or not self._transient_failure(error):
                    yield ProviderResponse("error", str(error))
                    return
                fallback = self._fallback(config, provider_label, error)
                if fallback is None:
                    yield ProviderResponse("error", str(error))
                    return
                fallback_provider, fallback_config = fallback
                fallback_stream = fallback_provider.stream(
                    system_prompt, messages, tool_schemas, fallback_config
                )
                try:
                    async for event in fallback_stream:
                        yield event
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    yield ProviderResponse("error", str(error))
                finally:
                    await fallback_provider._close_stream(fallback_stream)
                    await fallback_provider.aclose()
                LLM_CALL_COUNT.labels(provider=provider_label, status="recovered").inc()
            finally:
                await self._close_stream(stream)

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

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from google import genai
            except ImportError as error:
                raise ImportError("google-genai SDK is required for GoogleGenAIProvider.") from error
            api_key = self.api_key or os.environ.get("GOOGLE_API_KEY")
            client_args = {}
            if api_key:
                client_args["api_key"] = api_key
            if self.base_url:
                client_args["http_options"] = {"base_url": self.base_url}
            self._client = genai.Client(**client_args)
        return self._client

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
            resp_type, resp_data = self._parse_response(response)
            
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                total_tokens = getattr(response.usage_metadata, "total_token_count", 0) or 0
            
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
            return ProviderResponse(resp_type, resp_data, usage)
        except Exception as error:
            logger.error("Google GenAI API call failed: %s", error)
            return ProviderResponse("error", str(error))

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
                resp_type, resp_data = self._parse_response(chunk)
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens = 0
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    prompt_tokens = getattr(chunk.usage_metadata, "prompt_token_count", 0) or 0
                    completion_tokens = getattr(chunk.usage_metadata, "candidates_token_count", 0) or 0
                    total_tokens = getattr(chunk.usage_metadata, "total_token_count", 0) or 0
                usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
                yield ProviderResponse(resp_type, resp_data, usage)
        except Exception as error:
            logger.error("Google GenAI API stream failed: %s", error)
            yield ProviderResponse("error", str(error))

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

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    async def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ) -> ProviderResult:
        try:
            import httpx

            api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("No OpenAI API key was provided.")
            base_url = self.base_url or config.get("base_url") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            payload: dict[str, Any] = {
                "model": config.get("model", "gpt-4o"),
                "messages": openai_messages(system_prompt, messages),
                "temperature": config.get("temperature", 0.0),
                "max_tokens": config.get("max_tokens", 4096),
            }
            tools = openai_tools(tool_schemas)
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            client = self._http_client(config.get("timeout", 120.0))
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            tool_calls = message.get("tool_calls") or []
            
            # Extract usage
            usage_data = data.get("usage") or {}
            usage = {
                "prompt_tokens": usage_data.get("prompt_tokens", 0) or 0,
                "completion_tokens": usage_data.get("completion_tokens", 0) or 0,
                "total_tokens": usage_data.get("total_tokens", 0) or 0
            }

            if tool_calls:
                resp_type, resp_data = "tool_calls", [
                    {
                        "name": call["function"]["name"],
                        "arguments": parse_json_arguments(call["function"].get("arguments")),
                    }
                    for call in tool_calls
                ]
            else:
                resp_type, resp_data = "text", message.get("content") or ""
            return ProviderResponse(resp_type, resp_data, usage)
        except Exception as error:
            logger.error("OpenAI API call failed: %s", error)
            return ProviderResponse("error", str(error))


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Messages API provider using direct HTTP."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

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

            api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("No Anthropic API key was provided.")
            base_url = self.base_url or config.get("base_url") or "https://api.anthropic.com/v1"
            payload: dict[str, Any] = {
                "model": config.get("model", "claude-3-5-sonnet-latest"),
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

            client = self._http_client(config.get("timeout", 120.0))
            response = await client.post(
                f"{base_url.rstrip('/')}/messages",
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
            
            # Extract usage
            usage_data = data.get("usage") or {}
            prompt_tokens = usage_data.get("input_tokens", 0) or 0
            completion_tokens = usage_data.get("output_tokens", 0) or 0
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }

            if tool_calls:
                resp_type, resp_data = "tool_calls", tool_calls
            else:
                resp_type, resp_data = "text", "".join(text_parts)
            return ProviderResponse(resp_type, resp_data, usage)
        except Exception as error:
            logger.error("Anthropic API call failed: %s", error)
            return ProviderResponse("error", str(error))


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider using the /api/chat endpoint."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    async def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tool_schemas: list[ToolSchema],
        config: dict[str, Any],
    ) -> ProviderResult:
        try:
            import httpx

            base_url = self.base_url or config.get("base_url") or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
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

            client = self._http_client(config.get("timeout", 120.0))
            response = await client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            message = data.get("message", {})
            tool_calls = message.get("tool_calls") or []
            
            # Extract usage
            prompt_tokens = data.get("prompt_eval_count", 0) or 0
            completion_tokens = data.get("eval_count", 0) or 0
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }

            if tool_calls:
                resp_type, resp_data = "tool_calls", [
                    {
                        "name": call.get("function", {}).get("name", ""),
                        "arguments": parse_json_arguments(call.get("function", {}).get("arguments")),
                    }
                    for call in tool_calls
                ]
            else:
                resp_type, resp_data = "text", message.get("content") or data.get("response", "")
            return ProviderResponse(resp_type, resp_data, usage)
        except Exception as error:
            logger.error("Ollama API call failed: %s", error)
            return ProviderResponse("error", str(error))


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
    def get_provider(cls, provider_name: str, api_key: str | None = None, base_url: str | None = None) -> BaseLLMProvider:
        normalized_name = provider_name.strip().lower()
        provider_cls = cls._providers.get(normalized_name)
        if not provider_cls:
            supported = ", ".join(sorted(cls._providers))
            raise ValueError(f"Unsupported LLM provider: {provider_name!r}. Supported providers: {supported}")
        return provider_cls(api_key=api_key, base_url=base_url)
