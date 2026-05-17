import type { ActivityLogEntry, Lang, TaskStatus } from "../types";

type ActivityLogProps = {
  entries: ActivityLogEntry[];
  lang: Lang;
  onClear: () => void;
};

type ActivityLogCopy = {
  title: string;
  subtitle: string;
  clear: string;
  empty: string;
  tasks: string;
  parent: string;
  events: Record<ActivityLogEntry["type"], string>;
  status: Record<TaskStatus, string>;
};

const COPY: Record<Lang, ActivityLogCopy> = {
  zh: {
    title: "即時活動記錄",
    subtitle: "最近的同步與任務操作",
    clear: "清除",
    empty: "尚無活動",
    tasks: "個任務",
    parent: "父任務",
    events: {
      "workspace-loaded": "工作區已載入",
      "workspace-synced": "記憶檔已同步",
      "topology-updated": "Topology updated",
      "task-status": "任務狀態更新",
      "task-description": "任務描述更新",
      "task-created": "新增子任務",
      "task-deleted": "刪除任務",
      "save-error": "寫入失敗",
    },
    status: {
      pending: "待處理",
      in_progress: "進行中",
      completed: "已完成",
    },
  },
  en: {
    title: "Live Activity Log",
    subtitle: "Recent sync and task activity",
    clear: "Clear",
    empty: "No activity yet",
    tasks: "tasks",
    parent: "parent",
    events: {
      "workspace-loaded": "Workspace loaded",
      "workspace-synced": "Memory file synced",
      "topology-updated": "Topology updated",
      "task-status": "Task status changed",
      "task-description": "Task description updated",
      "task-created": "Subtask created",
      "task-deleted": "Task deleted",
      "save-error": "Save failed",
    },
    status: {
      pending: "Pending",
      in_progress: "In Progress",
      completed: "Completed",
    },
  },
};

const TYPE_STYLES: Record<ActivityLogEntry["type"], { dot: string; border: string }> = {
  "workspace-loaded": { dot: "#38bdf8", border: "rgba(56,189,248,0.34)" },
  "workspace-synced": { dot: "#22d3ee", border: "rgba(34,211,238,0.34)" },
  "topology-updated": { dot: "#378ADD", border: "rgba(55,138,221,0.38)" },
  "task-status": { dot: "#f59e0b", border: "rgba(245,158,11,0.36)" },
  "task-description": { dot: "#a78bfa", border: "rgba(167,139,250,0.34)" },
  "task-created": { dot: "#22c55e", border: "rgba(34,197,94,0.34)" },
  "task-deleted": { dot: "#fb7185", border: "rgba(251,113,133,0.36)" },
  "save-error": { dot: "#ef4444", border: "rgba(239,68,68,0.42)" },
};

function formatTime(timestamp: string, lang: Lang) {
  return new Intl.DateTimeFormat(lang === "zh" ? "zh-TW" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(timestamp));
}

function formatDetail(entry: ActivityLogEntry, copy: ActivityLogCopy) {
  if (entry.type === "topology-updated") {
    return [entry.workspaceName, entry.detail].filter(Boolean).join(" | ");
  }

  if (entry.type === "task-status") {
    const fromStatus = entry.fromStatus ? copy.status[entry.fromStatus] : "";
    const toStatus = entry.toStatus ? copy.status[entry.toStatus] : "";
    return [entry.taskId, `${fromStatus} -> ${toStatus}`, entry.taskDescription].filter(Boolean).join(" · ");
  }

  if (entry.type === "task-created") {
    return [entry.taskId, entry.parentTaskId ? `${copy.parent} ${entry.parentTaskId}` : "", entry.taskDescription]
      .filter(Boolean)
      .join(" · ");
  }

  if (entry.type === "task-deleted") {
    return [entry.taskId, entry.removedCount ? `${entry.removedCount} ${copy.tasks}` : ""].filter(Boolean).join(" · ");
  }

  if (entry.type === "workspace-loaded" || entry.type === "workspace-synced") {
    return [entry.workspaceName, entry.taskCount !== undefined ? `${entry.taskCount} ${copy.tasks}` : "", entry.detail]
      .filter(Boolean)
      .join(" · ");
  }

  return entry.detail ?? entry.taskDescription ?? entry.workspaceName;
}

export function ActivityLog({ entries, lang, onClear }: ActivityLogProps) {
  const copy = COPY[lang];

  return (
    <section
      className="panel-bg flex min-h-0 flex-col rounded-2xl border shadow-xl"
      style={{ borderColor: "var(--border-c)" }}
    >
      <div className="flex flex-shrink-0 items-start justify-between gap-3 border-b px-4 py-3" style={{ borderColor: "var(--border-c)" }}>
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: "var(--accent)", boxShadow: "0 0 12px var(--accent)" }} />
            <h3 className="text-sm font-black t1">{copy.title}</h3>
          </div>
          <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] t3">{copy.subtitle}</p>
        </div>
        <button
          type="button"
          onClick={onClear}
          disabled={entries.length === 0}
          className="rounded-lg border px-2.5 py-1.5 text-xs font-bold transition-all disabled:cursor-not-allowed disabled:opacity-40"
          style={{ borderColor: "var(--border-c)", color: "var(--t2)", background: "var(--bg-card)" }}
        >
          {copy.clear}
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {entries.length === 0 ? (
          <div className="flex h-full min-h-36 items-center justify-center rounded-xl border border-dashed px-4 text-center text-xs font-semibold t3" style={{ borderColor: "var(--border-c)" }}>
            {copy.empty}
          </div>
        ) : (
          <div className="space-y-2">
            {entries.map((entry) => {
              const style = TYPE_STYLES[entry.type];

              return (
                <article
                  key={entry.id}
                  className="rounded-xl border px-3 py-2.5"
                  style={{ background: "var(--bg-card)", borderColor: style.border }}
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="h-2 w-2 flex-shrink-0 rounded-full" style={{ background: style.dot }} />
                      <p className="truncate text-xs font-black t1">{copy.events[entry.type]}</p>
                    </div>
                    <time className="flex-shrink-0 text-[10px] font-mono t3">{formatTime(entry.timestamp, lang)}</time>
                  </div>
                  <p className="line-clamp-2 text-xs leading-relaxed t2">{formatDetail(entry, copy)}</p>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
