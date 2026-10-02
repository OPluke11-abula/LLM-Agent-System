import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { adminAuthHeaders } from "../services/adminRuntimeAuth";
import { STAGES } from "../components/pipeline/types";

export type CompanionStatus = "idle" | "thinking" | "awaiting_approval" | "verified" | "error";
export type CompanionConnectionStatus = "connecting" | "connected" | "disconnected";

export interface CompanionTask {
  taskId: string;
  planSummary?: string;
  targetFiles?: string[];
  assignedRole?: string;
  testStrategy?: string[];
  gateStatus?: string;
  stage?: string;
  tokenMasked?: string;
  timestamp?: number;
}

export interface DroppedFileItem {
  name: string;
  size: number;
  type: string;
  lastModified: number;
}

export interface PeripheralDevice {
  name: string;
  level: number | null;
  charging: boolean;
  online: boolean;
  kind: "mouse" | "keyboard" | "headset" | "controller" | "bluetooth" | "other";
  seconds_left?: number | null;
  text?: string;
}

export interface UseAmbientCompanionReturn {
  status: CompanionStatus;
  connectionStatus: CompanionConnectionStatus;
  activeTask: CompanionTask | null;
  currentStageIndex: number;
  totalStages: number;
  approvalToken: string;
  setApprovalToken: (token: string) => void;
  actionMessage: string | null;
  errorMessage: string | null;
  droppedFiles: DroppedFileItem[];
  peripherals: PeripheralDevice[];
  peripheralAlerts: string[];
  quietMode: boolean;
  approve: (customToken?: string, approverName?: string) => Promise<boolean>;
  deny: (reason?: string) => Promise<void>;
  createTaskFromDrop: (requirementPrompt?: string, targetBranch?: string) => Promise<string | null>;
  handleFileDrop: (files: FileList | File[]) => void;
  clearDroppedFiles: () => void;
  resetStatus: () => void;
}

const DEFAULT_APPROVAL_TOKEN = "PO_LUKE_TOKEN";
const DEFAULT_APPROVER = "Luke (PO / Domain Owner)";
const API_BASE = "http://localhost:8000/v1/pipeline";
const WS_URL = "ws://localhost:8000/v1/pipeline/ws";

async function loadSystemTelemetry(signal?: AbortSignal): Promise<{
  devices: PeripheralDevice[];
  alerts: string[];
  quietMode: boolean;
}> {
  let devices: PeripheralDevice[] = [];
  let alerts: string[] = [];
  let quietMode = false;

  try {
    const res = await fetch("http://localhost:8000/v1/system/peripherals", { signal });
    if (res.ok) {
      const data = await res.json();
      if (data && Array.isArray(data.devices)) {
        devices = data.devices;
        alerts = data.low_battery_alerts || [];
      }
    }
  } catch {
    // Graceful offline fallback
  }

  try {
    const focusRes = await fetch("http://localhost:8000/v1/system/focus-state", { signal });
    if (focusRes.ok) {
      const focusData = await focusRes.json();
      if (focusData && typeof focusData.in_quiet_mode === "boolean") {
        quietMode = focusData.in_quiet_mode;
      }
    }
  } catch {
    // Graceful offline fallback
  }

  return { devices, alerts, quietMode };
}

export function useAmbientCompanion(): UseAmbientCompanionReturn {
  const [status, setStatus] = useState<CompanionStatus>("idle");
  const [connectionStatus, setConnectionStatus] = useState<CompanionConnectionStatus>("connecting");
  const [activeTask, setActiveTask] = useState<CompanionTask | null>(null);
  const [approvalToken, setApprovalToken] = useState<string>(DEFAULT_APPROVAL_TOKEN);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [droppedFiles, setDroppedFiles] = useState<DroppedFileItem[]>([]);
  const [peripherals, setPeripherals] = useState<PeripheralDevice[]>([]);
  const [peripheralAlerts, setPeripheralAlerts] = useState<string[]>([]);
  const [quietMode, setQuietMode] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);

  const syncTelemetry = useCallback((signal?: AbortSignal) => {
    loadSystemTelemetry(signal).then(({ devices, alerts, quietMode: qm }) => {
      setPeripherals(devices);
      setPeripheralAlerts(alerts);
      setQuietMode(qm);
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    syncTelemetry(controller.signal);
    const timer = setInterval(() => {
      syncTelemetry();
    }, 30000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [syncTelemetry]);

  // Sync companion state with Tauri desktop system tray
  useEffect(() => {
    try {
      const taskLabel = activeTask?.taskId ? ` (${activeTask.taskId})` : "";
      const tooltip = `LAS Agent: [${status.toUpperCase()}]${taskLabel}`;
      invoke("update_tray_status", { status, tooltip }).catch(() => {});
    } catch {
      // Browser or test environment fallback
    }
  }, [status, activeTask?.taskId]);

  useEffect(() => {
    setConnectionStatus("connecting");
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("connected");
      setErrorMessage(null);
      ws.send("ping");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (!data || !data.event) return;

        switch (data.event) {
          case "pipeline_task_created": {
            setActiveTask({
              taskId: data.task_id,
              stage: "INTAKE",
              timestamp: Date.now(),
            });
            setStatus("thinking");
            setActionMessage(`Task ${data.task_id} initialized.`);
            break;
          }

          case "pipeline_plan_submitted": {
            setActiveTask((prev) => ({
              taskId: data.task_id || prev?.taskId || "UNKNOWN",
              targetFiles: data.target_files || prev?.targetFiles || [],
              gateStatus: data.gate_status || "LOCKED",
              planSummary: data.plan_summary || prev?.planSummary || "Stop-and-Wait Architecture Gate awaiting confirmation.",
              assignedRole: data.assigned_role || prev?.assignedRole || "ARCHITECT_PLANNER_AGENT",
              testStrategy: data.test_strategy || prev?.testStrategy || ["Default verification ladder"],
              stage: "PLAN_AND_GATE",
              timestamp: Date.now(),
            }));
            setStatus("awaiting_approval");
            setActionMessage(`Stop-and-Wait Gate locked for ${data.task_id}. Human approval required.`);
            break;
          }

          case "pipeline_debate_turn": {
            setStatus("thinking");
            setActionMessage(
              data.speaker ? `Deliberation: ${data.speaker} arguing...` : "Multi-agent committee deliberating..."
            );
            break;
          }

          case "pipeline_gate_approved": {
            setStatus("thinking");
            setActiveTask((prev) =>
              prev ? { ...prev, gateStatus: "APPROVED", tokenMasked: data.token_masked } : null
            );
            setActionMessage(`Gate approved (${data.token_masked ?? "***"}). Starting worktree mutation...`);
            break;
          }

          case "pipeline_stage_changed": {
            const currentStage = String(data.stage ?? "");
            setActionMessage(`Stage transition: ${currentStage}`);
            if (currentStage === "PLAN_AND_GATE") {
              setStatus("awaiting_approval");
            } else if (currentStage === "COMPLETED" || currentStage === "DRAFT_PR_EXPORT") {
              setStatus("verified");
              setActionMessage(`Pipeline verified & ready! Stage: ${currentStage}`);
            } else {
              setStatus("thinking");
            }
            break;
          }

          case "pipeline_completed": {
            setStatus("verified");
            setActionMessage(`Task ${data.task_id ?? ""} successfully verified!`);
            break;
          }

          case "pipeline_error": {
            setStatus("error");
            setErrorMessage(data.error || "Pipeline execution failed.");
            break;
          }

          default:
            break;
        }
      } catch {
        // Non-JSON telemetry or heartbeat ping
      }
    };

    ws.onerror = () => {
      setConnectionStatus("disconnected");
    };

    ws.onclose = () => {
      setConnectionStatus("disconnected");
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, []);

  const approve = useCallback(
    async (customToken?: string, approverName?: string): Promise<boolean> => {
      const targetTaskId = activeTask?.taskId;
      if (!targetTaskId) {
        setErrorMessage("No active task available for approval.");
        return false;
      }

      const tokenToSend = customToken || approvalToken || DEFAULT_APPROVAL_TOKEN;
      const approver = approverName || DEFAULT_APPROVER;

      try {
        setErrorMessage(null);
        setActionMessage(`Authorizing Stop-and-Wait Gate for ${targetTaskId}...`);

        const authHeaders = adminAuthHeaders();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
          ...authHeaders,
        };
        if (!headers["x-api-key"] && !headers["authorization"]) {
          headers["x-api-key"] = tokenToSend;
        }

        const approveRes = await fetch(`${API_BASE}/tasks/${targetTaskId}/approve`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            approval_token: tokenToSend,
            approver,
            notes: "1-Click HITL approval via Ambient Companion",
          }),
        });

        if (!approveRes.ok) {
          const errData = await approveRes.json().catch(() => ({}));
          const reason = errData.detail || `HTTP ${approveRes.status} approval rejected`;
          setErrorMessage(reason);
          setStatus("error");
          return false;
        }

        setStatus("thinking");
        setActionMessage(`Gate approved! Launching worktree execution for ${targetTaskId}...`);

        // Trigger execute
        const execRes = await fetch(`${API_BASE}/tasks/${targetTaskId}/execute`, {
          method: "POST",
          headers,
        });

        if (!execRes.ok) {
          const errData = await execRes.json().catch(() => ({}));
          const reason = errData.detail || `HTTP ${execRes.status} execution failed`;
          setErrorMessage(reason);
          setStatus("error");
          return false;
        }

        setActionMessage(`Execution underway in isolated git worktree.`);
        return true;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setErrorMessage(`Network error during approval: ${msg}`);
        setStatus("error");
        return false;
      }
    },
    [activeTask?.taskId, approvalToken]
  );

  const deny = useCallback(
    async (reason?: string): Promise<void> => {
      const taskId = activeTask?.taskId;
      setStatus("idle");
      setActionMessage(
        taskId
          ? `Task ${taskId} gate denied by user (${reason || "Explicit user rejection"}).`
          : "Gate denied."
      );
      setErrorMessage(null);
    },
    [activeTask?.taskId]
  );

  const handleFileDrop = useCallback((files: FileList | File[]) => {
    const list = Array.from(files).map((f) => ({
      name: f.name,
      size: f.size,
      type: f.type || "application/octet-stream",
      lastModified: f.lastModified,
    }));
    setDroppedFiles((prev) => [...prev, ...list]);
    setActionMessage(`Injected ${list.length} context file(s): ${list.map((f) => f.name).join(", ")}`);
  }, []);

  const currentStageIndex = activeTask?.stage
    ? STAGES.findIndex((s) => s.id === activeTask.stage)
    : -1;

  const createTaskFromDrop = useCallback(
    async (requirementPrompt?: string, targetBranch?: string): Promise<string | null> => {
      if (droppedFiles.length === 0) {
        setErrorMessage("No context files dropped to initiate task.");
        return null;
      }
      const newTaskId = `TASK-COMPANION-${Date.now().toString(36).toUpperCase()}`;
      const reqPrompt =
        requirementPrompt?.trim() ||
        `Context-driven task from dropped files: ${droppedFiles.map((f) => f.name).join(", ")}`;
      const branch = targetBranch || `feat/companion-${Date.now().toString(36)}`;

      try {
        setErrorMessage(null);
        setStatus("thinking");
        setActionMessage(`Spawning pipeline task ${newTaskId} with dropped context...`);

        const authHeaders = adminAuthHeaders();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
          ...authHeaders,
        };

        const payload = {
          task_id: newTaskId,
          repository_path: "d:/GitHub/LLM-Agent-System",
          requirement_prompt: reqPrompt,
          base_branch: "main",
          target_branch: branch,
          inspected_files: droppedFiles.map((f) => f.name),
          target_files: [],
          allowed_roles: ["DOMAIN_LOGIC_AGENT", "BACKEND_INFRA_AGENT", "UI_UX_AGENT"],
        };

        const res = await fetch(`${API_BASE}/tasks`, {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          const reason = errData.detail || `HTTP ${res.status} task creation failed`;
          setErrorMessage(reason);
          setStatus("error");
          return null;
        }

        setActiveTask({
          taskId: newTaskId,
          stage: "INTAKE",
          targetFiles: [],
          timestamp: Date.now(),
        });
        setActionMessage(`Task ${newTaskId} initialized. Pipeline intake running...`);
        return newTaskId;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setErrorMessage(`Network error creating task: ${msg}`);
        setStatus("error");
        return null;
      }
    },
    [droppedFiles]
  );

  const clearDroppedFiles = useCallback(() => {
    setDroppedFiles([]);
  }, []);

  const resetStatus = useCallback(() => {
    setStatus("idle");
    setErrorMessage(null);
    setActionMessage(null);
  }, []);

  return {
    status,
    connectionStatus,
    activeTask,
    currentStageIndex,
    totalStages: STAGES.length,
    approvalToken,
    setApprovalToken,
    actionMessage,
    errorMessage,
    droppedFiles,
    peripherals,
    peripheralAlerts,
    quietMode,
    approve,
    deny,
    createTaskFromDrop,
    handleFileDrop,
    clearDroppedFiles,
    resetStatus,
  };
}
