"""Unit and integration tests for Executor vs. Advisor Delegation Packet (Phase 105 Task C).

Verifies DelegationPacket, AdvisorMode, SanitizedContextExtractor, desensitization of secrets,
token containment (< 2000 tokens), Zero-Risk manual mode, and Graceful Fallback degradation.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock

from agent_workspace.core.delegation_packet import (
    AdvisorMode,
    AdvisorResponse,
    AdvisorTaskType,
    DelegationManager,
    DelegationPacket,
    SanitizedContextExtractor,
)
from agent_workspace.core.reasoning_router import (
    DynamicThinkingRouter,
    ModelTier,
    ReasoningConfig,
    RoleModelProfile,
)


class TestSanitizedContextExtractor(unittest.TestCase):
    """Verifies scrubbing of API keys, tokens, secrets, and path redaction."""

    def setUp(self):
        self.extractor = SanitizedContextExtractor()

    def test_scrub_api_keys_and_tokens(self):
        raw_text = (
            "OpenAI key: sk-abcdef1234567890abcdef1234567890\n"
            "Google key: AIzaSyD9876543210zyxwvutsrqponmlkjihgfed\n"
            "GitHub token: ghp_1234567890abcdef1234567890abcdef1234\n"
            "Authorization: Bearer mySecretToken1234567890abcdef\n"
            "DB_PASSWORD='super_secret_password_123'"
        )
        scrubbed = self.extractor.scrub_sensitive_data(raw_text)
        self.assertNotIn("sk-abcdef", scrubbed)
        self.assertNotIn("AIzaSyD", scrubbed)
        self.assertNotIn("ghp_1234", scrubbed)
        self.assertNotIn("mySecretToken", scrubbed)
        self.assertNotIn("super_secret_password_123", scrubbed)
        self.assertIn("[REDACTED", scrubbed)

    def test_scrub_local_filesystem_paths(self):
        raw_text = (
            "Error occurred at C:\\Users\\luke2\\AppData\\Roaming\\secrets.json "
            "and /home/developer/workspace/project/main.py"
        )
        scrubbed = self.extractor.scrub_sensitive_data(raw_text)
        self.assertNotIn("C:\\Users\\luke2", scrubbed)
        self.assertNotIn("/home/developer", scrubbed)
        self.assertIn("[WORKSPACE]", scrubbed)

    def test_token_containment_under_2000_tokens(self):
        """Massive content is intelligently truncated and bounded under 2000 tokens."""
        massive_file = "def process_data(i):\n    return i * 2\n" * 1000
        files = {"large_module.py": massive_file}
        sanitized_files = self.extractor.extract_and_bound_files(files, max_total_tokens=1500)
        
        # Verify token count is strictly bounded
        total_tokens = sum(
            self.extractor.estimate_tokens(content)
            for content in sanitized_files.values()
        )
        self.assertLessEqual(total_tokens, 1500)
        self.assertIn("[TRUNCATED", sanitized_files["large_module.py"])


class TestDelegationPacket(unittest.TestCase):
    """Verifies DelegationPacket construction, Zero-Risk mode, and MCP formats."""

    def setUp(self):
        self.manager = DelegationManager()

    def test_create_packet_metadata_and_budget(self):
        packet = self.manager.create_packet(
            task_id="task_001",
            task_type=AdvisorTaskType.ARCHITECTURE_DESIGN,
            objective="Refactor monolith routing module into separate components",
            files={"router.py": "class MonolithRouter: pass"},
            constraints=["Zero dead code", "Maintain backward compatibility"],
            questions=["What is the cleanest decoupling boundary?"],
            mode=AdvisorMode.AUTOMATED_MCP,
        )
        self.assertEqual(packet.task_id, "task_001")
        self.assertEqual(packet.mode, AdvisorMode.AUTOMATED_MCP)
        self.assertLessEqual(packet.estimated_tokens, 2000)
        self.assertTrue(packet.packet_id.startswith("del_"))

    def test_zero_risk_clipboard_markdown_generation(self):
        packet = self.manager.create_packet(
            task_id="task_002",
            task_type=AdvisorTaskType.CODE_REVIEW,
            objective="Audit security of authentication endpoint",
            files={"auth.py": "def login(): pass"},
            constraints=["Zero credential leakage"],
            questions=["Are there any timing attack risks?"],
            mode=AdvisorMode.ZERO_RISK_MANUAL,
        )
        md = packet.to_clipboard_markdown()
        self.assertIn("# LAS External Advisor Consultation Packet", md)
        self.assertIn("Mode: ZERO_RISK_MANUAL", md)
        self.assertIn("Audit security of authentication endpoint", md)
        self.assertIn("Are there any timing attack risks?", md)

    def test_mcp_arguments_payload(self):
        packet = self.manager.create_packet(
            task_id="task_003",
            task_type=AdvisorTaskType.REFACTORING_STRATEGY,
            objective="Plan migration to Pydantic v2",
            files={},
            constraints=[],
            questions=[],
        )
        payload = packet.to_mcp_arguments()
        self.assertIn("packet_id", payload)
        self.assertIn("objective", payload)
        self.assertIn("task_type", payload)


class TestDelegationExecutionAndFallback(unittest.TestCase):
    """Verifies automated MCP delegation execution and graceful fallback degradation."""

    def setUp(self):
        self.manager = DelegationManager()
        self.packet = self.manager.create_packet(
            task_id="task_004",
            task_type=AdvisorTaskType.ARCHITECTURE_DESIGN,
            objective="Design high-performance cache layer",
            files={},
            constraints=[],
            questions=[],
            mode=AdvisorMode.AUTOMATED_MCP,
        )

    def test_successful_advisor_delegation(self):
        mock_external = MagicMock(return_value={
            "status": "success",
            "model": "claude-3-7-sonnet",
            "recommendations": ["Use Redis with local LRU tier"],
            "proposed_plan": "1. Scaffolding\n2. Implementation",
            "code_patches": [{"file": "cache.py", "diff": "+ class Cache: pass"}],
        })

        resp = self.manager.execute_delegation(
            packet=self.packet,
            external_caller=mock_external,
        )
        self.assertTrue(resp.success)
        self.assertFalse(resp.fallback_triggered)
        self.assertEqual(resp.advisor_model, "claude-3-7-sonnet")
        self.assertIn("Use Redis with local LRU tier", resp.recommendations)

    def test_timeout_triggers_graceful_fallback(self):
        """When external advisor times out or errors, graceful fallback to local model is triggered."""
        mock_external = MagicMock(side_effect=TimeoutError("External Advisor timeout after 30s"))
        mock_fallback = MagicMock(return_value="Local fallback: Recommended simple in-memory dict cache.")

        resp = self.manager.execute_delegation(
            packet=self.packet,
            external_caller=mock_external,
            fallback_caller=mock_fallback,
        )
        self.assertTrue(resp.success)
        self.assertTrue(resp.fallback_triggered)
        self.assertIn("fallback", resp.advisor_model.lower())
        self.assertIn("in-memory dict cache", resp.raw_content)
        mock_fallback.assert_called_once()

    def test_invalid_structure_triggers_fallback(self):
        """When external advisor returns unparseable junk, fallback caller recovers."""
        mock_external = MagicMock(return_value="NON_JSON_CORRUPTED_STRING")
        mock_fallback = MagicMock(return_value="Internal fallback recovery plan.")

        resp = self.manager.execute_delegation(
            packet=self.packet,
            external_caller=mock_external,
            fallback_caller=mock_fallback,
        )
        self.assertTrue(resp.success)
        self.assertTrue(resp.fallback_triggered)
        self.assertIn("Internal fallback", resp.raw_content)


class TestReasoningRouterAdvisorIntegration(unittest.TestCase):
    """Verifies ModelTier.ADVISOR_DELEGATION integration in reasoning_router.py."""

    def test_model_tier_contains_advisor_delegation(self):
        self.assertIn("ADVISOR_DELEGATION", ModelTier.__members__)
        self.assertEqual(ModelTier.ADVISOR_DELEGATION.value, "ADVISOR_DELEGATION")

    def test_router_profile_supports_advisor_delegation(self):
        profile = RoleModelProfile(
            role="ARCHITECT_ADVISOR",
            preferred_tier=ModelTier.ADVISOR_DELEGATION,
            default_provider="advisor_bridge",
            default_model="external-advisor",
            fallback_provider="gemini",
            fallback_model="gemini-2.5-flash",
        )
        router = DynamicThinkingRouter()
        router.register_profile(profile)

        retrieved = router.get_profile("ARCHITECT_ADVISOR")
        self.assertEqual(retrieved.preferred_tier, ModelTier.ADVISOR_DELEGATION)


class TestDelegateToAdvisorSkill(unittest.TestCase):
    """Verifies runtime skill invocation of delegate_to_advisor."""

    def test_invoke_delegate_to_advisor_zero_risk_mode(self):
        from agent_workspace.skills.delegate_to_advisor import (
            DelegateToAdvisorArgs,
            delegate_to_advisor,
        )
        args = DelegateToAdvisorArgs(
            task_id="task_skill_01",
            task_type="ARCHITECTURE_DESIGN",
            objective="Evaluate microservice boundary",
            files={"service.py": "def handle(): pass"},
            constraints=["Zero data leakage"],
            questions=["Should we use gRPC or REST?"],
            mode="ZERO_RISK_MANUAL",
        )
        res_json = delegate_to_advisor(args)
        parsed = json.loads(res_json)
        self.assertEqual(parsed.get("status"), "SUCCESS")
        self.assertEqual(parsed.get("mode"), "ZERO_RISK_MANUAL")
        self.assertIn("clipboard_payload", parsed)
        self.assertIn("Evaluate microservice boundary", parsed["clipboard_payload"])


if __name__ == "__main__":
    unittest.main()
