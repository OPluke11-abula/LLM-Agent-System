"""TaskEnvironment and TaskGraph Orchestration (Phase 2-B).

Implements the 15-attribute TaskEnvironment aggregate, TaskGraph DAG scheduler,
AgentCapabilityRequirement, and TaskEnvironmentSynthesizer aligned with ADR-006.

Core Invariants:
1. Context is allocated, not accumulated (Minimum Sufficient Engineering Environment).
2. Useful parallelism > maximal parallelism (Strict no-overlapping mutable scope between concurrent agents).
3. Containment over trust (Hard-path boundaries, role scope restrictions, zero-egress sandbox policy).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.policy_gate import ROLE_SCOPE_RESTRICTIONS
from agent_workspace.core.repository import (
    DEFAULT_PROTECTED_PATTERNS,
    RepositoryProfile,
)
from agent_workspace.core.pipeline.models import WorktreeSessionConfig

logger = logging.getLogger(__name__)

# Default minimal governed tools for coding agents under Bounded Autonomy
MINIMAL_GOVERNED_TOOLS: tuple[str, ...] = (
    "filesystem.read",
    "filesystem.write",
    "shell.exec",
    "git.diff",
)


class CyclicDependencyError(Exception):
    """Raised when a circular dependency is detected within a TaskGraph."""

    def __init__(self, message: str, cycle: list[str]):
        super().__init__(message)
        self.cycle = cycle


class ScopeBoundaryError(Exception):
    """Raised when a task's mutable scope violates role restrictions or system invariants."""


class TaskStatus(str, Enum):
    """Lifecycle states of a task in the TaskGraph."""

    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AgentCapabilityRequirement(BaseModel):
    """Specification of capabilities and constraints required for a task."""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., description="Designated grounded agent role (e.g. DOMAIN_LOGIC_AGENT)")
    required_tools: list[str] = Field(
        default_factory=lambda: list(MINIMAL_GOVERNED_TOOLS),
        description="Governed tool whitelist allocated for this task",
    )
    max_turns: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Loop limit safety gate (default 3, hard ceiling 5)",
    )
    context_budget_tokens: int = Field(
        default=8192,
        ge=512,
        le=32768,
        description="Bounded token allocation for prompt and tool execution",
    )
    read_only: bool = Field(
        default=False,
        description="Whether this capability is strictly read-only",
    )
    forbidden_prefixes: list[str] = Field(
        default_factory=list,
        description="Path prefixes forbidden from mutation by this role",
    )


class SandboxPolicy(BaseModel):
    """Sandbox containment and resource limits."""

    model_config = ConfigDict(extra="forbid")

    isolation_level: str = Field(
        default="worktree",
        description="Isolation strategy: 'worktree', 'process', or 'container'",
    )
    max_execution_seconds: float = Field(
        default=60.0,
        gt=0.0,
        le=300.0,
        description="Hard timeout for individual tool calls or command execution",
    )
    max_memory_mb: int = Field(
        default=1024,
        ge=128,
        description="Resource quota limit in megabytes",
    )
    network_access: bool = Field(
        default=False,
        description="Network egress policy (default False for zero egress)",
    )
    allow_subprocesses: bool = Field(
        default=True,
        description="Whether isolated subcommands (git, test runners) are permitted",
    )


class TaskEnvironment(BaseModel):
    """The 15-attribute Minimum Sufficient Engineering Environment (ADR-006)."""

    model_config = ConfigDict(extra="forbid")

    # 1. Intent & Acceptance Criteria
    intent: str = Field(..., description="1. Human developer intent and engineering objective")
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="2. Objective, measurable conditions of satisfaction",
    )

    # 2. Role & Boundary Scopes
    agent_role: str = Field(..., description="3. Assigned grounded specialist role")
    mutable_scope: list[str] = Field(
        default_factory=list,
        description="4. Strict allowlist of repository paths authorized for mutation",
    )
    protected_scope: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PROTECTED_PATTERNS),
        description="5. Strict denylist of protected paths (e.g. .env*, .git/, CI)",
    )

    # 3. Minimum Sufficient Context
    relevant_architecture: list[str] = Field(
        default_factory=list,
        description="6. Architectural views, topologies, or relevant ADRs",
    )
    relevant_contracts: list[str] = Field(
        default_factory=list,
        description="7. Relevant schemas, interfaces, and typed models",
    )
    relevant_source: list[str] = Field(
        default_factory=list,
        description="8. Concrete source files with targeted line ranges",
    )
    relevant_tests: list[str] = Field(
        default_factory=list,
        description="9. Targeted test files and verification commands",
    )
    current_failure_evidence: list[str] = Field(
        default_factory=list,
        description="10. Current test failures, stack traces, or reproduction logs",
    )

    # 4. Tools, Sandbox & Execution
    available_governed_tools: list[str] = Field(
        default_factory=lambda: list(MINIMAL_GOVERNED_TOOLS),
        description="11. Allocated governed tool whitelist",
    )
    sandbox_policy: SandboxPolicy = Field(
        default_factory=SandboxPolicy,
        description="12. Sandbox containment level and execution quotas",
    )
    execution_environment: Optional[WorktreeSessionConfig] = Field(
        default=None,
        description="13. Native Git Worktree physical isolation environment",
    )

    # 5. Governance, Review & Termination
    required_reviews: list[str] = Field(
        default_factory=lambda: ["QA_TEST_AGENT"],
        description="14. Mandatory independent review roles required before completion",
    )
    stop_condition: dict[str, Any] = Field(
        default_factory=lambda: {
            "max_turns": 3,
            "loop_limit": 3,
            "hitl_gate_required": True,
        },
        description="15. Execution termination criteria and HITL gate requirements",
    )

    def is_path_mutable(self, file_path: str) -> tuple[bool, Optional[str]]:
        """Verify if a specific file path is authorized for mutation within this environment."""
        clean_path = file_path.replace("\\", "/").strip().lstrip("/")

        # 1. Protected scope check (always takes precedence)
        for pattern in self.protected_scope:
            clean_pat = pattern.replace("\\", "/").strip().lstrip("/")
            if clean_pat.endswith("*"):
                prefix = clean_pat[:-1]
                if clean_path.startswith(prefix) or Path(clean_path).name.startswith(prefix):
                    return False, f"Path '{file_path}' matches protected pattern '{pattern}'"
            elif clean_pat.endswith("/"):
                if clean_path.startswith(clean_pat) or f"/{clean_pat}" in f"/{clean_path}":
                    return False, f"Path '{file_path}' resides inside protected directory '{pattern}'"
            else:
                if clean_path == clean_pat or clean_path.endswith(f"/{clean_pat}") or Path(clean_path).name == clean_pat:
                    return False, f"Path '{file_path}' matches protected path '{pattern}'"

        # 2. Mutable scope allowlist check
        if self.mutable_scope:
            is_allowed = False
            for allowed in self.mutable_scope:
                clean_allowed = allowed.replace("\\", "/").strip().lstrip("/")
                if clean_allowed.endswith("/"):
                    if clean_path.startswith(clean_allowed):
                        is_allowed = True
                        break
                elif clean_path == clean_allowed:
                    is_allowed = True
                    break
            if not is_allowed:
                return False, f"Path '{file_path}' is outside designated mutable scope: {self.mutable_scope}"

        return True, None

    def validate_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is within the allocated governed tools."""
        return tool_name in self.available_governed_tools


class TaskNode(BaseModel):
    """An individual unit of work within a TaskGraph."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., description="Unique task identifier (e.g. 'task-81-01')")
    title: str = Field(..., description="Short task title")
    intent: str = Field(..., description="Detailed engineering goal")
    assigned_role: str = Field(..., description="Designated specialist agent role")
    mutable_scope: list[str] = Field(
        default_factory=list,
        description="Target files or directories permitted for mutation",
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Observable conditions for marking task complete",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Task IDs that must complete before this task can become READY",
    )
    capability_requirement: Optional[AgentCapabilityRequirement] = Field(
        default=None,
        description="Bound agent capability requirements",
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current task execution state",
    )
    result_summary: Optional[str] = Field(
        default=None,
        description="Summary of task completion or failure evidence",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TaskGraph(BaseModel):
    """DAG scheduler for coordinating multi-agent missions without scope collisions."""

    model_config = ConfigDict(extra="forbid")

    graph_id: str = Field(..., description="Unique task graph identifier")
    description: str = Field(default="", description="Mission description")
    tasks: dict[str, TaskNode] = Field(
        default_factory=dict,
        description="Lookup map of task_id to TaskNode",
    )

    def add_task(self, task: TaskNode) -> None:
        """Add a task node to the graph and validate for acyclicity."""
        if task.task_id in self.tasks:
            raise ValueError(f"Task with ID '{task.task_id}' already exists in TaskGraph '{self.graph_id}'.")
        self.tasks[task.task_id] = task
        self.detect_cycles()

    def get_task(self, task_id: str) -> TaskNode:
        """Retrieve a task by ID or raise KeyError."""
        if task_id not in self.tasks:
            raise KeyError(f"Task '{task_id}' not found in TaskGraph '{self.graph_id}'.")
        return self.tasks[task_id]

    def detect_cycles(self) -> None:
        """Detect cyclic dependencies using depth-first search. Raises CyclicDependencyError if found."""
        visited: dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited
        path: list[str] = []

        def dfs(node_id: str) -> None:
            visited[node_id] = 1
            path.append(node_id)

            task = self.tasks.get(node_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id not in self.tasks:
                        continue  # External or unadded dependency
                    state = visited.get(dep_id, 0)
                    if state == 1:
                        cycle_index = path.index(dep_id)
                        cycle = path[cycle_index:] + [dep_id]
                        raise CyclicDependencyError(
                            f"Cyclic dependency detected: {' -> '.join(cycle)}",
                            cycle=cycle,
                        )
                    if state == 0:
                        dfs(dep_id)

            path.pop()
            visited[node_id] = 2

        for task_id in self.tasks:
            if visited.get(task_id, 0) == 0:
                dfs(task_id)

    def get_ready_tasks(self) -> list[TaskNode]:
        """Return all tasks that are currently PENDING and have all dependencies COMPLETED."""
        ready: list[TaskNode] = []
        for task in self.tasks.values():
            if task.status in (TaskStatus.PENDING, TaskStatus.READY):
                # Check all dependencies
                all_deps_satisfied = True
                for dep_id in task.dependencies:
                    dep_task = self.tasks.get(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        all_deps_satisfied = False
                        break
                if all_deps_satisfied:
                    task.status = TaskStatus.READY
                    ready.append(task)
        return ready

    def mark_completed(self, task_id: str, summary: str = "") -> None:
        """Mark a task as COMPLETED and update ready status of dependents."""
        task = self.get_task(task_id)
        task.status = TaskStatus.COMPLETED
        task.result_summary = summary
        logger.info("[TaskGraph %s] Task %s marked COMPLETED.", self.graph_id, task_id)

    def mark_failed(self, task_id: str, reason: str = "") -> None:
        """Mark a task as FAILED and transitively block its dependents."""
        task = self.get_task(task_id)
        task.status = TaskStatus.FAILED
        task.result_summary = reason
        logger.warning("[TaskGraph %s] Task %s marked FAILED: %s", self.graph_id, task_id, reason)

        # Mark dependents as BLOCKED
        for other_task in self.tasks.values():
            if task_id in other_task.dependencies and other_task.status in (TaskStatus.PENDING, TaskStatus.READY):
                other_task.status = TaskStatus.BLOCKED
                other_task.result_summary = f"Blocked by failed dependency '{task_id}'"

    def validate_no_overlapping_scopes(
        self, task_ids: list[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Enforce Useful Parallelism Constraint:
        Concurrent tasks running in parallel MUST NOT have overlapping mutable scopes.
        """
        scopes_by_task: dict[str, list[str]] = {}
        for tid in task_ids:
            task = self.get_task(tid)
            scopes_by_task[tid] = [s.replace("\\", "/").strip().lstrip("/") for s in task.mutable_scope]

        evaluated = list(scopes_by_task.items())
        for i in range(len(evaluated)):
            tid_a, scope_a = evaluated[i]
            for j in range(i + 1, len(evaluated)):
                tid_b, scope_b = evaluated[j]
                for path_a in scope_a:
                    for path_b in scope_b:
                        # Direct equality or directory prefix overlap
                        if path_a == path_b:
                            return False, (
                                f"Parallel scope collision: Task '{tid_a}' and Task '{tid_b}' "
                                f"both target exact path '{path_a}'"
                            )
                        # Prefix containment check
                        norm_a = path_a if path_a.endswith("/") else path_a + "/"
                        norm_b = path_b if path_b.endswith("/") else path_b + "/"
                        if path_b.startswith(norm_a) or path_a.startswith(norm_b):
                            return False, (
                                f"Parallel scope collision: Task '{tid_a}' ('{path_a}') and "
                                f"Task '{tid_b}' ('{path_b}') have overlapping directory boundaries"
                            )

        return True, None


class TaskEnvironmentSynthesizer:
    """Factory and synthesizer that provisions a sealed TaskEnvironment for execution."""

    def __init__(self, workspace_path: Optional[str] = None):
        self.workspace_path = Path(workspace_path).resolve() if workspace_path else Path.cwd()

    def synthesize(
        self,
        task: TaskNode,
        repo_profile: RepositoryProfile,
        worktree_session: Optional[WorktreeSessionConfig] = None,
        relevant_architecture: Optional[list[str]] = None,
        relevant_contracts: Optional[list[str]] = None,
        relevant_source: Optional[list[str]] = None,
        relevant_tests: Optional[list[str]] = None,
        current_failure_evidence: Optional[list[str]] = None,
        sandbox_policy: Optional[SandboxPolicy] = None,
    ) -> TaskEnvironment:
        """
        Synthesize a Minimum Sufficient Engineering Environment for a task.
        Validates role boundaries, merges protected scopes, and mounts minimal governed tools.
        """
        # 1. Enforce Role Scope Restrictions from policy_gate.py
        role = task.assigned_role
        role_rule = ROLE_SCOPE_RESTRICTIONS.get(role, {})
        is_read_only = role_rule.get("read_only", False)
        forbidden_prefixes = role_rule.get("forbidden_prefixes", ())

        if is_read_only and task.mutable_scope:
            raise ScopeBoundaryError(
                f"Role '{role}' is strictly read-only and cannot have mutable_scope: {task.mutable_scope}"
            )

        for path in task.mutable_scope:
            clean_path = path.replace("\\", "/").strip().lstrip("/")
            for forbidden in forbidden_prefixes:
                clean_forbidden = forbidden.replace("\\", "/").strip().lstrip("/")
                if clean_path.startswith(clean_forbidden):
                    raise ScopeBoundaryError(
                        f"Role '{role}' is forbidden from modifying '{path}' "
                        f"(violates boundary prefix '{forbidden}')"
                    )

        # 2. Merge protected scopes: System defaults + RepoProfile protected paths
        protected_set = set(DEFAULT_PROTECTED_PATTERNS)
        for p in repo_profile.protected_paths:
            protected_set.add(p)

        # 3. Mount governed tools according to role and read_only constraint
        mounted_tools = list(MINIMAL_GOVERNED_TOOLS)
        if is_read_only and "filesystem.write" in mounted_tools:
            mounted_tools.remove("filesystem.write")

        # 4. Build capability requirement if not provided
        cap_req = task.capability_requirement or AgentCapabilityRequirement(
            role=role,
            required_tools=mounted_tools,
            max_turns=3,
            context_budget_tokens=8192,
            read_only=is_read_only,
            forbidden_prefixes=list(forbidden_prefixes),
        )

        # 5. Extract default tests from repo_profile if relevant_tests is empty
        final_tests = list(relevant_tests or [])
        if not final_tests and repo_profile.test_commands:
            for tcmd in repo_profile.test_commands:
                final_tests.append(f"{tcmd.get('name')}: {tcmd.get('command')}")

        env = TaskEnvironment(
            intent=task.intent,
            acceptance_criteria=task.acceptance_criteria,
            agent_role=role,
            mutable_scope=task.mutable_scope,
            protected_scope=sorted(list(protected_set)),
            relevant_architecture=relevant_architecture or [],
            relevant_contracts=relevant_contracts or [],
            relevant_source=relevant_source or [],
            relevant_tests=final_tests,
            current_failure_evidence=current_failure_evidence or [],
            available_governed_tools=cap_req.required_tools,
            sandbox_policy=sandbox_policy or SandboxPolicy(),
            execution_environment=worktree_session,
            required_reviews=["QA_TEST_AGENT"],
            stop_condition={
                "max_turns": cap_req.max_turns,
                "loop_limit": 3,
                "hitl_gate_required": True,
            },
        )

        logger.info(
            "[TaskEnvironmentSynthesizer] Synthesized TaskEnvironment for '%s' (Role: %s, Mutable files: %d)",
            task.task_id,
            role,
            len(env.mutable_scope),
        )
        return env
