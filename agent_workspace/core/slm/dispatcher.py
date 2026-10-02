"""Complexity-Aware Smart Model Dispatcher (Phase 110).

Aligned with Universal Coding Agent Development Protocol v3.8.0, Anti-Corruption
Principle #4 (Typed Failures), Principle #5 (Specification-First), and
Principle #7 (Configuration over Hardcoding).

Routes code tasks with Cyclomatic Complexity (CC) <= 10 to local Edge SLM for zero-cloud-token
latency-optimized processing, and CC > 10 or architectural refactoring to Cloud Reasoning Engine.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.factory.complexity_analyzer import CodeComplexityAnalyzer
from agent_workspace.core.factory.models import CodeComplexityMetrics, RefactoringTaskType
from agent_workspace.core.federated_mesh import PeerCapability
from agent_workspace.core.slm.engine import EdgeSLMEngine, EdgeSLMResponse

logger = logging.getLogger("SmartModelDispatcher")


class ModelRouteTarget(str, Enum):
    """Target execution tier for dispatched code workloads."""

    EDGE_SLM = "EDGE_SLM"
    CLOUD_REASONER = "CLOUD_REASONER"


class RoutingDecision(BaseModel):
    """Structured decision explaining workload target routing."""

    model_config = ConfigDict(extra="ignore")

    target: ModelRouteTarget
    reason: str
    cyclomatic_complexity: int
    loc: int
    efferent_coupling: int
    is_local_eligible: bool
    estimated_cloud_tokens_saved: int = 0
    fallback_triggered: bool = False


class SmartModelDispatcher:
    """Evaluates AST complexity and dispatches refactoring tasks to Edge SLM or Cloud."""

    def __init__(
        self,
        slm_engine: Optional[EdgeSLMEngine] = None,
        complexity_analyzer: Optional[CodeComplexityAnalyzer] = None,
        complexity_threshold: int = 10,
        cloud_fallback_enabled: bool = True,
    ) -> None:
        self.slm_engine = slm_engine or EdgeSLMEngine()
        self.analyzer = complexity_analyzer or CodeComplexityAnalyzer()
        self.complexity_threshold = complexity_threshold
        self.cloud_fallback_enabled = cloud_fallback_enabled

    def evaluate_code(self, code_snippet: str, file_path: str = "snippet.py") -> CodeComplexityMetrics:
        """Computes AST complexity metrics for code snippet."""
        return self.analyzer.analyze_source(code_snippet, file_path=file_path)

    async def decide_route(
        self,
        code_snippet: str,
        task_type: Optional[str] = None,
        check_health: bool = True,
    ) -> RoutingDecision:
        """Determines whether to route to local Edge SLM or cloud reasoning engine."""
        metrics = self.evaluate_code(code_snippet)
        cc = metrics.cyclomatic_complexity
        loc = metrics.loc
        coupling = metrics.efferent_coupling

        # Low-complexity task types naturally suited for edge SLM
        slm_natural_tasks = {
            RefactoringTaskType.SYNTAX_CLEANUP.value,
            RefactoringTaskType.TEST_STUB_GENERATION.value,
        }

        is_slm_task_type = task_type in slm_natural_tasks if task_type else False

        # Local eligible if CC <= threshold and efferent coupling is low (<= 5)
        is_local_eligible = (cc <= self.complexity_threshold and coupling <= 5) or is_slm_task_type

        # Estimate potential token savings (prompt + code length in tokens estimate)
        approx_tokens = max(10, int(loc * 8))

        if not is_local_eligible:
            return RoutingDecision(
                target=ModelRouteTarget.CLOUD_REASONER,
                reason=f"Code complexity (CC={cc}, coupling={coupling}) exceeds threshold ({self.complexity_threshold})",
                cyclomatic_complexity=cc,
                loc=loc,
                efferent_coupling=coupling,
                is_local_eligible=False,
                estimated_cloud_tokens_saved=0,
                fallback_triggered=False,
            )

        # Health probe if local is eligible
        if check_health:
            is_healthy = await self.slm_engine.health_check()
            if not is_healthy:
                if self.cloud_fallback_enabled:
                    logger.warning("Edge SLM is offline. Falling back to CLOUD_REASONER.")
                    return RoutingDecision(
                        target=ModelRouteTarget.CLOUD_REASONER,
                        reason="Edge SLM offline; triggered graceful fallback to cloud reasoning engine",
                        cyclomatic_complexity=cc,
                        loc=loc,
                        efferent_coupling=coupling,
                        is_local_eligible=True,
                        estimated_cloud_tokens_saved=0,
                        fallback_triggered=True,
                    )
                else:
                    raise RuntimeError("Edge SLM offline and cloud fallback is disabled")

        return RoutingDecision(
            target=ModelRouteTarget.EDGE_SLM,
            reason=f"Low complexity (CC={cc} <= {self.complexity_threshold}); routed to local Edge SLM",
            cyclomatic_complexity=cc,
            loc=loc,
            efferent_coupling=coupling,
            is_local_eligible=True,
            estimated_cloud_tokens_saved=approx_tokens,
            fallback_triggered=False,
        )

    async def execute_task(
        self,
        prompt: str,
        code_snippet: str,
        task_type: Optional[str] = None,
        system_prompt: str = "You are an optimized local coding SLM.",
        cloud_executor: Optional[Callable[[str, str], Any]] = None,
    ) -> Dict[str, Any]:
        """Routes and executes the task against either Edge SLM or cloud executor."""
        decision = await self.decide_route(code_snippet, task_type=task_type)

        if decision.target == ModelRouteTarget.EDGE_SLM:
            full_prompt = f"{prompt}\n\n```python\n{code_snippet}\n```"
            slm_resp = await self.slm_engine.generate_completion(
                prompt=full_prompt,
                system_prompt=system_prompt,
            )
            return {
                "decision": decision.model_dump(),
                "response": slm_resp.model_dump(),
                "source": "EDGE_SLM",
                "tokens_saved": decision.estimated_cloud_tokens_saved,
            }
        else:
            if cloud_executor is not None:
                content = await cloud_executor(prompt, code_snippet) if callable(cloud_executor) else str(cloud_executor)
            else:
                content = "[Mock Cloud Reasoner Execution Output]"

            return {
                "decision": decision.model_dump(),
                "response": {
                    "content": content,
                    "model": "cloud-reasoning-engine",
                    "cloud_egress_prevented": False,
                },
                "source": "CLOUD_REASONER",
                "tokens_saved": 0,
            }
