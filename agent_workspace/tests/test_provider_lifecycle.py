import json
from pathlib import Path
from typing import Any, Mapping

import anyio
import pytest

from core.account_manager import AccountManager
from core.providers import (
    BaseLLMProvider,
    OpenAIProvider,
    ProviderFactory,
    ProviderResponse,
)


class UpstreamFailureError(Exception):
    pass


def _write_accounts(path: Path) -> None:
    (path / "accounts.json").write_text(
        json.dumps(
            {
                "accounts": [
                    {
                        "id": "primary",
                        "provider": "openai",
                        "model": "gpt-test",
                        "api_key": "test-key",
                        "is_active": True,
                        "token_budget": -1,
                        "tokens_used": 0,
                    },
                    {
                        "id": "fallback",
                        "provider": "openai",
                        "model": "gpt-fallback",
                        "api_key": "fallback-key",
                        "is_active": False,
                        "token_budget": -1,
                        "tokens_used": 0,
                    },
                ],
                "active_account_id": "primary",
            }
        ),
        encoding="utf-8",
    )


class _PartialFailureProvider(BaseLLMProvider):
    async def complete(self, system_prompt, messages, tool_schemas, config):
        return ProviderResponse("error", "HTTP 500 upstream failure")

    async def stream(self, system_prompt, messages, tool_schemas, config):
        yield ProviderResponse(
            "text",
            "partial",
            {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
        )
        raise UpstreamFailureError("HTTP 500 upstream failure")


class _AuthFailureProvider(BaseLLMProvider):
    async def complete(self, system_prompt, messages, tool_schemas, config):
        return ProviderResponse("error", "401 Unauthorized")


class _NeverEndingProvider(BaseLLMProvider):
    async def complete(self, system_prompt, messages, tool_schemas, config):
        return ProviderResponse("error", "timeout")

    async def stream(self, system_prompt, messages, tool_schemas, config):
        await anyio.sleep(1)
        yield ProviderResponse("text", "unreachable")


class _FallbackProvider(BaseLLMProvider):
    async def complete(self, system_prompt, messages, tool_schemas, config):
        return ProviderResponse("text", "fallback")

    async def stream(self, system_prompt, messages, tool_schemas, config):
        yield ProviderResponse("text", "fallback")


@pytest.fixture
def provider_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _write_accounts(tmp_path)
    monkeypatch.setenv("AGENT_WORKSPACE_DIR", str(tmp_path))
    AccountManager.clear_failovers()
    AccountManager.register_session_tenant("provider-test", "tenant-test")
    return tmp_path


@pytest.mark.asyncio
async def test_stream_does_not_failover_after_partial_output(
    provider_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary = _PartialFailureProvider()
    fallback = _FallbackProvider()
    monkeypatch.setattr(
        ProviderFactory,
        "get_provider",
        lambda provider_name, api_key=None, base_url=None: fallback,
    )

    events = [
        event
        async for event in primary.generate_content_stream(
            "system", [], [], {"session_id": "provider-test"}
        )
    ]

    assert [(event[0], event[1]) for event in events] == [
        ("text", "partial"),
        ("error", "HTTP 500 upstream failure"),
    ]


@pytest.mark.asyncio
async def test_auth_failure_does_not_failover(
    provider_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary = _AuthFailureProvider()
    fallback = _FallbackProvider()
    fallback_calls = 0

    def get_provider(provider_name, api_key=None, base_url=None):
        nonlocal fallback_calls
        fallback_calls += 1
        return fallback

    monkeypatch.setattr(ProviderFactory, "get_provider", get_provider)

    result = await primary.generate_content(
        "system", [], [], {"session_id": "provider-test"}
    )

    assert result[0] == "error"
    assert "Unauthorized" in result[1]
    assert fallback_calls == 0


@pytest.mark.asyncio
async def test_never_ending_stream_is_bounded(
    provider_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary = _NeverEndingProvider()
    fallback = _FallbackProvider()
    monkeypatch.setattr(
        ProviderFactory,
        "get_provider",
        lambda provider_name, api_key=None, base_url=None: fallback,
    )

    events = [
        event
        async for event in primary.generate_content_stream(
            "system", [], [], {"session_id": "provider-test", "stream_timeout": 0.01}
        )
    ]

    assert events[0][1] == "fallback"


@pytest.mark.asyncio
async def test_openai_client_is_reused_and_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    clients = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> Mapping[str, Any]:
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }

    class FakeClient:
        def __init__(self, **kwargs):
            self.closed = False
            clients.append(self)

        async def post(self, *args, **kwargs):
            return FakeResponse()

        async def aclose(self):
            self.closed = True

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    provider = OpenAIProvider(api_key="test-key", base_url="https://example.test/v1")

    await provider.complete("system", [], [], {})
    await provider.complete("system", [], [], {})

    assert len(clients) == 1
    await provider.aclose()
    assert clients[0].closed is True


def test_usage_id_makes_ledger_recording_idempotent(provider_workspace: Path) -> None:
    manager = AccountManager(str(provider_workspace))
    assert manager.record_usage("primary", 2, 3, "provider-test", usage_id="u-1")
    assert manager.record_usage("primary", 2, 3, "provider-test", usage_id="u-1")
    assert manager.get_account("primary")["tokens_used"] == 5
