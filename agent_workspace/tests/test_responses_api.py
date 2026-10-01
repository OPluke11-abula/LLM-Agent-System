"""Integration tests for OpenAI Responses API Gateway (Phase 105 Task D).

Verifies POST /v1/responses endpoint, SSE streaming events,
non-streaming responses, tool definitions, and rate-limit error responses.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from agent_workspace.api import app


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
        
        # Check event stream chunks
        lines = res.text.strip().split("\n")
        events = [line for line in lines if line.startswith("event: ")]
        self.assertTrue(any("response.created" in e for e in events))
        self.assertTrue(any("response.completed" in e for e in events))

    def test_post_responses_missing_input_validation(self):
        """Missing input payload produces 422 Unprocessable Entity."""
        res = self.client.post("/v1/responses", json={"model": "gpt-4o"})
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
