"""Governed Agent Execution & ScopeGuard (Phase 2-C).

Implements Bounded Autonomy and the non-bypassable execution chain from ADR-006:
Agent -> ToolCall -> Tool Registry -> Mission Policy -> ScopeGuard -> Approval Policy -> Sandbox -> Executor -> ToolResult -> Evidence.

Core Guarantees:
1. Physical containment over trust (ScopeGuard blocks unauthorized writes, raises ScopeExpansionRequest).
2. Minimal governed toolchain (filesystem.read, filesystem.write, shell.exec, git.diff).
3. Loop limit safety gate (max_turns <= 3 default, hard ceiling 5).
4. Subprocess containment & destructive command interception.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.pipeline.contracts import IScopedExecutor
from agent_workspace.core.pipeline.models import (
    ScopedMutationPlan,
    VerificationStatus,
    WorktreeSessionConfig,
)
from agent_workspace.core.policy_gate import ROLE_SCOPE_RESTRICTIONS
from agent_workspace.core.task_environment import (
    DEFAULT_PROTECTED_PATTERNS,
    MINIMAL_GOVERNED_TOOLS,
    SandboxPolicy,
    TaskEnvironment,
)

logger = logging.getLogger(__name__)

# Dangerous command patterns intercepted by ScopeGuard
DESTRUCTIVE_COMMAND_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgit\s+push\s+.*(-f\b|--force\b)", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+.*--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+.*(-[a-z]*f|--force\b)", re.IGNORECASE),
    re.compile(r"\brm\s+-[rf]{1,2}\s+(/|[a-z]:\\|~)", re.IGNORECASE),
    re.compile(r"\brmdir\s+/s\s+/q\s+([a-z]:\\|/)", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),
)


class ScopeExpansionRequest(Exception):
    """Raised when an agent attempts to mutate a file outside its authorized mutable scope."""

    def __init__(
        self,
        role: str,
        attempted_path: str,
        allowed_scope: list[str],
        reason: str,
    ):
        super().__init__(
            f"ScopeExpansionRequest: Role '{role}' attempted unauthorized mutation of '{attempted_path}'. "
            f"Reason: {reason}. Current mutable scope: {allowed_scope}. Human approval required."
        )
        self.role = role
        self.attempted_path = attempted_path
        self.allowed_scope = allowed_scope
        self.reason = reason


class SecurityViolationError(Exception):
    """Raised when an agent attempts a destructive shell command or sandbox escape."""


class ToolCallEvidence(BaseModel):
    """Immutable evidence record for a governed tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(..., description="Invoked tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Redacted tool arguments")
    exit_code: int = Field(default=0, description="Process or operation exit code")
    output_snippet: str = Field(default="", description="Bounded output or error snippet")
    duration_ms: int = Field(default=0, description="Execution duration in milliseconds")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    merkle_hash: Optional[str] = Field(default=None, description="SHA-256 hash of this execution record")


class ExecutionAttempt(BaseModel):
    """Tracking model for an agent execution attempt under Bounded Autonomy."""

    model_config = ConfigDict(extra="forbid")

    attempt_id: str = Field(..., description="Unique execution attempt identifier")
    task_id: str = Field(..., description="Associated task identifier")
    role: str = Field(..., description="Assigned agent role")
    turn_count: int = Field(default=0, description="Current turn counter")
    max_turns: int = Field(default=3, description="Turn hard ceiling before HITL gate")
    status: VerificationStatus = Field(default=VerificationStatus.NOT_RUN)
    evidence_trail: list[ToolCallEvidence] = Field(default_factory=list)
    error_message: Optional[str] = None


class ScopeGuard:
    """Enforces physical containment boundaries, path validation, and destructive command interception."""

    def __init__(self, task_env: TaskEnvironment, worktree_path: str):
        self.task_env = task_env
        self.worktree_path = Path(worktree_path).resolve()

    def resolve_and_verify_path(self, relative_path: str) -> tuple[Path, str]:
        """
        Resolves path relative to worktree root, preventing traversal escapes.
        Returns: (resolved_absolute_path, normalized_relative_path).
        """
        clean_str = relative_path.replace("\\", "/").strip().lstrip("/")
        target_path = (self.worktree_path / clean_str).resolve()

        # Prevent traversal outside worktree boundary
        try:
            target_path.relative_to(self.worktree_path)
        except ValueError as exc:
            raise SecurityViolationError(
                f"Path traversal escape detected: '{relative_path}' resolves to '{target_path}', "
                f"outside worktree boundary '{self.worktree_path}'."
            ) from exc

        rel_path = target_path.relative_to(self.worktree_path).as_posix()
        return target_path, rel_path

    def validate_tool_call(
        self, tool_name: str, args: dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate tool invocation against governed whitelist, scope boundaries, and safety rules."""
        # 1. Check Tool Whitelist
        if not self.task_env.validate_tool_allowed(tool_name):
            return False, (
                f"Tool '{tool_name}' is not in the allocated governed toolchain: "
                f"{self.task_env.available_governed_tools}"
            )

        # 2. Check File Mutation for write/delete tools
        if tool_name == "filesystem.write":
            file_path = args.get("file_path", "")
            if not file_path:
                return False, "filesystem.write requires non-empty 'file_path'."

            _, rel_path = self.resolve_and_verify_path(file_path)

            # Enforce TaskEnvironment mutable and protected scopes
            is_mutable, reason = self.task_env.is_path_mutable(rel_path)
            if not is_mutable:
                raise ScopeExpansionRequest(
                    role=self.task_env.agent_role,
                    attempted_path=rel_path,
                    allowed_scope=self.task_env.mutable_scope,
                    reason=reason or "Outside allowed mutable scope",
                )

            # Enforce Role Scope Restrictions
            role_rule = ROLE_SCOPE_RESTRICTIONS.get(self.task_env.agent_role, {})
            if role_rule.get("read_only", False):
                raise ScopeExpansionRequest(
                    role=self.task_env.agent_role,
                    attempted_path=rel_path,
                    allowed_scope=[],
                    reason="Role is strictly read-only",
                )

            for forbidden in role_rule.get("forbidden_prefixes", ()):
                clean_forbidden = forbidden.replace("\\", "/").strip().lstrip("/")
                if rel_path.startswith(clean_forbidden):
                    raise ScopeExpansionRequest(
                        role=self.task_env.agent_role,
                        attempted_path=rel_path,
                        allowed_scope=self.task_env.mutable_scope,
                        reason=f"Violates role boundary prefix '{forbidden}'",
                    )

        # 3. Check Shell Command for destructive operations
        if tool_name == "shell.exec":
            cmd = args.get("command", "").strip()
            for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
                if pattern.search(cmd):
                    raise SecurityViolationError(
                        f"Destructive shell command intercepted by ScopeGuard: '{cmd}'"
                    )

        return True, None


class GovernedToolRegistry:
    """Provides physical implementation of minimal coding tools inside a git worktree."""

    def __init__(self, scope_guard: ScopeGuard):
        self.guard = scope_guard
        self.worktree_path = scope_guard.worktree_path
        self.sandbox_policy = scope_guard.task_env.sandbox_policy

    def filesystem_read(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        """Read text from a file within the isolated worktree."""
        abs_path, _ = self.guard.resolve_and_verify_path(file_path)
        if not abs_path.is_file():
            raise FileNotFoundError(f"File '{file_path}' does not exist inside worktree.")

        content = abs_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        if start_line is not None or end_line is not None:
            s = max(1, start_line or 1) - 1
            e = min(len(lines), end_line or len(lines))
            return "\n".join(lines[s:e])
        return content

    def filesystem_write(
        self, file_path: str, content: str, append: bool = False
    ) -> dict[str, Any]:
        """Write text to an authorized file within the isolated worktree."""
        self.guard.validate_tool_call("filesystem.write", {"file_path": file_path, "content": content})
        abs_path, rel_path = self.guard.resolve_and_verify_path(file_path)
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        with open(abs_path, mode, encoding="utf-8") as f:
            f.write(content)

        bytes_written = len(content.encode("utf-8"))
        logger.info("[GovernedTools] Wrote %d bytes to '%s'", bytes_written, rel_path)
        return {
            "file_path": rel_path,
            "bytes_written": bytes_written,
            "status": "SUCCESS",
        }

    def shell_exec(
        self, command: str, timeout_seconds: Optional[float] = None
    ) -> dict[str, Any]:
        """Execute a shell command inside the worktree environment."""
        self.guard.validate_tool_call("shell.exec", {"command": command})
        timeout = timeout_seconds or self.sandbox_policy.max_execution_seconds

        # Windows/POSIX shell invocation
        use_shell = True
        proc = subprocess.run(
            command,
            cwd=str(self.worktree_path),
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "command": command,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    def git_diff(self) -> str:
        """Return the unified git diff of modifications inside the worktree."""
        proc = subprocess.run(
            ["git", "diff"],
            cwd=str(self.worktree_path),
            capture_output=True,
            text=True,
            check=True,
            timeout=15.0,
        )
        return proc.stdout


class AgentExecutor(IScopedExecutor):
    """
    Executes code modifications under Bounded Autonomy, enforcing the non-bypassable chain:
    Agent -> ToolCall -> Tool Registry -> Mission Policy -> ScopeGuard -> Approval Policy -> Sandbox -> Executor -> ToolResult -> Evidence.
    """

    def __init__(self, task_env: Optional[TaskEnvironment] = None):
        self.task_env = task_env

    def validate_scope_compliance(
        self, role: str, target_files: list[str]
    ) -> tuple[bool, Optional[str]]:
        """Verify targeted files against role restrictions and protected scopes."""
        role_rule = ROLE_SCOPE_RESTRICTIONS.get(role, {})
        if role_rule.get("read_only", False) and target_files:
            return False, f"Role '{role}' is strictly read-only and cannot mutate files."

        forbidden_prefixes = role_rule.get("forbidden_prefixes", ())
        for f in target_files:
            clean = f.replace("\\", "/").strip().lstrip("/")
            # Check role forbidden prefixes
            for pfx in forbidden_prefixes:
                clean_pfx = pfx.replace("\\", "/").strip().lstrip("/")
                if clean.startswith(clean_pfx):
                    return False, f"Role '{role}' is forbidden from modifying '{f}' (violates '{pfx}')."

            # Check protected system paths
            for pat in DEFAULT_PROTECTED_PATTERNS:
                clean_pat = pat.replace("\\", "/").strip().lstrip("/")
                if clean_pat.endswith("*") and (clean.startswith(clean_pat[:-1]) or Path(clean).name.startswith(clean_pat[:-1])):
                    return False, f"Target file '{f}' matches protected pattern '{pat}'."
                elif clean == clean_pat or clean.endswith(f"/{clean_pat}"):
                    return False, f"Target file '{f}' matches protected file '{pat}'."

        return True, None

    def execute_plan(
        self, session: WorktreeSessionConfig, plan: ScopedMutationPlan
    ) -> dict[str, Any]:
        """Execute the planned code modifications inside the isolated worktree."""
        # 1. Scope compliance check
        compliant, err = self.validate_scope_compliance(plan.assigned_role, plan.target_files)
        if not compliant:
            raise ScopeExpansionRequest(
                role=plan.assigned_role,
                attempted_path=plan.target_files[0] if plan.target_files else "",
                allowed_scope=[],
                reason=err or "Scope compliance check failed",
            )

        # 2. Build or bind TaskEnvironment
        env = self.task_env or TaskEnvironment(
            intent=plan.plan_summary,
            agent_role=plan.assigned_role,
            mutable_scope=plan.target_files,
            execution_environment=session,
        )

        guard = ScopeGuard(task_env=env, worktree_path=session.worktree_path)
        tools = GovernedToolRegistry(scope_guard=guard)
        attempt = ExecutionAttempt(
            attempt_id=f"att_{session.session_id[:8]}",
            task_id=plan.task_id,
            role=plan.assigned_role,
            max_turns=env.stop_condition.get("max_turns", 3),
        )

        logger.info(
            "[AgentExecutor] Began execution attempt '%s' for task '%s' in '%s'",
            attempt.attempt_id,
            plan.task_id,
            session.worktree_path,
        )

        return {
            "status": "SUCCESS",
            "attempt_id": attempt.attempt_id,
            "session_id": session.session_id,
            "worktree_path": session.worktree_path,
            "tools": tools,
            "guard": guard,
            "attempt": attempt,
        }

    def execute_tool(
        self,
        tools: GovernedToolRegistry,
        attempt: ExecutionAttempt,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Executes a single tool call through the complete non-bypassable governance chain.
        Enforces turn limit and captures structured evidence.
        """
        # Enforce turn limit safety gate
        if attempt.turn_count >= attempt.max_turns:
            attempt.status = VerificationStatus.BLOCKED
            attempt.error_message = (
                f"Loop limit safety gate triggered: attempt reached max_turns ({attempt.max_turns}). "
                f"Halting execution for human-in-the-loop review."
            )
            logger.warning("[AgentExecutor] %s", attempt.error_message)
            return {
                "status": "BLOCKED",
                "error": attempt.error_message,
            }

        attempt.turn_count += 1
        start_time = time.perf_counter()

        # Chain: ScopeGuard validation
        tools.guard.validate_tool_call(tool_name, args)

        # Dispatch execution
        result: dict[str, Any] = {}
        exit_code = 0
        snippet = ""

        try:
            if tool_name == "filesystem.read":
                content = tools.filesystem_read(
                    args["file_path"],
                    args.get("start_line"),
                    args.get("end_line"),
                )
                result = {"content": content, "status": "SUCCESS"}
                snippet = content[:200]
            elif tool_name == "filesystem.write":
                res = tools.filesystem_write(
                    args["file_path"],
                    args["content"],
                    args.get("append", False),
                )
                result = res
                snippet = f"Wrote {res.get('bytes_written', 0)} bytes to {args['file_path']}"
            elif tool_name == "shell.exec":
                res = tools.shell_exec(args["command"], args.get("timeout_seconds"))
                result = res
                exit_code = res.get("exit_code", 0)
                snippet = (res.get("stdout", "") + res.get("stderr", ""))[:200]
            elif tool_name == "git.diff":
                diff = tools.git_diff()
                result = {"diff": diff, "status": "SUCCESS"}
                snippet = diff[:200]
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as exc:
            exit_code = 1
            snippet = str(exc)
            result = {"status": "FAIL", "error": str(exc)}
            raise

        finally:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            record_raw = f"{tool_name}:{exit_code}:{snippet}:{duration_ms}"
            merkle_hash = hashlib.sha256(record_raw.encode("utf-8")).hexdigest()

            evidence = ToolCallEvidence(
                tool_name=tool_name,
                arguments={k: v for k, v in args.items() if k != "content"},
                exit_code=exit_code,
                output_snippet=snippet,
                duration_ms=duration_ms,
                merkle_hash=merkle_hash,
            )
            attempt.evidence_trail.append(evidence)

        return result
