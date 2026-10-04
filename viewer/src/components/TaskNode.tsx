import { Handle, Position, type NodeProps } from "reactflow";
import type { TaskNodeData, TaskStatus } from "../types";

const STATUS_CONFIG: Record<
  TaskStatus,
  {
    dot: string;
    chipClass: string;
    label: "pending" | "inProgress" | "completed";
  }
> = {
  pending: {
    dot: "var(--t3)",
    chipClass: "status-pending",
    label: "pending",
  },
  in_progress: {
    dot: "var(--warning)",
    chipClass: "status-progress",
    label: "inProgress",
  },
  completed: {
    dot: "var(--success)",
    chipClass: "status-complete",
    label: "completed",
  },
};

export function TaskNode({ data, selected }: NodeProps<TaskNodeData>) {
  const config = STATUS_CONFIG[data.status];

  return (
    <div
      className={`task-node w-[280px] p-3.5 rounded-lg border bg-[var(--bg-card)] ${
        selected ? "border-[var(--border-strong)] ring-1 ring-[var(--ring)]" : "border-[var(--border-c)]"
      } ${data.isHighlighted ? "border-[var(--accent)]" : ""}`}
      style={{
        opacity: data.isDimmed && !selected ? 0.34 : 1,
        transform: data.isDimmed && !selected ? "scale(0.985)" : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: "var(--bg-elevated)",
          width: 8,
          height: 8,
          border: "1px solid var(--border-strong)",
          borderRadius: 2,
        }}
      />

      <div className="mb-2.5 flex items-start justify-between gap-2.5">
        <div className="min-w-0">
          <span className="block truncate font-mono text-[10px] text-[var(--t3)]">
            {data.id}
          </span>
          <span className={`mt-1 inline-flex rounded border px-1.5 py-0.5 text-[10px] font-medium ${config.chipClass}`}>
            {data.labels[config.label]}
          </span>
        </div>
        <span
          className="mt-1 h-2 w-2 flex-shrink-0 rounded-full"
          style={{ background: config.dot }}
        />
      </div>

      <p className="mb-3 line-clamp-3 text-xs leading-relaxed text-[var(--t1)]">
        {data.description}
      </p>

      <select
        aria-label={`Set status for task ${data.id}`}
        value={data.status}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => data.onStatusChange(data.id, event.target.value as TaskStatus)}
        className="w-full cursor-pointer rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-2.5 py-1.5 text-xs text-[var(--t1)] outline-none hover:border-[var(--border-strong)] focus:border-[var(--border-strong)]"
      >
        <option value="pending">{data.labels.pending}</option>
        <option value="in_progress">{data.labels.inProgress}</option>
        <option value="completed">{data.labels.completed}</option>
      </select>

      {data.ai_feedback && (
        <div
          className="mt-2 rounded border border-[var(--border-c)] bg-[var(--accent-bg)] px-2 py-1 text-[10px] text-[var(--accent-strong)]"
        >
          {data.labels.feedbackBadge}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: "var(--bg-elevated)",
          width: 8,
          height: 8,
          border: "1px solid var(--border-strong)",
          borderRadius: 2,
        }}
      />
    </div>
  );
}
