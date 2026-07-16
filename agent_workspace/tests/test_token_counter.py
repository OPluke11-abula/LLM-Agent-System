import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from agent_workspace.core.token_counter import TokenCounter, TokenCount


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
