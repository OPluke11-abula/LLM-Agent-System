import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  BackgroundVariant,
  ReactFlow,
  type ReactFlowInstance,
  useEdgesState,
  useNodesState,
  type Node,
} from "reactflow";
import { buildFlow, flattenTasks } from "../utils/graphUtils";
import {
  buildExportFilename,
  buildMemoryJsonExport,
  buildMemoryMarkdownExport,
  downloadTextFile,
} from "../utils/exportUtils";
import { Modal } from "./Modal";
import { ContextMenu } from "./ContextMenu";
import { ActivityLog } from "./ActivityLog";
import { TASK_NODE_TYPES } from "./TaskNode";
import type {
  ActivityLogEntry,
  AgentMemory,
  Lang,
  TaskNodeData,
  TaskNodeLabels,
  TaskStatus,
  TranslationMessages,
  Workspace,
} from "../types";

type TaskFlowViewProps = {
  memory: AgentMemory;
  workspaces: Workspace[];
  activeWorkspaceId: string;
  setActiveWorkspaceId: (id: string) => void;
  onStatusChange: (id: string, status: TaskStatus) => void;
  onDescriptionChange: (id: string, description: string) => Promise<void>;
  onAddSubtask: (parentId: string, description: string) => Promise<void>;
  onDeleteTask: (id: string) => Promise<void>;
  activityEntries: ActivityLogEntry[];
  onClearActivityLog: () => void;
  t: TranslationMessages;
  lang: Lang;
};

type FilterStatus = "all" | TaskStatus;

type ContextMenuState = {
  x: number;
  y: number;
  taskId: string;
};

type DraftState = {
  taskId: string;
  description: string;
};

type LocalizedCopy = {
  total: string;
  inProgress: string;
  pending: string;
  completionRate: string;
  searchPlaceholder: string;
  matchingCount: string;
  filters: Record<FilterStatus, string>;
  searchLabel: string;
  editDescription: string;
  addSubtask: string;
  copyTaskId: string;
  markInProgress: string;
  markCompleted: string;
  deleteTask: string;
  editTitle: string;
  addTitle: string;
  deleteTitle: string;
  deleteConfirm: string;
  descriptionPlaceholder: string;
  subtaskPlaceholder: string;
  save: string;
  create: string;
  noMatches: string;
  exportLabel: string;
  exportJson: string;
  exportMarkdown: string;
  exportedJson: string;
  exportedMarkdown: string;
  exportTitle: string;
  exportWorkspace: string;
  exportGeneratedAt: string;
  exportDependencies: string;
  exportNoTasks: string;
};

const LOCAL_COPY: Record<Lang, LocalizedCopy> = {
  zh: {
    total: "總任務",
    inProgress: "進行中",
    pending: "待處理",
    completionRate: "完成率",
    searchPlaceholder: "搜尋任務 ID、描述或 AI 回饋...",
    matchingCount: "符合條件",
    filters: {
      all: "全部",
      pending: "待處理",
      in_progress: "進行中",
      completed: "已完成",
    },
    searchLabel: "搜尋與篩選",
    editDescription: "編輯描述",
    addSubtask: "新增子任務",
    copyTaskId: "複製任務 ID",
    markInProgress: "標記為進行中",
    markCompleted: "標記為已完成",
    deleteTask: "刪除任務",
    editTitle: "編輯任務描述",
    addTitle: "新增子任務",
    deleteTitle: "刪除任務",
    deleteConfirm: "確定要刪除這個任務與其所有子任務嗎？",
    descriptionPlaceholder: "輸入任務描述...",
    subtaskPlaceholder: "輸入子任務描述...",
    save: "儲存",
    create: "新增",
    noMatches: "目前沒有符合搜尋與篩選條件的任務。",
    exportLabel: "匯出",
    exportJson: "JSON",
    exportMarkdown: "Markdown",
    exportedJson: "已匯出 JSON",
    exportedMarkdown: "已匯出 Markdown",
    exportTitle: "任務流程匯出",
    exportWorkspace: "工作區",
    exportGeneratedAt: "匯出時間",
    exportDependencies: "依賴項目",
    exportNoTasks: "目前沒有任務。",
  },
  en: {
    total: "Total Tasks",
    inProgress: "In Progress",
    pending: "Pending",
    completionRate: "Completion",
    searchPlaceholder: "Search by task ID, description, or AI note...",
    matchingCount: "Matching",
    filters: {
      all: "All",
      pending: "Pending",
      in_progress: "In Progress",
      completed: "Completed",
    },
    searchLabel: "Search & Filter",
    editDescription: "Edit description",
    addSubtask: "Add subtask",
    copyTaskId: "Copy task ID",
    markInProgress: "Mark in progress",
    markCompleted: "Mark completed",
    deleteTask: "Delete task",
    editTitle: "Edit Task Description",
    addTitle: "Add Subtask",
    deleteTitle: "Delete Task",
    deleteConfirm: "Delete this task and all of its subtasks?",
    descriptionPlaceholder: "Enter a task description...",
    subtaskPlaceholder: "Enter a subtask description...",
    save: "Save",
    create: "Create",
    noMatches: "No tasks match the current search and filter.",
    exportLabel: "Export",
    exportJson: "JSON",
    exportMarkdown: "Markdown",
    exportedJson: "JSON exported",
    exportedMarkdown: "Markdown exported",
    exportTitle: "Task Flow Export",
    exportWorkspace: "Workspace",
    exportGeneratedAt: "Generated at",
    exportDependencies: "Dependencies",
    exportNoTasks: "No tasks yet.",
  },
  ja: {
    total: "総タスク",
    inProgress: "進行中",
    pending: "保留中",
    completionRate: "進捗率",
    searchPlaceholder: "タスクID、説明、またはAIフィードバックで検索...",
    matchingCount: "一致件数",
    filters: {
      all: "すべて",
      pending: "保留中",
      in_progress: "進行中",
      completed: "完了",
    },
    searchLabel: "検索とフィルター",
    editDescription: "説明の編集",
    addSubtask: "サブタスクを追加",
    copyTaskId: "タスクIDをコピー",
    markInProgress: "進行中にマーク",
    markCompleted: "完了にマーク",
    deleteTask: "タスクを削除",
    editTitle: "タスク説明の編集",
    addTitle: "サブタスクの追加",
    deleteTitle: "タスクの削除",
    deleteConfirm: "このタスクとすべてのサブタスクを削除してもよろしいですか？",
    descriptionPlaceholder: "タスクの説明を入力...",
    subtaskPlaceholder: "サブタスクの説明を入力...",
    save: "保存",
    create: "作成",
    noMatches: "現在、条件に一致するタスクはありません。",
    exportLabel: "エクスポート",
    exportJson: "JSON",
    exportMarkdown: "Markdown",
    exportedJson: "JSONエクスポート完了",
    exportedMarkdown: "Markdownエクスポート完了",
    exportTitle: "タスクフローエクスポート",
    exportWorkspace: "ワークスペース",
    exportGeneratedAt: "出力時間",
    exportDependencies: "依存関係",
    exportNoTasks: "タスクはありません。",
  },
  fr: {
    total: "Total Tâches",
    inProgress: "En Cours",
    pending: "En Attente",
    completionRate: "Complétion",
    searchPlaceholder: "Rechercher par ID, description ou retour IA...",
    matchingCount: "Correspondance",
    filters: {
      all: "Tout",
      pending: "En attente",
      in_progress: "En Cours",
      completed: "Terminé",
    },
    searchLabel: "Recherche & Filtres",
    editDescription: "Modifier la description",
    addSubtask: "Ajouter une sous-tâche",
    copyTaskId: "Copier l'ID de la tâche",
    markInProgress: "Marquer en cours",
    markCompleted: "Marquer terminé",
    deleteTask: "Supprimer la tâche",
    editTitle: "Modifier la Description de la Tâche",
    addTitle: "Ajouter une Sous-Tâche",
    deleteTitle: "Supprimer la Tâche",
    deleteConfirm: "Supprimer cette tâche et toutes ses sous-tâches ?",
    descriptionPlaceholder: "Entrer la description de la tâche...",
    subtaskPlaceholder: "Entrer la description de la sous-tâche...",
    save: "Enregistrer",
    create: "Créer",
    noMatches: "Aucune tâche ne correspond à la recherche et aux filtres actuels.",
    exportLabel: "Exporter",
    exportJson: "JSON",
    exportMarkdown: "Markdown",
    exportedJson: "JSON exporté",
    exportedMarkdown: "Markdown exporté",
    exportTitle: "Export du Flux de Tâches",
    exportWorkspace: "Espace de travail",
    exportGeneratedAt: "Généré le",
    exportDependencies: "Dépendances",
    exportNoTasks: "Aucune tâche.",
  },
};

function buildVisualState(
  memory: AgentMemory,
  filter: FilterStatus,
  search: string,
) {
  const query = search.trim().toLowerCase();
  const flatTasks = flattenTasks(memory.tasks);

  return Object.fromEntries(
    flatTasks.map((task) => {
      const statusMatch = filter === "all" || task.status === filter;
      const haystack = `${task.id} ${task.description} ${task.ai_feedback ?? ""}`.toLowerCase();
      const searchMatch = query === "" || haystack.includes(query);

      return [
        task.id,
        {
          isHighlighted: query !== "" && statusMatch && searchMatch,
          isDimmed: !(statusMatch && searchMatch),
        },
      ];
    }),
  );
}

export function TaskFlowView({
  memory,
  workspaces,
  activeWorkspaceId,
  setActiveWorkspaceId,
  onStatusChange,
  onDescriptionChange,
  onAddSubtask,
  onDeleteTask,
  activityEntries,
  onClearActivityLog,
  t,
  lang,
}: TaskFlowViewProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<TaskNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const flowContainerRef = useRef<HTMLDivElement | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [filter, setFilter] = useState<FilterStatus>("all");
  const [search, setSearch] = useState("");
  const [flowInstance, setFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [editDraft, setEditDraft] = useState<DraftState | null>(null);
  const [subtaskDraft, setSubtaskDraft] = useState<DraftState | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const local = LOCAL_COPY[lang];
  const activeWorkspace = workspaces.find((workspace) => workspace.id === activeWorkspaceId);
  const labels: TaskNodeLabels = {
    pending: t.pending,
    inProgress: t.inProgress,
    completed: t.completed,
    feedbackBadge: t.feedbackBadge,
  };

  const flatTasks = flattenTasks(memory.tasks);
  const total = flatTasks.length;
  const completed = flatTasks.filter((task) => task.status === "completed").length;
  const inProgress = flatTasks.filter((task) => task.status === "in_progress").length;
  const pending = flatTasks.filter((task) => task.status === "pending").length;
  const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;
  const query = search.trim().toLowerCase();
  const matchedTasks = flatTasks.filter((task) => {
    const statusMatch = filter === "all" || task.status === filter;
    const haystack = `${task.id} ${task.description} ${task.ai_feedback ?? ""}`.toLowerCase();
    const searchMatch = query === "" || haystack.includes(query);
    return statusMatch && searchMatch;
  });
  const flowLayoutKey = useMemo(
    () =>
      [
        activeWorkspaceId,
        nodes.map((node) => `${node.id}:${node.position.x},${node.position.y}`).join("|"),
        edges.map((edge) => `${edge.source}>${edge.target}`).join("|"),
      ].join("::"),
    [activeWorkspaceId, edges, nodes],
  );
  const fitFlowToView = useCallback(
    (duration = 0) => {
      const container = flowContainerRef.current;

      if (!flowInstance || nodes.length === 0 || !container || container.clientWidth === 0 || container.clientHeight === 0) {
        return;
      }

      if (nodes.length > 5) {
        const zoom = 0.55;
        const minX = Math.min(...nodes.map((node) => node.position.x));
        const minY = Math.min(...nodes.map((node) => node.position.y));
        const maxY = Math.max(...nodes.map((node) => node.position.y + 155));
        const graphCenterY = (minY + maxY) / 2;

        void flowInstance.setViewport(
          {
            x: 40 - minX * zoom,
            y: container.clientHeight / 2 - graphCenterY * zoom,
            zoom,
          },
          { duration },
        );
        return;
      }

      void flowInstance.fitView({
        padding: 0.14,
        duration,
        includeHiddenNodes: true,
        minZoom: 0.55,
        maxZoom: 1.05,
      });
    },
    [flowInstance, nodes],
  );

  useEffect(() => {
    const visualState = buildVisualState(memory, filter, search);
    const flow = buildFlow(memory, labels, onStatusChange, visualState);
    setNodes(flow.nodes);
    setEdges(flow.edges);
  }, [
    filter,
    labels.completed,
    labels.feedbackBadge,
    labels.inProgress,
    labels.pending,
    memory,
    onStatusChange,
    search,
    setEdges,
    setNodes,
  ]);

  useEffect(() => {
    if (selectedTaskId && !nodes.some((node) => node.id === selectedTaskId)) {
      setSelectedTaskId(null);
    }
  }, [nodes, selectedTaskId]);

  useEffect(() => {
    const animationFrame = window.requestAnimationFrame(() => fitFlowToView(0));
    const timeoutIds = [80, 240].map((delay) => window.setTimeout(() => fitFlowToView(160), delay));

    return () => {
      window.cancelAnimationFrame(animationFrame);
      timeoutIds.forEach((timeoutId) => window.clearTimeout(timeoutId));
    };
  }, [fitFlowToView, flowLayoutKey]);

  useEffect(() => {
    const container = flowContainerRef.current;

    if (!container || typeof ResizeObserver === "undefined") {
      return;
    }

    let animationFrame = 0;
    const observer = new ResizeObserver(() => {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = window.requestAnimationFrame(() => fitFlowToView(120));
    });

    observer.observe(container);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      observer.disconnect();
    };
  }, [fitFlowToView]);

  const selectedTask = selectedTaskId
    ? nodes.find((node) => node.id === selectedTaskId)?.data ?? null
    : null;

  const contextTask = contextMenu
    ? flatTasks.find((task) => task.id === contextMenu.taskId) ?? null
    : null;

  function copyText(text: string) {
    void navigator.clipboard.writeText(text);
  }

  async function submitDescriptionChange() {
    if (!editDraft?.description.trim()) {
      return;
    }

    await onDescriptionChange(editDraft.taskId, editDraft.description.trim());
    setEditDraft(null);
  }

  async function submitSubtask() {
    if (!subtaskDraft?.description.trim()) {
      return;
    }

    await onAddSubtask(subtaskDraft.taskId, subtaskDraft.description.trim());
    setSubtaskDraft(null);
  }

  async function confirmDeleteTask() {
    if (!deleteTargetId) {
      return;
    }

    await onDeleteTask(deleteTargetId);
    if (selectedTaskId === deleteTargetId) {
      setSelectedTaskId(null);
    }
    setDeleteTargetId(null);
  }

  function handleExport(format: "json" | "markdown") {
    const generatedAt = new Date();
    const filename = buildExportFilename(activeWorkspace, format, generatedAt);

    if (format === "json") {
      downloadTextFile(
        filename,
        buildMemoryJsonExport(memory, activeWorkspace, generatedAt),
        "application/json;charset=utf-8",
      );
      setExportStatus(local.exportedJson);
    } else {
      downloadTextFile(
        filename,
        buildMemoryMarkdownExport(memory, activeWorkspace, {
          generatedAt,
          statusLabels: {
            pending: t.pending,
            in_progress: t.inProgress,
            completed: t.completed,
          },
          statsLabels: {
            title: local.exportTitle,
            workspace: local.exportWorkspace,
            generatedAt: local.exportGeneratedAt,
            total: local.total,
            pending: local.pending,
            inProgress: local.inProgress,
            completed: t.completed,
            completionRate: local.completionRate,
            dependencies: local.exportDependencies,
            aiFeedback: t.aiFeedback,
            noTasks: local.exportNoTasks,
          },
        }),
        "text/markdown;charset=utf-8",
      );
      setExportStatus(local.exportedMarkdown);
    }

    window.setTimeout(() => setExportStatus(null), 2200);
  }

  const stats = [
    { value: total, label: local.total },
    { value: inProgress, label: local.inProgress },
    { value: pending, label: local.pending },
    { value: `${completionRate}%`, label: local.completionRate },
  ];

  const contextItems = contextTask
    ? [
        {
          id: "edit",
          label: local.editDescription,
          onClick: () => {
            setEditDraft({ taskId: contextTask.id, description: contextTask.description });
            setContextMenu(null);
          },
        },
        {
          id: "add-subtask",
          label: local.addSubtask,
          onClick: () => {
            setSubtaskDraft({ taskId: contextTask.id, description: "" });
            setContextMenu(null);
          },
        },
        {
          id: "copy-id",
          label: local.copyTaskId,
          onClick: () => {
            copyText(contextTask.id);
            setContextMenu(null);
          },
        },
        {
          id: "mark-progress",
          label: local.markInProgress,
          onClick: () => {
            void onStatusChange(contextTask.id, "in_progress");
            setContextMenu(null);
          },
        },
        {
          id: "mark-complete",
          label: local.markCompleted,
          onClick: () => {
            void onStatusChange(contextTask.id, "completed");
            setContextMenu(null);
          },
        },
        {
          id: "delete",
          label: local.deleteTask,
          tone: "danger" as const,
          separatorBefore: true,
          onClick: () => {
            setDeleteTargetId(contextTask.id);
            setContextMenu(null);
          },
        },
      ]
    : [];

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto xl:overflow-hidden">
      {workspaces.length > 0 && (
        <div className="flex flex-shrink-0 flex-wrap gap-2">
          {workspaces.map((workspace) => (
            <button
              key={workspace.id}
              type="button"
              onClick={() => setActiveWorkspaceId(workspace.id)}
              className={`flex flex-col items-start rounded-lg px-3 py-2 text-xs font-semibold ${
                workspace.id === activeWorkspaceId ? "primary-button" : "quiet-button"
              }`}
              style={
                workspace.id === activeWorkspaceId
                  ? { color: "var(--accent-strong)" }
                  : { color: "var(--t3)" }
              }
            >
              <span>
                {workspace.name} · {workspace.lang}
              </span>
              {workspace.path && (
                <span className="mt-0.5 font-mono opacity-60" style={{ fontSize: "9px" }}>
                  {workspace.path}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="metric-card p-4"
          >
            <p className="text-2xl font-semibold tracking-tight" style={{ color: "var(--t1)" }}>
              {stat.value}
            </p>
            <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.14em] t3">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="control-surface flex flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] t3">{local.searchLabel}</p>
          <div className="flex flex-wrap items-center justify-end gap-2">
            {exportStatus && <p className="text-xs font-semibold" style={{ color: "var(--accent)" }}>{exportStatus}</p>}
            <p className="text-xs t2">
              {local.matchingCount} {matchedTasks.length} / {total}
            </p>
            <div className="flex flex-wrap items-center gap-1.5 rounded-lg border p-1" style={{ borderColor: "var(--border-c)", background: "var(--bg-card)" }}>
              <span className="hidden px-2 text-[10px] font-semibold uppercase tracking-[0.14em] t3 sm:inline">{local.exportLabel}</span>
              <button
                type="button"
                onClick={() => handleExport("json")}
                className="primary-button rounded-md px-2.5 py-1.5 text-xs font-semibold"
              >
                {local.exportJson}
              </button>
              <button
                type="button"
                onClick={() => handleExport("markdown")}
                className="quiet-button rounded-md px-2.5 py-1.5 text-xs font-semibold"
              >
                <span className="hidden sm:inline">{local.exportMarkdown}</span>
                <span className="sm:hidden">MD</span>
              </button>
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={local.searchPlaceholder}
            className="field-input w-full rounded-lg px-4 py-3 text-sm outline-none"
          />
          <div className="flex flex-wrap gap-2">
            {(["all", "pending", "in_progress", "completed"] as FilterStatus[]).map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setFilter(status)}
                className={`rounded-lg px-3 py-2 text-xs font-semibold ${filter === status ? "primary-button" : "quiet-button"}`}
                style={
                  filter === status
                    ? { color: "var(--accent-strong)" }
                    : { color: "var(--t2)" }
                }
              >
                {local.filters[status]}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)_160px] gap-3 2xl:grid-cols-[minmax(0,1fr)_320px] 2xl:grid-rows-none">
        <div
          ref={flowContainerRef}
          className="flow-canvas relative min-h-[320px] overflow-hidden rounded-lg border shadow-2xl xl:min-h-0"
          style={{ borderColor: "var(--border-c)" }}
        >
        {memory.tasks.length === 0 && (
          <div className="pointer-events-none absolute inset-0 z-10 flex flex-col items-center justify-center px-6 text-center">
            <div className="mb-4 text-5xl opacity-20">⬡</div>
            <p className="text-sm font-bold opacity-30" style={{ color: "var(--t2)" }}>
              {lang === "zh"
                ? "此工作區尚無任務。在設定中指定 JSON 路徑，或讓 AI 代理寫入資料。"
                : "No tasks in this workspace yet. Set the JSON path in Settings or let an AI agent write data."}
            </p>
          </div>
        )}

        {memory.tasks.length > 0 && matchedTasks.length === 0 && (
          <div
            className="absolute top-4 left-1/2 z-20 -translate-x-1/2 rounded-full border px-4 py-2 text-xs font-semibold shadow-xl"
            style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)", color: "var(--t2)" }}
          >
            {local.noMatches}
          </div>
        )}

        <ReactFlow
          className="h-full w-full"
          nodes={nodes}
          edges={edges}
          onInit={setFlowInstance}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={(_, node: Node<TaskNodeData>) => {
            setSelectedTaskId(node.id);
            setContextMenu(null);
          }}
          onNodeContextMenu={(event, node: Node<TaskNodeData>) => {
            event.preventDefault();
            setSelectedTaskId(node.id);
            setContextMenu({
              x: event.clientX,
              y: event.clientY,
              taskId: node.id,
            });
          }}
          onPaneClick={() => {
            setSelectedTaskId(null);
            setContextMenu(null);
          }}
          fitView
          minZoom={0.55}
          maxZoom={1.4}
          fitViewOptions={{
            padding: 0.14,
            includeHiddenNodes: true,
            minZoom: 0.55,
            maxZoom: 1.05,
          }}
          nodeTypes={TASK_NODE_TYPES}
        >
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="var(--grid)" />
        </ReactFlow>

        <aside
          className={`absolute top-0 right-0 flex h-full w-80 flex-col border-l shadow-2xl transition-transform duration-300 ease-out ${
            selectedTask ? "translate-x-0" : "translate-x-full"
          }`}
          style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}
        >
          {selectedTask && (
            <>
              <div
                className="flex flex-shrink-0 items-center justify-between border-b px-5 pt-5 pb-4"
                style={{ borderColor: "var(--border-c)" }}
              >
                <h3 className="text-sm font-semibold" style={{ color: "var(--t1)" }}>
                  {t.taskDetails}
                </h3>
                <button
                  type="button"
                  onClick={() => setSelectedTaskId(null)}
                  className="quiet-button flex h-7 w-7 items-center justify-center rounded-md text-sm"
                  style={{ background: "var(--bg-card)" }}
                >
                  ✕
                </button>
              </div>
              <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
                <div>
                  <label className="t3 text-[9px] font-bold uppercase tracking-widest">{t.taskId}</label>
                  <div
                    className="mt-1 rounded-lg border px-3 py-2 text-xs font-mono"
                    style={{ background: "var(--bg-card)", borderColor: "var(--border-c)", color: "var(--accent-strong)" }}
                  >
                    {selectedTask.id}
                  </div>
                </div>
                <div>
                  <label className="t3 text-[9px] font-bold uppercase tracking-widest">{t.desc}</label>
                  <p className="mt-1 text-sm leading-relaxed t1">{selectedTask.description}</p>
                </div>
                <div>
                  <label className="t3 text-[9px] font-bold uppercase tracking-widest">{t.deps}</label>
                  {selectedTask.dependencies.length > 0 ? (
                    <ul className="mt-2 space-y-1">
                      {selectedTask.dependencies.map((dependency) => {
                        const depId = typeof dependency === "string" ? dependency : dependency.id;
                        const category = typeof dependency === "string" ? "" : ` (${dependency.category})`;
                        return (
                          <li
                            key={depId}
                            className="rounded-lg border px-3 py-1.5 text-xs font-mono"
                            style={{ background: "var(--bg-card)", color: "var(--accent-strong)", borderColor: "var(--border-c)" }}
                          >
                            {depId}{category}
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p className="mt-1 text-xs italic t3">{t.noDeps}</p>
                  )}
                </div>
                {selectedTask.ai_feedback && (
                  <div>
                    <div className="flex items-center justify-between gap-3">
                      <label className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
                        {t.aiFeedback}
                      </label>
                      <button
                        type="button"
                        onClick={() => copyText(selectedTask.ai_feedback ?? "")}
                        className="quiet-button rounded-md px-2 py-1 text-xs"
                        title={t.copy}
                      >
                        {t.copy}
                      </button>
                    </div>
                    <div className="mt-2 rounded-lg border p-4" style={{ background: "var(--accent-bg)", borderColor: "var(--border-c)" }}>
                      <p className="text-xs leading-relaxed" style={{ color: "var(--t1)", whiteSpace: "pre-wrap" }}>
                        {selectedTask.ai_feedback}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </aside>

          {contextMenu && <ContextMenu x={contextMenu.x} y={contextMenu.y} items={contextItems} onClose={() => setContextMenu(null)} />}
        </div>

        <ActivityLog entries={activityEntries} lang={lang} onClear={onClearActivityLog} />
      </div>

      {editDraft && (
        <Modal
          title={local.editTitle}
          onConfirm={() => void submitDescriptionChange()}
          onCancel={() => setEditDraft(null)}
          confirmText={local.save}
          cancelText={t.cancel}
        >
          <textarea
            autoFocus
            rows={4}
            value={editDraft.description}
            onChange={(event) => setEditDraft({ ...editDraft, description: event.target.value })}
            placeholder={local.descriptionPlaceholder}
            className="field-input w-full resize-none rounded-lg p-3 text-sm focus:outline-none t1"
          />
        </Modal>
      )}

      {subtaskDraft && (
        <Modal
          title={local.addTitle}
          onConfirm={() => void submitSubtask()}
          onCancel={() => setSubtaskDraft(null)}
          confirmText={local.create}
          cancelText={t.cancel}
        >
          <textarea
            autoFocus
            rows={4}
            value={subtaskDraft.description}
            onChange={(event) => setSubtaskDraft({ ...subtaskDraft, description: event.target.value })}
            placeholder={local.subtaskPlaceholder}
            className="field-input w-full resize-none rounded-lg p-3 text-sm focus:outline-none t1"
          />
        </Modal>
      )}

      {deleteTargetId && (
        <Modal
          title={local.deleteTitle}
          onConfirm={() => void confirmDeleteTask()}
          onCancel={() => setDeleteTargetId(null)}
          confirmText={t.confirm}
          cancelText={t.cancel}
          danger
        >
          <p className="text-sm leading-relaxed t2">{local.deleteConfirm}</p>
          <div className="mt-3 rounded-lg border px-3 py-2 text-xs font-mono" style={{ background: "var(--bg-card)", borderColor: "var(--border-c)", color: "var(--accent-strong)" }}>
            {deleteTargetId}
          </div>
        </Modal>
      )}
    </div>
  );
}
