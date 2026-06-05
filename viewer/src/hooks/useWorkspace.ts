import { useEffect, type Dispatch, type SetStateAction } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import { EMPTY_MEMORY } from "../constants";
import { sanitizeMemory } from "../utils/schemaValidator";
import type { ActivityLogInput, AgentMemory, AgentTask, TaskStatus, Workspace } from "../types";

type UseWorkspaceOptions = {
  activeWorkspaceId: string;
  fallbackMemory: AgentMemory;
  memoryMap: Record<string, AgentMemory>;
  setMemoryMap: Dispatch<SetStateAction<Record<string, AgentMemory>>>;
  workspaces: Workspace[];
  onActivity?: (activity: ActivityLogInput) => void;
};

type WorkspaceActivity = Omit<ActivityLogInput, "workspaceId" | "workspaceName">;

function saveWorkspaceMemory(workspace: Workspace | undefined, memory: AgentMemory) {
  const command = workspace?.path ? "save_agent_memory_to" : "save_agent_memory";
  const args = workspace?.path ? { path: workspace.path, memory } : { memory };

  return invoke(command, args);
}

function patchTask(tasks: AgentTask[], taskId: string, updater: (task: AgentTask) => void): boolean {
  for (const task of tasks) {
    if (task.id === taskId) {
      updater(task);
      return true;
    }

    if (task.tasks && patchTask(task.tasks, taskId, updater)) {
      return true;
    }
  }

  return false;
}

function collectTaskIds(tasks: AgentTask[]): Set<string> {
  const ids = new Set<string>();

  function visit(list: AgentTask[]) {
    for (const task of list) {
      ids.add(task.id);
      visit(task.tasks ?? []);
    }
  }

  visit(tasks);
  return ids;
}

function createSubtaskId(parentId: string, siblings: AgentTask[], existingIds: Set<string>) {
  let index = siblings.length + 1;

  while (existingIds.has(`${parentId}-${String(index).padStart(2, "0")}`)) {
    index += 1;
  }

  return `${parentId}-${String(index).padStart(2, "0")}`;
}

function collectSubtreeIds(task: AgentTask): string[] {
  return [task.id, ...(task.tasks ?? []).flatMap(collectSubtreeIds)];
}

function deleteTaskById(tasks: AgentTask[], taskId: string): string[] {
  for (let index = 0; index < tasks.length; index += 1) {
    const task = tasks[index];

    if (task.id === taskId) {
      const removedIds = collectSubtreeIds(task);
      tasks.splice(index, 1);
      return removedIds;
    }

    const removedIds = deleteTaskById(task.tasks ?? [], taskId);
    if (removedIds.length > 0) {
      return removedIds;
    }
  }

  return [];
}

function stripDependencies(tasks: AgentTask[], removedIds: Set<string>) {
  for (const task of tasks) {
    task.dependencies = (task.dependencies ?? []).filter((dependency) => {
      const depId = typeof dependency === "string" ? dependency : dependency.id;
      return !removedIds.has(depId);
    });
    stripDependencies(task.tasks ?? [], removedIds);
  }
}

function countTasks(tasks: AgentTask[]): number {
  return tasks.reduce((total, task) => total + 1 + countTasks(task.tasks ?? []), 0);
}

function describeTopologyState(payload: unknown) {
  if (!payload || typeof payload !== "object") {
    return "topology_updated";
  }

  const state = payload as { session_id?: unknown; stats?: { total_nodes?: unknown; errors?: unknown } };
  const sessionId = typeof state.session_id === "string" ? state.session_id : "unknown-session";
  const totalNodes = typeof state.stats?.total_nodes === "number" ? state.stats.total_nodes : 0;
  const errors = typeof state.stats?.errors === "number" ? state.stats.errors : 0;

  return `session ${sessionId} | nodes ${totalNodes} | errors ${errors}`;
}

function describeError(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

export function useWorkspace({
  activeWorkspaceId,
  fallbackMemory,
  memoryMap,
  setMemoryMap,
  workspaces,
  onActivity,
}: UseWorkspaceOptions) {
  const isTauriAvailable = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
  const activeWorkspace = workspaces.find((workspace) => workspace.id === activeWorkspaceId);
  const activeWorkspaceName = activeWorkspace?.name ?? activeWorkspaceId;
  const activeMemory = memoryMap[activeWorkspaceId] ?? fallbackMemory;

  function recordWorkspaceActivity(activity: WorkspaceActivity) {
    onActivity?.({
      workspaceId: activeWorkspaceId,
      workspaceName: activeWorkspaceName,
      ...activity,
    });
  }

  useEffect(() => {
    if (!isTauriAvailable) {
      setMemoryMap((current) => ({
        ...current,
        [activeWorkspaceId]: current[activeWorkspaceId] ?? fallbackMemory,
      }));
      onActivity?.({
        type: "workspace-loaded",
        workspaceId: activeWorkspaceId,
        workspaceName: activeWorkspaceName,
        taskCount: countTasks(fallbackMemory.tasks),
      });
      return;
    }

    const invokeArgs = activeWorkspace?.path ? { path: activeWorkspace.path } : undefined;
    const loadCommand = activeWorkspace?.path ? "load_agent_memory_from" : "load_agent_memory";
    let memoryUnlisten: (() => void) | undefined;
    let topologyUnlisten: (() => void) | undefined;
    let cancelled = false;

    invoke<unknown>(loadCommand, invokeArgs)
      .then((payload) => {
        if (cancelled) {
          return;
        }

        const sanitized = sanitizeMemory(payload);
        setMemoryMap((current) => ({
          ...current,
          [activeWorkspaceId]: sanitized,
        }));
        onActivity?.({
          type: "workspace-loaded",
          workspaceId: activeWorkspaceId,
          workspaceName: activeWorkspaceName,
          taskCount: countTasks(sanitized.tasks),
        });
      })
      .catch((error) => {
        const emptyMemory = EMPTY_MEMORY;

        saveWorkspaceMemory(activeWorkspace, emptyMemory).catch((saveError) => {
          if (!cancelled) {
            onActivity?.({
              type: "save-error",
              workspaceId: activeWorkspaceId,
              workspaceName: activeWorkspaceName,
              taskCount: 0,
              detail: describeError(saveError),
            });
          }
        });
        if (!cancelled) {
          setMemoryMap((current) => ({
            ...current,
            [activeWorkspaceId]: emptyMemory,
          }));
          onActivity?.({
            type: "workspace-loaded",
            workspaceId: activeWorkspaceId,
            workspaceName: activeWorkspaceName,
            taskCount: 0,
            detail: describeError(error),
          });
        }
      });

    if (!activeWorkspace?.path) {
      listen<unknown>("agent_memory_updated", (event) => {
        if (cancelled) {
          return;
        }

        const sanitized = sanitizeMemory(event.payload);
        setMemoryMap((current) => ({
          ...current,
          [activeWorkspaceId]: sanitized,
        }));
        onActivity?.({
          type: "workspace-synced",
          workspaceId: activeWorkspaceId,
          workspaceName: activeWorkspaceName,
          taskCount: countTasks(sanitized.tasks),
        });
      })
        .then((dispose) => {
          memoryUnlisten = dispose;
        })
        .catch(() => undefined);
    }

    listen<unknown>("topology_updated", (event) => {
      if (cancelled) {
        return;
      }

      onActivity?.({
        type: "topology-updated",
        workspaceId: activeWorkspaceId,
        workspaceName: activeWorkspaceName,
        detail: describeTopologyState(event.payload),
      });
    })
      .then((dispose) => {
        topologyUnlisten = dispose;
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
      memoryUnlisten?.();
      topologyUnlisten?.();
    };
  }, [activeWorkspace?.path, activeWorkspaceId, activeWorkspaceName, fallbackMemory, isTauriAvailable, onActivity, setMemoryMap]);

  async function applyMemoryMutation(mutator: (memory: AgentMemory) => WorkspaceActivity | undefined) {
    const updated = structuredClone(activeMemory);
    const activity = mutator(updated);

    setMemoryMap((current) => ({
      ...current,
      [activeWorkspaceId]: updated,
    }));

    if (activity) {
      recordWorkspaceActivity(activity);
    }

    try {
      await saveWorkspaceMemory(activeWorkspace, updated);
    } catch (error) {
      if (isTauriAvailable) {
        recordWorkspaceActivity({
          type: "save-error",
          taskCount: countTasks(updated.tasks),
          detail: describeError(error),
        });
      }
    }
  }

  async function handleStatusChange(taskId: string, nextStatus: TaskStatus) {
    await applyMemoryMutation((memory) => {
      let previousStatus: TaskStatus | undefined;
      let taskDescription: string | undefined;
      const changed = patchTask(memory.tasks, taskId, (task) => {
        previousStatus = task.status;
        taskDescription = task.description;
        task.status = nextStatus;
      });

      if (!changed || previousStatus === nextStatus) {
        return undefined;
      }

      return {
        type: "task-status",
        taskId,
        taskDescription,
        fromStatus: previousStatus,
        toStatus: nextStatus,
        taskCount: countTasks(memory.tasks),
      };
    });
  }

  async function handleDescriptionChange(taskId: string, description: string) {
    await applyMemoryMutation((memory) => {
      const changed = patchTask(memory.tasks, taskId, (task) => {
        task.description = description;
      });

      if (!changed) {
        return undefined;
      }

      return {
        type: "task-description",
        taskId,
        taskDescription: description,
        taskCount: countTasks(memory.tasks),
      };
    });
  }

  async function handleAddSubtask(parentId: string, description: string) {
    await applyMemoryMutation((memory) => {
      const existingIds = collectTaskIds(memory.tasks);
      let createdTaskId: string | undefined;

      const changed = patchTask(memory.tasks, parentId, (task) => {
        const subtasks = task.tasks ?? [];
        const previousTask = subtasks[subtasks.length - 1];
        const id = createSubtaskId(parentId, subtasks, existingIds);
        createdTaskId = id;

        subtasks.push({
          id,
          description,
          status: "pending",
          dependencies: previousTask ? [previousTask.id] : [parentId],
          ai_feedback: null,
          tasks: [],
        });

        task.tasks = subtasks;
      });

      if (!changed || !createdTaskId) {
        return undefined;
      }

      return {
        type: "task-created",
        taskId: createdTaskId,
        parentTaskId: parentId,
        taskDescription: description,
        taskCount: countTasks(memory.tasks),
      };
    });
  }

  async function handleDeleteTask(taskId: string) {
    await applyMemoryMutation((memory) => {
      const removedIds = deleteTaskById(memory.tasks, taskId);
      if (removedIds.length > 0) {
        stripDependencies(memory.tasks, new Set(removedIds));
      }

      if (removedIds.length === 0) {
        return undefined;
      }

      return {
        type: "task-deleted",
        taskId,
        removedCount: removedIds.length,
        taskCount: countTasks(memory.tasks),
      };
    });
  }

  return {
    activeMemory,
    activeWorkspace,
    handleStatusChange,
    handleDescriptionChange,
    handleAddSubtask,
    handleDeleteTask,
  };
}
