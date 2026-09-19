"""Refactoring Task DAG Decomposer (Phase 101).

Translates repository complexity and coupling analysis into an acyclic directed graph (DAG)
of modular refactoring tasks, guaranteeing mutable scope isolation between parallel tasks.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from agent_workspace.core.factory.models import (
    CodeComplexityMetrics,
    ComplexityRiskLevel,
    RefactoringTaskDAG,
    RefactoringTaskNode,
    RefactoringTaskType,
)

logger = logging.getLogger("DAGDecomposer")


class RefactoringDAGDecomposer:
    """Decomposes repository-wide technical debt into a verified refactoring DAG."""

    def __init__(self, dag_name: str = "Autonomous-Factory-DAG") -> None:
        self.dag_name = dag_name

    def decompose(
        self,
        metrics: Dict[str, CodeComplexityMetrics],
        goal: str = "Autonomous Repository Modernization",
        max_tasks: int = 10,
    ) -> RefactoringTaskDAG:
        """Translates analyzed code metrics into a prioritized, dependency-ordered refactoring DAG."""
        dag = RefactoringTaskDAG(name=self.dag_name)

        # Filter and rank candidate modules by risk score
        sorted_metrics = sorted(metrics.values(), key=lambda m: m.risk_score, reverse=True)
        top_candidates = sorted_metrics[:max_tasks]

        if not top_candidates:
            # Generate a baseline health inspection task if no metrics exist
            dummy_node = RefactoringTaskNode(
                title="Baseline Repository Modernization Sweep",
                task_type=RefactoringTaskType.TYPE_HARDENING,
                target_files=["."],
                mutable_scope=["."],
                priority=1,
            )
            dag.add_node(dummy_node)
            return dag

        created_nodes: Dict[str, RefactoringTaskNode] = {}
        file_to_node_id: Dict[str, str] = {}

        # 1. Create task nodes for each candidate
        for rank, item in enumerate(top_candidates, start=1):
            file_clean = item.file_path.replace("\\", "/")

            if item.cyclomatic_complexity >= 15 or item.loc >= 400:
                task_type = RefactoringTaskType.MODULARIZE
                title = f"Decompose high-complexity module: {file_clean} (CC={item.cyclomatic_complexity}, LOC={item.loc})"
            elif item.efferent_coupling + item.afferent_coupling >= 8:
                task_type = RefactoringTaskType.DECOUPLING
                title = f"Decouple entangled dependencies in: {file_clean} (Coupling={item.efferent_coupling + item.afferent_coupling})"
            elif item.risk_level in (ComplexityRiskLevel.HIGH, ComplexityRiskLevel.CRITICAL):
                task_type = RefactoringTaskType.ASYNC_MIGRATION
                title = f"Migrate async non-blocking pipeline: {file_clean}"
            else:
                task_type = RefactoringTaskType.TYPE_HARDENING
                title = f"Apply strict contract and type hardening: {file_clean}"

            effort = min(10, max(1, int(item.risk_score // 10) + 1))
            priority = 100 - rank

            node = RefactoringTaskNode(
                title=title,
                task_type=task_type,
                target_files=[file_clean],
                mutable_scope=[file_clean],
                estimated_effort=effort,
                priority=priority,
            )
            created_nodes[node.node_id] = node
            file_to_node_id[file_clean] = node.node_id
            dag.add_node(node)

        # 2. Establish dependencies and enforce Scope Isolation
        # If file A has afferent coupling to file B (B depends on A), refactor A first!
        for file_path, item in metrics.items():
            file_clean = file_path.replace("\\", "/")
            if file_clean in file_to_node_id:
                node_id = file_to_node_id[file_clean]
                # Check for other nodes that might touch or conflict with this file
                for other_id, other_node in created_nodes.items():
                    if other_id == node_id:
                        continue
                    # Scope collision prevention: if two tasks touch the same file, serialize them
                    if created_nodes[node_id].shares_scope_with(other_node):
                        # The lower priority task depends on the higher priority task
                        if created_nodes[node_id].priority < other_node.priority:
                            if other_id not in created_nodes[node_id].dependencies:
                                created_nodes[node_id].dependencies.append(other_id)
                        else:
                            if node_id not in other_node.dependencies:
                                other_node.dependencies.append(node_id)

        # Validate that the resulting DAG is strictly acyclic
        dag.validate_acyclic()
        return dag

    def decompose_custom_plan(
        self,
        tasks: List[RefactoringTaskNode],
        dag_name: Optional[str] = None,
    ) -> RefactoringTaskDAG:
        """Constructs and validates a custom refactoring DAG, enforcing scope isolation between concurrent tasks."""
        dag = RefactoringTaskDAG(name=dag_name or self.dag_name)

        for task in tasks:
            dag.add_node(task)

        # Automatically serialize tasks that share mutable scopes to prevent race conditions
        task_list = list(dag.nodes.values())
        for i in range(len(task_list)):
            for j in range(i + 1, len(task_list)):
                node_a = task_list[i]
                node_b = task_list[j]
                if node_a.shares_scope_with(node_b):
                    # Higher priority runs first
                    if node_a.priority >= node_b.priority:
                        if node_a.node_id not in node_b.dependencies and node_b.node_id not in node_a.dependencies:
                            node_b.dependencies.append(node_a.node_id)
                    else:
                        if node_b.node_id not in node_a.dependencies and node_a.node_id not in node_b.dependencies:
                            node_a.dependencies.append(node_b.node_id)

        dag.validate_acyclic()
        return dag
