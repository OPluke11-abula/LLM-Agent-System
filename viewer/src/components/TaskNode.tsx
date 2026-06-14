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
      className={`task-node w-[280px] p-4 ${selected ? "task-node-selected" : ""} ${
        data.isHighlighted ? "task-node-selected" : ""
      }`}
      style={{
        opacity: data.isDimmed && !selected ? 0.34 : 1,
        transform: data.isDimmed && !selected ? "scale(0.985)" : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: "var(--bg-elevated)", width: 9, height: 9, border: "1px solid var(--border-strong)" }}
      />

      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="block truncate text-[10px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--t3)" }}>
            {data.id}
          </span>
          <span className={`mt-2 inline-flex rounded-md border px-2 py-0.5 text-[10px] font-semibold ${config.chipClass}`}>
            {data.labels[config.label]}
          </span>
        </div>
        <span className="status-dot mt-1 h-2.5 w-2.5 flex-shrink-0 rounded-full" style={{ background: config.dot }} />
      </div>

      <p className="mb-4 line-clamp-3 text-sm font-medium leading-6" style={{ color: "var(--t1)" }}>
        {data.description}
      </p>

      <select
        value={data.status}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => data.onStatusChange(data.id, event.target.value as TaskStatus)}
        className="field-input w-full cursor-pointer rounded-lg px-2.5 py-2 text-xs font-semibold outline-none"
      >
        <option value="pending">{data.labels.pending}</option>
        <option value="in_progress">{data.labels.inProgress}</option>
        <option value="completed">{data.labels.completed}</option>
      </select>

      {data.ai_feedback && (
        <div
          className="mt-2 rounded-md border px-2 py-1 text-[10px] font-semibold"
          style={{ color: "var(--accent-strong)", borderColor: "var(--border-c)", background: "var(--accent-bg)" }}
        >
          AI note recorded
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        style={{ background: "var(--bg-elevated)", width: 9, height: 9, border: "1px solid var(--border-strong)" }}
      />
    </div>
  );
}

export const TASK_NODE_TYPES = { taskNode: TaskNode };
