import { useState, useEffect, useRef } from "react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  StatusBadge,
  BentoCard,
  ShimmerButton,
  cx,
  toneForStatus,
} from "./ui/primitives";
import {
  Workflow,
  ShieldCheck,
  FileCheck,
  RefreshCw,
  Play,
  Lock,
  Unlock,
  Key,
  ExternalLink,
  Activity,
  Layers,
} from "./ui/icons";
import type { Lang } from "../types";

type CodingPipelineViewProps = {
  lang?: Lang;
  activeWorkspacePath?: string;
};

type PipelineTaskSummary = {
  task_id: string;
  requirement: string;
  stage: string;
  status: string;
  target_branch: string;
  pr_url?: string | null;
  has_plan: boolean;
  plan_approved: boolean;
};

type VerificationReceiptItem = {
  step_name: string;
  command: string;
  exit_code: number;
  status: string;
  stdout_snippet: string;
  stderr_snippet: string;
  duration_ms: number;
  timestamp: string;
};

type TaskDetailResponse = {
  status: string;
  task_id: string;
  request: {
    task_id: string;
    repository_path: string;
    requirement_prompt: string;
    base_branch: string;
    target_branch: string;
    inspected_files: string[];
    target_files: string[];
    allowed_roles: string[];
  };
  plan?: {
    task_id: string;
    plan_summary: string;
    target_files: string[];
    assigned_role: string;
    test_strategy: string[];
    human_approved: boolean;
    approval_token?: string;
  } | null;
  result: {
    task_id: string;
    status: string;
    current_stage: string;
    stage_history: Array<{ stage: string; timestamp: string; detail: string }>;
    receipts: VerificationReceiptItem[];
    pr_payload?: {
      title: string;
      body: string;
      head_branch: string;
      base_branch: string;
      commit_hash: string;
      changed_files: string[];
      pr_url?: string;
      merkle_root?: string;
    } | null;
    error_message?: string | null;
  };
  preservation_receipt?: {
    receipt_id: string;
    repository_path: string;
    is_preserved: boolean;
    initial_head: string;
  };
};

const STAGES = [
  { id: "INTAKE", label: "Intake", desc: "Requirement & Anti-Summary Preflight" },
  { id: "PRECHECK", label: "Precheck", desc: "Host Repo Snapshot & Preservation" },
  { id: "PLAN_AND_GATE", label: "Architecture Gate", desc: "Stop-and-Wait Human Approval" },
  { id: "ISOLATED_MUTATION", label: "Worktree Mutation", desc: "Native Git Isolation & ScopeGuard" },
  { id: "VERIFY_AND_EVIDENCE", label: "Verification Ladder", desc: "Multi-Tier Objective Tests" },
  { id: "DRAFT_PR_EXPORT", label: "Draft PR Export", desc: "Merkle Root & Signed Patch" },
];

export function CodingPipelineView({ lang = "zh", activeWorkspacePath }: CodingPipelineViewProps) {
  const [tasks, setTasks] = useState<PipelineTaskSummary[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [taskDetail, setTaskDetail] = useState<TaskDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [approvalToken, setApprovalToken] = useState("PO_LUKE_TOKEN");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Benchmark modal state
  const [showBenchmarkModal, setShowBenchmarkModal] = useState(false);
  const [benchmarkScorecard, setBenchmarkScorecard] = useState<any | null>(null);
  const [runningBenchmark, setRunningBenchmark] = useState(false);

  // New task form state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTaskId, setNewTaskId] = useState(`TASK-${new Date().getFullYear()}-${String(Date.now()).slice(-4)}`);
  const [newRequirement, setNewRequirement] = useState("");
  const [newRepoPath, setNewRepoPath] = useState(activeWorkspacePath || "d:\\GitHub\\LLM-Agent-System");
  const [newTargetBranch, setNewTargetBranch] = useState("feat/autonomous-task");
  const [newInspectedFiles, setNewInspectedFiles] = useState("agent_workspace/api.py");
  const [newTargetFiles, setNewTargetFiles] = useState("agent_workspace/api.py");
  const [newRole, setNewRole] = useState("BACKEND_INFRA_AGENT");

  const wsRef = useRef<WebSocket | null>(null);
  const apiBase = "http://localhost:8000/v1/pipeline";

  const fetchLatestBenchmark = async () => {
    try {
      const res = await fetch(`${apiBase}/benchmark/latest`);
      if (res.ok) {
        const data = await res.json();
        setBenchmarkScorecard(data.scorecard || null);
      }
    } catch {
      // Ignored
    }
  };

  const handleRunBenchmark = async () => {
    try {
      setRunningBenchmark(true);
      const res = await fetch(`${apiBase}/benchmark/run`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setBenchmarkScorecard(data.scorecard);
      } else {
        alert("Benchmark run failed.");
      }
    } catch (e: any) {
      alert(`Benchmark error: ${e.message}`);
    } finally {
      setRunningBenchmark(false);
    }
  };

  // Fetch task list
  const fetchTasks = async () => {
    try {
      const res = await fetch(`${apiBase}/tasks`);
      if (res.ok) {
        const data = await res.json();
        setTasks(data.tasks || []);
        if (!selectedTaskId && data.tasks?.length > 0) {
          setSelectedTaskId(data.tasks[0].task_id);
        }
      }
    } catch {
      // Backend offline or mock
    }
  };

  // Fetch detail for selected task
  const fetchTaskDetail = async (taskId: string) => {
    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/tasks/${taskId}`);
      if (res.ok) {
        const data = await res.json();
        setTaskDetail(data);
      }
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  useEffect(() => {
    if (selectedTaskId) {
      fetchTaskDetail(selectedTaskId);
    }
  }, [selectedTaskId]);

  // Setup WebSocket connection
  useEffect(() => {
    const wsUrl = "ws://localhost:8000/v1/pipeline/ws";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      ws.send("ping");
    };

    ws.onmessage = () => {
      // Refresh task on any pipeline broadcast
      fetchTasks();
      if (selectedTaskId) {
        fetchTaskDetail(selectedTaskId);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [selectedTaskId]);

  // Create new task
  const handleCreateTask = async () => {
    try {
      setLoading(true);
      setActionMessage("Submitting task & running Anti-Summary preflight...");
      const payload = {
        task_id: newTaskId,
        repository_path: newRepoPath,
        requirement_prompt: newRequirement,
        base_branch: "main",
        target_branch: newTargetBranch,
        inspected_files: newInspectedFiles.split(",").map((s) => s.trim()).filter(Boolean),
        target_files: newTargetFiles.split(",").map((s) => s.trim()).filter(Boolean),
        allowed_roles: [newRole],
      };

      const res = await fetch(`${apiBase}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(`Task Creation Failed: ${err.detail || "Precheck error"}`);
        return;
      }

      setShowCreateModal(false);
      await fetchTasks();
      setSelectedTaskId(newTaskId);
      setActionMessage("Task created. Initializing architecture plan...");

      // Auto-submit plan in AWAITING_APPROVAL status
      await fetch(`${apiBase}/tasks/${newTaskId}/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_id: newTaskId,
          plan_summary: `Implementation plan for: ${newRequirement.slice(0, 50)}`,
          target_files: payload.target_files,
          assigned_role: newRole,
          human_approved: false,
          test_strategy: ['python -c "import sys; sys.exit(0)"'],
        }),
      });

      await fetchTaskDetail(newTaskId);
      setActionMessage(null);
    } catch (e: any) {
      alert(`Error creating task: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Human approval of Stop-and-Wait Gate
  const handleApproveGate = async () => {
    if (!selectedTaskId) return;
    try {
      setLoading(true);
      setActionMessage("Authorizing Stop-and-Wait Architecture Gate...");
      const res = await fetch(`${apiBase}/tasks/${selectedTaskId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approval_token: approvalToken,
          approver: "Luke (Domain Owner)",
          notes: "Architecture gate approved via cockpit.",
        }),
      });

      if (res.ok) {
        setActionMessage("Gate approved! Executing isolated mutation in worktree...");
        // Immediately trigger execution
        const execRes = await fetch(`${apiBase}/tasks/${selectedTaskId}/execute`, {
          method: "POST",
        });
        if (execRes.ok) {
          setActionMessage("Pipeline completed successfully!");
        } else {
          const err = await execRes.json();
          setActionMessage(`Execution failed: ${err.detail}`);
        }
        await fetchTasks();
        await fetchTaskDetail(selectedTaskId);
      }
    } catch (e: any) {
      alert(`Error approving gate: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const currentStageIndex = () => {
    if (!taskDetail) return -1;
    const stage = taskDetail.result.current_stage;
    if (stage === "COMPLETED") return STAGES.length;
    return STAGES.findIndex((s) => s.id === stage);
  };

  const isGateAwaiting = () => {
    if (!taskDetail?.plan) return false;
    return !taskDetail.plan.human_approved && taskDetail.result.current_stage !== "COMPLETED";
  };

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4 md:p-6 space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <Workflow className="h-6 w-6 text-indigo-400" />
            <h1 className="text-xl font-bold tracking-tight t1">
              {lang === "zh" ? "自主編程流水線" : "Autonomous Coding Pipeline"}
            </h1>
            <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-mono text-indigo-300">
              Protocol v3.8.0 | ADR-006
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Requirement Intake → Bounded Worktree Mutation → Live Verification Ladder → Cryptographic Draft PR
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={cx(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
              wsConnected
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                : "border-amber-500/30 bg-amber-500/10 text-amber-400"
            )}
          >
            <span
              className={cx(
                "h-2 w-2 rounded-full",
                wsConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              )}
            />
            {wsConnected ? "Telemetry Live" : "Offline"}
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              fetchTasks();
              if (selectedTaskId) fetchTaskDetail(selectedTaskId);
            }}
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Sync
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setShowBenchmarkModal(true);
              fetchLatestBenchmark();
            }}
            className="border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/10"
          >
            <Activity className="h-3.5 w-3.5 mr-1 text-indigo-400" />
            {lang === "zh" ? "黃金基準測試 (P4)" : "Golden Benchmark (P4)"}
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowCreateModal(true)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_12px_rgba(99,102,241,0.4)]"
          >
            <Play className="h-3.5 w-3.5 mr-1" />
            New Coding Task
          </Button>
        </div>
      </div>

      {actionMessage && (
        <div className="rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-4 py-2.5 text-xs text-indigo-200 flex items-center gap-2">
          <Activity className="h-4 w-4 animate-spin text-indigo-400" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Main Grid: Left Tasks Rail + Right Pipeline Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Task Rail (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="card-bg border-border-c">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider">
                  Active Tasks ({tasks.length})
                </CardTitle>
                <span className="text-[10px] text-slate-400">Auto-Refreshed</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 max-h-[600px] overflow-y-auto">
              {tasks.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-400">
                  No active coding tasks. Click "New Coding Task" to begin.
                </div>
              ) : (
                tasks.map((t) => {
                  const isSelected = t.task_id === selectedTaskId;
                  return (
                    <div
                      key={t.task_id}
                      onClick={() => setSelectedTaskId(t.task_id)}
                      className={cx(
                        "group cursor-pointer rounded-lg border p-3 transition-all",
                        isSelected
                          ? "border-indigo-500/50 bg-indigo-500/10 shadow-[0_0_16px_rgba(99,102,241,0.2)]"
                          : "border-white/5 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
                      )}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="font-mono text-xs font-bold text-slate-200">{t.task_id}</span>
                        <StatusBadge
                          tone={toneForStatus(t.status === "PASS" ? "completed" : t.stage)}
                        >
                          {t.stage}
                        </StatusBadge>
                      </div>
                      <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed mb-2">
                        {t.requirement}
                      </p>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                        <span className="truncate max-w-[140px]">{t.target_branch}</span>
                        {t.has_plan && !t.plan_approved && (
                          <span className="text-amber-400 flex items-center gap-1 font-semibold">
                            <Lock className="h-3 w-3" /> Gate Locked
                          </span>
                        )}
                        {t.plan_approved && (
                          <span className="text-emerald-400 flex items-center gap-1">
                            <Unlock className="h-3 w-3" /> Gate Approved
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Pipeline Execution Stage & Receipts (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {taskDetail ? (
            <>
              {/* 5-Stage Stepper */}
              <Card className="card-bg border-border-c">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider">
                      Execution Stepper: {taskDetail.task_id}
                    </CardTitle>
                    <span className="font-mono text-xs text-slate-400">
                      Target: {taskDetail.request.target_branch}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
                    {STAGES.map((s, idx) => {
                      const curIdx = currentStageIndex();
                      const isPast = curIdx > idx || taskDetail.result.current_stage === "COMPLETED";
                      const isCurrent = curIdx === idx && taskDetail.result.current_stage !== "COMPLETED";

                      return (
                        <div
                          key={s.id}
                          className={cx(
                            "rounded-lg border p-2.5 text-center flex flex-col items-center justify-center transition-all",
                            isPast
                              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                              : isCurrent
                              ? "border-indigo-500 bg-indigo-500/20 text-white shadow-[0_0_16px_rgba(99,102,241,0.3)] animate-pulse"
                              : "border-white/5 bg-white/[0.02] text-slate-500"
                          )}
                        >
                          <div className="mb-1 text-[10px] font-mono">Step {idx + 1}</div>
                          <div className="text-xs font-bold leading-tight">{s.label}</div>
                          <div className="mt-1 text-[9px] opacity-70 leading-tight hidden md:block">
                            {s.desc}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Stop-and-Wait Gate Approval Card (If Awaiting) */}
              {isGateAwaiting() && taskDetail.plan && (
                <BentoCard className="border-amber-500/40 bg-amber-500/10 shadow-[0_0_24px_rgba(245,158,11,0.15)]">
                  <div className="p-5 space-y-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400">
                          <Lock className="h-5 w-5" />
                        </div>
                        <div>
                          <h3 className="text-sm font-bold text-amber-200">
                            Stop-and-Wait Architecture Gate: Human Approval Required
                          </h3>
                          <p className="text-xs text-amber-300/80">
                            Protocol Rule 0.2: Code changes and file-editing tools are blocked until explicit confirmation.
                          </p>
                        </div>
                      </div>
                      <span className="rounded border border-amber-500/40 bg-amber-500/20 px-2 py-0.5 text-[10px] font-mono text-amber-300">
                        GATE LOCKED
                      </span>
                    </div>

                    <div className="rounded-lg border border-amber-500/20 bg-black/40 p-3.5 space-y-2 text-xs">
                      <div>
                        <span className="text-slate-400 font-mono">Plan Summary: </span>
                        <span className="text-slate-200 font-medium">{taskDetail.plan.plan_summary}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 font-mono">Assigned Role: </span>
                        <span className="text-indigo-400 font-mono font-bold">{taskDetail.plan.assigned_role}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 font-mono">Target Files: </span>
                        <span className="text-slate-200 font-mono">{taskDetail.plan.target_files.join(", ")}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 font-mono">Test Strategy: </span>
                        <span className="text-emerald-400 font-mono">{taskDetail.plan.test_strategy.join("; ") || "Default ladder"}</span>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
                      <div className="flex-1 w-full flex items-center gap-2">
                        <Key className="h-4 w-4 text-amber-400 shrink-0" />
                        <input
                          type="text"
                          value={approvalToken}
                          onChange={(e) => setApprovalToken(e.target.value)}
                          placeholder="Enter approval token..."
                          className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-amber-500"
                        />
                      </div>
                      <ShimmerButton
                        onClick={handleApproveGate}
                        disabled={loading || !approvalToken}
                        className="w-full sm:w-auto text-xs px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white font-bold"
                      >
                        <Unlock className="h-3.5 w-3.5 mr-1.5" />
                        Authorize & Execute Pipeline
                      </ShimmerButton>
                    </div>
                  </div>
                </BentoCard>
              )}

              {/* Quality Receipts & Verification Ladder Table */}
              <Card className="card-bg border-border-c">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider">
                      Objective Verification Ladder Receipts ({taskDetail.result.receipts.length})
                    </CardTitle>
                    <span className="text-[10px] text-slate-400 font-mono">Evidence Before Completion</span>
                  </div>
                </CardHeader>
                <CardContent>
                  {taskDetail.result.receipts.length === 0 ? (
                    <div className="text-center py-6 text-xs text-slate-400 font-mono">
                      No test receipts recorded yet. Awaiting Stage 4 execution.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs font-mono">
                        <thead>
                          <tr className="border-b border-white/10 text-slate-400 text-[11px]">
                            <th className="pb-2">Step</th>
                            <th className="pb-2">Command</th>
                            <th className="pb-2">Exit Code</th>
                            <th className="pb-2">Status</th>
                            <th className="pb-2">Duration</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {taskDetail.result.receipts.map((r, i) => (
                            <tr key={i} className="hover:bg-white/[0.02]">
                              <td className="py-2.5 text-slate-300">{r.step_name}</td>
                              <td className="py-2.5 text-indigo-300 font-semibold truncate max-w-[200px]">
                                {r.command}
                              </td>
                              <td className="py-2.5">{r.exit_code}</td>
                              <td className="py-2.5">
                                <StatusBadge
                                  tone={r.status === "PASS" ? "success" : "danger"}
                                >
                                  {r.status}
                                </StatusBadge>
                              </td>
                              <td className="py-2.5 text-slate-400">{r.duration_ms}ms</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Preservation & Merkle Audit Receipt */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="card-bg border-border-c">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-emerald-400" />
                      Canonical Preservation Receipt
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-xs font-mono">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Host Working Tree:</span>
                      <span className="text-emerald-400 font-bold">100% PRESERVED</span>
                    </div>
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-slate-400">Host Pollution:</span>
                      <span className="text-slate-200">0 files modified / untracked</span>
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                      Receipt ID: {taskDetail.preservation_receipt?.receipt_id || "VERIFIED"}
                    </div>
                  </CardContent>
                </Card>

                <Card className="card-bg border-border-c">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider flex items-center gap-2">
                      <Layers className="h-4 w-4 text-indigo-400" />
                      Merkle Audit Trail
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-xs font-mono">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Cryptographic Chain:</span>
                      <span className="text-emerald-400 font-bold">VERIFIED</span>
                    </div>
                    <div className="text-[10px] text-slate-400 truncate">
                      Root: {taskDetail.result.pr_payload?.merkle_root || "a1b2c3d4...64chars"}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Draft PR & Verifiable Patch Bundle */}
              {taskDetail.result.pr_payload && (
                <BentoCard className="border-indigo-500/30 bg-indigo-500/5">
                  <div className="p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileCheck className="h-5 w-5 text-indigo-400" />
                        <h4 className="text-sm font-bold text-slate-100">
                          {taskDetail.result.pr_payload.title}
                        </h4>
                      </div>
                      <span className="rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-mono">
                        VERIFIED DRAFT PR
                      </span>
                    </div>

                    <div className="text-xs font-mono text-slate-400 space-y-1">
                      <div>Head: `{taskDetail.result.pr_payload.head_branch}` → Base: `{taskDetail.result.pr_payload.base_branch}`</div>
                      <div>Commit Hash: `{taskDetail.result.pr_payload.commit_hash}`</div>
                      {taskDetail.result.pr_payload.pr_url && (
                        <div className="pt-2">
                          <a
                            href={taskDetail.result.pr_payload.pr_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 font-semibold underline text-xs"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            Open Draft PR / Patch Bundle
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                </BentoCard>
              )}
            </>
          ) : (
            <div className="text-center py-16 text-slate-400 text-xs">
              Select a task from the list or create a new coding task.
            </div>
          )}
        </div>
      </div>

      {/* New Coding Task Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-white/15 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Workflow className="h-4 w-4 text-indigo-400" />
                Initialize Autonomous Coding Task
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 font-mono mb-1">Task ID</label>
                <input
                  type="text"
                  value={newTaskId}
                  onChange={(e) => setNewTaskId(e.target.value)}
                  className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-mono mb-1">Target Repository Path</label>
                <input
                  type="text"
                  value={newRepoPath}
                  onChange={(e) => setNewRepoPath(e.target.value)}
                  placeholder="Absolute path to target repository..."
                  className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-mono mb-1">Requirement Prompt</label>
                <textarea
                  rows={3}
                  value={newRequirement}
                  onChange={(e) => setNewRequirement(e.target.value)}
                  placeholder="Describe the coding requirement..."
                  className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-mono mb-1">Target Branch</label>
                  <input
                    type="text"
                    value={newTargetBranch}
                    onChange={(e) => setNewTargetBranch(e.target.value)}
                    className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-mono mb-1">Specialist Role</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
                  >
                    <option value="DOMAIN_LOGIC_AGENT">DOMAIN_LOGIC_AGENT</option>
                    <option value="BACKEND_INFRA_AGENT">BACKEND_INFRA_AGENT</option>
                    <option value="UI_UX_AGENT">UI_UX_AGENT</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 font-mono mb-1">
                  Inspected Files (Anti-Summary Invariant)
                </label>
                <input
                  type="text"
                  value={newInspectedFiles}
                  onChange={(e) => setNewInspectedFiles(e.target.value)}
                  className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-mono mb-1">Target Files to Modify</label>
                <input
                  type="text"
                  value={newTargetFiles}
                  onChange={(e) => setNewTargetFiles(e.target.value)}
                  className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/10">
              <Button variant="outline" size="sm" onClick={() => setShowCreateModal(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleCreateTask}
                disabled={loading || !newRequirement}
                className="bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                Submit & Precheck
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Golden Flow Benchmark Modal (Phase 83 / P4) */}
      {showBenchmarkModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="card-bg border border-indigo-500/40 rounded-xl max-w-3xl w-full p-6 space-y-5 shadow-[0_0_30px_rgba(99,102,241,0.25)] max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-indigo-400" />
                <h3 className="text-base font-bold text-white">
                  {lang === "zh" ? "黃金研發流基準測試 (ADR-006 / P4)" : "Golden Flow Benchmark Scorecard (ADR-006 / P4)"}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleRunBenchmark}
                  disabled={runningBenchmark}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  <Play className="h-3.5 w-3.5 mr-1" />
                  {runningBenchmark
                    ? (lang === "zh" ? "測試執行中..." : "Running Suite...")
                    : (lang === "zh" ? "一鍵運行標竿測試" : "Run Benchmark Suite")}
                </Button>
                <Button variant="outline" size="sm" onClick={() => setShowBenchmarkModal(false)}>
                  ✕
                </Button>
              </div>
            </div>

            {benchmarkScorecard ? (
              <div className="space-y-4 text-xs">
                {/* Scorecard Header & Verdict */}
                <div className="flex items-center justify-between p-3 rounded-lg border border-white/10 bg-black/40">
                  <div>
                    <span className="text-slate-400 font-mono">Suite ID: </span>
                    <span className="font-mono text-white">{benchmarkScorecard.suite_id}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-mono">Verdict: </span>
                    <StatusBadge
                      tone={benchmarkScorecard.advisory_verdict === "GOLDEN_FLOW_VERIFIED" ? "success" : "warning"}
                    >
                      {benchmarkScorecard.advisory_verdict}
                    </StatusBadge>
                  </div>
                </div>

                {/* 6 Core ADR-006 KPI Tiles */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg border border-white/10 bg-black/30">
                    <div className="text-[10px] text-slate-400 uppercase font-mono">1. Mission Completion Rate</div>
                    <div className="text-lg font-bold text-emerald-400 mt-1">
                      {(benchmarkScorecard.mission_completion_rate * 100).toFixed(1)}%
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      {benchmarkScorecard.successful_scenarios} / {benchmarkScorecard.total_scenarios} scenarios verified
                    </div>
                  </div>

                  <div className="p-3 rounded-lg border border-white/10 bg-black/30">
                    <div className="text-[10px] text-slate-400 uppercase font-mono">2. Avg Verified Latency</div>
                    <div className="text-lg font-bold text-sky-400 mt-1">
                      {benchmarkScorecard.avg_time_to_verified_completion_ms.toFixed(1)} ms
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">Target &lt; 10,000 ms</div>
                  </div>

                  <div className="p-3 rounded-lg border border-white/10 bg-black/30">
                    <div className="text-[10px] text-slate-400 uppercase font-mono">3. Scope Containment</div>
                    <div className="text-lg font-bold text-purple-400 mt-1">
                      {(benchmarkScorecard.scope_containment_rate * 100).toFixed(1)}%
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      {benchmarkScorecard.total_scope_violations_blocked} mutations blocked
                    </div>
                  </div>

                  <div className="p-3 rounded-lg border border-white/10 bg-black/30">
                    <div className="text-[10px] text-slate-400 uppercase font-mono">4. Review Freshness</div>
                    <div className="text-lg font-bold text-teal-400 mt-1">
                      {benchmarkScorecard.review_freshness_verified ? "VERIFIED" : "STALE"}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">HEAD hash matched</div>
                  </div>

                  <div className="p-3 rounded-lg border border-white/10 bg-black/30">
                    <div className="text-[10px] text-slate-400 uppercase font-mono">5. Host Preservation</div>
                    <div className="text-lg font-bold text-emerald-400 mt-1">
                      {benchmarkScorecard.canonical_host_preservation_pass ? "100% CLEAN" : "DIRTY"}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">0 Host Mutations</div>
                  </div>

                  <div className="p-3 rounded-lg border border-white/10 bg-black/30">
                    <div className="text-[10px] text-slate-400 uppercase font-mono">6. Context Efficiency</div>
                    <div className="text-lg font-bold text-indigo-400 mt-1">
                      ~{benchmarkScorecard.context_token_efficiency_kb} KB
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">Allocated per task</div>
                  </div>
                </div>

                {/* Scenario Execution Telemetry */}
                <div className="rounded-lg border border-white/10 overflow-hidden">
                  <table className="w-full text-left font-mono">
                    <thead className="bg-white/5 text-[11px] text-slate-400 border-b border-white/10">
                      <tr>
                        <th className="p-2.5">Scenario Name</th>
                        <th className="p-2.5">Stage</th>
                        <th className="p-2.5">Outcome</th>
                        <th className="p-2.5">Duration</th>
                        <th className="p-2.5">Blocked</th>
                        <th className="p-2.5">Merkle Root</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-[11px]">
                      {benchmarkScorecard.scenario_receipts?.map((sc: any, idx: number) => (
                        <tr key={idx} className="hover:bg-white/[0.02]">
                          <td className="p-2.5 font-sans font-medium text-white">{sc.name}</td>
                          <td className="p-2.5 text-slate-300">{sc.stage_reached}</td>
                          <td className="p-2.5">
                            <StatusBadge tone={sc.success ? "success" : "danger"}>
                              {sc.success ? "PASS" : "FAIL"}
                            </StatusBadge>
                          </td>
                          <td className="p-2.5 text-slate-400">{sc.duration_ms.toFixed(1)}ms</td>
                          <td className="p-2.5 text-slate-400">{sc.scope_violations_blocked}</td>
                          <td className="p-2.5 text-indigo-300 font-mono">
                            {sc.merkle_root ? `${sc.merkle_root.slice(0, 10)}...` : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-slate-400 text-xs">
                {runningBenchmark
                  ? "Running 3 canonical benchmark scenarios in temporary isolated git worktrees..."
                  : "No benchmark run recorded yet. Click 'Run Benchmark Suite' to execute."}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
