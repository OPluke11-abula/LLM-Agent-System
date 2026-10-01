"""Integration tests for OpenAI Responses API Gateway (Phase 105 Task D & Polish).

Verifies POST /v1/responses endpoint, SSE streaming events,
non-streaming responses, tool definitions, structured function calls, and rate-limit handling.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from agent_workspace.api import app
from agent_workspace.routes.responses import _infer_provider_from_model, _normalize_input_messages


class TestResponsesApi(unittest.TestCase):
    """Verifies POST /v1/responses endpoint behavior and SSE streaming."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("agent_workspace.core.providers.ProviderFactory.get_provider")
    def test_post_responses_non_streaming_success(self, mock_factory):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = ("text", "Hello from LAS Gateway!")
        mock_factory.return_value = mock_provider

        payload = {
            "model": "gpt-4o",
            "input": "Say hello",
            "stream": False,
        }
        res = self.client.post("/v1/responses", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["object"], "response")
        self.assertTrue(len(data["output"]) > 0)
        self.assertEqual(data["output"][0]["content"][0]["text"], "Hello from LAS Gateway!")

    @patch("agent_workspace.core.providers.ProviderFactory.get_provider")
    def test_post_responses_non_streaming_tool_calls(self, mock_factory):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = (
            "tool_calls",
            [{"name": "fetch_weather", "arguments": {"city": "Tokyo"}}],
        )
        mock_factory.return_value = mock_provider

        payload = {
            "model": "gpt-4o",
            "input": "Check weather in Tokyo",
            "stream": False,
            "tools": [{"name": "fetch_weather", "description": "Fetches weather"}],
        }
        res = self.client.post("/v1/responses", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        content = data["output"][0]["content"][0]
        self.assertEqual(content["type"], "function_call")
        self.assertEqual(content["name"], "fetch_weather")
        self.assertIn("Tokyo", content["arguments"])

    @patch("agent_workspace.core.providers.ProviderFactory.get_provider")
    def test_post_responses_streaming_sse(self, mock_factory):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = ("text", "Streaming chunk response.")
        mock_factory.return_value = mock_provider

        payload = {
            "model": "gemini-2.5-flash",
            "input": [{"role": "user", "content": "Stream me"}],
            "stream": True,
        }
        res = self.client.post("/v1/responses", json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/event-stream", res.headers.get("content-type", ""))

        lines = res.text.strip().split("\n")
        events = [line for line in lines if line.startswith("event: ")]
        self.assertTrue(any("response.created" in e for e in events))
        self.assertTrue(any("response.completed" in e for e in events))

    @patch("agent_workspace.core.providers.ProviderFactory.get_provider")
    def test_post_responses_streaming_function_call(self, mock_factory):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = (
            "tool_calls",
            [{"name": "execute_bash", "arguments": {"cmd": "ls -la"}}],
        )
        mock_factory.return_value = mock_provider

        payload = {
            "model": "gpt-4o",
            "input": "Run ls",
            "stream": True,
        }
        res = self.client.post("/v1/responses", json=payload)
        self.assertEqual(res.status_code, 200)
        lines = res.text.strip().split("\n")
        events = [line for line in lines if line.startswith("event: ")]
        self.assertTrue(any("response.function_call" in e for e in events))

    @patch("agent_workspace.core.providers.ProviderFactory.get_provider")
    def test_post_responses_rate_limit_429(self, mock_factory):
        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = RuntimeError("429 Rate limit exceeded by upstream")
        mock_factory.return_value = mock_provider

        payload = {
            "model": "gpt-4o",
            "input": "Rate limit test",
            "stream": False,
        }
        res = self.client.post("/v1/responses", json=payload)
        self.assertEqual(res.status_code, 429)

    def test_post_responses_missing_input_validation(self):
        """Missing input payload produces 422 Unprocessable Entity."""
        res = self.client.post("/v1/responses", json={"model": "gpt-4o"})
        self.assertEqual(res.status_code, 422)

    def test_normalize_input_messages_variations(self):
        self.assertEqual(_normalize_input_messages("hello"), [{"role": "user", "content": "hello"}])
        self.assertEqual(
            _normalize_input_messages(["msg1", "msg2"]),
            [{"role": "user", "content": "msg1"}, {"role": "user", "content": "msg2"}],
        )
        self.assertEqual(
            _normalize_input_messages([{"role": "system", "content": "sys"}, {"content": "c"}]),
            [{"role": "system", "content": "sys"}, {"role": "user", "content": "c"}],
        )

    def test_infer_provider_from_model(self):
        self.assertEqual(_infer_provider_from_model("gemini-2.5-pro"), "google-genai")
        self.assertEqual(_infer_provider_from_model("claude-3-5-sonnet"), "anthropic")
        self.assertEqual(_infer_provider_from_model("ollama:llama3"), "ollama")
        self.assertEqual(_infer_provider_from_model("deepseek-chat"), "deepseek")
        self.assertEqual(_infer_provider_from_model("gpt-4o"), "openai")

    @patch("agent_workspace.core.providers.ProviderFactory.get_provider")
    def test_post_responses_streaming_tool_repair_event(self, mock_factory):
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = (
            "tool_calls",
            [{"name": "filesystem.read", "arguments": "```json\n{\"path\": \"app.py\", \"start_line\": \"10\"}\n```"}],
        )
        mock_factory.return_value = mock_provider

        payload = {
            "model": "gpt-4o",
            "input": "Read file",
            "stream": True,
            "tools": [{
                "name": "filesystem.read",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "start_line": {"type": "integer"},
                    },
                    "required": ["file_path"],
                },
            }],
        }
        res = self.client.post("/v1/responses", json=payload)
        self.assertEqual(res.status_code, 200)
        lines = res.text.strip().split("\n")
        events = [line for line in lines if line.startswith("event: ")]
        self.assertTrue(any("response.repair" in e for e in events))
        self.assertTrue(any("response.function_call" in e for e in events))

    @patch("agent_workspace.core.providers.ProviderFactory.get_provider")
    def test_post_responses_streaming_dynamic_failover(self, mock_factory):
        primary_provider = AsyncMock()
        primary_provider.complete.side_effect = RuntimeError("429 Quota Exceeded")
        fallback_provider = AsyncMock()
        fallback_provider.complete.return_value = ("text", "Response from fallback provider")

        def factory_side_effect(provider_name, **kwargs):
            if provider_name == "openai":
                return primary_provider
            return fallback_provider

        mock_factory.side_effect = factory_side_effect

        payload = {
            "model": "gpt-4o",
            "input": "Prompt needing failover",
            "stream": True,
        }
        res = self.client.post("/v1/responses", json=payload)
        self.assertEqual(res.status_code, 200)
        lines = res.text.strip().split("\n")
        events = [line for line in lines if line.startswith("event: ")]
        self.assertTrue(any("response.failover" in e for e in events))
        self.assertTrue(any("response.completed" in e for e in events))

    @patch("agent_workspace.core.providers.ProviderFactory.get_provider")
    def test_post_responses_non_streaming_dynamic_failover(self, mock_factory):
        primary_provider = AsyncMock()
        primary_provider.complete.side_effect = RuntimeError("429 Quota Exceeded")
        fallback_provider = AsyncMock()
        fallback_provider.complete.return_value = ("text", "Recovered in non-streaming mode")

        def factory_side_effect(provider_name, **kwargs):
            if provider_name == "openai":
                return primary_provider
            return fallback_provider

        mock_factory.side_effect = factory_side_effect

        payload = {
            "model": "gpt-4o",
            "input": "Prompt needing failover",
            "stream": False,
        }
        res = self.client.post("/v1/responses", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["output"][0]["content"][0]["text"], "Recovered in non-streaming mode")


if __name__ == "__main__":
    unittest.main()
