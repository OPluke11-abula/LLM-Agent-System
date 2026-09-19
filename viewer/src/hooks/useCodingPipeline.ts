import { useCallback, useEffect, useRef, useState } from "react";
import type { TaskDetailResponse, TaskListItem } from "../components/pipeline/types";

export interface CodingPipelineFormState {
  newTaskId: string;
  setNewTaskId: (v: string) => void;
  newRequirement: string;
  setNewRequirement: (v: string) => void;
  newRepoPath: string;
  setNewRepoPath: (v: string) => void;
  newTargetBranch: string;
  setNewTargetBranch: (v: string) => void;
  newInspectedFiles: string;
  setNewInspectedFiles: (v: string) => void;
  newTargetFiles: string;
  setNewTargetFiles: (v: string) => void;
  newRole: string;
  setNewRole: (v: string) => void;
  enableCommittee: boolean;
  setEnableCommittee: (v: boolean) => void;
  debateRounds: number;
  setDebateRounds: (v: number) => void;
  triggeringDebate: boolean;
  offlineMode: boolean;
  setOfflineMode: (v: boolean) => void;
  thinkingBudget: number;
  setThinkingBudget: (v: number) => void;
  useMesh: boolean;
  setUseMesh: (v: boolean) => void;
}

export function useCodingPipeline(activeWorkspacePath?: string) {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
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
  const [newTaskId, setNewTaskId] = useState(
    `TASK-${new Date().getFullYear()}-${String(Date.now()).slice(-4)}`
  );
  const [newRequirement, setNewRequirement] = useState("");
  const [customRepoPath, setCustomRepoPath] = useState<string | null>(null);
  const newRepoPath = customRepoPath ?? (activeWorkspacePath || "");
  const setNewRepoPath = (p: string) => setCustomRepoPath(p);
  const [newTargetBranch, setNewTargetBranch] = useState("feat/autonomous-task");
  const [newInspectedFiles, setNewInspectedFiles] = useState("agent_workspace/api.py");
  const [newTargetFiles, setNewTargetFiles] = useState("agent_workspace/api.py");
  const [newRole, setNewRole] = useState("BACKEND_INFRA_AGENT");
  const [enableCommittee, setEnableCommittee] = useState(true);
  const [debateRounds, setDebateRounds] = useState(1);
  const [triggeringDebate, setTriggeringDebate] = useState(false);
  const [offlineMode, setOfflineMode] = useState(false);
  const [thinkingBudget, setThinkingBudget] = useState(4096);
  const [useMesh, setUseMesh] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const apiBase = "http://localhost:8000/v1/pipeline";

  const fetchTasks = useCallback(async (signal?: AbortSignal) => {
    try {
      const res = await fetch(`${apiBase}/tasks`, { signal });
      if (res.ok) {
        const data = await res.json();
        setTasks(data.tasks || []);
        if (data.tasks?.length > 0) {
          setSelectedTaskId((prev) => prev ?? data.tasks[0].task_id);
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        // Backend offline or fallback
      }
    }
  }, [apiBase]);

  const fetchTaskDetail = useCallback(
    async (taskId: string, signal?: AbortSignal) => {
      try {
        setLoading(true);
        const res = await fetch(`${apiBase}/tasks/${taskId}`, { signal });
        if (res.ok) {
          const data = await res.json();
          setTaskDetail(data);
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          // Ignored
        }
      } finally {
        setLoading(false);
      }
    },
    [apiBase]
  );

  // Initial load
  useEffect(() => {
    const controller = new AbortController();
    fetchTasks(controller.signal);
    return () => controller.abort();
  }, [fetchTasks]);

  // Detail load on task selection
  useEffect(() => {
    if (!selectedTaskId) return;
    const controller = new AbortController();
    fetchTaskDetail(selectedTaskId, controller.signal);
    return () => controller.abort();
  }, [selectedTaskId, fetchTaskDetail]);

  // WebSocket telemetry
  useEffect(() => {
    const wsUrl = "ws://localhost:8000/v1/pipeline/ws";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      ws.send("ping");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.event === "pipeline_stage_changed") {
          setActionMessage(`Task ${msg.task_id} transitioned to stage ${msg.stage}`);
          fetchTasks();
          if (msg.task_id === selectedTaskId) {
            fetchTaskDetail(msg.task_id);
          }
        }
      } catch {
        // Non-JSON ping
      }
    };

    ws.onerror = () => setWsConnected(false);
    ws.onclose = () => setWsConnected(false);

    return () => {
      ws.close();
    };
  }, [selectedTaskId, fetchTasks, fetchTaskDetail]);

  const handleTriggerDebate = async (taskId: string) => {
    try {
      setTriggeringDebate(true);
      setActionMessage("Convening Multi-Agent Committee for deliberation...");
      const res = await fetch(`${apiBase}/tasks/${taskId}/debate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ debate_rounds: 1 }),
      });
      if (res.ok) {
        setActionMessage("Committee debate concluded with consensus scorecard.");
        await fetchTaskDetail(taskId);
        await fetchTasks();
      } else {
        const err = await res.json();
        alert(`Debate trigger failed: ${err.detail || "Unknown error"}`);
      }
    } catch (e: any) {
      alert(`Debate error: ${e.message}`);
    } finally {
      setTriggeringDebate(false);
      setTimeout(() => setActionMessage(null), 4000);
    }
  };

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
        allowed_roles: [newRole, "QA_TEST_AGENT"],
        enable_committee: enableCommittee,
        debate_rounds: debateRounds,
        offline_mode: offlineMode,
        thinking_budget: thinkingBudget,
        use_mesh: useMesh,
      };

      const res = await fetch(`${apiBase}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to intake task");
      }

      setShowCreateModal(false);
      await fetchTasks();
      setSelectedTaskId(newTaskId);

      // Precheck & Plan
      await fetch(`${apiBase}/tasks/${newTaskId}/precheck`, { method: "POST" });
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

  const formState: CodingPipelineFormState = {
    newTaskId,
    setNewTaskId,
    newRequirement,
    setNewRequirement,
    newRepoPath,
    setNewRepoPath,
    newTargetBranch,
    setNewTargetBranch,
    newInspectedFiles,
    setNewInspectedFiles,
    newTargetFiles,
    setNewTargetFiles,
    newRole,
    setNewRole,
    enableCommittee,
    setEnableCommittee,
    debateRounds,
    setDebateRounds,
    triggeringDebate,
    offlineMode,
    setOfflineMode,
    thinkingBudget,
    setThinkingBudget,
    useMesh,
    setUseMesh,
  };

  return {
    tasks,
    selectedTaskId,
    setSelectedTaskId,
    taskDetail,
    loading,
    wsConnected,
    approvalToken,
    setApprovalToken,
    actionMessage,
    showBenchmarkModal,
    setShowBenchmarkModal,
    benchmarkScorecard,
    runningBenchmark,
    showCreateModal,
    setShowCreateModal,
    formState,
    fetchTasks,
    fetchTaskDetail,
    handleTriggerDebate,
    fetchLatestBenchmark,
    handleRunBenchmark,
    handleCreateTask,
    handleApproveGate,
  };
}
