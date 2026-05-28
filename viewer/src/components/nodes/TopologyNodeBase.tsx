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

export function TopologyNodeBase({ data, selected, tone, badge }: TopologyNodeBaseProps) {
  const event = data.event;
  const color = NODE_COLORS[tone];
  const isLive = event.status === "running" || event.status === "awaiting_approval" || event.status === "in_process" || event.status === "review";
  const isHitl = event.node_type === "hitl_gate";

  // Dynamic color-coding based on active model (Task 8-02)
  const model = String(event.payload?.model || event.payload?.active_model || "").toLowerCase();
  let modelBorderColor: string = color;
  if (model.includes("gemini")) {
    modelBorderColor = "#1a73e8"; // Gemini Blue
  } else if (model.includes("claude") || model.includes("anthropic")) {
    modelBorderColor = "#f97316"; // Claude Orange
  } else if (model.includes("gpt") || model.includes("openai")) {
    modelBorderColor = "#22c55e"; // GPT Green
  }

  // Cumulative token cost history SVG sparkline chart (Task 8-02)
  const tokenCount = Number(event.payload?.token_used ?? event.payload?.tokens ?? 0);
  const costVal = tokenCount * 0.00002;
  const historyLength = 6;
  const hash = (event.node_id || event.id || "").charCodeAt(0) || 1;
  const costHistory = Array.from({ length: historyLength }, (_, i) => {
    const progress = (i + 1) / historyLength;
    return costVal * (progress * 0.75 + 0.25) * (1 + Math.sin(hash + i) * 0.08);
  });

  const points = costHistory.map((val, idx) => {
    const x = (idx / (costHistory.length - 1)) * 48; // 48px width
    const maxVal = Math.max(...costHistory, 0.0001);
    const y = 13 - (val / maxVal) * 10; // 13px height
    return `${x},${y}`;
  }).join(" ");

  return (
    <button
      type="button"
      onClick={() => data.onOpen(event)}
      className={`group relative w-[260px] rounded-xl border p-3.5 text-left shadow-xl backdrop-blur-xl transition-all duration-300 ${
        selected ? "scale-[1.03] ring-2 ring-white/50" : ""
      } ${isHitl ? "topology-hitl-pulse" : ""} ${isLive ? "active-streaming-node" : ""}`}
      style={{
        background: `linear-gradient(135deg, ${color}1e, rgba(15,23,42,0.85))`,
        borderColor: selected ? "#ffffff" : `${modelBorderColor}aa`,
        boxShadow: isLive ? `0 0 24px ${modelBorderColor}48` : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: modelBorderColor, width: 10, height: 10, border: "2px solid #020817" }}
      />
      <div className="mb-2 flex items-center justify-between gap-2">
        <span
          className="rounded-md border px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.16em]"
          style={{ borderColor: `${modelBorderColor}88`, color: modelBorderColor }}
        >
          {badge}
        </span>
        <span className="flex items-center gap-1.5 text-[10px] font-bold t2">
          <span className={`h-2 w-2 rounded-full ${isLive ? "animate-ping" : ""}`} style={{ background: modelBorderColor }} />
          {STATUS_LABELS[event.status]}
        </span>
      </div>
      <p className="truncate text-sm font-black t1">{data.label}</p>
      <p className="mt-1 line-clamp-2 min-h-8 text-xs leading-relaxed t2">{data.description}</p>
      <div className="mt-3 flex items-center justify-between text-[10px] font-mono t3">
        <span className="truncate pr-2">{event.node_id || event.id}</span>
        <div className="flex items-center gap-2 flex-shrink-0">
          {tokenCount > 0 && (
            <svg className="h-3.5 w-[48px] overflow-visible" style={{ stroke: modelBorderColor, strokeWidth: 1.5, fill: "none" }}>
              <polyline points={points} />
            </svg>
          )}
          <span className="t2 font-bold">{tokenCount} tok</span>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: modelBorderColor, width: 10, height: 10, border: "2px solid #020817" }}
      />
    </button>
  );
}
