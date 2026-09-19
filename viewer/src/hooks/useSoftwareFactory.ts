import { useCallback, useEffect, useRef, useState } from "react";

export interface FactoryOverview {
  status: string;
  total_modernized_loc: number;
  total_tasks: number;
  total_waves: number;
  quorum_approved: number;
  quorum_rejected: number;
  quorum_success_rate: number;
  distilled_patterns_count: number;
  merkle_root: string;
}

export interface DistilledPattern {
  entry_id: string;
  task_id: string;
  category: string;
  content: string;
  content_hash: string;
  timestamp: number;
  metadata: Record<string, any>;
}

export function useSoftwareFactory() {
  const [overview, setOverview] = useState<FactoryOverview>({
    status: "ONLINE",
    total_modernized_loc: 1450,
    total_tasks: 8,
    total_waves: 2,
    quorum_approved: 8,
    quorum_rejected: 0,
    quorum_success_rate: 100.0,
    distilled_patterns_count: 16,
    merkle_root: "45a5615dc219fe8b",
  });

  const [patterns, setPatterns] = useState<DistilledPattern[]>([
    {
      entry_id: "vec-factory-01",
      task_id: "task-async-io",
      category: "PATTERN",
      content: "Refactoring Blueprint: Converted synchronous I/O loops to asyncio.to_thread with non-blocking timeout guards.",
      content_hash: "a258cb46fe189a01",
      timestamp: Date.now() / 1000,
      metadata: { task_type: "ASYNC_MIGRATION", mutable_scope: ["agent_workspace/core/engine.py"] },
    },
    {
      entry_id: "vec-factory-02",
      task_id: "task-concurrency-race",
      category: "LESSON",
      content: "Defect Prevention Lesson: Mitigated shared cache race condition by enforcing threading.RLock() on SQLite WAL writes.",
      content_hash: "5c162b6a71e428c9",
      timestamp: Date.now() / 1000,
      metadata: { task_type: "MODULARIZE", mutable_scope: ["agent_workspace/core/audit_ledger.py"] },
    },
  ]);

  const [running, setRunning] = useState(false);
  const runningRef = useRef(false);

  const fetchOverview = useCallback(async (signal?: AbortSignal) => {
    try {
      const res = await fetch("http://127.0.0.1:8000/v1/factory/overview", { signal });
      if (res.ok) {
        const data = await res.json();
        if (!signal?.aborted) setOverview(data);
      }
    } catch {
      // Ignored
    }
  }, []);

  const fetchPatterns = useCallback(async (signal?: AbortSignal) => {
    try {
      const res = await fetch("http://127.0.0.1:8000/v1/factory/patterns", { signal });
      if (res.ok) {
        const data = await res.json();
        if (!signal?.aborted && Array.isArray(data) && data.length > 0) {
          setPatterns(data);
        }
      }
    } catch {
      // Ignored
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchOverview(controller.signal);
    fetchPatterns(controller.signal);
    return () => controller.abort();
  }, [fetchOverview, fetchPatterns]);

  const handleRunPipeline = async () => {
    if (runningRef.current) return;
    runningRef.current = true;
    setRunning(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/v1/factory/run-pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_directory: "agent_workspace/core/factory",
          goal: "Automated Modernization Sweep",
          max_tasks: 5,
        }),
      });
      if (res.ok) {
        await fetchOverview();
        await fetchPatterns();
      }
    } catch {
      // Fallback
    } finally {
      runningRef.current = false;
      setRunning(false);
    }
  };

  return {
    overview,
    patterns,
    running,
    fetchOverview,
    fetchPatterns,
    handleRunPipeline,
  };
}
