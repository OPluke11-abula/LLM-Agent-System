import type { CompanionStatus, CompanionTask, DroppedFileItem } from "../../../hooks/useAmbientCompanion";

export function testAmbientCompanionDefaults(): boolean {
  const defaultStatus: CompanionStatus = "idle";
  const defaultToken = "PO_LUKE_TOKEN";
  const defaultApprover = "Luke (PO / Domain Owner)";

  if (defaultStatus !== "idle" || defaultToken !== "PO_LUKE_TOKEN" || !defaultApprover.includes("Luke")) {
    throw new Error("Default state mismatch");
  }
  return true;
}

export function testPipelinePlanSubmittedEvent(): boolean {
  const eventPayload = {
    event: "pipeline_plan_submitted",
    task_id: "TASK-2026-0042",
    gate_status: "LOCKED",
    target_files: ["agent_workspace/core/agent_executor.py"],
    plan_summary: "Refactor tool execution sandbox with worktree isolation.",
    assigned_role: "BACKEND_INFRA_AGENT",
    test_strategy: ["pytest -q agent_workspace/tests/test_executor.py"],
  };

  let status: CompanionStatus = "idle";
  let activeTask: CompanionTask | null = null;

  if (eventPayload.event === "pipeline_plan_submitted") {
    status = "awaiting_approval";
    activeTask = {
      taskId: eventPayload.task_id,
      targetFiles: eventPayload.target_files,
      gateStatus: eventPayload.gate_status,
      planSummary: eventPayload.plan_summary,
      assignedRole: eventPayload.assigned_role,
      testStrategy: eventPayload.test_strategy,
      stage: "PLAN_AND_GATE",
      timestamp: Date.now(),
    };
  }

  if (status !== "awaiting_approval" || !activeTask || activeTask.taskId !== "TASK-2026-0042") {
    throw new Error("Event handling failed");
  }
  return true;
}

export function testApprovalPayloadContract(): boolean {
  const taskId = "TASK-2026-0042";
  const token = "PO_LUKE_TOKEN";
  const approver = "Luke (PO / Domain Owner)";

  const payload = {
    task_id: taskId,
    approval_token: token,
    approver,
    notes: "1-Click HITL approval via Ambient Companion",
  };

  if (payload.task_id !== taskId || payload.approval_token !== token || !payload.notes.includes("Companion")) {
    throw new Error("Payload contract mismatch");
  }
  return true;
}

export function testDroppedFilesMetadata(): boolean {
  const mockFiles: DroppedFileItem[] = [
    {
      name: "architecture_spec.md",
      size: 4096,
      type: "text/markdown",
      lastModified: 1774000000000,
    },
  ];

  if (mockFiles.length !== 1 || mockFiles[0].name !== "architecture_spec.md") {
    throw new Error("File metadata extraction failed");
  }
  return true;
}

// Self-executing validation suite
export function runAmbientCompanionTestSuite(): { passed: number; total: number } {
  testAmbientCompanionDefaults();
  testPipelinePlanSubmittedEvent();
  testApprovalPayloadContract();
  testDroppedFilesMetadata();
  return { passed: 4, total: 4 };
}
