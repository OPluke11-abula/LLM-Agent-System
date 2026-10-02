"""Edge Small Language Model (SLM) Subsystem (Phase 110).

Aligned with Universal Coding Agent Development Protocol v3.8.0.
Provides local model inference, zero-cloud-token AST static analysis,
and complexity-aware intelligent model routing.
"""

from __future__ import annotations

from agent_workspace.core.slm.dispatcher import (
    ModelRouteTarget,
    RoutingDecision,
    SmartModelDispatcher,
)
from agent_workspace.core.slm.engine import EdgeSLMEngine, EdgeSLMResponse
from agent_workspace.core.slm.offline_analyzer import (
    ASTDefectItem,
    OfflineAnalysisResult,
    OfflineASTAnalyzer,
)

__all__ = [
    "EdgeSLMEngine",
    "EdgeSLMResponse",
    "OfflineASTAnalyzer",
    "ASTDefectItem",
    "OfflineAnalysisResult",
    "SmartModelDispatcher",
    "ModelRouteTarget",
    "RoutingDecision",
]
