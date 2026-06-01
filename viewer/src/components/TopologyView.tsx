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
import { buildTopologyFlow, formatDuration, NODE_COLORS, summarizeTopology } from "../utils/topologyUtils";
import type { ActivityLogEntry, Lang, TopologyEvent, TopologyNodeData, TopologyState } from "../types";

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
      className="relative min-h-[360px] overflow-hidden rounded-xl border"
      style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}
    >
      <div className="absolute top-3 left-3 z-10 rounded-lg border px-3 py-2 shadow-xl panel-bg" style={{ borderColor: "var(--border-c)" }}>
        <p className="text-xs font-black t1">{state.session_id}</p>
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
          maskColor="rgba(2,8,23,0.62)"
          style={{ background: "var(--bg-panel)", border: "1px solid var(--border-c)", borderRadius: 10 }}
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
        console.error("Failed to fetch turns:", e);
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
        console.error("Failed to fetch defrag metrics:", e);
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
        console.error("Failed to fetch ledger:", e);
      }
    };

    fetchLedger();
    const interval = setInterval(fetchLedger, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
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
      console.error(e);
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
      console.error(e);
      alert(`Defragmentation sweep failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setDefragmenting(false);
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
      console.error(e);
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
    <div className="grid h-full min-h-0 grid-cols-[260px_minmax(0,1fr)_320px] gap-3 overflow-hidden">
      <aside className="panel-bg flex min-h-0 flex-col rounded-xl border shadow-xl" style={{ borderColor: "var(--border-c)" }}>
        <div className="border-b p-4" style={{ borderColor: "var(--border-c)" }}>
          <p className="text-sm font-black t1">{visibleSessions[0]?.project_name || copy.title}</p>
          <p className="mt-1 text-xs leading-relaxed t3">{visibleSessions[0]?.summary || copy.subtitle}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 p-3">
          {[
            [copy.nodes, aggregate.nodes],
            [copy.errors, aggregate.errors],
            [copy.tokens, aggregate.tokens],
            [copy.completion, `${completionRate}%`],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border p-2" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
              <p className="text-lg font-black" style={{ color: "var(--accent)" }}>{value}</p>
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{label}</p>
            </div>
          ))}
        </div>
        
        {activeSessionId && (
          <>
            <div className="px-3 pb-3 relative group">
              <button
                type="button"
                disabled={exporting}
                onClick={handleHandoff}
                className={`w-full py-2 px-3 rounded-lg border text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                  turnsInfo?.should_glow
                    ? "glow-gold border-amber-500 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20"
                    : "border-slate-700 bg-slate-800/40 text-slate-300 hover:bg-slate-800/80"
                }`}
                title={
                  lang === "zh"
                    ? "對話狀態交接：點選將匯出狀態並複製英文交接提示詞至剪貼簿，以遷移至全新 Thread"
                    : "Context Handoff & Compaction: Click to export state and copy warm-thread handoff prompt to clipboard"
                }
              >
                {turnsInfo?.should_glow && (
                  <svg className="h-4 w-4 animate-bounce text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                )}
                {exporting ? "Compacting..." : `Compaction Handoff (${turnsInfo?.turns ?? 0}/${turnsInfo?.threshold ?? 5})`}
              </button>
              <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded bg-slate-950 px-3 py-2 text-center text-[10px] leading-normal text-slate-300 opacity-0 transition-opacity border border-slate-800 shadow-2xl group-hover:opacity-100">
                {lang === "zh"
                  ? "點選以執行對話狀態匯出與壓縮。系統將產出包含 handoff_id 的交接提示詞並複製至剪貼簿，以加載全新 thread。"
                  : "Instructs the agent to compact active context and migrate threads. Copies pre-formatted English handoff prompt containing handoff_id to clipboard."}
              </div>
            </div>

            <div className="mx-3 mb-3 p-3 rounded-lg border flex flex-col gap-2 relative group/defrag" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
                  {lang === "zh" ? "自主記憶重整" : "Swarm Memory Control"}
                </p>
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-2 my-1">
                <div className="rounded border p-2 flex flex-col" style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}>
                  <span className="text-[9px] font-bold uppercase tracking-[0.1em] t3">
                    {lang === "zh" ? "碎片率" : "Fragmentation"}
                  </span>
                  <span className="text-sm font-black text-amber-500 font-mono">
                    {defragMetrics ? `${Math.round(defragMetrics.fragmentation_rate * 100)}%` : "18%"}
                  </span>
                </div>
                <div className="rounded border p-2 flex flex-col" style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}>
                  <span className="text-[9px] font-bold uppercase tracking-[0.1em] t3">
                    {lang === "zh" ? "協同效率" : "Efficiency"}
                  </span>
                  <span className="text-sm font-black text-emerald-500 font-mono">
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
                    className="drop-shadow-[0_0_4px_var(--accent)]"
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

              <button
                type="button"
                disabled={defragmenting}
                onClick={handleDefragment}
                className="w-full py-1.5 px-3 rounded-lg border border-slate-700 bg-slate-800/40 text-slate-300 hover:bg-slate-800/80 transition-all text-[11px] font-bold flex items-center justify-center gap-1.5 active:scale-95 duration-100"
              >
                <svg className={`h-3.5 w-3.5 text-slate-400 ${defragmenting ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3-3 3 3m-3-3v12" />
                </svg>
                {defragmenting ? (lang === "zh" ? "重整中..." : "Sweeping...") : (lang === "zh" ? "記憶重整" : "Trigger Memory Sweep")}
              </button>

              <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded bg-slate-950 px-3 py-2 text-center text-[10px] leading-normal text-slate-300 opacity-0 transition-opacity border border-slate-800 shadow-2xl group-hover/defrag:opacity-100">
                {lang === "zh"
                  ? "記憶重整：掃描 handoff json，清理冗餘，壓縮狀態並生成聯邦知識圖譜"
                  : "Memory Defrag: Sweeps handoffs, resolves duplicates, reconciles tasks, and merges into knowledge graph"}
              </div>
            </div>

            <div className="mx-3 mb-3 p-3 rounded-lg border flex flex-col gap-2 relative group/cost" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: "var(--accent)" }}>
                  {lang === "zh" ? "財務帳本與額度控管" : "Swarm Cost Balance & Ledger"}
                </p>
                <span className="text-[10px] font-mono font-bold text-slate-500">
                  USD
                </span>
              </div>
              
              <div className="flex flex-col gap-1 my-1">
                <div className="flex items-baseline justify-between">
                  <span className="text-xl font-black text-emerald-400 font-mono">
                    ${ledgerData ? ledgerData.total_cost.toFixed(5) : "0.00000"}
                  </span>
                  <span className="text-[9px] font-bold text-slate-500 font-mono">
                    / ${ledgerData ? ledgerData.cost_threshold.toFixed(2) : "0.05"} Limit
                  </span>
                </div>
                
                {/* Limit Progress Bar Gauge */}
                <div className="w-full h-1.5 rounded-full bg-slate-850 overflow-hidden relative border border-slate-700">
                  <div
                    className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-emerald-500 to-amber-500"
                    style={{
                      width: `${Math.min(100, ((ledgerData?.total_cost ?? 0) / (ledgerData?.cost_threshold ?? 0.05)) * 100)}%`
                    }}
                  />
                </div>
              </div>

              {/* Real-time scrolling Ledger Transactions List */}
              <div className="rounded border flex flex-col p-1.5 gap-1.5 overflow-hidden" style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}>
                <span className="text-[8px] font-bold uppercase tracking-[0.1em] t3 border-b pb-1" style={{ borderColor: "var(--border-c)" }}>
                  {lang === "zh" ? "實時消費明細" : "Ledger Transactions"}
                </span>
                <div className="max-h-20 overflow-y-auto space-y-1 pr-1 font-mono text-[9px]">
                  {ledgerData && ledgerData.transactions.length > 0 ? (
                    ledgerData.transactions.slice().reverse().map((tx: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center text-slate-400 hover:text-slate-200 transition-colors">
                        <span className="truncate max-w-[80px]" title={tx.model}>{tx.model.replace("gemini-2.5-", "")}</span>
                        <span className="text-[8px] text-slate-500">{new Date(tx.timestamp).toLocaleTimeString()}</span>
                        <span className="text-emerald-400 font-bold">${tx.cost.toFixed(5)}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-slate-600 text-[8px] py-2">
                      {lang === "zh" ? "尚無交易記錄" : "No transactions logged"}
                    </div>
                  )}
                </div>
              </div>

              <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded bg-slate-950 px-3 py-2 text-center text-[10px] leading-normal text-slate-300 opacity-0 transition-opacity border border-slate-800 shadow-2xl group-hover/cost:opacity-100">
                {lang === "zh"
                  ? "財務審計：基於 SQLite 記錄的實時 API 消耗與 Token 計費帳本，額度超限將自動降級"
                  : "Financial Audit: SQLite-backed real-time API expense tracker. Auto-downscale triggers when limit is exceeded"}
              </div>
            </div>
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
        <section className="panel-bg min-h-0 overflow-hidden rounded-xl border shadow-xl" style={{ borderColor: "var(--border-c)" }}>
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
                    <span className="rounded bg-blue-500/10 px-1.5 py-0.5 text-[9px] font-bold text-blue-500">
                      @{selectedNode.assigned_agent}
                    </span>
                  )}
                </div>
                <h3 className="mt-1 text-lg font-black t1">{selectedNode.title || selectedNode.payload?.name || selectedNode.id || selectedNode.node_id}</h3>
                <p className="mt-1 text-xs t2">{selectedNode.description || selectedNode.payload?.description || selectedNode.status}</p>
              </div>
              
              {(selectedNode.status === "awaiting_approval" || selectedNode.status === "review" || selectedNode.node_type === "hitl_gate") && (
                <div className="rounded-lg border p-3 border-amber-500/20 bg-amber-500/5 space-y-3">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500">Human-in-the-Loop Required</p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={resolving !== null}
                      onClick={() => handleResolveApproval(selectedNode.session_id, true)}
                      className="flex-1 py-1.5 px-3 rounded bg-amber-500 text-slate-950 text-xs font-bold hover:bg-amber-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-1"
                    >
                      {resolving === "approving" ? "..." : "Approve"}
                    </button>
                    <button
                      type="button"
                      disabled={resolving !== null}
                      onClick={() => handleResolveApproval(selectedNode.session_id, false)}
                      className="flex-1 py-1.5 px-3 rounded bg-slate-800 text-slate-200 border border-slate-700 text-xs font-bold hover:bg-slate-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-1"
                    >
                      {resolving === "rejecting" ? "..." : "Reject"}
                    </button>
                  </div>
                </div>
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
                  <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-green-500">Result Summary</p>
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
        </section>
        <ActivityLog entries={activityEntries} lang={lang} onClear={onClearActivityLog} />
      </aside>
    </div>
  );
}
