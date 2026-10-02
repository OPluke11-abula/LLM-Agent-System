"""Data models and DAG contracts for Autonomous Software Factory (Phase 101).

Defines AST code complexity metrics, refactoring task nodes, DAG dependency resolution,
and capability-aware mesh dispatch schemas.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field


class ComplexityRiskLevel(str, Enum):
    """Risk classification based on AST cyclomatic complexity and module coupling."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CodeComplexityMetrics(BaseModel):
    """Quantified AST complexity and coupling metrics for a source module."""

    model_config = ConfigDict(extra="allow")

    file_path: str
    loc: int = 0
    cyclomatic_complexity: int = 1
    function_count: int = 0
    class_count: int = 0
    afferent_coupling: int = 0  # Incoming dependencies (modules that import this)
    efferent_coupling: int = 0  # Outgoing dependencies (modules imported by this)
    risk_level: ComplexityRiskLevel = ComplexityRiskLevel.LOW
    risk_score: float = 0.0

    def compute_risk(self) -> float:
        """Computes standardized risk score from complexity, LOC, and coupling."""
        # Weighted formula:
        # Cyclomatic complexity weight = 0.45
        # Coupling weight = 0.35
        # LOC weight = 0.20 (normalized per 100 LOC)
        cc_component = min(50.0, float(self.cyclomatic_complexity)) * 2.0
        coupling_component = min(20.0, float(self.afferent_coupling + self.efferent_coupling)) * 5.0
        loc_component = min(1000.0, float(self.loc)) / 10.0

        score = (cc_component * 0.45) + (coupling_component * 0.35) + (loc_component * 0.20)
        self.risk_score = round(score, 2)

        if self.risk_score >= 70.0 or self.cyclomatic_complexity >= 25:
            self.risk_level = ComplexityRiskLevel.CRITICAL
        elif self.risk_score >= 45.0 or self.cyclomatic_complexity >= 15:
            self.risk_level = ComplexityRiskLevel.HIGH
        elif self.risk_score >= 20.0 or self.cyclomatic_complexity >= 8:
            self.risk_level = ComplexityRiskLevel.MEDIUM
        else:
            self.risk_level = ComplexityRiskLevel.LOW

        return self.risk_score


class RefactoringTaskType(str, Enum):
    """Categorization of autonomous refactoring operations."""

    MODULARIZE = "MODULARIZE"              # Break giant module into smaller units
    ASYNC_MIGRATION = "ASYNC_MIGRATION"    # Convert sync I/O to async/await
    TYPE_HARDENING = "TYPE_HARDENING"      # Strict type annotations and contract enforcement
    DECOUPLING = "DECOUPLING"              # Break circular dependencies and reduce coupling
    TEST_EXPANSION = "TEST_EXPANSION"      # Increase test coverage on high-risk boundaries


class RefactoringTaskNode(BaseModel):
    """An individual refactoring unit with strictly bounded mutable scopes."""

    model_config = ConfigDict(extra="allow")

    node_id: str = Field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    title: str
    task_type: RefactoringTaskType
    target_files: List[str] = Field(default_factory=list)
    mutable_scope: List[str] = Field(default_factory=list)  # Files permitted to be mutated
    dependencies: List[str] = Field(default_factory=list)  # Task node IDs that must finish first
    estimated_effort: int = 1                              # Complexity weight (1-10)
    priority: int = 1                                      # Scheduling priority (higher runs first)
    self_healing_contract: Optional[Any] = None            # Phase 102: Verified adversarial contract

    def shares_scope_with(self, other: RefactoringTaskNode) -> bool:
        """Returns True if this task and other task have overlapping mutable file scopes."""
        self_scope = {f.replace("\\", "/").lower() for f in self.mutable_scope}
        other_scope = {f.replace("\\", "/").lower() for f in other.mutable_scope}
        return bool(self_scope.intersection(other_scope))


class RefactoringTaskDAG(BaseModel):
    """Acyclic directed graph of refactoring tasks with wave-based parallel scheduling."""

    model_config = ConfigDict(extra="allow")

    dag_id: str = Field(default_factory=lambda: f"dag-{uuid.uuid4().hex[:8]}")
    name: str = "Modernization-DAG"
    nodes: Dict[str, RefactoringTaskNode] = Field(default_factory=dict)

    def add_node(self, node: RefactoringTaskNode) -> None:
        """Adds a task node to the DAG."""
        self.nodes[node.node_id] = node

    def add_dependency(self, dependent_id: str, prerequisite_id: str) -> None:
        """Adds a directed dependency edge: prerequisite_id must finish before dependent_id."""
        if dependent_id not in self.nodes:
            raise KeyError(f"Dependent node '{dependent_id}' not found in DAG")
        if prerequisite_id not in self.nodes:
            raise KeyError(f"Prerequisite node '{prerequisite_id}' not found in DAG")
        if prerequisite_id not in self.nodes[dependent_id].dependencies:
            self.nodes[dependent_id].dependencies.append(prerequisite_id)
        self.validate_acyclic()

    def validate_acyclic(self) -> bool:
        """Validates that the DAG contains no directed cycles using Kahn's algorithm."""
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        adj_list: Dict[str, List[str]] = {nid: [] for nid in self.nodes}

        for nid, node in self.nodes.items():
            for dep in node.dependencies:
                if dep in adj_list:
                    adj_list[dep].append(nid)
                    in_degree[nid] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited_count = 0

        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for neighbor in adj_list[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(self.nodes):
            raise ValueError("Cycle detected in RefactoringTaskDAG! Tasks must form an acyclic graph.")
        return True

    def topological_sort(self) -> List[str]:
        """Returns node IDs in valid topological execution order."""
        self.validate_acyclic()
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        adj_list: Dict[str, List[str]] = {nid: [] for nid in self.nodes}

        for nid, node in self.nodes.items():
            for dep in node.dependencies:
                adj_list[dep].append(nid)
                in_degree[nid] += 1

        queue = sorted([nid for nid, deg in in_degree.items() if deg == 0])
        order: List[str] = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for neighbor in sorted(adj_list[curr]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return order

    def get_parallel_waves(self) -> List[List[RefactoringTaskNode]]:
        """Computes parallel execution waves, guaranteeing disjoint mutable scopes within each wave."""
        self.validate_acyclic()
        remaining_nodes = dict(self.nodes)
        completed_ids: Set[str] = set()
        waves: List[List[RefactoringTaskNode]] = []

        while remaining_nodes:
            # Find all nodes whose dependencies are completely satisfied
            candidate_ids = [
                nid for nid, node in remaining_nodes.items()
                if all(dep in completed_ids for dep in node.dependencies)
            ]

            if not candidate_ids:
                raise ValueError("Deadlock or cycle encountered while calculating parallel waves")

            # Sort candidate nodes by priority (descending) and effort (ascending)
            candidate_ids.sort(
                key=lambda nid: (-remaining_nodes[nid].priority, remaining_nodes[nid].estimated_effort)
            )

            # Greedily schedule candidates into current wave ensuring zero scope overlap
            current_wave: List[RefactoringTaskNode] = []
            occupied_scopes: Set[str] = set()

            for cid in candidate_ids:
                node = remaining_nodes[cid]
                node_scope = {f.replace("\\", "/").lower() for f in node.mutable_scope}
                # Check for mutable scope conflict with other tasks already in this wave
                if not node_scope.intersection(occupied_scopes):
                    current_wave.append(node)
                    occupied_scopes.update(node_scope)
                    del remaining_nodes[cid]
                    completed_ids.add(cid)

            if not current_wave:
                # Should not occur, but safeguard against starvation
                first_id = candidate_ids[0]
                node = remaining_nodes.pop(first_id)
                current_wave.append(node)
                completed_ids.add(first_id)

            waves.append(current_wave)

        return waves


class FactoryDispatchAssignment(BaseModel):
    """Mapping of an individual task node to an assigned mesh peer."""

    task_id: str
    task_title: str
    assigned_peer_id: str
    required_capability: str
    status: str = "PENDING"
    scheduled_at: float = Field(default_factory=time.time)


class FactoryDispatchPlan(BaseModel):
    """Complete execution dispatch plan mapping a refactoring DAG to mesh nodes."""

    dag_id: str
    plan_id: str = Field(default_factory=lambda: f"plan-{uuid.uuid4().hex[:8]}")
    assignments: List[FactoryDispatchAssignment] = Field(default_factory=list)
    total_waves: int = 0
    wave_breakdown: List[List[str]] = Field(default_factory=list)  # List of waves containing task IDs
    created_at: float = Field(default_factory=time.time)
