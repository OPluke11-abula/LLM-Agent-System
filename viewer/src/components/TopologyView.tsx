import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  BackgroundVariant,
  MiniMap,
  ReactFlow,
  type ReactFlowInstance,
  useEdgesState,
  useNodesState,
} from "reactflow";
import { ActivityLog } from "./ActivityLog";
import { TOPOLOGY_EDGE_TYPES } from "./edges";
import { TOPOLOGY_NODE_TYPES } from "./nodes";
import { Button, MetricTile, ProgressBar, StatusBadge, Surface, Tooltip } from "./ui/primitives";
import { buildTopologyFlow, formatDuration, NODE_COLORS, summarizeTopology } from "../utils/topologyUtils";
import { logUiDiagnostic } from "../utils/logger";
import type { ActivityLogEntry, ConductorTrace, Lang, TopologyEvent, TopologyNodeData, TopologyState } from "../types";

type TopologyViewProps = {
  sessions: TopologyState[];
  lastUpdatedSessionId: string | null;
  activityEntries: ActivityLogEntry[];
  onClearActivityLog: () => void;
  lang: Lang;
};

type SessionCanvasProps = {
  state: TopologyState;
  onOpenNode: (event: TopologyEvent) => void;
};

const COPY = {
  zh: {
    title: "Agent 拓撲全景",
    subtitle: "即時呈現 Session、工具、Handoff、RBAC 與錯誤路徑",
    sessions: "Sessions",
    active: "顯示中",
    nodes: "節點",
    errors: "錯誤",
    tokens: "Tokens",
    completion: "完成率",
    updated: "更新",
    details: "節點文件",
    noNode: "選取節點後查看完整執行文件",
    input: "輸入",
    output: "輸出",
    notes: "人類備注",
    deps: "依賴",
    cost: "成本",
  },
  en: {
    title: "Agent Topology Panorama",
    subtitle: "Live view of sessions, tools, handoffs, RBAC, and error paths",
    sessions: "Sessions",
    active: "Visible",
    nodes: "Nodes",
    errors: "Errors",
    tokens: "Tokens",
    completion: "Completion",
    updated: "Updated",
    details: "Node Document",
    noNode: "Select a node to inspect its execution document",
    input: "Input",
    output: "Output",
    notes: "Human Notes",
    deps: "Dependencies",
    cost: "cost",
  },
  ja: {
    title: "Agent トポロジーパノラマ",
    subtitle: "セッション、ツール、ハンドオフ、RBAC、エラーパスのリアルタイム監視",
    sessions: "セッション",
    active: "表示中",
    nodes: "ノード",
    errors: "エラー",
    tokens: "トークン",
    completion: "完了率",
    updated: "更新",
    details: "ノード文書",
    noNode: "ノードを選択して詳細ドキュメントを表示",
    input: "入力",
    output: "出力",
    notes: "人間の注記",
    deps: "依存関係",
    cost: "コスト",
  },
  fr: {
    title: "Agent Topologie Panorama",
    subtitle: "Vue en direct des sessions, outils, handoffs, RBAC et chemins d'erreurs",
    sessions: "Sessions",
    active: "Visible",
    nodes: "Nœuds",
    errors: "Erreurs",
    tokens: "Tokens",
    completion: "Complétion",
    updated: "Mis à jour",
    details: "Document du Nœud",
    noNode: "Sélectionnez un nœud pour inspecter son document d'exécution",
    input: "Entrée",
    output: "Sortie",
    notes: "Notes Humaines",
    deps: "Dépendances",
    cost: "Coût",
  },
} as const;

function formatTime(timestamp: string, lang: Lang) {
  return new Intl.DateTimeFormat(lang === "zh" ? "zh-TW" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(timestamp));
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre
      className="max-h-44 overflow-auto rounded-lg border p-3 text-[11px] leading-relaxed"
      style={{ background: "var(--bg-card)", borderColor: "var(--border-c)", color: "var(--t2)" }}
    >
      {JSON.stringify(value ?? null, null, 2)}
    </pre>
  );
}

function asMetricRecord(value: unknown): Record<string, any> {
  return value && typeof value === "object" ? value as Record<string, any> : {};
}

function isConductorTrace(value: unknown): value is ConductorTrace {
  if (!value || typeof value !== "object") return false;
  const trace = value as Partial<ConductorTrace>;
  return typeof trace.task_id === "string" && Array.isArray(trace.subtasks) && Array.isArray(trace.selected_models);
}

function latestConductorTrace(session?: TopologyState) {
  if (!session) return null;
  for (const node of [...session.nodes].reverse()) {
    if (isConductorTrace(node.payload?.conductor_trace)) {
      return node.payload.conductor_trace;
    }
  }
  return null;
}

function ConductorTracePanel({
  trace,
  telemetry,
  ledger,
  lang,
}: {
  trace: ConductorTrace | null;
  telemetry: unknown;
  ledger: { total_cost: number; cost_threshold: number } | null;
  lang: Lang;
}) {
  const metric = asMetricRecord(telemetry);
  const selectedModel = trace?.selected_models?.[0];
  const verification = trace?.verification_strategy;
  const latencyValue = metric.latency_ms ?? metric.latencyMs ?? metric.ws_latency_ms ?? metric.wsLatencyMs;
  const latency = Number.isFinite(Number(latencyValue)) ? `${Number(latencyValue).toFixed(0)}ms` : "--";
  const cost = ledger ? `$${ledger.total_cost.toFixed(5)}` : "--";
  const costLimit = ledger?.cost_threshold ?? trace?.budget?.cost_limit ?? null;
  const memoryHits = trace?.routing_memory_hints ?? [];
  const verifierTone = verification?.approval_required ? "warning" : verification?.required ? "accent" : "success";

  return (
    <Surface className="group/conductor relative mx-3 mb-3 flex flex-col gap-2 p-3">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
          {lang === "zh" ? "Conductor Trace" : "Conductor Trace"}
        </p>
        <StatusBadge tone={trace ? "accent" : "warning"} className="text-[8px]">
          {trace ? trace.execution_mode : "WAITING"}
        </StatusBadge>
      </div>

      {trace ? (
        <>
          <div className="grid grid-cols-3 gap-1.5 text-center font-mono">
            <MetricTile label={lang === "zh" ? "Memory" : "Memory"} value={memoryHits.length} tone={memoryHits.length > 0 ? "success" : "neutral"} className="p-1" />
            <MetricTile label={lang === "zh" ? "Cost" : "Cost"} value={cost} tone="success" className="p-1" />
            <MetricTile label={lang === "zh" ? "Latency" : "Latency"} value={latency} tone="accent" className="p-1" />
          </div>

          <div className="space-y-1.5 border-t pt-2 font-mono text-[8px]" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold uppercase tracking-[0.14em] t3">{lang === "zh" ? "Model" : "Model"}</span>
              <span className="truncate text-right t1" title={selectedModel ? `${selectedModel.provider}/${selectedModel.model}` : ""}>
                {selectedModel ? `${selectedModel.provider}/${selectedModel.model}` : "--"}
              </span>
            </div>
            <p className="line-clamp-2 leading-relaxed t2">
              {selectedModel?.selection_reason || trace.decision_rationale}
            </p>
          </div>

          <div className="space-y-1.5 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between">
              <span className="text-[8px] font-bold uppercase tracking-[0.14em] t3">
                {lang === "zh" ? "Verification" : "Verification"}
              </span>
              <StatusBadge tone={verifierTone} className="text-[8px]">
                {verification?.kind ?? "none"}
              </StatusBadge>
            </div>
            <p className="text-[8px] leading-relaxed t3">
              {verification?.success_criteria?.[0] || (lang === "zh" ? "No verifier criteria published yet." : "No verifier criteria published yet.")}
            </p>
          </div>

          <div className="space-y-1.5 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
            <span className="text-[8px] font-bold uppercase tracking-[0.14em] t3">
              {lang === "zh" ? "Task Breakdown" : "Task Breakdown"}
            </span>
            <div className="max-h-20 space-y-1 overflow-y-auto pr-1">
              {trace.subtasks.slice(0, 4).map((subtask) => (
                <div key={subtask.id} className="flex items-start justify-between gap-2 font-mono text-[8px]">
                  <span className="min-w-0 flex-1 truncate t2" title={subtask.description || subtask.title}>
                    {subtask.title}
                  </span>
                  <span className="shrink-0 t3">{subtask.role_id || "worker"}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-1.5 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between font-mono text-[8px]">
              <span className="font-bold uppercase tracking-[0.14em] t3">{lang === "zh" ? "Budget" : "Budget"}</span>
              <span className="t2">
                {trace.budget?.max_iterations ?? "--"} loops / {trace.budget?.max_tool_calls ?? "--"} tools
              </span>
            </div>
            {costLimit !== null && (
              <ProgressBar
                value={ledger ? (ledger.total_cost / Math.max(costLimit, 0.00001)) * 100 : 0}
                tone={ledger && ledger.total_cost > costLimit * 0.8 ? "warning" : "success"}
              />
            )}
          </div>

          {memoryHits.length > 0 && (
            <div className="space-y-1.5 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
              <span className="text-[8px] font-bold uppercase tracking-[0.14em] t3">
                {lang === "zh" ? "Memory Hits" : "Memory Hits"}
              </span>
              <div className="max-h-20 space-y-1 overflow-y-auto pr-1 font-mono text-[8px]">
                {memoryHits.slice(0, 3).map((hint) => (
                  <div key={hint.record_id || `${hint.task_type}-${hint.latency_ms}`} className="flex items-center justify-between gap-2">
                    <span className="truncate t2">{hint.task_type} / {hint.execution_mode}</span>
                    <span style={{ color: hint.success ? "var(--success)" : "var(--danger)" }}>
                      {hint.success ? "ok" : hint.error_type || "fail"} {hint.latency_ms}ms
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="rounded border p-3 text-[9px] leading-relaxed t3" style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}>
          {lang === "zh"
            ? "Waiting for a routed session to publish conductor task breakdown, model rationale, memory hints, verification, cost, and latency."
            : "Waiting for a routed session to publish conductor task breakdown, model rationale, memory hints, verification, cost, and latency."}
        </div>
      )}

      <Tooltip>
        {lang === "zh"
          ? "Conductor trace: shows the telemetry-only route plan emitted before provider execution."
          : "Conductor trace: shows the telemetry-only route plan emitted before provider execution."}
      </Tooltip>
    </Surface>
  );
}

function SessionCanvas({ state, onOpenNode }: SessionCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<TopologyNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [instance, setInstance] = useState<ReactFlowInstance | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const flow = useMemo(() => buildTopologyFlow(state, onOpenNode), [onOpenNode, state]);

  useEffect(() => {
    setNodes(flow.nodes);
    setEdges(flow.edges);
  }, [flow, setEdges, setNodes]);

  useEffect(() => {
    if (!instance || nodes.length === 0) return;
    const frame = window.requestAnimationFrame(() => {
      instance.fitView({ padding: 0.16, duration: 180, minZoom: 0.05, maxZoom: 1.1 });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [instance, nodes.length, state.updated_at]);

  return (
    <section
      ref={containerRef}
      className="flow-canvas relative min-h-[360px] overflow-hidden rounded-lg border"
      style={{ borderColor: "var(--border-c)" }}
    >
      <div className="control-surface absolute top-3 left-3 z-10 px-3 py-2">
        <p className="text-xs font-semibold t1">{state.session_id}</p>
        <p className="mt-0.5 text-[10px] font-mono t3">{state.stats.total_nodes} nodes / {state.stats.errors} errors</p>
      </div>
      <ReactFlow
        className="h-full min-h-[360px]"
        nodes={nodes}
        edges={edges}
        onInit={setInstance}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={TOPOLOGY_NODE_TYPES}
        edgeTypes={TOPOLOGY_EDGE_TYPES}
        fitView
        minZoom={0.05}
        maxZoom={1.4}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="var(--grid)" />
        <MiniMap
          pannable
          zoomable
          nodeColor={(node) => {
            const event = (node.data as TopologyNodeData | undefined)?.event;
            return event ? NODE_COLORS[event.node_type] : "#64748b";
          }}
          maskColor="rgba(5,7,11,0.54)"
          style={{ background: "var(--bg-panel)", border: "1px solid var(--border-c)", borderRadius: 8 }}
        />
      </ReactFlow>
    </section>
  );
}

export function TopologyView({ sessions, lastUpdatedSessionId, activityEntries, onClearActivityLog, lang }: TopologyViewProps) {
  const copy = COPY[lang];
  const [visibleSessionIds, setVisibleSessionIds] = useState<string[]>([]);
  const [selectedNode, setSelectedNode] = useState<TopologyEvent | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);
  const [turnsInfo, setTurnsInfo] = useState<{ turns: number; threshold: number; should_glow: boolean } | null>(null);
  const [exporting, setExporting] = useState(false);
  const [defragMetrics, setDefragMetrics] = useState<{ fragmentation_rate: number; reconciliation_efficiency: number } | null>(null);
  const [defragHistory, setDefragHistory] = useState<number[]>([0.48, 0.42, 0.35, 0.28, 0.22]);
  const [defragmenting, setDefragmenting] = useState(false);
  const [ledgerData, setLedgerData] = useState<{ total_cost: number; cost_threshold: number; active_model: string; transactions: any[] } | null>(null);
  const [sandboxStatus, setSandboxStatus] = useState<{ total_executions: number; blocked_executions: number; allowed_executions: number; last_execution_status: string } | null>(null);
  const [telemetryData, setTelemetryData] = useState<{ metrics: any[] } | null>(null);
  const [collabConnected, setCollabConnected] = useState(false);
  const [activityStream, setActivityStream] = useState<any[]>([]);
  const [routerStatus, setRouterStatus] = useState<{ routes: any[]; pruned_history: any[] } | null>(null);
  const [pruning, setPruning] = useState(false);
  const subscribedChannels = ["logs", "telemetry", "ledger", "topology", "stdout", "state_sync"];

  const activeSessionId = visibleSessionIds[0] || (sessions[0]?.session_id);

  const generateSparklinePath = (data: number[], width: number, height: number) => {
    if (data.length < 2) return "";
    const max = Math.max(...data, 0.5);
    const min = Math.min(...data, 0);
    const range = max - min || 1;
    return data
      .map((val, index) => {
        const x = (index / (data.length - 1)) * width;
        const y = height - ((val - min) / range) * height;
        return `${index === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");
  };

  useEffect(() => {
    if (!activeSessionId) return;
    let cancelled = false;

    const fetchTurns = async () => {
      try {
        const response = await fetch(`http://localhost:8000/v1/sessions/${activeSessionId}/turns`);
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled) {
          setTurnsInfo({
            turns: data.turns,
            threshold: data.threshold,
            should_glow: data.should_glow,
          });
        }
      } catch (e) {
        logUiDiagnostic("Failed to fetch turns", e);
      }
    };

    fetchTurns();
    const interval = setInterval(fetchTurns, 4000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [activeSessionId, sessions]);

  useEffect(() => {
    if (!activeSessionId) return;
    let cancelled = false;

    const fetchDefragMetrics = async () => {
      try {
        const response = await fetch(`http://localhost:8000/v1/sessions/${activeSessionId}/defragment/metrics`);
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled) {
          setDefragMetrics({
            fragmentation_rate: data.fragmentation_rate,
            reconciliation_efficiency: data.reconciliation_efficiency
          });
        }
      } catch (e) {
        logUiDiagnostic("Failed to fetch defrag metrics", e);
      }
    };

    fetchDefragMetrics();
    const interval = setInterval(fetchDefragMetrics, 6000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [activeSessionId, sessions]);

  useEffect(() => {
    if (!activeSessionId) return;
    let cancelled = false;

    const fetchLedger = async () => {
      try {
        const response = await fetch(`http://localhost:8000/v1/sessions/${activeSessionId}/ledger`);
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled) {
          setLedgerData({
            total_cost: data.total_cost,
            cost_threshold: data.cost_threshold,
            active_model: data.active_model,
            transactions: data.transactions
          });
        }
      } catch (e) {
        logUiDiagnostic("Failed to fetch ledger", e);
      }
    };

    fetchLedger();
    const interval = setInterval(fetchLedger, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [activeSessionId, sessions]);

  useEffect(() => {
    if (!activeSessionId) return;
    let cancelled = false;

    const fetchSandboxStatus = async () => {
      try {
        const response = await fetch(`http://localhost:8000/v1/sessions/${activeSessionId}/sandbox/status`);
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled) {
          setSandboxStatus({
            total_executions: data.total_executions,
            blocked_executions: data.blocked_executions,
            allowed_executions: data.allowed_executions,
            last_execution_status: data.last_execution_status
          });
        }
      } catch (e) {
        logUiDiagnostic("Failed to fetch sandbox status", e);
      }
    };

    fetchSandboxStatus();
    const interval = setInterval(fetchSandboxStatus, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [activeSessionId, sessions]);

  useEffect(() => {
    if (!activeSessionId) return;
    let cancelled = false;

    const fetchTelemetry = async () => {
      try {
        const response = await fetch(`http://localhost:8000/v1/sessions/${activeSessionId}/telemetry`);
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled) {
          setTelemetryData({
            metrics: data.metrics
          });
        }
      } catch (e) {
        logUiDiagnostic("Failed to fetch telemetry", e);
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [activeSessionId, sessions]);

  useEffect(() => {
    if (!activeSessionId) return;
    let cancelled = false;

    const fetchRouterStatus = async () => {
      try {
        const response = await fetch(`http://localhost:8000/v1/sessions/${activeSessionId}/router/status`);
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled) {
          setRouterStatus({
            routes: data.routes || [],
            pruned_history: data.pruned_history || []
          });
        }
      } catch (e) {
        logUiDiagnostic("Failed to fetch router status", e);
      }
    };

    fetchRouterStatus();
    const interval = setInterval(fetchRouterStatus, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [activeSessionId, sessions]);

  useEffect(() => {
    if (!activeSessionId) return;
    let ws: WebSocket | null = null;
    let cancelled = false;

    const connectCollab = () => {
      if (cancelled) return;
      try {
        ws = new WebSocket(`ws://localhost:8000/v1/collaboration/${activeSessionId}`);
        
        ws.onopen = () => {
          if (cancelled) {
            ws?.close();
            return;
          }
          setCollabConnected(true);
          // Subscribe to channels
          const channels = ["logs", "telemetry", "ledger", "topology", "stdout", "state_sync"];
          channels.forEach(ch => {
            ws?.send(JSON.stringify({
              action: "subscribe",
              channel: ch
            }));
          });
        };

        ws.onmessage = (event) => {
          if (cancelled) return;
          try {
            const data = JSON.parse(event.data);
            // Append incoming event to the scrolling stream
            setActivityStream(prev => {
              const next = [...prev, data];
              if (next.length > 25) {
                next.shift(); // Limit to 25 items
              }
              return next;
            });

            // Optimistic update of component states on message arrival
            if (data.channel === "telemetry" && data.payload) {
              setTelemetryData({ metrics: [data.payload] });
            } else if (data.channel === "ledger" && data.payload) {
              setLedgerData(prev => prev ? {
                ...prev,
                total_cost: data.payload.total_cost || prev.total_cost,
                transactions: data.payload.transactions || prev.transactions
              } : null);
            }
          } catch (e) {
            logUiDiagnostic("Failed to parse websocket message", e);
          }
        };

        ws.onclose = () => {
          setCollabConnected(false);
          // Reconnect logic
          setTimeout(connectCollab, 3000);
        };

        ws.onerror = () => {
          ws?.close();
        };
      } catch (e) {
        logUiDiagnostic("WebSocket collab connection failed", e);
      }
    };

    connectCollab();

    return () => {
      cancelled = true;
      if (ws) {
        ws.close();
      }
    };
  }, [activeSessionId, sessions]);

  const handleHandoff = async () => {
    if (!activeSessionId) return;
    setExporting(true);
    try {
      const response = await fetch(`http://localhost:8000/v1/sessions/${activeSessionId}/handoff`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Handoff export failed");
      const data = await response.json();
      
      await navigator.clipboard.writeText(data.prompt);
      alert(`Successfully exported session state!\nHandoff ID: ${data.handoff_id}\n\nThe English handoff prompt has been copied to your clipboard.`);
    } catch (e) {
      logUiDiagnostic("Failed to export handoff", e);
      alert(`Failed to export handoff: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setExporting(false);
    }
  };

  const handleDefragment = async () => {
    if (!activeSessionId) return;
    setDefragmenting(true);
    try {
      const response = await fetch(`http://localhost:8000/v1/sessions/${activeSessionId}/defragment`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Defragmentation sweep failed");
      const data = await response.json();
      
      setDefragMetrics({
        fragmentation_rate: data.fragmentation_rate,
        reconciliation_efficiency: data.reconciliation_efficiency
      });
      setDefragHistory(prev => [...prev, data.fragmentation_rate].slice(-8));
      
      alert(
        lang === "zh"
          ? `記憶碎片重整成功！\n碎片率下降至: ${Math.round(data.fragmentation_rate * 100)}%\n協同效率: ${Math.round(data.reconciliation_efficiency * 100)}%\n知識圖譜已更新至 .agent/memory/defragmented_graph.json`
          : `Swarm Memory Sweep completed!\nFragmentation rate: ${Math.round(data.fragmentation_rate * 100)}%\nEfficiency: ${Math.round(data.reconciliation_efficiency * 100)}%\nFederated graph saved.`
      );
    } catch (e) {
      logUiDiagnostic("Defragmentation sweep failed", e);
      alert(`Defragmentation sweep failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setDefragmenting(false);
    }
  };

  const handlePrune = async (force: boolean = false) => {
    if (!activeSessionId) return;
    setPruning(true);
    try {
      const response = await fetch(`http://localhost:8000/v1/sessions/${activeSessionId}/router/prune?force=${force}`, {
        method: "POST",
      });
      if (!response.ok) throw new Error("Pruning sweep failed");
      const data = await response.json();
      
      setRouterStatus({
        routes: data.active_routes || [],
        pruned_history: data.pruned_history || []
      });
      
      alert(
        lang === "zh"
          ? `路由優化清理完成！\n是否執行了清理: ${data.pruned_any ? '是' : '否'}\n活動路由數: ${data.active_routes?.length ?? 0}`
          : `Route optimization complete!\nRoutes pruned: ${data.pruned_any ? 'Yes' : 'No'}\nActive routes: ${data.active_routes?.length ?? 0}`
      );
    } catch (e) {
      logUiDiagnostic("Pruning failed", e);
      alert(`Pruning failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setPruning(false);
    }
  };

  const handleResolveApproval = async (sessionId: string, approved: boolean) => {
    setResolving(approved ? "approving" : "rejecting");
    const action = approved ? "approve" : "reject";
    try {
      const response = await fetch(`http://localhost:8000/v1/sessions/${sessionId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) throw new Error("API call failed");
    } catch (e) {
      logUiDiagnostic(`Failed to ${action} session`, e);
      alert(`Failed to ${action} session: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setResolving(null);
    }
  };

  useEffect(() => {
    if (sessions.length === 0) return;
    setVisibleSessionIds((current) => {
      const valid = current.filter((id) => sessions.some((session) => session.session_id === id));
      if (valid.length > 0) return valid.slice(0, 2);
      return [(lastUpdatedSessionId || sessions[0].session_id)];
    });
  }, [lastUpdatedSessionId, sessions]);

  const visibleSessions = sessions.filter((session) => visibleSessionIds.includes(session.session_id)).slice(0, 2);
  const activeSession = visibleSessions[0] || sessions.find((session) => session.session_id === activeSessionId);
  const conductorTrace = useMemo(() => latestConductorTrace(activeSession), [activeSession]);
  const aggregate = sessions.reduce(
    (acc, session) => ({
      nodes: acc.nodes + session.stats.total_nodes,
      errors: acc.errors + session.stats.errors,
      tokens: acc.tokens + session.stats.total_tokens,
      completed: acc.completed + session.stats.completed,
    }),
    { nodes: 0, errors: 0, tokens: 0, completed: 0 },
  );
  const completionRate = aggregate.nodes > 0 ? Math.round((aggregate.completed / aggregate.nodes) * 100) : 0;

  const toggleSession = useCallback((sessionId: string) => {
    setVisibleSessionIds((current) => {
      if (current.includes(sessionId)) {
        return current.length === 1 ? current : current.filter((id) => id !== sessionId);
      }
      return [sessionId, ...current].slice(0, 2);
    });
  }, []);

  return (
    <div className="grid h-full min-h-0 grid-cols-[280px_minmax(0,1fr)_320px] gap-4 overflow-hidden">
      <aside className="control-surface flex min-h-0 flex-col overflow-hidden">
        <div className="border-b p-4" style={{ borderColor: "var(--border-c)" }}>
          <p className="text-sm font-semibold t1">{visibleSessions[0]?.project_name || copy.title}</p>
          <p className="mt-1 text-xs leading-relaxed t3">{visibleSessions[0]?.summary || copy.subtitle}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 p-3">
          {[
            [copy.nodes, aggregate.nodes],
            [copy.errors, aggregate.errors],
            [copy.tokens, aggregate.tokens],
            [copy.completion, `${completionRate}%`],
          ].map(([label, value]) => (
            <MetricTile key={label} label={label} value={value} />
          ))}
        </div>
        
        {activeSessionId && (
          <>
            <div className="px-3 pb-3 relative group">
              <button
                type="button"
                disabled={exporting}
                onClick={handleHandoff}
                className={`w-full rounded-lg px-3 py-2 text-xs font-semibold transition-all flex items-center justify-center gap-2 ${
                  turnsInfo?.should_glow
                    ? "primary-button"
                    : "quiet-button"
                }`}
                title={
                  lang === "zh"
                    ? "對話狀態交接：點選將匯出狀態並複製英文交接提示詞至剪貼簿，以遷移至全新 Thread"
                    : "Context Handoff & Compaction: Click to export state and copy warm-thread handoff prompt to clipboard"
                }
              >
                {turnsInfo?.should_glow && (
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                )}
                {exporting ? "Compacting..." : `Compaction Handoff (${turnsInfo?.turns ?? 0}/${turnsInfo?.threshold ?? 5})`}
              </button>
              <Tooltip>
                {lang === "zh"
                  ? "點選以執行對話狀態匯出與壓縮。系統將產出包含 handoff_id 的交接提示詞並複製至剪貼簿，以加載全新 thread。"
                  : "Instructs the agent to compact active context and migrate threads. Copies pre-formatted English handoff prompt containing handoff_id to clipboard."}
              </Tooltip>
            </div>

            <ConductorTracePanel
              trace={conductorTrace}
              telemetry={telemetryData?.metrics?.[0]}
              ledger={ledgerData}
              lang={lang}
            />

            <Surface className="group/defrag relative mx-3 mb-3 flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
                  {lang === "zh" ? "自主記憶重整" : "Swarm Memory Control"}
                </p>
                <StatusBadge tone="success">Ready</StatusBadge>
              </div>
              
              <div className="grid grid-cols-2 gap-2 my-1">
                <div className="rounded border p-2 flex flex-col" style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}>
                  <span className="text-[9px] font-bold uppercase tracking-[0.1em] t3">
                    {lang === "zh" ? "碎片率" : "Fragmentation"}
                  </span>
                  <span className="font-mono text-sm font-black" style={{ color: "var(--warning)" }}>
                    {defragMetrics ? `${Math.round(defragMetrics.fragmentation_rate * 100)}%` : "18%"}
                  </span>
                </div>
                <div className="rounded border p-2 flex flex-col" style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}>
                  <span className="text-[9px] font-bold uppercase tracking-[0.1em] t3">
                    {lang === "zh" ? "協同效率" : "Efficiency"}
                  </span>
                  <span className="font-mono text-sm font-black" style={{ color: "var(--success)" }}>
                    {defragMetrics ? `${Math.round(defragMetrics.reconciliation_efficiency * 100)}%` : "95%"}
                  </span>
                </div>
              </div>

              {/* Glowing SVG Sparkline */}
              <div className="h-10 w-full rounded border flex items-center justify-center p-1 relative overflow-hidden" style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}>
                <svg className="w-full h-full" viewBox="0 0 200 40" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="sparklineGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>
                  <path
                    d={generateSparklinePath(defragHistory, 200, 32)}
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d={`${generateSparklinePath(defragHistory, 200, 32)} L 200 40 L 0 40 Z`}
                    fill="url(#sparklineGrad)"
                  />
                </svg>
                <span className="absolute bottom-0.5 right-1.5 text-[8px] font-mono t3">
                  {lang === "zh" ? "碎片趨勢" : "Defrag Trend"}
                </span>
              </div>

              <Button
                type="button"
                disabled={defragmenting}
                onClick={handleDefragment}
                className="flex w-full items-center justify-center gap-1.5 py-1.5 text-[11px]"
              >
                <svg className={`h-3.5 w-3.5 t3 ${defragmenting ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3m-3-3v12" />
                </svg>
                {defragmenting ? (lang === "zh" ? "重整中..." : "Sweeping...") : (lang === "zh" ? "記憶重整" : "Trigger Memory Sweep")}
              </Button>

              <Tooltip>
                {lang === "zh"
                  ? "記憶重整：掃描 handoff json，清理冗餘，壓縮狀態並生成聯邦知識圖譜"
                  : "Memory Defrag: Sweeps handoffs, resolves duplicates, reconciles tasks, and merges into knowledge graph"}
              </Tooltip>
            </Surface>

            <Surface className="group/cost relative mx-3 mb-3 flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
                  {lang === "zh" ? "財務帳本與額度控管" : "Swarm Cost Balance & Ledger"}
                </p>
                <span className="font-mono text-[10px] font-bold t3">USD</span>
              </div>
              
              <div className="flex flex-col gap-1 my-1">
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-xl font-black" style={{ color: "var(--success)" }}>
                    ${ledgerData ? ledgerData.total_cost.toFixed(5) : "0.00000"}
                  </span>
                  <span className="font-mono text-[9px] font-bold t3">
                    / ${ledgerData ? ledgerData.cost_threshold.toFixed(2) : "0.05"} Limit
                  </span>
                </div>
                
                {/* Limit Progress Bar Gauge */}
                <ProgressBar
                  value={((ledgerData?.total_cost ?? 0) / (ledgerData?.cost_threshold ?? 0.05)) * 100}
                  tone={((ledgerData?.total_cost ?? 0) / (ledgerData?.cost_threshold ?? 0.05)) > 0.8 ? "warning" : "success"}
                />
              </div>

              {/* Real-time scrolling Ledger Transactions List */}
              <div className="rounded border flex flex-col p-1.5 gap-1.5 overflow-hidden" style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}>
                <span className="text-[8px] font-bold uppercase tracking-[0.1em] t3 border-b pb-1" style={{ borderColor: "var(--border-c)" }}>
                  {lang === "zh" ? "實時消費明細" : "Ledger Transactions"}
                </span>
                <div className="max-h-20 overflow-y-auto space-y-1 pr-1 font-mono text-[9px]">
                  {ledgerData && ledgerData.transactions.length > 0 ? (
                    ledgerData.transactions.slice().reverse().map((tx: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between transition-colors t3 hover:t2">
                        <span className="truncate max-w-[80px]" title={tx.model}>{tx.model.replace("gemini-2.5-", "")}</span>
                        <span className="text-[8px] t3">{new Date(tx.timestamp).toLocaleTimeString()}</span>
                        <span className="font-bold" style={{ color: "var(--success)" }}>${tx.cost.toFixed(5)}</span>
                      </div>
                    ))
                  ) : (
                    <div className="py-2 text-center text-[8px] t3">
                      {lang === "zh" ? "尚無交易記錄" : "No transactions logged"}
                    </div>
                  )}
                </div>
              </div>

              <Tooltip>
                {lang === "zh"
                  ? "財務審計：基於 SQLite 記錄的實時 API 消耗與 Token 計費帳本，額度超限將自動降級"
                  : "Financial Audit: SQLite-backed real-time API expense tracker. Auto-downscale triggers when limit is exceeded"}
              </Tooltip>
            </Surface>

            <Surface className="group/sandbox relative mx-3 mb-3 flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
                  {lang === "zh" ? "沙箱零信任防禦" : "Zero-Trust Sandbox Guard"}
                </p>
                <StatusBadge tone={sandboxStatus?.last_execution_status === "blocked" ? "danger" : "success"} className="text-[8px]">
                  {sandboxStatus?.last_execution_status ? sandboxStatus.last_execution_status.toUpperCase() : "IDLE"}
                </StatusBadge>
              </div>
              
              <div className="grid grid-cols-3 gap-1.5 text-center mt-1 font-mono">
                <MetricTile label="Total" value={sandboxStatus?.total_executions ?? 0} className="p-1" />
                <MetricTile label="Blocked" value={sandboxStatus?.blocked_executions ?? 0} tone="danger" className="p-1" />
                <MetricTile label="Allowed" value={sandboxStatus?.allowed_executions ?? 0} tone="success" className="p-1" />
              </div>

              <Tooltip>
                {lang === "zh"
                  ? "零信任沙箱防禦：驗證共識簽章並物理隔離動態代碼與自定義腳本的執行"
                  : "Zero-Trust Sandbox: Intercepts & executes dynamic code with cryptographic signature verification"}
              </Tooltip>
            </Surface>

            <Surface className="group/telemetry relative mx-3 mb-3 flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
                  {lang === "zh" ? "異步遙測與開銷路由" : "Telemetry & Cost Router"}
                </p>
                <span className="font-mono text-[8px] font-bold t3">ASYNC</span>
              </div>
              
              <div className="mt-1 flex flex-col gap-2 font-mono text-[9px] t3">
                <div className="flex justify-between items-center">
                  <span>CPU Load</span>
                  <span className="t1">{telemetryData?.metrics?.[0]?.cpu_percent ?? 15.4}%</span>
                </div>
                <ProgressBar value={telemetryData?.metrics?.[0]?.cpu_percent ?? 15.4} tone="accent" />
                
                <div className="flex justify-between items-center">
                  <span>Memory RSS</span>
                  <span className="t1">{telemetryData?.metrics?.[0]?.memory_mb ? telemetryData.metrics[0].memory_mb.toFixed(1) : "124.5"} MB</span>
                </div>
                <ProgressBar value={Math.min(100, ((telemetryData?.metrics?.[0]?.memory_mb ?? 124.5) / 512.0) * 100)} tone="warning" />

                <div className="flex justify-between items-center text-[8px] t3">
                  <span>WS Latency: <span className="t2">{telemetryData?.metrics?.[0]?.ws_latency_ms ?? 8}ms</span></span>
                  <span>Exec Latency: <span className="t2">{telemetryData?.metrics?.[0]?.latency_ms ?? 12.5}ms</span></span>
                </div>
              </div>

              <Tooltip>
                {lang === "zh"
                  ? "遙測路由：非阻塞緩衝與轉發系統運行時之 CPU、記憶體佔用、 WebSocket 延遲與 SQLite 累積成本"
                  : "Telemetry Router: Non-blocking real-time routing of CPU, Memory, WS latency, and cumulative API USD cost metrics"}
              </Tooltip>
            </Surface>

            <Surface className="group/router relative mx-3 mb-3 flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
                  {lang === "zh" ? "拓撲負載與路由優化" : "Topological Load & Route Map"}
                </p>
                <StatusBadge tone="warning" className="text-[8px]">Optimizing</StatusBadge>
              </div>
              
              <div className="mt-1 flex flex-col gap-2 font-mono text-[9px] t3">
                <span className="text-[8px] font-bold uppercase tracking-[0.15em] t3">
                  {lang === "zh" ? "活躍節點負載" : "Active Node Load"}
                </span>
                {routerStatus && routerStatus.routes && routerStatus.routes.filter(r => r.status === "active").length > 0 ? (
                  routerStatus.routes.filter(r => r.status === "active").map((r) => {
                    const avgLat = r.latency_history.length > 0 ? (r.latency_history.reduce((a: number, b: number) => a + b, 0) / r.latency_history.length * 1000) : 0;
                    return (
                      <div key={r.node_id} className="flex flex-col gap-1 border-t pt-1.5 first:border-0 first:pt-0" style={{ borderColor: "var(--border-c)" }}>
                        <div className="flex justify-between items-center text-[8px]">
                          <span className="font-bold t2">{r.node_id}</span>
                          <span className="text-[8px] font-bold t3">
                            {r.active_load} active / {Math.round(avgLat)}ms
                          </span>
                        </div>
                        <ProgressBar value={Math.min(100, (r.active_load > 0 ? r.active_load * 25 : 10))} tone={r.active_load > 0 ? "warning" : "success"} />
                      </div>
                    );
                  })
                ) : (
                  <div className="py-1 text-center text-[8px] t3">
                    {lang === "zh" ? "無活躍節點負載" : "No active node dispatches"}
                  </div>
                )}

                <div className="mt-1 border-t pt-1.5 flex flex-col gap-1.5" style={{ borderColor: "var(--border-c)" }}>
                  <span className="text-[8px] font-bold uppercase tracking-[0.15em]" style={{ color: "var(--warning)" }}>
                    {lang === "zh" ? "被修剪路由路徑" : "Pruned Path History"}
                  </span>
                  <div className="max-h-20 overflow-y-auto space-y-1.5 font-mono text-[8px] scrollbar-thin">
                    {routerStatus && routerStatus.pruned_history && routerStatus.pruned_history.length > 0 ? (
                      routerStatus.pruned_history.slice().reverse().map((p: any, idx: number) => (
                        <div key={idx} className="flex flex-col rounded border p-1 t3" style={{ background: "var(--danger-bg)", borderColor: "color-mix(in srgb, var(--danger) 28%, transparent)" }}>
                          <div className="flex justify-between items-center text-[7px] font-bold">
                            <span style={{ color: "var(--danger)" }}>{p.node_id}</span>
                            <span className="t3">{new Date(p.pruned_at).toLocaleTimeString()}</span>
                          </div>
                          <span className="mt-0.5 break-all text-[7.5px] leading-relaxed t2">{p.reason}</span>
                        </div>
                      ))
                    ) : (
                      <div className="py-1 text-center text-[8px] t3">
                        {lang === "zh" ? "無已修剪路徑" : "No paths pruned yet"}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex gap-1.5 mt-1 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
                <Button
                  type="button"
                  disabled={pruning}
                  onClick={() => handlePrune(false)}
                  className="flex flex-1 items-center justify-center gap-1 px-2 py-1 text-[9px]"
                >
                  <svg className={`h-2.5 w-2.5 t3 ${pruning ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  {pruning ? "..." : (lang === "zh" ? "清理過期" : "Prune Stale")}
                </Button>
                <Button
                  type="button"
                  disabled={pruning}
                  onClick={() => handlePrune(true)}
                  variant="warning"
                  className="flex-1 px-2 py-1 text-[9px]"
                >
                  {lang === "zh" ? "強制修剪" : "Force Prune"}
                </Button>
              </div>

              <Tooltip>
                {lang === "zh"
                  ? "拓撲路由優化：動態監控代理負載及響應時間，對低效或無響應的路由進行自動修剪，並可手動一鍵 sweeps 清理"
                  : "Topological Optimization: Measures node dispatch latencies & success rates, auto-prunes low-performance paths, and supports admin sweeps."}
              </Tooltip>
            </Surface>

            <Surface className="group/collab relative mx-3 mb-3 flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
                  {lang === "zh" ? "多通道實時協作" : "Live Swarm Collaboration"}
                </p>
                <StatusBadge tone={collabConnected ? "success" : "danger"} className="text-[8px]">
                  {collabConnected ? "CONNECTED" : "OFFLINE"}
                </StatusBadge>
              </div>
              
              <div className="flex flex-wrap gap-1 mt-1">
                {subscribedChannels.map((ch) => (
                  <span key={ch} className="rounded border px-1 py-0.5 font-mono text-[7px] font-black uppercase t3" style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}>
                    #{ch}
                  </span>
                ))}
              </div>

              <Tooltip>
                {lang === "zh"
                  ? "協作通道：提供跨代理/用戶之實時 Pub/Sub 廣播與多路訂閱路由服務"
                  : "Collaboration channels: Pub/Sub routing for dynamic swarm collaboration streams"}
              </Tooltip>
            </Surface>

            <Surface className="group/activity relative mx-3 mb-3 flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between border-b pb-1" style={{ borderColor: "var(--border-c)" }}>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
                  {lang === "zh" ? "實時群落活動流" : "Live Activity Stream"}
                </p>
                <span className="font-mono text-[8px] font-bold t3">REAL-TIME</span>
              </div>
              
              <div className="max-h-24 space-y-1.5 overflow-y-auto pr-1 font-mono text-[9px] t3">
                {activityStream.length > 0 ? (
                  activityStream.slice().reverse().map((act: any, idx: number) => {
                    const chLabel = act.channel || "logs";
                    const timestamp = act.timestamp ? new Date(act.timestamp).toLocaleTimeString() : "";
                    const payload = act.payload || {};
                    let displayMsg = JSON.stringify(payload);
                    if (chLabel === "stdout") {
                      displayMsg = payload.text || "";
                    } else if (chLabel === "logs") {
                      displayMsg = payload.content || payload.msg || displayMsg;
                    } else if (chLabel === "topology") {
                      displayMsg = `Node ${payload.node_id || ""} status: ${payload.status || ""}`;
                    } else if (chLabel === "state_sync") {
                      displayMsg = `Delta Sync: ${Object.keys(payload.values || {}).join(", ")}`;
                    }

                    if (displayMsg.length > 60) {
                      displayMsg = displayMsg.substring(0, 57) + "...";
                    }

                    return (
                      <div key={idx} className="flex flex-col border-b pb-1 last:border-b-0" style={{ borderColor: "var(--border-c)" }}>
                        <div className="mb-0.5 flex justify-between text-[7px] font-bold t3">
                          <span style={{ color: "var(--accent)" }}>#{chLabel}</span>
                          <span>{timestamp}</span>
                        </div>
                        <span className="break-all leading-tight t2">{displayMsg}</span>
                      </div>
                    );
                  })
                ) : (
                  <div className="py-4 text-center text-[8px] t3">
                    {lang === "zh" ? "等待實時廣播活動中..." : "Awaiting collaboration streams..."}
                  </div>
                )}
              </div>

              <Tooltip>
                {lang === "zh"
                  ? "活動流：呈現當前 Session 發送至多通道之最新 logs、stdout 與 delta 狀態變化"
                  : "Activity stream: chronological live feed of multi-channel logs, stdout, and delta states"}
              </Tooltip>
            </Surface>
          </>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] t3">{copy.sessions}</p>
          <div className="space-y-2">
            {sessions.map((session) => {
              const isVisible = visibleSessionIds.includes(session.session_id);
              const summary = summarizeTopology(session);
              return (
                <button
                  key={session.session_id}
                  type="button"
                  onClick={() => toggleSession(session.session_id)}
                  className="w-full rounded-lg border p-3 text-left transition-all"
                  style={
                    isVisible
                      ? { background: "var(--accent-bg)", borderColor: "var(--accent)" }
                      : { background: "var(--bg-card)", borderColor: "var(--border-c)" }
                  }
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-xs font-black t1">{session.session_id}</p>
                    {isVisible && <span className="text-[9px] font-black uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>{copy.active}</span>}
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-1 text-[10px] t3">
                    <span>{session.stats.total_nodes} nodes</span>
                    <span>{summary.completionRate}% done</span>
                    <span>{summary.errorRate}% err</span>
                  </div>
                  <p className="mt-2 text-[10px] font-mono t3">{copy.updated} {formatTime(session.updated_at, lang)}</p>
                </button>
              );
            })}
          </div>
        </div>
      </aside>

      <main className={`grid min-h-0 gap-3 ${visibleSessions.length > 1 ? "grid-rows-2" : "grid-rows-1"}`}>
        {visibleSessions.map((session) => (
          <SessionCanvas key={session.session_id} state={session} onOpenNode={setSelectedNode} />
        ))}
      </main>

      <aside className="grid min-h-0 grid-rows-[minmax(0,1fr)_220px] gap-3">
        <Surface as="section" elevated className="min-h-0 overflow-hidden">
          <div className="border-b p-4" style={{ borderColor: "var(--border-c)" }}>
            <p className="text-sm font-black t1">{copy.details}</p>
            <p className="mt-1 text-[10px] font-mono t3">{selectedNode?.node_id || copy.noNode}</p>
          </div>
          {selectedNode ? (
            <div className="h-full space-y-4 overflow-y-auto p-4 pb-20">
              <div>
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] t3">{selectedNode.node_type}</p>
                  {selectedNode.assigned_agent && (
                    <StatusBadge tone="accent" className="text-[9px]">
                      @{selectedNode.assigned_agent}
                    </StatusBadge>
                  )}
                </div>
                <h3 className="mt-1 text-lg font-black t1">{selectedNode.title || selectedNode.payload?.name || selectedNode.id || selectedNode.node_id}</h3>
                <p className="mt-1 text-xs t2">{selectedNode.description || selectedNode.payload?.description || selectedNode.status}</p>
              </div>
              
              {(selectedNode.status === "awaiting_approval" || selectedNode.status === "review" || selectedNode.node_type === "hitl_gate") && (
                <Surface className="space-y-3 p-3" style={{ borderColor: "color-mix(in srgb, var(--warning) 30%, transparent)", background: "var(--warning-bg)" }}>
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--warning)" }}>Human-in-the-Loop Required</p>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      disabled={resolving !== null}
                      onClick={() => handleResolveApproval(selectedNode.session_id, true)}
                      variant="warning"
                      className="flex-1"
                    >
                      {resolving === "approving" ? "..." : "Approve"}
                    </Button>
                    <Button
                      type="button"
                      disabled={resolving !== null}
                      onClick={() => handleResolveApproval(selectedNode.session_id, false)}
                      className="flex-1"
                    >
                      {resolving === "rejecting" ? "..." : "Reject"}
                    </Button>
                  </div>
                </Surface>
              )}

              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg border p-2" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
                  <p className="text-[10px] font-bold t3">Status</p>
                  <p className="text-xs font-black t1">{selectedNode.status}</p>
                </div>
                <div className="rounded-lg border p-2" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
                  <p className="text-[10px] font-bold t3">Duration</p>
                  <p className="text-xs font-black t1">{formatDuration(selectedNode.payload?.duration_ms)}</p>
                </div>
              </div>
              
              {(selectedNode.status === 'done' || selectedNode.status === 'completed') && selectedNode.result_summary && (
                <div>
                  <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--success)" }}>Result Summary</p>
                  <p className="rounded-lg border p-3 text-xs t2" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
                    {selectedNode.result_summary}
                  </p>
                </div>
              )}
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] t3">{copy.input}</p>
                <JsonBlock value={selectedNode.payload?.input} />
              </div>
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] t3">{copy.output}</p>
                <JsonBlock value={selectedNode.payload?.output} />
              </div>
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] t3">{copy.notes}</p>
                <p className="rounded-lg border p-3 text-xs t2" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
                  {selectedNode.payload?.human_notes || "-"}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex h-64 items-center justify-center p-6 text-center text-xs font-semibold t3">{copy.noNode}</div>
          )}
        </Surface>
        <ActivityLog entries={activityEntries} lang={lang} onClear={onClearActivityLog} />
      </aside>
    </div>
  );
}
