import dagre from "dagre";
import { MarkerType, Position, type Edge, type Node } from "reactflow";
import type { TopologyEdgeData, TopologyEvent, TopologyNodeData, TopologyState } from "../types";

const NODE_WIDTH = 260;
const NODE_HEIGHT = 132;

export const NODE_COLORS = {
  session_root: "#0C447C",
  agent: "#534AB7",
  handoff: "#534AB7",
  tool_call: "#0F6E56",
  hitl_gate: "#993C1D",
  workflow_stage: "#6B5B95",
  error: "#E24B4A",
} as const;

export const EDGE_COLORS = {
  handoff: "#378ADD",
  tool: "#1D9E75",
  rbac: "#D85A30",
  error: "#E24B4A",
  hitl: "#D85A30",
} as const;

export function nodeComponentType(nodeType: TopologyEvent["node_type"]) {
  if (nodeType === "session_root") return "rootNode";
  if (nodeType === "tool_call") return "toolNode";
  if (nodeType === "hitl_gate") return "hitlNode";
  return "agentNode";
}

export function edgeComponentType(edgeType: TopologyEdgeData["edgeType"]) {
  if (edgeType === "tool") return "toolEdge";
  if (edgeType === "rbac" || edgeType === "hitl") return "rbacEdge";
  if (edgeType === "error") return "errorEdge";
  return "handoffEdge";
}

export function topologyNodeLabel(event: TopologyEvent) {
  return event.title || event.payload?.name || event.payload?.description || event.node_id || event.id;
}

export function topologyNodeDescription(event: TopologyEvent) {
  if (event.description && event.description.trim()) {
    return event.description;
  }
  if (typeof event.payload?.description === "string" && event.payload.description.trim()) {
    return event.payload.description;
  }
  if (event.node_type === "session_root") return `Session ${event.session_id}`;
  if (event.node_type === "tool_call") return "Tool execution";
  if (event.node_type === "hitl_gate") return "Awaiting human approval";
  if (event.node_type === "workflow_stage") return "Workflow stage telemetry";
  return event.node_type;
}

export function buildTopologyFlow(
  state: TopologyState,
  onOpen: (event: TopologyEvent) => void,
): { nodes: Node<TopologyNodeData>[]; edges: Edge<TopologyEdgeData>[] } {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 58, ranksep: 128 });

  const nodes: Node<TopologyNodeData>[] = state.nodes.map((event) => {
    const nodeId = event.node_id || event.id;
    graph.setNode(nodeId, { width: NODE_WIDTH, height: NODE_HEIGHT });
    return {
      id: nodeId,
      type: nodeComponentType(event.node_type),
      position: { x: 0, y: 0 },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
      data: {
        event,
        label: String(topologyNodeLabel(event)),
        description: topologyNodeDescription(event),
        onOpen,
      },
    };
  });

  const edges: Edge<TopologyEdgeData>[] = state.edges.map((edge) => {
    const edgeType = edge.edge_type || edge.type || "handoff";
    graph.setEdge(edge.source, edge.target);
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edgeComponentType(edgeType),
      animated: edgeType === "tool" || edgeType === "handoff" || edgeType === "hitl",
      data: { edgeType, label: edge.label },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: EDGE_COLORS[edgeType],
      },
      style: {
        stroke: EDGE_COLORS[edgeType],
        strokeWidth: edgeType === "error" ? 2.8 : 2.2,
      },
    };
  });

  dagre.layout(graph);

  return {
    nodes: nodes.map((node) => {
      const position = graph.node(node.id);
      return {
        ...node,
        position: {
          x: position.x - NODE_WIDTH / 2,
          y: position.y - NODE_HEIGHT / 2,
        },
      };
    }),
    edges,
  };
}

export function formatDuration(ms?: number | null) {
  if (!ms) return "0ms";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function summarizeTopology(state: TopologyState) {
  const total = Math.max(state.stats.total_nodes, 1);
  return {
    completionRate: Math.round((state.stats.completed / total) * 100),
    errorRate: Math.round((state.stats.errors / total) * 100),
  };
}
