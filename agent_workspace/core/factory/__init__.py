"""Autonomous Software Factory Subsystem (Phase 101).

Provides AST-based repository complexity analysis, acyclic refactoring task DAG decomposition
with guaranteed scope isolation, and capability-aware dispatching to Federated Mesh peer nodes.
"""

from agent_workspace.core.factory.models import (
    CodeComplexityMetrics,
    ComplexityRiskLevel,
    FactoryDispatchAssignment,
    FactoryDispatchPlan,
    RefactoringTaskDAG,
    RefactoringTaskNode,
    RefactoringTaskType,
)
from agent_workspace.core.factory.complexity_analyzer import CodeComplexityAnalyzer
from agent_workspace.core.factory.task_decomposer import RefactoringDAGDecomposer
from agent_workspace.core.factory.mesh_dispatcher import MeshFactoryDispatcher
from agent_workspace.core.factory.adversarial_committee import (
    AdversarialCommitteeEngine,
    AdversarialDebateRecord,
    AdversarialDebateTurn,
    AdversarialPersona,
    SelfHealingContract,
    VulnerabilitySeverity,
    VulnerabilityVector,
)
from agent_workspace.core.factory.distillation import PatternDistillationEngine
from agent_workspace.core.factory.obsidian_synapse import ObsidianSynapseSynchronizer

__all__ = [
    "CodeComplexityMetrics",
    "ComplexityRiskLevel",
    "FactoryDispatchAssignment",
    "FactoryDispatchPlan",
    "RefactoringTaskDAG",
    "RefactoringTaskNode",
    "RefactoringTaskType",
    "CodeComplexityAnalyzer",
    "RefactoringDAGDecomposer",
    "MeshFactoryDispatcher",
    "AdversarialCommitteeEngine",
    "AdversarialDebateRecord",
    "AdversarialDebateTurn",
    "AdversarialPersona",
    "SelfHealingContract",
    "VulnerabilitySeverity",
    "VulnerabilityVector",
    "PatternDistillationEngine",
    "ObsidianSynapseSynchronizer",
]
