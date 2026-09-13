"""
core/reasoning_router.py - Heterogeneous Reasoning Model Adapters & Dynamic Thinking Router.

Aligned with ADR-005 (Stop-and-Wait Architecture Gate), ADR-006 (Agent Strategy Integration),
and the Universal Coding Agent Development Protocol v3.8.0.

Provides dynamic role-to-model tier routing, thinking budget containment,
deep reasoning telemetry extraction, and offline/air-gapped local model failover.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.providers import (
    BaseLLMProvider,
    ProviderFactory,
    ProviderResponse,
    ProviderResult,
)

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    """Execution tiers categorized by cognitive profile and latency."""
    REASONING = "REASONING"                  # Deep reasoning, thinking tokens (DeepSeek-R1, o3-mini, Claude 3.7)
    STANDARD_CODING = "STANDARD_CODING"      # Precision coding & AST compliance (Claude 3.5 Sonnet, GPT-4o, Qwen 2.5 Coder)
    FAST_PRECHECK = "FAST_PRECHECK"          # Sub-second latency, cheap preflight verification (Gemini 2.5 Flash, Haiku 3.5)
    LOCAL_OFFLINE = "LOCAL_OFFLINE"          # 100% air-gapped local inference via Ollama (deepseek-r1:8b, qwen2.5-coder)


class ReasoningConfig(BaseModel):
    """Dynamic reasoning parameters configured per request or per role."""
    model_config = ConfigDict(extra="ignore")

    tier: ModelTier = ModelTier.STANDARD_CODING
    thinking_budget: int = Field(default=0, ge=0, description="Allocated tokens for extended thinking/chain-of-thought")
    reasoning_effort: Optional[str] = Field(default=None, description="Reasoning intensity: low, medium, high")
    offline_mode: bool = Field(default=False, description="Enforce air-gapped zero-cloud execution via Ollama")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)


class RoleModelProfile(BaseModel):
    """Cognitive profile mapping a grounded role to its optimal model tier."""
    model_config = ConfigDict(extra="ignore")

    role: str
    preferred_tier: ModelTier
    default_provider: str
    default_model: str
    fallback_provider: str = "openai"
    fallback_model: str = "gpt-4o"
    thinking_budget: int = 0
    reasoning_effort: Optional[str] = None


class DynamicThinkingRouter:
    """Dynamic router mapping Grounded Roles to optimal heterogeneous models with thinking budgets."""

    DEFAULT_PROFILES: Dict[str, RoleModelProfile] = {
        "ARCHITECT_PLANNER_AGENT": RoleModelProfile(
            role="ARCHITECT_PLANNER_AGENT",
            preferred_tier=ModelTier.REASONING,
            default_provider="anthropic",
            default_model="claude-3-7-sonnet-latest",
            fallback_provider="deepseek",
            fallback_model="deepseek-reasoner",
            thinking_budget=8192,
            reasoning_effort="high",
        ),
        "SECURITY_AUDIT_AGENT": RoleModelProfile(
            role="SECURITY_AUDIT_AGENT",
            preferred_tier=ModelTier.REASONING,
            default_provider="openai",
            default_model="o3-mini",
            fallback_provider="deepseek",
            fallback_model="deepseek-reasoner",
            thinking_budget=4096,
            reasoning_effort="medium",
        ),
        "DOMAIN_LOGIC_AGENT": RoleModelProfile(
            role="DOMAIN_LOGIC_AGENT",
            preferred_tier=ModelTier.STANDARD_CODING,
            default_provider="anthropic",
            default_model="claude-3-5-sonnet-latest",
            fallback_provider="openai",
            fallback_model="gpt-4o",
            thinking_budget=0,
            reasoning_effort=None,
        ),
        "QA_TEST_AGENT": RoleModelProfile(
            role="QA_TEST_AGENT",
            preferred_tier=ModelTier.STANDARD_CODING,
            default_provider="openai",
            default_model="gpt-4o",
            fallback_provider="anthropic",
            fallback_model="claude-3-5-sonnet-latest",
            thinking_budget=0,
            reasoning_effort=None,
        ),
        "UI_UX_AGENT": RoleModelProfile(
            role="UI_UX_AGENT",
            preferred_tier=ModelTier.STANDARD_CODING,
            default_provider="anthropic",
            default_model="claude-3-5-sonnet-latest",
            fallback_provider="openai",
            fallback_model="gpt-4o",
            thinking_budget=0,
            reasoning_effort=None,
        ),
        "BACKEND_INFRA_AGENT": RoleModelProfile(
            role="BACKEND_INFRA_AGENT",
            preferred_tier=ModelTier.STANDARD_CODING,
            default_provider="openai",
            default_model="gpt-4o",
            fallback_provider="anthropic",
            fallback_model="claude-3-5-sonnet-latest",
            thinking_budget=0,
            reasoning_effort=None,
        ),
        "APPLICATION_FLOW_AGENT": RoleModelProfile(
            role="APPLICATION_FLOW_AGENT",
            preferred_tier=ModelTier.STANDARD_CODING,
            default_provider="openai",
            default_model="gpt-4o",
            fallback_provider="anthropic",
            fallback_model="claude-3-5-sonnet-latest",
            thinking_budget=0,
            reasoning_effort=None,
        ),
        "KNOWLEDGE_TOPOLOGY_AGENT": RoleModelProfile(
            role="KNOWLEDGE_TOPOLOGY_AGENT",
            preferred_tier=ModelTier.FAST_PRECHECK,
            default_provider="gemini",
            default_model="gemini-2.5-flash",
            fallback_provider="openai",
            fallback_model="gpt-4o-mini",
            thinking_budget=0,
            reasoning_effort=None,
        ),
        "DEV_OPS_AGENT": RoleModelProfile(
            role="DEV_OPS_AGENT",
            preferred_tier=ModelTier.STANDARD_CODING,
            default_provider="openai",
            default_model="gpt-4o",
            fallback_provider="anthropic",
            fallback_model="claude-3-5-sonnet-latest",
            thinking_budget=0,
            reasoning_effort=None,
        ),
        "CODE_REVIEW_AGENT": RoleModelProfile(
            role="CODE_REVIEW_AGENT",
            preferred_tier=ModelTier.REASONING,
            default_provider="anthropic",
            default_model="claude-3-7-sonnet-latest",
            fallback_provider="openai",
            fallback_model="o3-mini",
            thinking_budget=4096,
            reasoning_effort="medium",
        ),
    }

    # Offline/air-gapped local model mappings (Ollama)
    OFFLINE_PROFILES: Dict[str, RoleModelProfile] = {
        "ARCHITECT_PLANNER_AGENT": RoleModelProfile(
            role="ARCHITECT_PLANNER_AGENT",
            preferred_tier=ModelTier.LOCAL_OFFLINE,
            default_provider="ollama",
            default_model="deepseek-r1:8b",
            fallback_provider="ollama",
            fallback_model="qwen2.5-coder:7b",
            thinking_budget=4096,
            reasoning_effort="high",
        ),
        "SECURITY_AUDIT_AGENT": RoleModelProfile(
            role="SECURITY_AUDIT_AGENT",
            preferred_tier=ModelTier.LOCAL_OFFLINE,
            default_provider="ollama",
            default_model="deepseek-r1:8b",
            fallback_provider="ollama",
            fallback_model="qwen2.5-coder:7b",
            thinking_budget=4096,
            reasoning_effort="medium",
        ),
        "CODE_REVIEW_AGENT": RoleModelProfile(
            role="CODE_REVIEW_AGENT",
            preferred_tier=ModelTier.LOCAL_OFFLINE,
            default_provider="ollama",
            default_model="deepseek-r1:8b",
            fallback_provider="ollama",
            fallback_model="qwen2.5-coder:7b",
            thinking_budget=4096,
            reasoning_effort="medium",
        ),
    }

    def __init__(
        self,
        offline_mode: bool = False,
        provider_factory: Optional[Callable[..., BaseLLMProvider]] = None,
    ):
        self.offline_mode = offline_mode or os.environ.get("LAS_OFFLINE_MODE", "").lower() in ("1", "true", "yes")
        self._provider_factory = provider_factory or ProviderFactory.get_provider
        self._custom_profiles: Dict[str, RoleModelProfile] = {}

    def register_profile(self, profile: RoleModelProfile) -> None:
        """Register or override a role model profile."""
        self._custom_profiles[profile.role] = profile

    def get_profile(self, role: str) -> RoleModelProfile:
        """Retrieve the active model profile for a given role, considering offline mode."""
        if role in self._custom_profiles:
            return self._custom_profiles[role]

        if self.offline_mode:
            if role in self.OFFLINE_PROFILES:
                return self.OFFLINE_PROFILES[role]
            # Default offline standard coding profile
            return RoleModelProfile(
                role=role,
                preferred_tier=ModelTier.LOCAL_OFFLINE,
                default_provider="ollama",
                default_model="qwen2.5-coder:7b",
                fallback_provider="ollama",
                fallback_model="llama3.1",
                thinking_budget=0,
                reasoning_effort=None,
            )

        if role in self.DEFAULT_PROFILES:
            return self.DEFAULT_PROFILES[role]

        # Generic default fallback
        return RoleModelProfile(
            role=role,
            preferred_tier=ModelTier.STANDARD_CODING,
            default_provider="openai",
            default_model="gpt-4o",
            fallback_provider="anthropic",
            fallback_model="claude-3-5-sonnet-latest",
            thinking_budget=0,
            reasoning_effort=None,
        )

    def resolve_provider_and_config(
        self,
        role: str,
        user_override: Optional[Dict[str, Any]] = None,
    ) -> Tuple[BaseLLMProvider, Dict[str, Any]]:
        """Instantiate the appropriate LLM provider and build the execution config.

        Applies dynamic thinking budgets, reasoning effort, and ensures offline constraints.
        """
        profile = self.get_profile(role)
        override = user_override or {}

        # Allow user overrides
        provider_name = override.get("provider") or profile.default_provider
        model_name = override.get("model") or profile.default_model
        thinking_budget = override.get("thinking_budget")
        if thinking_budget is None:
            thinking_budget = profile.thinking_budget

        reasoning_effort = override.get("reasoning_effort") or profile.reasoning_effort
        temperature = override.get("temperature", 0.0)
        max_tokens = override.get("max_tokens", 4096)

        # Enforce offline constraint
        if self.offline_mode:
            provider_name = "ollama"
            if thinking_budget and thinking_budget > 0:
                model_name = override.get("model") or "deepseek-r1:8b"
            else:
                model_name = override.get("model") or "qwen2.5-coder:7b"

        # Instantiate provider via factory
        api_key = override.get("api_key")
        base_url = override.get("base_url")
        provider = self._provider_factory(provider_name, api_key=api_key, base_url=base_url)

        # Build augmented config
        config: Dict[str, Any] = {
            "model": model_name,
            "provider": provider_name,
            "tier": profile.preferred_tier.value,
            "thinking_budget": thinking_budget,
            "reasoning_effort": reasoning_effort,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "offline_mode": self.offline_mode,
        }
        # Merge other arbitrary options
        for key, val in override.items():
            if key not in config:
                config[key] = val

        return provider, config

    async def execute_turn(
        self,
        role: str,
        system_prompt: str,
        messages: list[Dict[str, Any]],
        tool_schemas: list[Dict[str, Any]] | None = None,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> ProviderResponse:
        """Execute an agent turn with dynamic reasoning and telemetry extraction."""
        provider, config = self.resolve_provider_and_config(role, config_override)
        schemas = tool_schemas or []
        resp = await provider.complete(system_prompt, messages, schemas, config)
        if not isinstance(resp, ProviderResponse):
            resp = ProviderResponse(resp[0], resp[1])
        return resp
