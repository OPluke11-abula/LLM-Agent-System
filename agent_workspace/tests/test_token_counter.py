import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from agent_workspace.core.token_counter import TokenCounter, TokenCount, TokenCountMemo


def test_count_text_with_tiktoken():
    text = "Hello, world! This is a test string for token counting."
    # With tiktoken available, it should decode/encode using tiktoken
    res = TokenCounter.count_text(text)
    assert isinstance(res, TokenCount)
    assert res.count > 0
    assert res.estimated is True


def test_get_encoding_reuses_cached_encoding(monkeypatch):
    calls = 0

    class FakeEncoding:
        def encode(self, text):
            return list(text)

    def get_encoding(name):
        nonlocal calls
        calls += 1
        return FakeEncoding()

    monkeypatch.setitem(sys.modules, "tiktoken", SimpleNamespace(get_encoding=get_encoding))
    TokenCounter.get_encoding.cache_clear()
    try:
        TokenCounter.count_text("first")
        TokenCounter.count_text("second")
        assert calls == 1
    finally:
        TokenCounter.get_encoding.cache_clear()


def test_count_text_fallback_character_division():
    text = "Hello, world! This is a test."
    # Force ImportError on tiktoken
    with patch("builtins.__import__", side_effect=lambda name, *args, **kwargs: sys.modules[name] if name != "tiktoken" else exec("raise ImportError")):
        res = TokenCounter.count_text(text)
        assert isinstance(res, TokenCount)
        assert res.count == len(text) // 4
        assert res.estimated is True


def test_count_messages():
    messages = [
        {"role": "user", "content": "Hello agent!"},
        {"role": "assistant", "content": "Hello user, how can I help you?"}
    ]
    res = TokenCounter.count_messages(messages)
    assert isinstance(res, TokenCount)
    assert res.count > 0
    assert res.estimated is True


def test_count_tool_schemas():
    schemas = [
        {
            "name": "calculate",
            "description": "Perform math",
            "input_schema": {"type": "object", "properties": {}}
        }
    ]
    res = TokenCounter.count_tool_schemas(schemas)
    assert isinstance(res, TokenCount)
    assert res.count > 0
    assert res.estimated is True


def test_estimate_components():
    system = "You are a helpful assistant."
    messages = [{"role": "user", "content": "Help me!"}]
    memory = "User likes programming."
    schemas = [{"name": "test_tool"}]

    estimates = TokenCounter.estimate_components(
        system_prompt=system,
        messages=messages,
        memory_context=memory,
        tool_schemas=schemas
    )

    assert "system_prompt" in estimates
    assert "messages" in estimates
    assert "memory_context" in estimates
    assert "tool_schemas" in estimates

    for key in ["system_prompt", "messages", "memory_context", "tool_schemas"]:
        assert estimates[key]["estimated"] is True
        assert estimates[key]["count"] >= 0


@pytest.mark.asyncio
async def test_get_aggregate_preflight_count_non_gemini():
    # If provider is not Gemini, return None
    mock_provider = MagicMock()
    type(mock_provider).__name__ = "OpenAIProvider"

    res = await TokenCounter.get_aggregate_preflight_count(
        provider=mock_provider,
        system_prompt="system",
        messages=[]
    )
    assert res is None


class GoogleGenAIProvider:
    def __init__(self, total_tokens=42, failure=None):
        self.client = SimpleNamespace(
            models=SimpleNamespace(
                count_tokens=MagicMock(
                    side_effect=failure,
                    return_value=SimpleNamespace(total_tokens=total_tokens),
                )
            )
        )

    @staticmethod
    def _build_google_contents(messages, types):
        return messages

    @staticmethod
    def _build_google_tools(tool_schemas, types):
        return tool_schemas


@pytest.fixture
def fake_google_types(monkeypatch):
    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")

    class GenerateContentConfig:
        pass

    genai_module.types = SimpleNamespace(GenerateContentConfig=GenerateContentConfig)
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)


@pytest.mark.asyncio
async def test_aggregate_preflight_memo_reuses_identical_payload(fake_google_types):
    provider = GoogleGenAIProvider()
    memo = TokenCountMemo(max_entries=4)
    kwargs = {
        "provider": provider,
        "system_prompt": "system",
        "messages": [{"role": "user", "content": "hello"}],
        "tool_schemas": [{"name": "search", "input_schema": {"type": "object"}}],
        "config": {"model": "gemini-2.5-flash"},
        "memo": memo,
    }

    first = await TokenCounter.get_aggregate_preflight_count(**kwargs)
    second = await TokenCounter.get_aggregate_preflight_count(**kwargs)

    assert first == TokenCount(42, False)
    assert second == first
    assert provider.client.models.count_tokens.call_count == 1
    assert len(memo) == 1


@pytest.mark.asyncio
async def test_aggregate_preflight_memo_recounts_when_token_inputs_change(fake_google_types):
    provider = GoogleGenAIProvider()
    memo = TokenCountMemo(max_entries=8)
    base = {
        "provider": provider,
        "system_prompt": "system",
        "messages": [{"role": "user", "content": "hello"}],
        "tool_schemas": [{"name": "search"}],
        "config": {"model": "gemini-2.5-flash"},
        "memo": memo,
    }

    await TokenCounter.get_aggregate_preflight_count(**base)
    await TokenCounter.get_aggregate_preflight_count(
        **{**base, "messages": [{"role": "user", "content": "changed"}]}
    )
    await TokenCounter.get_aggregate_preflight_count(
        **{**base, "config": {"model": "gemini-2.0-flash"}}
    )
    await TokenCounter.get_aggregate_preflight_count(
        **{**base, "tool_schemas": [{"name": "write"}]}
    )

    assert provider.client.models.count_tokens.call_count == 4
    assert len(memo) == 4


@pytest.mark.asyncio
async def test_aggregate_preflight_memo_is_bounded_and_does_not_cache_failures(fake_google_types):
    provider = GoogleGenAIProvider()
    memo = TokenCountMemo(max_entries=2)

    for value in ("one", "two", "three"):
        await TokenCounter.get_aggregate_preflight_count(
            provider=provider,
            system_prompt="system",
            messages=[{"role": "user", "content": value}],
            memo=memo,
        )

    assert len(memo) == 2

    failing = GoogleGenAIProvider(failure=RuntimeError("count failed"))
    assert await TokenCounter.get_aggregate_preflight_count(
        provider=failing,
        system_prompt="system",
        messages=[],
        memo=memo,
    ) is None
    assert await TokenCounter.get_aggregate_preflight_count(
        provider=failing,
        system_prompt="system",
        messages=[],
        memo=memo,
    ) is None
    assert failing.client.models.count_tokens.call_count == 2


@pytest.mark.asyncio
async def test_aggregate_preflight_memo_uses_stable_provider_and_config_inputs(fake_google_types):
    provider_one = GoogleGenAIProvider()
    provider_two = GoogleGenAIProvider()
    memo = TokenCountMemo(max_entries=4)
    messages = [{"role": "user", "content": "hello"}]

    await TokenCounter.get_aggregate_preflight_count(
        provider=provider_one,
        system_prompt="system",
        messages=messages,
        config={"model": "gemini-2.5-flash", "output_schema": {"type": "object"}},
        memo=memo,
    )
    await TokenCounter.get_aggregate_preflight_count(
        provider=provider_one,
        system_prompt="system",
        messages=messages,
        config={"model": "gemini-2.5-flash", "output_schema": {"type": "string"}},
        memo=memo,
    )

    assert provider_one.client.models.count_tokens.call_count == 2
    assert TokenCounter._preflight_cache_key(
        provider_one, "system", messages, None, "gemini-2.5-flash"
    ) == TokenCounter._preflight_cache_key(
        provider_two, "system", messages, None, "gemini-2.5-flash"
    )


@pytest.mark.asyncio
async def test_aggregate_preflight_memo_recounts_after_in_place_mutation(fake_google_types):
    provider = GoogleGenAIProvider()
    memo = TokenCountMemo(max_entries=4)
    messages = [{"role": "user", "content": "before"}]

    await TokenCounter.get_aggregate_preflight_count(
        provider=provider, system_prompt="system", messages=messages, memo=memo
    )
    messages[0]["content"] = "after"
    await TokenCounter.get_aggregate_preflight_count(
        provider=provider, system_prompt="system", messages=messages, memo=memo
    )

    assert provider.client.models.count_tokens.call_count == 2


@pytest.mark.asyncio
async def test_aggregate_preflight_memo_does_not_cache_unserializable_payload(fake_google_types):
    provider = GoogleGenAIProvider()
    memo = TokenCountMemo(max_entries=4)
    messages = [{"role": "user", "content": object()}]

    await TokenCounter.get_aggregate_preflight_count(
        provider=provider, system_prompt="system", messages=messages, memo=memo
    )
    await TokenCounter.get_aggregate_preflight_count(
        provider=provider, system_prompt="system", messages=messages, memo=memo
    )

    assert provider.client.models.count_tokens.call_count == 2
    assert len(memo) == 0


@pytest.mark.asyncio
async def test_aggregate_preflight_memo_propagates_cancellation(fake_google_types):
    provider = GoogleGenAIProvider(failure=asyncio.CancelledError())
    memo = TokenCountMemo(max_entries=4)

    with pytest.raises(asyncio.CancelledError):
        await TokenCounter.get_aggregate_preflight_count(
            provider=provider, system_prompt="system", messages=[], memo=memo
        )

    assert len(memo) == 0


def test_token_count_memo_is_safe_for_concurrent_access():
    memo = TokenCountMemo(max_entries=8)

    def write_and_read(index):
        key = ("provider", index)
        value = TokenCount(index, False)
        memo.set(key, value)
        return memo.get(key)[1]

    with ThreadPoolExecutor(max_workers=8) as executor:
        values = list(executor.map(write_and_read, range(32)))

    assert all(value is not None for value in values)
    assert len(memo) <= 8
