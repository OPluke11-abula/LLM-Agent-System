"""
tests/test_reasoning_router_p86.py - Conformance tests for Phase 86:
Heterogeneous Reasoning Model Adapters & Dynamic Thinking Router.

Validates:
1. ProviderResponse backward compatibility with reasoning attributes.
2. OpenAIProvider DeepSeek reasoning_content & reasoning_tokens extraction.
3. AnthropicProvider extended thinking payload generation & thinking block parsing.
4. OllamaProvider local <think>...</think> tag isolation and text sanitization.
5. DynamicThinkingRouter role-to-tier mappings and execution config resolution.
6. Offline/air-gapped local model override (Ollama).
7. Pipeline Committee debate integration with reasoning token telemetry.
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_workspace.core.pipeline.committee import CommitteeCoordinator
from agent_workspace.core.pipeline.debate_protocol import PipelineDebateProtocol
from agent_workspace.core.pipeline.models import CodingTaskRequest, ScopedMutationPlan
from agent_workspace.core.providers import (
    AnthropicProvider,
    BaseLLMProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderFactory,
    ProviderResponse,
)
from agent_workspace.core.reasoning_router import (
    DynamicThinkingRouter,
    ModelTier,
    ReasoningConfig,
    RoleModelProfile,
)


class TestReasoningRouterP86(unittest.TestCase):
    """Test suite for Phase 86 Heterogeneous Reasoning & Dynamic Router."""

    def test_provider_response_backward_compatibility(self):
        """Verify ProviderResponse maintains 2-tuple unpacking while exposing reasoning fields."""
        resp = ProviderResponse("text", "hello world")
        resp_type, resp_data = resp
        self.assertEqual(resp_type, "text")
        self.assertEqual(resp_data, "hello world")
        self.assertIsNone(resp.reasoning_content)
        self.assertEqual(resp.reasoning_tokens, 0)
        self.assertEqual(resp.usage["total_tokens"], 0)

        # Extended response with reasoning
        resp_extended = ProviderResponse(
            "text",
            "computed output",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            reasoning_content="internal chain-of-thought",
            reasoning_tokens=15,
        )
        t, d = resp_extended
        self.assertEqual(t, "text")
        self.assertEqual(d, "computed output")
        self.assertEqual(resp_extended.reasoning_content, "internal chain-of-thought")
        self.assertEqual(resp_extended.reasoning_tokens, 15)
        self.assertEqual(resp_extended.usage["total_tokens"], 30)

    def test_openai_provider_deepseek_and_reasoning_parsing(self):
        """Verify OpenAIProvider extracts reasoning_content (DeepSeek) and reasoning_tokens."""
        provider = OpenAIProvider(api_key="test-key")

        mock_json_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Final implementation plan.",
                        "reasoning_content": "Deductive step 1: check invariant. Deductive step 2: verify AST.",
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 80,
                "total_tokens": 180,
                "completion_tokens_details": {
                    "reasoning_tokens": 50,
                },
            },
        }

        mock_http_response = MagicMock()
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.json = MagicMock(return_value=mock_json_response)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_http_response)
        provider._http_client = MagicMock(return_value=mock_client)

        result = asyncio.run(
            provider.complete(
                system_prompt="You are an architect.",
                messages=[{"role": "user", "content": "Analyze boundaries."}],
                tool_schemas=[],
                config={"model": "deepseek-reasoner", "reasoning_effort": "high"},
            )
        )

        self.assertEqual(result[0], "text")
        self.assertEqual(result[1], "Final implementation plan.")
        self.assertEqual(
            result.reasoning_content,
            "Deductive step 1: check invariant. Deductive step 2: verify AST.",
        )
        self.assertEqual(result.reasoning_tokens, 50)
        self.assertEqual(result.usage["reasoning_tokens"], 50)

        # Also verify deepseek provider registration in ProviderFactory
        deepseek_provider = ProviderFactory.get_provider("deepseek", api_key="sk-test")
        self.assertIsInstance(deepseek_provider, OpenAIProvider)

    def test_anthropic_provider_extended_thinking_payload_and_parsing(self):
        """Verify AnthropicProvider formats thinking parameters and parses thinking content blocks."""
        provider = AnthropicProvider(api_key="test-anthropic-key")

        mock_json_response = {
            "content": [
                {
                    "type": "thinking",
                    "thinking": "Deep analysis: checking security sandbox boundaries before mutation.",
                },
                {
                    "type": "text",
                    "text": "Approved architectural mutation.",
                },
            ],
            "usage": {
                "input_tokens": 120,
                "output_tokens": 90,
            },
        }

        mock_http_response = MagicMock()
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.json = MagicMock(return_value=mock_json_response)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_http_response)
        provider._http_client = MagicMock(return_value=mock_client)

        result = asyncio.run(
            provider.complete(
                system_prompt="You are a principal architect.",
                messages=[{"role": "user", "content": "Review plan."}],
                tool_schemas=[],
                config={
                    "model": "claude-3-7-sonnet-latest",
                    "thinking_budget": 8192,
                    "max_tokens": 4096,
                },
            )
        )

        # Check payload sent to Anthropic
        call_args = mock_client.post.call_args
        sent_payload = call_args.kwargs.get("json") or call_args[1].get("json")
        self.assertIn("thinking", sent_payload)
        self.assertEqual(sent_payload["thinking"]["type"], "enabled")
        self.assertEqual(sent_payload["thinking"]["budget_tokens"], 8192)
        self.assertEqual(sent_payload["temperature"], 1.0)
        self.assertGreater(sent_payload["max_tokens"], 8192)

        # Check parsed response
        self.assertEqual(result[0], "text")
        self.assertEqual(result[1], "Approved architectural mutation.")
        self.assertEqual(
            result.reasoning_content,
            "Deep analysis: checking security sandbox boundaries before mutation.",
        )
        self.assertGreater(result.reasoning_tokens, 0)

    def test_ollama_provider_local_think_tag_extraction(self):
        """Verify OllamaProvider isolates <think>...</think> tags from local models and sanitizes output text."""
        provider = OllamaProvider(base_url="http://127.0.0.1:11434")

        raw_stream_output = (
            "<think>\n"
            "1. Verify caller has domain authority.\n"
            "2. Ensure AST node complies with single responsibility.\n"
            "</think>\n"
            "```json\n"
            '{"status": "APPROVED", "blast_radius": 1}\n'
            "```"
        )

        mock_json_response = {
            "message": {
                "role": "assistant",
                "content": raw_stream_output,
            },
            "prompt_eval_count": 50,
            "eval_count": 80,
        }

        mock_http_response = MagicMock()
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.json = MagicMock(return_value=mock_json_response)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_http_response)
        provider._http_client = MagicMock(return_value=mock_client)

        result = asyncio.run(
            provider.complete(
                system_prompt="You are local DeepSeek-R1.",
                messages=[{"role": "user", "content": "Analyze offline."}],
                tool_schemas=[],
                config={"model": "deepseek-r1:8b"},
            )
        )

        self.assertEqual(result[0], "text")
        # Text must NOT contain <think> tags
        self.assertNotIn("<think>", result[1])
        self.assertNotIn("</think>", result[1])
        self.assertIn('{"status": "APPROVED", "blast_radius": 1}', result[1])

        # Reasoning content must contain the extracted thoughts
        self.assertIsNotNone(result.reasoning_content)
        self.assertIn("Verify caller has domain authority", result.reasoning_content)
        self.assertIn("complies with single responsibility", result.reasoning_content)
        self.assertGreater(result.reasoning_tokens, 0)

    def test_dynamic_thinking_router_role_profiles(self):
        """Verify DynamicThinkingRouter maps grounded roles to optimal tiers and configs."""
        mock_factory = MagicMock(return_value=MagicMock(spec=BaseLLMProvider))
        router = DynamicThinkingRouter(offline_mode=False, provider_factory=mock_factory)

        # 1. Architect -> REASONING tier, thinking budget 8192
        arch_profile = router.get_profile("ARCHITECT_PLANNER_AGENT")
        self.assertEqual(arch_profile.preferred_tier, ModelTier.REASONING)
        self.assertEqual(arch_profile.thinking_budget, 8192)
        self.assertEqual(arch_profile.reasoning_effort, "high")

        _, arch_config = router.resolve_provider_and_config("ARCHITECT_PLANNER_AGENT")
        self.assertEqual(arch_config["tier"], "REASONING")
        self.assertEqual(arch_config["thinking_budget"], 8192)

        # 2. Security Auditor -> REASONING tier, thinking budget 4096
        sec_profile = router.get_profile("SECURITY_AUDIT_AGENT")
        self.assertEqual(sec_profile.preferred_tier, ModelTier.REASONING)
        self.assertEqual(sec_profile.thinking_budget, 4096)

        # 3. Domain Logic -> STANDARD_CODING tier, thinking budget 0
        domain_profile = router.get_profile("DOMAIN_LOGIC_AGENT")
        self.assertEqual(domain_profile.preferred_tier, ModelTier.STANDARD_CODING)
        self.assertEqual(domain_profile.thinking_budget, 0)

        # 4. Knowledge / Precheck -> FAST_PRECHECK tier
        precheck_profile = router.get_profile("KNOWLEDGE_TOPOLOGY_AGENT")
        self.assertEqual(precheck_profile.preferred_tier, ModelTier.FAST_PRECHECK)

    def test_dynamic_thinking_router_offline_override(self):
        """Verify DynamicThinkingRouter redirects all roles to Ollama in air-gapped offline mode."""
        mock_factory = MagicMock(return_value=MagicMock(spec=BaseLLMProvider))
        router = DynamicThinkingRouter(offline_mode=True, provider_factory=mock_factory)

        # In offline mode, architect should be deepseek-r1 on ollama
        arch_provider, arch_config = router.resolve_provider_and_config("ARCHITECT_PLANNER_AGENT")
        self.assertEqual(arch_config["provider"], "ollama")
        self.assertEqual(arch_config["model"], "deepseek-r1:8b")
        self.assertTrue(arch_config["offline_mode"])
        mock_factory.assert_called_with("ollama", api_key=None, base_url=None)

        # Standard coding agent should be qwen2.5-coder on ollama
        _, domain_config = router.resolve_provider_and_config("DOMAIN_LOGIC_AGENT")
        self.assertEqual(domain_config["provider"], "ollama")
        self.assertEqual(domain_config["model"], "qwen2.5-coder:7b")
        self.assertTrue(domain_config["offline_mode"])

    def test_committee_and_debate_with_reasoning_telemetry(self):
        """Verify full integration: committee coordinator assigns tiers and debate protocol extracts reasoning telemetry."""
        from pathlib import Path

        request = CodingTaskRequest(
            task_id="TASK-REASONING-01",
            repository_path=str(Path(".").resolve()),
            requirement_prompt="Implement zero-trust auth token rotation in agent_workspace/core/security.py",
            target_branch="feat/auth-rotation",
            inspected_files=["agent_workspace/core/security.py"],
            target_files=["agent_workspace/core/security.py"],
            enable_committee=True,
            debate_rounds=1,
            thinking_budget=4096,
        )

        coordinator = CommitteeCoordinator()
        formation = coordinator.evaluate_committee(request)

        # Security auditor and architect must have REASONING tier and thinking budgets
        member_map = {m.role: m for m in formation.members}
        self.assertIn("securityauditor", member_map)
        self.assertEqual(member_map["securityauditor"].model_tier, "REASONING")
        self.assertEqual(member_map["securityauditor"].thinking_budget, 4096)

        # Execute debate protocol
        protocol = PipelineDebateProtocol()
        draft_plan = ScopedMutationPlan(
            task_id=request.task_id,
            plan_summary="Draft plan",
            target_files=request.target_files,
            assigned_role="SECURITY_AUDIT_AGENT",
        )

        debate_record = protocol.run_debate(request=request, draft_plan=draft_plan, formation=formation)

        # Validate reasoning tokens telemetry on speech turns and scorecard
        self.assertTrue(len(debate_record.rounds) > 0)
        first_round = debate_record.rounds[0]
        self.assertTrue(len(first_round.turns) > 0)

        # At least one turn must have reasoning content and reasoning tokens
        turns_with_reasoning = [t for t in first_round.turns if t.reasoning_content and t.reasoning_tokens > 0]
        self.assertGreater(len(turns_with_reasoning), 0)

        # Consensus scorecard must record total reasoning tokens
        scorecard = debate_record.consensus_scorecard
        self.assertGreater(scorecard.total_reasoning_tokens, 0)
        self.assertEqual(
            scorecard.total_reasoning_tokens,
            sum(t.reasoning_tokens for r in debate_record.rounds for t in r.turns),
        )


if __name__ == "__main__":
    unittest.main()
