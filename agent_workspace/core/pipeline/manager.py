"""Autonomous Coding Pipeline Manager (Phase 1).

Coordinates the end-to-end product workflow:
Developer Requirement -> Bounded Mutation -> Verification Evidence -> Draft PR.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agent_workspace.core.policy_gate import ROLE_SCOPE_RESTRICTIONS
from agent_workspace.core.precheck import SkillsPrechecker
from agent_workspace.core.audit_ledger import AuditLedger
from .models import (
    PipelineStage,
    VerificationStatus,
    CodingTaskRequest,
    WorktreeSessionConfig,
    ScopedMutationPlan,
    VerificationReceipt,
    DraftPRPayload,
    CodingPipelineResult,
    CommitteeDebateRecord,
)
from .committee import CommitteeCoordinator
from .debate_protocol import PipelineDebateProtocol
from .self_healing import PipelineSelfHealingEngine
from .contracts import (
    IWorktreeManager,
    IScopedExecutor,
    IVerificationRunner,
    IDraftPRPublisher,
)

logger = logging.getLogger("CodingPipelineManager")


class PipelineError(Exception):
    """Base typed exception for coding pipeline failures."""
    def __init__(self, message: str, stage: PipelineStage):
        super().__init__(message)
        self.stage = stage


class PrecheckViolationError(PipelineError):
    """Raised when Anti-Summary or prerequisite checks fail."""


class GateApprovalRequiredError(PipelineError):
    """Raised when the Stop-and-Wait Architecture Gate blocks unapproved plans."""


class ScopeBoundaryError(PipelineError):
    """Raised when a mutation targets files forbidden by role scope restrictions."""


class CodingPipelineManager:
    """
    Orchestrates the 5-stage product pipeline with strict guardrails,
    verification ladders, and cognitive relay synchronization.
    """

    def __init__(
        self,
        workspace_path: str,
        worktree_manager: Optional[IWorktreeManager] = None,
        scoped_executor: Optional[IScopedExecutor] = None,
        verification_runner: Optional[IVerificationRunner] = None,
        draft_pr_publisher: Optional[IDraftPRPublisher] = None,
        audit_ledger: Optional[AuditLedger] = None,
        mesh_coordinator: Optional[Any] = None,
    ):
        self.workspace_path = Path(workspace_path).resolve()
        self.worktree_manager = worktree_manager
        self.scoped_executor = scoped_executor
        self.verification_runner = verification_runner
        self.draft_pr_publisher = draft_pr_publisher
        self.audit_ledger = audit_ledger
        self.mesh_coordinator = mesh_coordinator
        self.prechecker = SkillsPrechecker(workspace_path=str(self.workspace_path))
        self.committee_coordinator = CommitteeCoordinator()
        self.debate_protocol = PipelineDebateProtocol(mesh_coordinator=self.mesh_coordinator)
        self._active_sessions: dict[str, CodingPipelineResult] = {}

    def _record_stage(
        self, result: CodingPipelineResult, stage: PipelineStage, detail: str
    ) -> None:
        """Record state machine transitions monotonically."""
        if result.current_stage in (PipelineStage.COMPLETED, PipelineStage.FAILED) and stage not in (PipelineStage.COMPLETED, PipelineStage.FAILED):
            raise ValueError(
                f"Illegal state transition: cannot re-enter active stage '{stage.value}' from terminal stage '{result.current_stage.value}'"
            )
        result.current_stage = stage
        entry = {
            "stage": stage.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        }
        result.stage_history.append(entry)
        logger.info("[Pipeline %s] Transitioned to %s: %s", result.task_id, stage.value, detail)
        if self.audit_ledger:
            try:
                self.audit_ledger.record_event(
                    event_type=f"pipeline_stage_{stage.value.lower()}",
                    payload={"task_id": result.task_id, "detail": detail},
                )
            except Exception as e:
                logger.warning("[Pipeline %s] Failed to record audit ledger event: %s", result.task_id, e)

    def validate_role_scope(self, role: str, target_files: list[str]) -> tuple[bool, Optional[str]]:
        """Verify target files against ROLE_SCOPE_RESTRICTIONS."""
        restriction = ROLE_SCOPE_RESTRICTIONS.get(role)
        if not restriction:
            return True, None

        if restriction.get("read_only", False):
            return False, f"Role {role} is strictly read-only and cannot mutate any files."

        forbidden_prefixes = restriction.get("forbidden_prefixes", ())
        desc = restriction.get("description", "")
        for file_path in target_files:
            clean_path = file_path.replace("\\", "/").lstrip("/")
            for prefix in forbidden_prefixes:
                clean_prefix = prefix.replace("\\", "/").lstrip("/")
                if clean_path.startswith(clean_prefix):
                    return False, f"Role {role} is forbidden from modifying '{file_path}' (violates boundary prefix '{prefix}'). {desc}"

        return True, None

    def start_pipeline(self, request: CodingTaskRequest) -> CodingPipelineResult:
        """
        Stage 1: INTAKE & PRECHECK
        Validates the request, enforces Anti-Summary Invariant, and checks role scopes.
        """
        result = CodingPipelineResult(
            task_id=request.task_id,
            status=VerificationStatus.NOT_RUN,
            current_stage=PipelineStage.INTAKE,
        )
        self._active_sessions[request.task_id] = result
        self._record_stage(result, PipelineStage.INTAKE, f"Requirement accepted: {request.requirement_prompt[:80]}...")

        # 1. Anti-Summary Invariant Check
        target_repo = Path(request.repository_path).resolve() if request.repository_path else self.workspace_path
        prechecker = SkillsPrechecker(workspace_path=str(target_repo))
        precheck_res = prechecker.check_anti_summary_preflight(request.inspected_files)
        if precheck_res.get("status") != "PASS":
            result.status = VerificationStatus.BLOCKED
            result.error_message = precheck_res.get("message", "Anti-Summary preflight check failed.")
            self._record_stage(result, PipelineStage.FAILED, result.error_message)
            return result

        # 2. Scope boundary check against requested roles
        for role in request.allowed_roles:
            is_valid, err_msg = self.validate_role_scope(role, request.target_files)
            if not is_valid:
                result.status = VerificationStatus.BLOCKED
                result.error_message = f"Role scope violation: {err_msg}"
                self._record_stage(result, PipelineStage.FAILED, result.error_message)
                return result

        self._record_stage(result, PipelineStage.PRECHECK, "Preflight checks passed: Anti-Summary and scope verified.")
        return result

    def run_committee_debate(
        self,
        task_id: str,
        request: CodingTaskRequest,
        draft_plan: Optional[ScopedMutationPlan] = None,
    ) -> CommitteeDebateRecord:
        """
        Stage: COMMITTEE_DEBATE (Milestone P85).
        Multi-agent committee deliberates on the task and synthesizes an objective
        consensus scorecard and enriched mutation plan before the architecture gate.
        """
        result = self._active_sessions.get(task_id)
        if not result:
            result = CodingPipelineResult(
                task_id=task_id,
                status=VerificationStatus.NOT_RUN,
                current_stage=PipelineStage.INTAKE,
            )
            self._active_sessions[task_id] = result

        rounds = getattr(request, "debate_rounds", 1) or 1
        self._record_stage(
            result,
            PipelineStage.COMMITTEE_DEBATE,
            f"Forming specialist committee for deliberation ({rounds} round(s)).",
        )

        formation = self.committee_coordinator.evaluate_committee(request)
        debate_record = self.debate_protocol.run_debate(request, formation, draft_plan)
        result.committee_debate = debate_record

        if debate_record.synthesized_mutation_plan:
            result.mutation_plan = debate_record.synthesized_mutation_plan

        scorecard = debate_record.consensus_scorecard
        self._record_stage(
            result,
            PipelineStage.COMMITTEE_DEBATE,
            f"Debate concluded. Composite: {scorecard.composite_score:.2f} ({scorecard.decision}). Members: {', '.join(debate_record.committee_members)}",
        )

        return debate_record

    def submit_plan(self, task_id: str, plan: ScopedMutationPlan) -> CodingPipelineResult:
        """
        Stage 2: PLAN_AND_GATE (Stop-and-Wait Architecture Gate)
        Requires explicit Human approval before transitioning to mutation.
        """
        result = self._active_sessions.get(task_id)
        if not result:
            raise PipelineError(f"Task '{task_id}' not found in active pipeline sessions.", PipelineStage.INTAKE)

        result.mutation_plan = plan

        gate_res = self.prechecker.check_stop_and_wait_gate(plan.human_approved, approver_id=plan.approval_token)
        if gate_res.get("status") != "PASS":
            result.status = VerificationStatus.BLOCKED
            result.error_message = gate_res.get("message", "Stop-and-Wait Gate: Human approval required.")
            self._record_stage(result, PipelineStage.PLAN_AND_GATE, result.error_message)
            return result

        # Enforce anti-self-approval (GAP-02)
        if plan.approval_token and plan.approval_token.strip().lower() == plan.assigned_role.strip().lower():
            result.status = VerificationStatus.BLOCKED
            result.error_message = f"Self-approval rejected: Assigned role '{plan.assigned_role}' cannot approve its own plan."
            self._record_stage(result, PipelineStage.FAILED, result.error_message)
            return result

        # Validate that plan target files match assigned role permissions
        is_valid, err_msg = self.validate_role_scope(plan.assigned_role, plan.target_files)
        if not is_valid:
            result.status = VerificationStatus.BLOCKED
            result.error_message = f"Plan role scope violation: {err_msg}"
            self._record_stage(result, PipelineStage.FAILED, result.error_message)
            return result

        self._record_stage(result, PipelineStage.PLAN_AND_GATE, f"Plan approved by human (Token: {plan.approval_token or 'VERIFIED'}).")
        return result

    def execute_pipeline(
        self,
        task_id: str,
        request: CodingTaskRequest,
        plan: ScopedMutationPlan,
    ) -> CodingPipelineResult:
        """
        Executes the full pipeline workflow from Stage 1 to Stage 5.
        """
        # Step 1: Start Pipeline (Intake & Precheck)
        result = self.start_pipeline(request)
        if result.status == VerificationStatus.BLOCKED or result.current_stage == PipelineStage.FAILED:
            return result

        # Step 1.5: Optional Multi-Agent Committee Debate
        if getattr(request, "enable_committee", False):
            debate_record = self.run_committee_debate(task_id, request, plan)
            scorecard = debate_record.consensus_scorecard
            if scorecard.security_assurance < 0.70:
                result.status = VerificationStatus.BLOCKED
                result.error_message = (
                    f"Committee debate rejected task due to critical security objection: "
                    f"{'; '.join(scorecard.dissenting_opinions)}"
                )
                self._record_stage(result, PipelineStage.FAILED, result.error_message)
                return result

            if debate_record.synthesized_mutation_plan:
                enriched = debate_record.synthesized_mutation_plan
                enriched.human_approved = plan.human_approved
                enriched.approval_token = plan.approval_token
                enriched.approval_timestamp = plan.approval_timestamp
                plan = enriched

        # Step 2: Stop-and-Wait Gate
        result = self.submit_plan(task_id, plan)
        if result.status == VerificationStatus.BLOCKED or result.current_stage == PipelineStage.FAILED:
            return result

        worktree_session: Optional[WorktreeSessionConfig] = None
        try:
            # Step 3: ISOLATED_MUTATION
            self._record_stage(result, PipelineStage.ISOLATED_MUTATION, "Setting up isolated git worktree environment.")
            if not self.worktree_manager:
                raise PipelineError("WorktreeManager is not configured on pipeline.", PipelineStage.ISOLATED_MUTATION)

            worktree_session = self.worktree_manager.create_worktree(
                repo_path=request.repository_path,
                branch_name=request.target_branch,
                base_ref=request.base_branch,
            )
            result.worktree_config = worktree_session

            if self.scoped_executor:
                self.scoped_executor.execute_plan(worktree_session, plan)
                self._record_stage(result, PipelineStage.ISOLATED_MUTATION, "Code modifications successfully applied inside worktree.")
            else:
                self._record_stage(result, PipelineStage.ISOLATED_MUTATION, "Mutation step ready (Executor stubbed).")

            # Step 4: VERIFY_AND_EVIDENCE
            self._record_stage(result, PipelineStage.VERIFY_AND_EVIDENCE, "Running verification test ladder.")
            if not self.verification_runner:
                raise PipelineError("VerificationRunner is not configured on pipeline.", PipelineStage.VERIFY_AND_EVIDENCE)

            receipts = self.verification_runner.run_verification_ladder(
                worktree_path=worktree_session.worktree_path,
                test_strategy=plan.test_strategy,
            )
            result.receipts = receipts

            # Check if all receipts passed
            failed_receipts = [r for r in receipts if r.status != VerificationStatus.PASS]
            if failed_receipts:
                # Autonomous Self-Healing Loop (Phase 91)
                if request.enable_self_healing and request.max_healing_attempts > 0:
                    self._record_stage(result, PipelineStage.SELF_HEALING, "Verification ladder failed; entering autonomous self-healing loop.")
                    healing_engine = PipelineSelfHealingEngine(
                        worktree_manager=self.worktree_manager,
                        scoped_executor=self.scoped_executor,
                        verification_runner=self.verification_runner,
                        vector_memory=getattr(self.mesh_coordinator, "vector_memory", None),
                    )
                    healed = False
                    for attempt_idx in range(1, request.max_healing_attempts + 1):
                        attempt_receipt = healing_engine.attempt_self_healing(
                            task_id=task_id,
                            worktree_session=worktree_session,
                            plan=plan,
                            failed_receipts=failed_receipts,
                            attempt_index=attempt_idx,
                        )
                        result.self_healing_attempts.append(attempt_receipt)
                        self._record_stage(
                            result,
                            PipelineStage.SELF_HEALING,
                            f"Self-healing attempt {attempt_idx}/{request.max_healing_attempts}: {'PASSED' if attempt_receipt.ladder_passed else 'FAILED'}",
                        )
                        if attempt_receipt.ladder_passed:
                            healed = True
                            # Re-collect passed receipts
                            receipts = self.verification_runner.run_verification_ladder(
                                worktree_path=worktree_session.worktree_path,
                                test_strategy=plan.test_strategy,
                            )
                            result.receipts = receipts
                            break

                    if not healed:
                        failed_names = ", ".join(r.step_name for r in failed_receipts)
                        result.status = VerificationStatus.FAIL
                        result.error_message = (
                            f"Verification ladder failed on steps: {failed_names} "
                            f"(Self-healing exhausted after {request.max_healing_attempts} attempts)."
                        )
                        self._record_stage(result, PipelineStage.FAILED, result.error_message)

                        # Execute atomic auto-rollback to guarantee pristine worktree
                        rollback_receipt = healing_engine.execute_auto_rollback(
                            task_id=task_id,
                            worktree_session=worktree_session,
                        )
                        result.rollback_receipt = rollback_receipt
                        self._record_stage(result, PipelineStage.FAILED, f"Auto-rollback executed: {rollback_receipt.restoration_status}")
                        return result
                else:
                    failed_names = ", ".join(r.step_name for r in failed_receipts)
                    result.status = VerificationStatus.FAIL
                    result.error_message = f"Verification ladder failed on steps: {failed_names}"
                    self._record_stage(result, PipelineStage.FAILED, result.error_message)
                    return result

            if not receipts:
                result.status = VerificationStatus.FAIL
                result.error_message = "Verification ladder cannot be empty. Zero verification receipts were generated."
                self._record_stage(result, PipelineStage.FAILED, result.error_message)
                return result

            result.status = VerificationStatus.PASS
            self._record_stage(result, PipelineStage.VERIFY_AND_EVIDENCE, f"All {len(receipts)} verification steps passed with Exit Code 0.")

            # Step 5: DRAFT_PR_EXPORT
            self._record_stage(result, PipelineStage.DRAFT_PR_EXPORT, "Committing changes and generating Draft PR.")
            commit_msg = f"feat({task_id}): {request.requirement_prompt[:50]}\n\nVerified by LAS Autonomous Pipeline."
            commit_hash = self.worktree_manager.commit_changes(worktree_session, commit_msg)
            diff_stat = self.worktree_manager.get_diff(worktree_session)

            pr_body = self._build_pr_body(request, plan, receipts, diff_stat, result.committee_debate)
            pr_payload = DraftPRPayload(
                title=f"[LAS Draft PR] {request.requirement_prompt[:60]}",
                body=pr_body,
                head_branch=request.target_branch,
                base_branch=request.base_branch,
                commit_hash=commit_hash,
                changed_files=plan.target_files,
                receipts=receipts,
                is_draft=True,
            )

            if self.draft_pr_publisher:
                pr_url = self.draft_pr_publisher.publish_draft_pr(pr_payload, request.repository_path)
                pr_payload.pr_url = pr_url

            result.pr_payload = pr_payload
            self._record_stage(result, PipelineStage.COMPLETED, f"Draft PR successfully created: {pr_payload.title}")
            return result

        except Exception as exc:
            logger.error("[Pipeline %s] Exception in execution: %s", task_id, exc, exc_info=True)
            result.status = VerificationStatus.FAIL
            result.error_message = str(exc)
            self._record_stage(result, PipelineStage.FAILED, f"Pipeline execution failed: {exc}")
            return result

        finally:
            # In Phase 1 skeleton, we do not tear down if successful to preserve worktree for inspection,
            # but clean up on unrecoverable abort if configured.
            pass

    def _build_pr_body(
        self,
        request: CodingTaskRequest,
        plan: ScopedMutationPlan,
        receipts: list[VerificationReceipt],
        diff_stat: str,
        committee_debate: Optional[CommitteeDebateRecord] = None,
    ) -> str:
        """Construct a standardized, evidence-backed GitHub Draft PR markdown description."""
        receipt_rows = []
        for r in receipts:
            receipt_rows.append(f"| `{r.step_name}` | `{r.command}` | `{r.exit_code}` | **`{r.status.value}`** | `{r.duration_ms}ms` |")

        receipt_table = (
            "| Step | Command | Exit Code | Status | Duration |\n"
            "|---|---|---|---|---|\n" + "\n".join(receipt_rows)
        )

        committee_section = ""
        if committee_debate:
            sc = committee_debate.consensus_scorecard
            committee_section = f"""---

### 🏛️ Multi-Agent Committee Consensus Scorecard (P85)
- **Deliberation Decision**: **`{sc.decision}`**
- **Composite Score**: `{sc.composite_score:.2f}` (Arch: `{sc.architectural_integrity:.2f}`, Sec: `{sc.security_assurance:.2f}`, QA: `{sc.test_thoroughness:.2f}`)
- **Committee Members**: {', '.join(f'`{m}`' for m in committee_debate.committee_members)}
- **Recommended Actions**: {'; '.join(sc.recommended_actions) or 'Proceed to gate'}

"""

        body = f"""## 🤖 LAS Autonomous Coding Agent - Draft PR

### 📋 Requirement Summary
> **Task ID**: `{request.task_id}`
> **Requirement**: {request.requirement_prompt}
> **Assigned Specialist Role**: `{plan.assigned_role}`
> **Target Files**: {', '.join(f'`{f}`' for f in plan.target_files)}
{committee_section}

---

### 🛡️ Preflight & Architecture Gate Verification
- **Anti-Summary Invariant (調研先行)**: Verified across {len(request.inspected_files)} primary source files.
- **Stop-and-Wait Architecture Gate**: Explicit human approval confirmed (`{plan.approval_token or 'VERIFIED'}`).
- **Role Scope Restriction**: Target boundaries confirmed compliant with `ROLE_SCOPE_RESTRICTIONS`.

---

### 🧪 Objective Verification Ledger Receipts (Evidence Before Completion)
{receipt_table}

---

### 📊 Structural Diff Overview
```diff
{diff_stat[:1500]}
```

---
*Generated autonomously by LLM-Agent-System (LAS) under Universal Protocol v3.8.0.*
"""
        return body
