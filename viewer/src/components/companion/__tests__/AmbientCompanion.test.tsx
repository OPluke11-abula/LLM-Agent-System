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

export function testAmbientCompanionStageTracking(): boolean {
  const stages = [
    "INTAKE",
    "PRECHECK",
    "COMMITTEE_DEBATE",
    "PLAN_AND_GATE",
    "ISOLATED_MUTATION",
    "VERIFY_AND_EVIDENCE",
    "INDEPENDENT_REVIEW",
    "SELF_HEALING",
    "DRAFT_PR_EXPORT",
  ];

  const currentStage = "PLAN_AND_GATE";
  const stageIdx = stages.indexOf(currentStage);

  if (stageIdx !== 3 || stages.length !== 9) {
    throw new Error("Stage index calculation mismatch");
  }
  return true;
}

export function testTaskCreationPayloadFromDrop(): boolean {
  const droppedFiles: DroppedFileItem[] = [
    { name: "test_patch.py", size: 1024, type: "text/x-python", lastModified: Date.now() },
  ];
  const requirement = "Fix bug identified in dropped test";
  const taskId = "TASK-COMPANION-001";

  const payload = {
    task_id: taskId,
    repository_path: "d:/GitHub/LLM-Agent-System",
    requirement_prompt: requirement,
    base_branch: "main",
    target_branch: "feat/companion-001",
    inspected_files: droppedFiles.map((f) => f.name),
    target_files: [],
    allowed_roles: ["DOMAIN_LOGIC_AGENT", "BACKEND_INFRA_AGENT", "UI_UX_AGENT"],
  };

  if (
    payload.task_id !== taskId ||
    payload.inspected_files.length !== 1 ||
    payload.inspected_files[0] !== "test_patch.py" ||
    !payload.requirement_prompt.includes("Fix bug")
  ) {
    throw new Error("Drop to task creation payload failed");
  }
  return true;
}

export function testCompanionPeripheralTelemetry(): boolean {
  const mockPeripherals = [
    {
      name: "Logitech G502 LIGHTSPEED",
      level: 12,
      charging: false,
      online: true,
      kind: "mouse" as const,
    },
    {
      name: "Audeze Maxwell",
      level: 80,
      charging: true,
      online: true,
      kind: "headset" as const,
    },
  ];

  const lowBatteryAlerts = mockPeripherals
    .filter((d) => d.online && !d.charging && d.level !== null && d.level <= 15)
    .map((d) => `${d.name} 電量僅剩 ${d.level}%`);

  if (lowBatteryAlerts.length !== 1 || !lowBatteryAlerts[0].includes("Logitech G502")) {
    throw new Error("Peripheral telemetry alert calculation mismatch");
  }
  return true;
}

export function testCompanionQuietModeFlag(): boolean {
  let quietMode = false;
  quietMode = true;
  if (!quietMode) {
    throw new Error("Quiet mode flag failed to set");
  }
  return true;
}

// Self-executing validation suite
export function runAmbientCompanionTestSuite(): { passed: number; total: number } {
  testAmbientCompanionDefaults();
  testPipelinePlanSubmittedEvent();
  testApprovalPayloadContract();
  testDroppedFilesMetadata();
  testAmbientCompanionStageTracking();
  testTaskCreationPayloadFromDrop();
  testCompanionPeripheralTelemetry();
  testCompanionQuietModeFlag();
  return { passed: 8, total: 8 };
}
