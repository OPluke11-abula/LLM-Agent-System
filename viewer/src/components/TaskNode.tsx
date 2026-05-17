import { Handle, Position, type NodeProps } from "reactflow";
import type { TaskNodeData, TaskStatus } from "../types";

export function TaskNode({ data, selected }: NodeProps<TaskNodeData>) {
  const config = {
    completed: {
      card: "border-cyan-500/40",
      bg: "rgba(8,47,73,0.4)",
      glow: "glow-cyan",
      dot: "bg-cyan-400",
      select: "border-cyan-500/40 text-cyan-300",
    },
    in_progress: {
      card: "border-amber-500/50",
      bg: "rgba(69,26,3,0.4)",
      glow: "glow-amber",
      dot: "bg-amber-400 animate-ping",
      select: "border-amber-500/50 text-amber-300",
    },
    pending: {
      card: "border-slate-700/50",
      bg: "rgba(15,23,42,0.4)",
      glow: "",
      dot: "bg-slate-600",
      select: "border-slate-700/50 text-slate-400",
    },
  }[data.status];

  return (
    <div
      className={`w-[280px] rounded-xl border p-4 shadow-xl backdrop-blur-xl transition-all duration-300 ${
        config.card
      } ${config.glow} ${selected ? "scale-[1.04] ring-2 ring-blue-400" : ""} ${data.isHighlighted ? "ring-2 ring-cyan-300/80" : ""}`}
      style={{
        background: config.bg,
        opacity: data.isDimmed && !selected ? 0.28 : 1,
        transform: data.isDimmed && !selected ? "scale(0.98)" : undefined,
        boxShadow: data.isHighlighted
          ? "0 0 0 1px rgba(103,232,249,0.32), 0 0 28px rgba(34,211,238,0.22)"
          : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: "#334155", width: 10, height: 10, border: "2px solid #0f172a" }}
      />
      <div className="mb-2 flex items-start justify-between">
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "var(--t3)" }}>
          {data.id}
        </span>
        <span className={`h-2 w-2 flex-shrink-0 rounded-full ${config.dot}`} />
      </div>
      <p className="mb-3 line-clamp-3 text-sm font-medium leading-relaxed" style={{ color: "var(--t1)" }}>
        {data.description}
      </p>
      <select
        value={data.status}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => data.onStatusChange(data.id, event.target.value as TaskStatus)}
        className={`w-full cursor-pointer rounded-lg border bg-black/30 px-2 py-1.5 text-xs font-bold outline-none backdrop-blur-sm focus:ring-1 focus:ring-blue-500 ${
          config.select
        }`}
      >
        <option value="pending">🟡 {data.labels.pending}</option>
        <option value="in_progress">🔵 {data.labels.inProgress}</option>
        <option value="completed">🟢 {data.labels.completed}</option>
      </select>
      {data.ai_feedback && (
        <div
          className="mt-2 rounded border px-2 py-1 text-[10px] font-semibold"
          style={{ color: "var(--accent)", borderColor: "var(--accent)", background: "var(--accent-bg)" }}
        >
          {data.labels.feedbackBadge}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: "#334155", width: 10, height: 10, border: "2px solid #0f172a" }}
      />
    </div>
  );
}

export const TASK_NODE_TYPES = { taskNode: TaskNode };
