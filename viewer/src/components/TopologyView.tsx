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
    cost: "Cost",
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
          <p className="text-sm font-black t1">{copy.title}</p>
          <p className="mt-1 text-xs leading-relaxed t3">{copy.subtitle}</p>
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
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] t3">{selectedNode.node_type}</p>
                <h3 className="mt-1 text-lg font-black t1">{selectedNode.payload.name || selectedNode.node_id}</h3>
                <p className="mt-1 text-xs t2">{selectedNode.payload.description || selectedNode.status}</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg border p-2" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
                  <p className="text-[10px] font-bold t3">Status</p>
                  <p className="text-xs font-black t1">{selectedNode.status}</p>
                </div>
                <div className="rounded-lg border p-2" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
                  <p className="text-[10px] font-bold t3">Duration</p>
                  <p className="text-xs font-black t1">{formatDuration(selectedNode.payload.duration_ms)}</p>
                </div>
              </div>
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] t3">{copy.input}</p>
                <JsonBlock value={selectedNode.payload.input} />
              </div>
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] t3">{copy.output}</p>
                <JsonBlock value={selectedNode.payload.output} />
              </div>
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] t3">{copy.notes}</p>
                <p className="rounded-lg border p-3 text-xs t2" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}>
                  {selectedNode.payload.human_notes || "-"}
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
