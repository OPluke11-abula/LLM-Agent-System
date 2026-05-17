import dagre from "dagre";
import { Position, type Edge, type Node } from "reactflow";
import type { AgentMemory, AgentTask, TaskNodeData, TaskNodeLabels, TaskStatus, TaskVisualState } from "../types";

type TaskWithDepth = AgentTask & { depth: number };

export function flattenTasks(tasks: AgentTask[], depth = 0): TaskWithDepth[] {
  return tasks.flatMap((task) => [
    {
      ...task,
      dependencies: task.dependencies ?? [],
      description: task.description || task.id,
      depth,
    },
    ...flattenTasks(task.tasks ?? [], depth + 1),
  ]);
}

export function getLayouted(nodes: Node<TaskNodeData>[], edges: Edge[]) {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 60, ranksep: 130 });

  nodes.forEach((node) => graph.setNode(node.id, { width: 280, height: 155 }));
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);

  return {
    nodes: nodes.map((node) => {
      const position = graph.node(node.id);

      return {
        ...node,
        targetPosition: Position.Left,
        sourcePosition: Position.Right,
        position: { x: position.x - 140, y: position.y - 77 },
      };
    }),
    edges,
  };
}

export function buildFlow(
  memory: AgentMemory,
  labels: TaskNodeLabels,
  onStatusChange: (id: string, status: TaskStatus) => void,
  visualStateById: Record<string, TaskVisualState> = {},
) {
  const flat = flattenTasks(memory.tasks);
  const idSet = new Set(flat.map((task) => task.id));

  const normalizedTasks = flat.map((task, index) => {
    const validDependencies = (task.dependencies ?? []).filter((dependency) => idSet.has(dependency));

    return {
      ...task,
      dependencies: validDependencies.length === 0 && index > 0 ? [flat[index - 1].id] : validDependencies,
    };
  });

  const nodes: Node<TaskNodeData>[] = normalizedTasks.map((task) => ({
    id: task.id,
    type: "taskNode",
    data: {
      id: task.id,
      description: task.description,
      status: task.status,
      dependencies: task.dependencies,
      ai_feedback: task.ai_feedback,
      labels,
      isHighlighted: visualStateById[task.id]?.isHighlighted ?? false,
      isDimmed: visualStateById[task.id]?.isDimmed ?? false,
      onStatusChange,
    },
    position: { x: 0, y: 0 },
  }));

  const edges: Edge[] = normalizedTasks.flatMap((task) =>
    (task.dependencies ?? []).map((dependency) => ({
      id: `${dependency}-${task.id}`,
      source: dependency,
      target: task.id,
      animated: task.status === "in_progress",
      style: {
        strokeWidth: 2,
        opacity:
          visualStateById[dependency]?.isDimmed || visualStateById[task.id]?.isDimmed
            ? 0.2
            : 1,
        stroke:
          task.status === "completed"
            ? "#22d3ee"
            : task.status === "in_progress"
              ? "#f59e0b"
              : "#334155",
      },
    })),
  );

  return getLayouted(nodes, edges);
}
