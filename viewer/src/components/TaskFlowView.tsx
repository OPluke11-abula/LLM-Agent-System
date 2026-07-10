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
import { Button, MetricTile, StatusBadge, Surface } from "./ui/primitives";
import type {
  ActivityLogEntry,
  AgentMemory,
  AgentTask,
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

type FlatTask = ReturnType<typeof flattenTasks>[number];

type TaskIntelligence = {
  owner: string;
  blocker: string;
  evidence: string;
  linkedFiles: string[];
  verificationCommand: string;
  handoffStatus: string;
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
  emptyWorkspace: string;
  closePanel: string;
  cockpitTitle: string;
  cockpitSubtitle: string;
  timeline: string;
  graphWorkspace: string;
  intelligence: string;
  ownerAgent: string;
  blocker: string;
  evidence: string;
  linkedFiles: string;
  verificationCommand: string;
  handoffStatus: string;
  noSelection: string;
  noLinkedFiles: string;
  noEvidence: string;
  noBlocker: string;
  handoffReady: string;
  handoffRunning: string;
  handoffWaiting: string;
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
    emptyWorkspace: "此工作區尚無任務。請在設定中指定 JSON 路徑，或讓 AI 代理寫入資料。",
    closePanel: "關閉",
    cockpitTitle: "Task Flow 2.0",
    cockpitSubtitle: "時間線、依賴圖與任務情報集中在同一個工作區。",
    timeline: "任務時間線",
    graphWorkspace: "依賴圖工作區",
    intelligence: "任務情報",
    ownerAgent: "Owner agent",
    blocker: "Blocker",
    evidence: "Evidence",
    linkedFiles: "Linked files",
    verificationCommand: "Verification command",
    handoffStatus: "Handoff status",
    noSelection: "選取任務或使用搜尋結果中的第一個任務。",
    noLinkedFiles: "尚未偵測到 linked files。",
    noEvidence: "尚未附加 evidence。",
    noBlocker: "目前沒有未完成依賴。",
    handoffReady: "Ready for handoff",
    handoffRunning: "Keep full context",
    handoffWaiting: "Waiting for dependencies",
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
    emptyWorkspace: "No tasks in this workspace yet. Set the JSON path in Settings or let an AI agent write data.",
    closePanel: "Close",
    cockpitTitle: "Task Flow 2.0",
    cockpitSubtitle: "Timeline, dependency graph, and task intelligence in one workspace.",
    timeline: "Task timeline",
    graphWorkspace: "Dependency graph workspace",
    intelligence: "Task intelligence",
    ownerAgent: "Owner agent",
    blocker: "Blocker",
    evidence: "Evidence",
    linkedFiles: "Linked files",
    verificationCommand: "Verification command",
    handoffStatus: "Handoff status",
    noSelection: "Select a task or use the first matching result.",
    noLinkedFiles: "No linked files detected yet.",
    noEvidence: "No evidence attached yet.",
    noBlocker: "No incomplete dependency.",
    handoffReady: "Ready for handoff",
    handoffRunning: "Keep full context",
    handoffWaiting: "Waiting for dependencies",
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
    emptyWorkspace: "このワークスペースにはまだタスクがありません。設定で JSON パスを指定するか、AI エージェントにデータを書き込ませてください。",
    closePanel: "閉じる",
    cockpitTitle: "Task Flow 2.0",
    cockpitSubtitle: "タイムライン、依存グラフ、タスク情報を一つの作業面に集約します。",
    timeline: "タスクタイムライン",
    graphWorkspace: "依存グラフ",
    intelligence: "タスク情報",
    ownerAgent: "Owner agent",
    blocker: "Blocker",
    evidence: "Evidence",
    linkedFiles: "Linked files",
    verificationCommand: "Verification command",
    handoffStatus: "Handoff status",
    noSelection: "タスクを選択するか、最初の一致結果を使用します。",
    noLinkedFiles: "linked files は未検出です。",
    noEvidence: "evidence は未添付です。",
    noBlocker: "未完了の依存関係はありません。",
    handoffReady: "Ready for handoff",
    handoffRunning: "Keep full context",
    handoffWaiting: "Waiting for dependencies",
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
    emptyWorkspace: "Aucune tâche dans cet espace. Définissez le chemin JSON dans Paramètres ou laissez un agent IA écrire les données.",
    closePanel: "Fermer",
    cockpitTitle: "Task Flow 2.0",
    cockpitSubtitle: "Timeline, graphe de dépendances et intelligence de tâche dans un workspace.",
    timeline: "Timeline tâches",
    graphWorkspace: "Graphe dépendances",
    intelligence: "Intelligence tâche",
    ownerAgent: "Owner agent",
    blocker: "Blocker",
    evidence: "Evidence",
    linkedFiles: "Linked files",
    verificationCommand: "Verification command",
    handoffStatus: "Handoff status",
    noSelection: "Sélectionnez une tâche ou le premier résultat.",
    noLinkedFiles: "Aucun linked file détecté.",
    noEvidence: "Aucune evidence attachée.",
    noBlocker: "Aucune dépendance incomplète.",
    handoffReady: "Ready for handoff",
    handoffRunning: "Keep full context",
    handoffWaiting: "Waiting for dependencies",
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

function dependencyId(dependency: AgentTask["dependencies"][number]) {
  return typeof dependency === "string" ? dependency : dependency.id;
}

function dependencyCategory(dependency: AgentTask["dependencies"][number]) {
  return typeof dependency === "string" ? "dependency" : dependency.category ?? "dependency";
}

function toneForTaskStatus(status: TaskStatus) {
  if (status === "completed") return "success";
  if (status === "in_progress") return "accent";
  return "warning";
}

function inferOwner(task: FlatTask) {
  const haystack = `${task.id} ${task.description} ${task.ai_feedback ?? ""}`.toLowerCase();
  if (haystack.includes("frontend") || haystack.includes("viewer") || haystack.includes("react") || haystack.includes("ui")) return "Frontend Programmer";
  if (haystack.includes("security") || haystack.includes("risk") || haystack.includes("audit")) return "Security Reviewer";
  if (haystack.includes("schema") || haystack.includes("pap") || haystack.includes("contract")) return "Protocol Architect";
  if (haystack.includes("test") || haystack.includes("verify") || haystack.includes("qa")) return "QA / Verification";
  if (haystack.includes("doc") || haystack.includes("design") || haystack.includes("plan")) return "Architect / Designer";
  return "Active agent";
}

function extractLinkedFiles(task: FlatTask) {
  const source = `${task.description}\n${task.ai_feedback ?? ""}`;
  const backtickMatches = Array.from(source.matchAll(/`([^`]+\.[A-Za-z0-9]+)`/g)).map((match) => match[1]);
  const pathMatches = source.match(/(?:[\w.-]+\/)+[\w.-]+\.[A-Za-z0-9]+/g) ?? [];
  return Array.from(new Set([...backtickMatches, ...pathMatches])).slice(0, 5);
}

function buildTaskIntelligence(task: FlatTask | null, flatTasks: FlatTask[], local: LocalizedCopy): TaskIntelligence | null {
  if (!task) return null;
  const dependencies = task.dependencies ?? [];
  const blockingDependency = dependencies
    .map((dependency) => flatTasks.find((candidate) => candidate.id === dependencyId(dependency)))
    .find((candidate) => candidate && candidate.status !== "completed");
  const dependencyCategories = dependencies.map(dependencyCategory);
  const evidenceBits = [
    task.ai_feedback ? "AI feedback" : "",
    dependencyCategories.includes("data_flow") ? "data-flow edge" : "",
    dependencyCategories.includes("feedback_loop") ? "feedback loop" : "",
    dependencies.length > 0 ? `${dependencies.length} dependency refs` : "",
  ].filter(Boolean);
  const linkedFiles = extractLinkedFiles(task);
  const owner = inferOwner(task);
  const haystack = `${task.id} ${task.description} ${task.ai_feedback ?? ""}`.toLowerCase();
  const verificationCommand =
    haystack.includes("viewer") || haystack.includes("react") || haystack.includes("ui")
      ? "npm.cmd --prefix viewer run build"
      : haystack.includes("pap") || haystack.includes("contract")
        ? "python agent_workspace/pap_validate.py .agent/agent.md"
        : ".\\scripts\\verify.cmd";

  return {
    owner,
    blocker: blockingDependency ? `${blockingDependency.id} · ${blockingDependency.description}` : local.noBlocker,
    evidence: evidenceBits.length > 0 ? evidenceBits.join(" · ") : local.noEvidence,
    linkedFiles,
    verificationCommand,
    handoffStatus: task.status === "completed" ? local.handoffReady : task.status === "in_progress" ? local.handoffRunning : local.handoffWaiting,
  };
}

function useTaskFlowController({
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

        void flowInstance.setViewport(
          {
            x: 40 - minX * zoom,
            y: 64 - minY * zoom,
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
    ? flatTasks.find((task) => task.id === selectedTaskId) ?? null
    : null;
  const focusTask =
    selectedTask ??
    matchedTasks.find((task) => task.status === "in_progress") ??
    matchedTasks.find((task) => task.status === "pending") ??
    matchedTasks[0] ??
    null;
  const focusIntelligence = buildTaskIntelligence(focusTask, flatTasks, local);
  const timelineTasks = matchedTasks.slice(0, 10);

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

  return {
    memory,
    workspaces,
    activeWorkspaceId,
    setActiveWorkspaceId,
    activityEntries,
    onClearActivityLog,
    t,
    lang,
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    flowContainerRef,
    setFlowInstance,
    selectedTaskId,
    setSelectedTaskId,
    contextMenu,
    setContextMenu,
    filter,
    setFilter,
    search,
    setSearch,
    editDraft,
    setEditDraft,
    subtaskDraft,
    setSubtaskDraft,
    deleteTargetId,
    setDeleteTargetId,
    exportStatus,
    local,
    total,
    matchedTasks,
    focusTask,
    focusIntelligence,
    timelineTasks,
    stats,
    contextItems,
    submitDescriptionChange,
    submitSubtask,
    confirmDeleteTask,
    handleExport,
  };
}

type TaskFlowController = ReturnType<typeof useTaskFlowController>;

export function TaskFlowView(props: TaskFlowViewProps) {
  const controller = useTaskFlowController(props);

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto">
      <TaskFlowWorkspaceTabs controller={controller} />
      <TaskFlowHero controller={controller} />
      <TaskFlowStats controller={controller} />
      <TaskFlowControls controller={controller} />
      <TaskFlowTimeline controller={controller} />
      <div className="grid min-h-[560px] gap-3 xl:grid-cols-[minmax(0,1fr)_360px]">
        <TaskFlowCanvas controller={controller} />
        <TaskIntelligencePanel controller={controller} />
      </div>
      <ActivityLog entries={controller.activityEntries} lang={controller.lang} onClear={controller.onClearActivityLog} />
      <TaskFlowModals controller={controller} />
    </div>
  );
}

function TaskFlowWorkspaceTabs({ controller }: { readonly controller: TaskFlowController }) {
  const { activeWorkspaceId, setActiveWorkspaceId, workspaces } = controller;

  if (workspaces.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-shrink-0 flex-wrap gap-2">
      {workspaces.map((workspace) => (
        <Button
          key={workspace.id}
          type="button"
          onClick={() => setActiveWorkspaceId(workspace.id)}
          variant={workspace.id === activeWorkspaceId ? "primary" : "quiet"}
          className="flex flex-col items-start px-3 py-2 text-xs"
        >
          <span>
            {workspace.name} · {workspace.lang}
          </span>
          {workspace.path && (
            <span className="mt-0.5 font-mono text-xs opacity-60">
              {workspace.path}
            </span>
          )}
        </Button>
      ))}
    </div>
  );
}

function TaskFlowHero({ controller }: { readonly controller: TaskFlowController }) {
  const { focusTask, local } = controller;

  return (
    <Surface elevated className="task-flow-hero flex min-h-[8rem] flex-col justify-center gap-3 p-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] accent-text">{local.graphWorkspace}</p>
        <h1 className="mt-1 text-2xl font-semibold t1 sm:text-3xl">{local.cockpitTitle}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed t2">{local.cockpitSubtitle}</p>
      </div>
      <StatusBadge tone={focusTask ? toneForTaskStatus(focusTask.status) : "warning"}>
        {focusTask ? focusTask.status.replace("_", " ") : local.exportNoTasks}
      </StatusBadge>
    </Surface>
  );
}

function TaskFlowStats({ controller }: { readonly controller: TaskFlowController }) {
  const { local, stats } = controller;

  return (
    <div className="grid gap-3 md:grid-cols-4">
      {stats.map((stat) => (
        <MetricTile
          key={stat.label}
          label={stat.label}
          value={stat.value}
          tone={stat.label === local.completionRate ? "accent" : "neutral"}
          className="p-4"
        />
      ))}
    </div>
  );
}

function TaskFlowControls({ controller }: { readonly controller: TaskFlowController }) {
  const { exportStatus, filter, handleExport, local, matchedTasks, search, setFilter, setSearch, total } = controller;
  const filterOptions = ["all", "pending", "in_progress", "completed"] as const satisfies readonly FilterStatus[];

  return (
    <Surface elevated className="flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] t3">{local.searchLabel}</p>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {exportStatus && <StatusBadge tone="success">{exportStatus}</StatusBadge>}
          <p className="text-xs t2">
            {local.matchingCount} {matchedTasks.length} / {total}
          </p>
          <div className="flex flex-wrap items-center gap-1.5 rounded-lg border p-1" style={{ borderColor: "var(--border-c)", background: "var(--bg-card)" }}>
            <span className="hidden px-2 text-[10px] font-semibold uppercase tracking-[0.14em] t3 sm:inline">{local.exportLabel}</span>
            <Button type="button" onClick={() => handleExport("json")} variant="primary" className="rounded-md px-2.5 py-1.5">
              {local.exportJson}
            </Button>
            <Button type="button" onClick={() => handleExport("markdown")} variant="quiet" className="rounded-md px-2.5 py-1.5">
              <span className="hidden sm:inline">{local.exportMarkdown}</span>
              <span className="sm:hidden">MD</span>
            </Button>
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
          {filterOptions.map((status) => (
            <Button
              key={status}
              type="button"
              onClick={() => setFilter(status)}
              variant={filter === status ? "primary" : "quiet"}
              className="px-3 py-2"
            >
              {local.filters[status]}
            </Button>
          ))}
        </div>
      </div>
    </Surface>
  );
}

function TaskFlowTimeline({ controller }: { readonly controller: TaskFlowController }) {
  const { focusTask, local, matchedTasks, setSelectedTaskId, timelineTasks } = controller;

  return (
    <Surface as="section" className="task-timeline-surface p-4" data-testid="task-flow-timeline">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{local.timeline}</p>
        <StatusBadge tone="accent">{timelineTasks.length} / {matchedTasks.length}</StatusBadge>
      </div>
      <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
        {timelineTasks.length === 0 ? (
          <p className="text-xs t3">{local.noMatches}</p>
        ) : (
          timelineTasks.map((task, index) => {
            const selected = focusTask?.id === task.id;
            return (
              <button
                key={task.id}
                type="button"
                onClick={() => setSelectedTaskId(task.id)}
                className={`task-timeline-item min-w-[12rem] rounded-lg border p-3 text-left transition-all ${selected ? "task-timeline-item-active" : ""}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[10px] t3">{String(index + 1).padStart(2, "0")} · {task.id}</span>
                  <StatusBadge tone={toneForTaskStatus(task.status)}>{task.status.replace("_", " ")}</StatusBadge>
                </div>
                <p className="mt-2 line-clamp-2 text-xs font-semibold leading-relaxed t1">{task.description}</p>
                <p className="mt-2 text-[10px] t3">{inferOwner(task)}</p>
              </button>
            );
          })
        )}
      </div>
    </Surface>
  );
}

function TaskFlowCanvas({ controller }: { readonly controller: TaskFlowController }) {
  const {
    contextItems,
    contextMenu,
    edges,
    flowContainerRef,
    local,
    matchedTasks,
    memory,
    nodes,
    onEdgesChange,
    onNodesChange,
    setContextMenu,
    setFlowInstance,
    setSelectedTaskId,
  } = controller;

  return (
    <div
      ref={flowContainerRef}
      className="flow-canvas relative min-h-[420px] overflow-hidden rounded-lg border xl:min-h-[560px]"
      style={{ borderColor: "var(--border-c)" }}
    >
      {memory.tasks.length === 0 && (
        <div className="pointer-events-none absolute inset-0 z-10 flex flex-col items-center justify-center px-6 text-center">
          <StatusBadge tone="warning">{local.exportNoTasks}</StatusBadge>
          <p className="mt-4 max-w-md text-sm font-semibold leading-relaxed t2">{local.emptyWorkspace}</p>
        </div>
      )}

      {memory.tasks.length > 0 && matchedTasks.length === 0 && (
        <Surface className="absolute top-4 left-1/2 z-20 -translate-x-1/2 px-4 py-2 text-xs font-semibold t2">
          {local.noMatches}
        </Surface>
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

      {contextMenu && <ContextMenu x={contextMenu.x} y={contextMenu.y} items={contextItems} onClose={() => setContextMenu(null)} />}
    </div>
  );
}

function TaskIntelligencePanel({ controller }: { readonly controller: TaskFlowController }) {
  const { focusIntelligence, focusTask, local, t } = controller;

  return (
    <Surface as="aside" className="task-intelligence-panel p-4" data-testid="task-intelligence-panel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{local.intelligence}</p>
          <h2 className="mt-1 line-clamp-2 text-sm font-semibold t1">{focusTask?.description ?? local.noSelection}</h2>
        </div>
        {focusTask && <StatusBadge tone={toneForTaskStatus(focusTask.status)}>{focusTask.status.replace("_", " ")}</StatusBadge>}
      </div>

      {focusTask && focusIntelligence ? (
        <div className="mt-4 space-y-4">
          <div>
            <p className="text-[9px] font-bold uppercase tracking-[0.12em] t3">{t.taskId}</p>
            <Surface className="mt-1 px-3 py-2 font-mono text-xs" style={{ color: "var(--accent-strong)" }}>{focusTask.id}</Surface>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <MetricTile label={local.ownerAgent} value={focusIntelligence.owner} className="p-3" />
            <MetricTile label={local.handoffStatus} value={focusIntelligence.handoffStatus} tone={focusTask.status === "completed" ? "success" : "warning"} className="p-3" />
          </div>
          <div>
            <p className="text-[9px] font-bold uppercase tracking-[0.12em] t3">{local.blocker}</p>
            <p className="mt-1 rounded-lg border px-3 py-2 text-xs leading-relaxed t2" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
              {focusIntelligence.blocker}
            </p>
          </div>
          <div>
            <p className="text-[9px] font-bold uppercase tracking-[0.12em] t3">{local.evidence}</p>
            <p className="mt-1 rounded-lg border px-3 py-2 text-xs leading-relaxed t2" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
              {focusIntelligence.evidence}
            </p>
          </div>
          <div>
            <p className="text-[9px] font-bold uppercase tracking-[0.12em] t3">{local.linkedFiles}</p>
            {focusIntelligence.linkedFiles.length > 0 ? (
              <div className="mt-2 space-y-1">
                {focusIntelligence.linkedFiles.map((file) => (
                  <p key={file} className="truncate rounded-md border px-2 py-1.5 font-mono text-[10px] t2" title={file} style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>{file}</p>
                ))}
              </div>
            ) : (
              <p className="mt-1 text-xs italic t3">{local.noLinkedFiles}</p>
            )}
          </div>
          <div>
            <p className="text-[9px] font-bold uppercase tracking-[0.12em] t3">{local.verificationCommand}</p>
            <pre className="mt-1 truncate rounded-lg border px-3 py-2 text-[11px] t2" title={focusIntelligence.verificationCommand} style={{ borderColor: "var(--border-c)", background: "var(--bg-base)" }}>{focusIntelligence.verificationCommand}</pre>
          </div>
          <div>
            <p className="text-[9px] font-bold uppercase tracking-[0.12em] t3">{t.deps}</p>
            {focusTask.dependencies.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {focusTask.dependencies.map((dependency) => {
                  const depId = dependencyId(dependency);
                  return <StatusBadge key={depId} tone="neutral">{depId}</StatusBadge>;
                })}
              </div>
            ) : (
              <p className="mt-1 text-xs italic t3">{t.noDeps}</p>
            )}
          </div>
        </div>
      ) : (
        <p className="mt-4 text-sm leading-relaxed t2">{local.noSelection}</p>
      )}
    </Surface>
  );
}

function TaskFlowModals({ controller }: { readonly controller: TaskFlowController }) {
  const {
    confirmDeleteTask,
    deleteTargetId,
    editDraft,
    local,
    setDeleteTargetId,
    setEditDraft,
    setSubtaskDraft,
    submitDescriptionChange,
    submitSubtask,
    subtaskDraft,
    t,
  } = controller;

  return (
    <>
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
          <Surface className="mt-3 px-3 py-2 font-mono text-xs" style={{ color: "var(--accent-strong)" }}>
            {deleteTargetId}
          </Surface>
        </Modal>
      )}
    </>
  );
}
