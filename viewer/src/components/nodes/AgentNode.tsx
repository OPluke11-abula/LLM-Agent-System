import type { NodeProps } from "reactflow";
import type { TopologyNodeData } from "../../types";
import { TopologyNodeBase } from "./TopologyNodeBase";

export function AgentNode(props: NodeProps<TopologyNodeData>) {
  const badge = props.data.event.node_type === "handoff" ? "Handoff" : "Agent";
  return <TopologyNodeBase {...props} tone="agent" badge={badge} />;
}
