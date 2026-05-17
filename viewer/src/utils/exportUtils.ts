import type { AgentMemory, AgentTask, TaskStatus, Workspace } from "../types";

type ExportFormat = "json" | "markdown";

type ExportStats = {
  total: number;
  pending: number;
  inProgress: number;
  completed: number;
  completionRate: number;
};

type StatusLabelSet = Record<TaskStatus, string>;

type MarkdownOptions = {
  generatedAt: Date;
  statusLabels: StatusLabelSet;
  statsLabels: {
    title: string;
    workspace: string;
    generatedAt: string;
    total: string;
    pending: string;
    inProgress: string;
    completed: string;
    completionRate: string;
    dependencies: string;
    aiFeedback: string;
    noTasks: string;
  };
};

function collectStats(tasks: AgentTask[]): ExportStats {
  const flatTasks = tasks.flatMap((task): AgentTask[] => [task, ...collectFlatTasks(task.tasks ?? [])]);
  const total = flatTasks.length;
  const completed = flatTasks.filter((task) => task.status === "completed").length;
  const inProgress = flatTasks.filter((task) => task.status === "in_progress").length;
  const pending = flatTasks.filter((task) => task.status === "pending").length;

  return {
    total,
    pending,
    inProgress,
    completed,
    completionRate: total > 0 ? Math.round((completed / total) * 100) : 0,
  };
}

function collectFlatTasks(tasks: AgentTask[]): AgentTask[] {
  return tasks.flatMap((task): AgentTask[] => [task, ...collectFlatTasks(task.tasks ?? [])]);
}

function sanitizeFilePart(value: string) {
  const normalized = value.trim().toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/gi, "-");
  return normalized.replace(/^-+|-+$/g, "") || "workspace";
}

function formatDateForFile(date: Date) {
  return date.toISOString().slice(0, 19).replace(/[:T]/g, "-");
}

export function buildExportFilename(workspace: Workspace | undefined, format: ExportFormat, generatedAt = new Date()) {
  const extension = format === "json" ? "json" : "md";
  const workspaceName = sanitizeFilePart(workspace?.name ?? workspace?.id ?? "workspace");

  return `${workspaceName}-agent-memory-${formatDateForFile(generatedAt)}.${extension}`;
}

export function buildMemoryJsonExport(memory: AgentMemory, workspace: Workspace | undefined, generatedAt = new Date()) {
  return JSON.stringify(
    {
      exported_at: generatedAt.toISOString(),
      workspace: workspace
        ? {
            id: workspace.id,
            name: workspace.name,
            lang: workspace.lang,
            path: workspace.path,
          }
        : null,
      stats: collectStats(memory.tasks),
      memory,
    },
    null,
    2,
  );
}

function appendTaskMarkdown(lines: string[], task: AgentTask, depth: number, options: MarkdownOptions) {
  const indent = "  ".repeat(depth);
  lines.push(`${indent}- **${task.id}** [${options.statusLabels[task.status]}] ${task.description}`);

  if ((task.dependencies ?? []).length > 0) {
    lines.push(`${indent}  - ${options.statsLabels.dependencies}: ${(task.dependencies ?? []).join(", ")}`);
  }

  if (task.ai_feedback) {
    lines.push(`${indent}  - ${options.statsLabels.aiFeedback}: ${task.ai_feedback.replace(/\n/g, " ")}`);
  }

  (task.tasks ?? []).forEach((subtask) => appendTaskMarkdown(lines, subtask, depth + 1, options));
}

export function buildMemoryMarkdownExport(
  memory: AgentMemory,
  workspace: Workspace | undefined,
  options: MarkdownOptions,
) {
  const stats = collectStats(memory.tasks);
  const lines = [
    `# ${options.statsLabels.title}`,
    "",
    `- ${options.statsLabels.workspace}: ${workspace?.name ?? workspace?.id ?? "Workspace"}`,
    `- ${options.statsLabels.generatedAt}: ${options.generatedAt.toISOString()}`,
    `- ${options.statsLabels.total}: ${stats.total}`,
    `- ${options.statsLabels.pending}: ${stats.pending}`,
    `- ${options.statsLabels.inProgress}: ${stats.inProgress}`,
    `- ${options.statsLabels.completed}: ${stats.completed}`,
    `- ${options.statsLabels.completionRate}: ${stats.completionRate}%`,
    "",
    "## Tasks",
    "",
  ];

  if (memory.tasks.length === 0) {
    lines.push(options.statsLabels.noTasks);
  } else {
    memory.tasks.forEach((task) => appendTaskMarkdown(lines, task, 0, options));
  }

  return `${lines.join("\n")}\n`;
}

export function downloadTextFile(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();

  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
