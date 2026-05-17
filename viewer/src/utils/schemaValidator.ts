import type { AgentMemory, AgentTask, TaskStatus } from "../types";

export const VALID_STATUS: TaskStatus[] = ["pending", "in_progress", "completed"];
export const REQUIRED_FIELDS = ["id", "description", "status", "dependencies"] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function sanitizeTask(raw: unknown, fallbackId = `task-${Date.now()}`): AgentTask {
  const record = isRecord(raw) ? raw : {};
  const rawId = record.id ?? record.title ?? record.name ?? fallbackId;
  const id = String(rawId).trim() || fallbackId;
  const rawDescription = record.description ?? record.title ?? record.name ?? "未命名任務";
  const status = VALID_STATUS.includes(record.status as TaskStatus)
    ? (record.status as TaskStatus)
    : "pending";

  return {
    id,
    description: String(rawDescription),
    status,
    dependencies: Array.isArray(record.dependencies)
      ? record.dependencies
          .filter((dependency): dependency is string | number => typeof dependency === "string" || typeof dependency === "number")
          .map(String)
      : [],
    ai_feedback: record.ai_feedback == null ? null : String(record.ai_feedback),
    tasks: Array.isArray(record.tasks)
      ? record.tasks.map((task, index) => sanitizeTask(task, `${id}-${index + 1}`))
      : [],
  };
}

export function sanitizeMemory(raw: unknown): AgentMemory {
  if (!isRecord(raw) || !Array.isArray(raw.tasks)) {
    return { tasks: [] };
  }

  return {
    tasks: raw.tasks.map((task, index) => sanitizeTask(task, `task-${index + 1}`)),
  };
}
