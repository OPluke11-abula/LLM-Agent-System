import { Handle, Position, type NodeProps } from "reactflow";
import type { TopologyNodeData, TopologyNodeType } from "../../types";
import { NODE_COLORS } from "../../utils/topologyUtils";

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  error: "Error",
  awaiting_approval: "Awaiting approval",
  todo: "To Do",
  in_process: "In Process",
  done: "Done",
  review: "Review",
};

type TopologyNodeBaseProps = NodeProps<TopologyNodeData> & {
  tone: TopologyNodeType;
  badge: string;
};

function resolveModelColor(tone: TopologyNodeType, model: string) {
  const normalized = model.toLowerCase();

  if (normalized.includes("gemini")) return "#7aa2df";
  if (normalized.includes("claude") || normalized.includes("anthropic")) return "#d7a174";
  if (normalized.includes("gpt") || normalized.includes("openai")) return "#83c79c";

  return NODE_COLORS[tone];
}

export function TopologyNodeBase({ data, selected, tone, badge }: TopologyNodeBaseProps) {
  const event = data.event;
  const model = String(event.payload?.model || event.payload?.active_model || "");
  const accent = resolveModelColor(tone, model);
  const isLive = event.status === "running" || event.status === "awaiting_approval" || event.status === "in_process" || event.status === "review";
  const isHitl = event.node_type === "hitl_gate";
  const tokenCount = Number(event.payload?.token_used ?? event.payload?.tokens ?? 0);
  const costVal = tokenCount * 0.00002;
  const historyLength = 6;
  const hash = (event.node_id || event.id || "").charCodeAt(0) || 1;
  const costHistory = Array.from({ length: historyLength }, (_, index) => {
    const progress = (index + 1) / historyLength;
    return costVal * (progress * 0.75 + 0.25) * (1 + Math.sin(hash + index) * 0.08);
  });
  const points = costHistory
    .map((value, index) => {
      const x = (index / (costHistory.length - 1)) * 48;
      const maxVal = Math.max(...costHistory, 0.0001);
      const y = 13 - (value / maxVal) * 10;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <button
      type="button"
      onClick={() => data.onOpen(event)}
      className={`topology-node group relative w-[260px] p-3.5 text-left ${selected ? "topology-node-selected" : ""}`}
      style={{
        borderColor: selected ? "var(--accent)" : isHitl ? "color-mix(in srgb, var(--warning) 45%, var(--border-c))" : "var(--border-c)",
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: "var(--bg-elevated)", width: 9, height: 9, border: `1px solid ${accent}` }}
      />

      <div className="mb-2 flex items-center justify-between gap-2">
        <span
          className="rounded-md border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.14em]"
          style={{ borderColor: "var(--border-c)", color: accent, background: "var(--bg-muted)" }}
        >
          {badge}
        </span>
        <span className="flex items-center gap-1.5 text-[10px] font-semibold" style={{ color: "var(--t2)" }}>
          <span className="status-dot h-2 w-2 rounded-full" style={{ background: isLive ? accent : "var(--t3)" }} />
          {STATUS_LABELS[event.status] ?? event.status}
        </span>
      </div>

      <p className="truncate text-sm font-semibold" style={{ color: "var(--t1)" }}>
        {data.label}
      </p>
      <p className="mt-1 line-clamp-2 min-h-8 text-xs leading-relaxed" style={{ color: "var(--t2)" }}>
        {data.description}
      </p>

      <div className="mt-3 flex items-center justify-between text-[10px] font-mono" style={{ color: "var(--t3)" }}>
        <span className="truncate pr-2">{event.node_id || event.id}</span>
        <div className="flex flex-shrink-0 items-center gap-2">
          {tokenCount > 0 && (
            <svg className="h-3.5 w-[48px] overflow-visible" style={{ stroke: accent, strokeWidth: 1.5, fill: "none" }}>
              <polyline points={points} />
            </svg>
          )}
          <span className="font-semibold" style={{ color: "var(--t2)" }}>
            {tokenCount} tok
          </span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{ background: "var(--bg-elevated)", width: 9, height: 9, border: `1px solid ${accent}` }}
      />
    </button>
  );
}
