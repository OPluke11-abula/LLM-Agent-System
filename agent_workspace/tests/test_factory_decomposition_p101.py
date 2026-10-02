"""Unit and integration tests for Autonomous Software Factory Subsystem (Phase 101).

Validates AST cyclomatic complexity analysis, coupling metrics, DAG decomposition,
scope isolation across parallel waves, cycle rejection, and mesh capability routing.
"""

import tempfile
from pathlib import Path
import pytest

from agent_workspace.core.factory import (
    CodeComplexityAnalyzer,
    CodeComplexityMetrics,
    ComplexityRiskLevel,
    MeshFactoryDispatcher,
    RefactoringDAGDecomposer,
    RefactoringTaskDAG,
    RefactoringTaskNode,
    RefactoringTaskType,
)
from agent_workspace.core.federated_mesh import PeerCapability


SAMPLE_COMPLEX_CODE = """
import os
import sys
from pathlib import Path

class LegacyMonolithService:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug

    def process_data(self, items: list, threshold: int = 10) -> int:
        count = 0
        for item in items:
            if item > threshold and (self.debug or item % 2 == 0):
                count += 1
            elif item == 0:
                count -= 1
            else:
                try:
                    count += self._fallback_calculate(item)
                except Exception as e:
                    pass
        return count

    def _fallback_calculate(self, val: int) -> int:
        while val > 10:
            val -= 2
        return val
"""


def test_complexity_analyzer_snippet():
    """Validates AST cyclomatic complexity calculation and function/class counts."""
    analyzer = CodeComplexityAnalyzer()
    metrics = analyzer.analyze_source(SAMPLE_COMPLEX_CODE, file_path="sample_service.py")

    assert metrics.file_path == "sample_service.py"
    assert metrics.function_count == 3  # __init__, process_data, _fallback_calculate
    assert metrics.class_count == 1     # LegacyMonolithService
    assert metrics.loc > 15
    # Complexity: base(1) + for(1) + if(1) + bool_and(1) + bool_or(1) + elif(1) + except(1) + while(1) >= 8
    assert metrics.cyclomatic_complexity >= 8
    assert metrics.efferent_coupling >= 2  # os, sys, pathlib
    assert metrics.risk_score > 0.0
    assert metrics.risk_level in (ComplexityRiskLevel.MEDIUM, ComplexityRiskLevel.HIGH, ComplexityRiskLevel.CRITICAL)


def test_complexity_analyzer_coupling_in_directory():
    """Validates afferent and efferent coupling calculations across local files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        module_b = tmp_path / "base_utils.py"
        module_b.write_text("def helper():\n    return 42\n", encoding="utf-8")

        module_a = tmp_path / "consumer.py"
        module_a.write_text("import base_utils\ndef run():\n    return base_utils.helper()\n", encoding="utf-8")

        analyzer = CodeComplexityAnalyzer(root_dir=tmp_path)
        metrics_dict = analyzer.analyze_repository(target_dir=tmp_path)

        assert "consumer.py" in metrics_dict
        assert "base_utils.py" in metrics_dict

        # consumer imports base_utils
        assert metrics_dict["consumer.py"].efferent_coupling >= 1
        # base_utils is imported by consumer
        assert metrics_dict["base_utils.py"].afferent_coupling >= 1


def test_dag_cycle_detection_and_topological_sort():
    """Validates Kahn's algorithm cycle detection and topological ordering."""
    dag = RefactoringTaskDAG(name="Cycle-Test-DAG")
    t1 = RefactoringTaskNode(node_id="t1", title="Task 1", task_type=RefactoringTaskType.TYPE_HARDENING)
    t2 = RefactoringTaskNode(node_id="t2", title="Task 2", task_type=RefactoringTaskType.MODULARIZE)
    t3 = RefactoringTaskNode(node_id="t3", title="Task 3", task_type=RefactoringTaskType.ASYNC_MIGRATION)

    dag.add_node(t1)
    dag.add_node(t2)
    dag.add_node(t3)

    # Valid dependency chain: t1 -> t2 -> t3
    dag.add_dependency(dependent_id="t2", prerequisite_id="t1")
    dag.add_dependency(dependent_id="t3", prerequisite_id="t2")

    order = dag.topological_sort()
    assert order == ["t1", "t2", "t3"]

    # Introduce a cyclic dependency: t1 depends on t3
    with pytest.raises(ValueError, match="Cycle detected"):
        dag.add_dependency(dependent_id="t1", prerequisite_id="t3")


def test_scope_isolation_in_parallel_waves():
    """Ensures tasks touching the same mutable scope are NEVER scheduled in the same parallel wave."""
    decomposer = RefactoringDAGDecomposer()

    t_shared_1 = RefactoringTaskNode(
        node_id="t_shared_1",
        title="Refactor routes/api.py Part 1",
        task_type=RefactoringTaskType.MODULARIZE,
        mutable_scope=["routes/api.py"],
        priority=10,
    )
    t_shared_2 = RefactoringTaskNode(
        node_id="t_shared_2",
        title="Refactor routes/api.py Part 2",
        task_type=RefactoringTaskType.ASYNC_MIGRATION,
        mutable_scope=["routes/api.py"],
        priority=5,
    )
    t_independent = RefactoringTaskNode(
        node_id="t_independent",
        title="Refactor models/user.py",
        task_type=RefactoringTaskType.TYPE_HARDENING,
        mutable_scope=["models/user.py"],
        priority=8,
    )

    dag = decomposer.decompose_custom_plan([t_shared_1, t_shared_2, t_independent])
    waves = dag.get_parallel_waves()

    # t_shared_1 and t_shared_2 must be in different waves
    assert len(waves) >= 2

    # Verify 100% disjoint mutable scopes within each wave
    for wave_idx, wave in enumerate(waves):
        seen_scopes = set()
        for task in wave:
            for f in task.mutable_scope:
                norm_f = f.lower()
                assert norm_f not in seen_scopes, f"Scope collision in wave {wave_idx} on file {norm_f}"
                seen_scopes.add(norm_f)


def test_decomposer_from_metrics():
    """Validates decomposition of repository metrics into a prioritized refactoring DAG."""
    metrics = {
        "core/giant_monolith.py": CodeComplexityMetrics(
            file_path="core/giant_monolith.py",
            loc=850,
            cyclomatic_complexity=28,
            risk_level=ComplexityRiskLevel.CRITICAL,
            risk_score=85.0,
        ),
        "core/entangled_router.py": CodeComplexityMetrics(
            file_path="core/entangled_router.py",
            loc=350,
            cyclomatic_complexity=12,
            efferent_coupling=10,
            afferent_coupling=4,
            risk_level=ComplexityRiskLevel.HIGH,
            risk_score=55.0,
        ),
        "core/simple_util.py": CodeComplexityMetrics(
            file_path="core/simple_util.py",
            loc=60,
            cyclomatic_complexity=2,
            risk_level=ComplexityRiskLevel.LOW,
            risk_score=10.0,
        ),
    }

    decomposer = RefactoringDAGDecomposer(dag_name="Test-Decomposition-DAG")
    dag = decomposer.decompose(metrics, max_tasks=5)

    assert len(dag.nodes) == 3
    # Giant monolith should be classified as MODULARIZE
    monolith_task = next(n for n in dag.nodes.values() if "giant_monolith.py" in n.target_files[0])
    assert monolith_task.task_type == RefactoringTaskType.MODULARIZE
    assert monolith_task.priority > 90

    # Entangled router should be classified as DECOUPLING
    router_task = next(n for n in dag.nodes.values() if "entangled_router.py" in n.target_files[0])
    assert router_task.task_type == RefactoringTaskType.DECOUPLING


def test_mesh_dispatcher_plan_generation():
    """Validates capability matching and dispatch plan generation across heterogeneous peers."""
    dag = RefactoringTaskDAG(name="Dispatch-Test-DAG")
    dag.add_node(
        RefactoringTaskNode(
            node_id="task-arch-1",
            title="Architectural Decoupling",
            task_type=RefactoringTaskType.DECOUPLING,
            mutable_scope=["arch/engine.py"],
        )
    )
    dag.add_node(
        RefactoringTaskNode(
            node_id="task-mut-1",
            title="Async I/O Rewrite",
            task_type=RefactoringTaskType.ASYNC_MIGRATION,
            mutable_scope=["io/client.py"],
        )
    )
    dag.add_node(
        RefactoringTaskNode(
            node_id="task-test-1",
            title="E2E Test Ladder Coverage",
            task_type=RefactoringTaskType.TEST_EXPANSION,
            mutable_scope=["tests/test_e2e.py"],
        )
    )

    custom_peers = {
        "cloud-deepseek-r1": [PeerCapability.REASONING_ENGINE],
        "workstation-edge-01": [PeerCapability.SANDBOX_MUTATION],
        "ci-worker-runner": [PeerCapability.TEST_RUNNER],
    }

    dispatcher = MeshFactoryDispatcher(registered_peers=custom_peers)
    plan = dispatcher.create_dispatch_plan(dag)

    assert plan.dag_id == dag.dag_id
    assert len(plan.assignments) == 3
    assert plan.total_waves >= 1

    assignment_map = {a.task_id: a for a in plan.assignments}
    # Decoupling goes to REASONING_ENGINE
    assert assignment_map["task-arch-1"].assigned_peer_id == "cloud-deepseek-r1"
    assert assignment_map["task-arch-1"].required_capability == PeerCapability.REASONING_ENGINE.value

    # Async migration goes to SANDBOX_MUTATION
    assert assignment_map["task-mut-1"].assigned_peer_id == "workstation-edge-01"
    assert assignment_map["task-mut-1"].required_capability == PeerCapability.SANDBOX_MUTATION.value

    # Test expansion goes to TEST_RUNNER
    assert assignment_map["task-test-1"].assigned_peer_id == "ci-worker-runner"
    assert assignment_map["task-test-1"].required_capability == PeerCapability.TEST_RUNNER.value


def test_end_to_end_factory_flow():
    """End-to-end integration: analyze factory code, decompose tasks, and dispatch to mesh."""
    factory_dir = Path("agent_workspace/core/factory")
    analyzer = CodeComplexityAnalyzer(root_dir=factory_dir)
    metrics = analyzer.analyze_repository(target_dir=factory_dir)

    assert len(metrics) >= 4  # __init__, models, complexity_analyzer, task_decomposer, mesh_dispatcher

    decomposer = RefactoringDAGDecomposer()
    dag = decomposer.decompose(metrics, goal="Factory Self-Analysis")
    assert len(dag.nodes) >= 4

    dispatcher = MeshFactoryDispatcher()
    plan = dispatcher.create_dispatch_plan(dag)

    assert plan.total_waves >= 1
    assert len(plan.assignments) == len(dag.nodes)
    for wave in plan.wave_breakdown:
        assert len(wave) >= 1
