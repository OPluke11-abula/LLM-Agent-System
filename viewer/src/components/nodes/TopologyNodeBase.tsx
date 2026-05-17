import { Handle, Position, type NodeProps } from "reactflow";
import type { TopologyNodeData, TopologyNodeType } from "../../types";
import { NODE_COLORS } from "../../utils/topologyUtils";

const STATUS_LABELS = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  error: "Error",
  awaiting_approval: "Awaiting approval",
} as const;

type TopologyNodeBaseProps = NodeProps<TopologyNodeData> & {
  tone: TopologyNodeType;
  badge: string;
};

export function TopologyNodeBase({ data, selected, tone, badge }: TopologyNodeBaseProps) {
  const event = data.event;
  const color = NODE_COLORS[tone];
  const isLive = event.status === "running" || event.status === "awaiting_approval";
  const isHitl = event.node_type === "hitl_gate";

  return (
    <button
      type="button"
      onClick={() => data.onOpen(event)}
      className={`group relative w-[260px] rounded-xl border p-3 text-left shadow-xl backdrop-blur-xl transition-all duration-300 ${
        selected ? "scale-[1.03] ring-2 ring-white/50" : ""
      } ${isHitl ? "topology-hitl-pulse" : ""}`}
      style={{
        background: `linear-gradient(135deg, ${color}33, rgba(15,23,42,0.78))`,
        borderColor: `${color}aa`,
        boxShadow: isLive ? `0 0 24px ${color}38` : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: color, width: 10, height: 10, border: "2px solid #020817" }}
      />
      <div className="mb-2 flex items-center justify-between gap-2">
        <span
          className="rounded-md border px-2 py-1 text-[9px] font-black uppercase tracking-[0.16em]"
          style={{ borderColor: `${color}88`, color }}
        >
          {badge}
        </span>
        <span className="flex items-center gap-1.5 text-[10px] font-bold t2">
          <span className={`h-2 w-2 rounded-full ${isLive ? "animate-ping" : ""}`} style={{ background: color }} />
          {STATUS_LABELS[event.status]}
        </span>
      </div>
      <p className="truncate text-sm font-black t1">{data.label}</p>
      <p className="mt-1 line-clamp-2 min-h-8 text-xs leading-relaxed t2">{data.description}</p>
      <div className="mt-3 flex items-center justify-between text-[10px] font-mono t3">
        <span className="truncate">{event.node_id}</span>
        <span>{event.payload.token_used ?? 0} tok</span>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: color, width: 10, height: 10, border: "2px solid #020817" }}
      />
    </button>
  );
}
