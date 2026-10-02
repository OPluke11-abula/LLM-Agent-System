import type { ActivityLogEntry, Lang, TaskStatus } from "../types";
import { Button, Surface } from "./ui/primitives";

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
      "topology-updated": "拓撲已更新",
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
  ja: {
    title: "リアルタイムアクティビティログ",
    subtitle: "最近の同期とタスク操作",
    clear: "クリア",
    empty: "まだアクティビティはありません",
    tasks: "個のタスク",
    parent: "親タスク",
    events: {
      "workspace-loaded": "ワークスペース読み込み完了",
      "workspace-synced": "メモリ同期完了",
      "topology-updated": "トポロジー更新完了",
      "task-status": "ステータス更新",
      "task-description": "説明更新",
      "task-created": "サブタスク作成",
      "task-deleted": "タスク削除",
      "save-error": "保存失敗",
    },
    status: {
      pending: "保留中",
      in_progress: "進行中",
      completed: "完了",
    },
  },
  fr: {
    title: "Journal d'Activité en Direct",
    subtitle: "Synchronisations et opérations récentes",
    clear: "Effacer",
    empty: "Aucune activité pour le moment",
    tasks: "tâches",
    parent: "parent",
    events: {
      "workspace-loaded": "Espace de travail chargé",
      "workspace-synced": "Fichier mémoire synchronisé",
      "topology-updated": "Topologie mise à jour",
      "task-status": "Statut de tâche modifié",
      "task-description": "Description de tâche modifiée",
      "task-created": "Sous-tâche créée",
      "task-deleted": "Tâche supprimée",
      "save-error": "Échec de l'enregistrement",
    },
    status: {
      pending: "En attente",
      in_progress: "En Cours",
      completed: "Terminé",
    },
  },
};

const TYPE_STYLES: Record<ActivityLogEntry["type"], { dot: string; border: string }> = {
  "workspace-loaded": { dot: "var(--accent)", border: "color-mix(in srgb, var(--accent) 32%, transparent)" },
  "workspace-synced": { dot: "var(--accent-strong)", border: "color-mix(in srgb, var(--accent) 28%, transparent)" },
  "topology-updated": { dot: "var(--accent)", border: "color-mix(in srgb, var(--accent) 30%, transparent)" },
  "task-status": { dot: "var(--warning)", border: "color-mix(in srgb, var(--warning) 34%, transparent)" },
  "task-description": { dot: "var(--t2)", border: "var(--border-c)" },
  "task-created": { dot: "var(--success)", border: "color-mix(in srgb, var(--success) 32%, transparent)" },
  "task-deleted": { dot: "var(--danger)", border: "color-mix(in srgb, var(--danger) 34%, transparent)" },
  "save-error": { dot: "var(--danger)", border: "color-mix(in srgb, var(--danger) 42%, transparent)" },
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
    <Surface as="section" elevated className="flex min-h-0 flex-col overflow-hidden">
      <div className="flex flex-shrink-0 items-start justify-between gap-3 border-b px-4 py-3" style={{ borderColor: "var(--border-c)" }}>
        <div>
          <div className="flex items-center gap-2">
            <span className="status-dot h-2 w-2 rounded-full" style={{ background: "var(--accent)" }} />
            <h3 className="text-sm font-semibold t1">{copy.title}</h3>
          </div>
          <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.14em] t3">{copy.subtitle}</p>
        </div>
        <Button
          type="button"
          onClick={onClear}
          disabled={entries.length === 0}
          variant="quiet"
          className="px-2.5 py-1.5"
        >
          {copy.clear}
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {entries.length === 0 ? (
          <div className="flex h-full min-h-36 items-center justify-center rounded-lg border border-dashed px-4 text-center text-xs font-medium t3" style={{ borderColor: "var(--border-c)" }}>
            {copy.empty}
          </div>
        ) : (
          <div className="space-y-2">
            {entries.map((entry) => {
              const style = TYPE_STYLES[entry.type];

              return (
                <article
                  key={entry.id}
                  className="rounded-lg border px-3 py-2.5"
                  style={{ background: "var(--bg-card)", borderColor: style.border }}
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="status-dot h-2 w-2 flex-shrink-0 rounded-full" style={{ background: style.dot }} />
                      <p className="truncate text-xs font-semibold t1">{copy.events[entry.type]}</p>
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
    </Surface>
  );
}
