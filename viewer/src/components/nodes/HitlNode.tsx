import type { NodeProps } from "reactflow";
import type { TopologyNodeData } from "../../types";
import { TopologyNodeBase } from "./TopologyNodeBase";

export function HitlNode(props: NodeProps<TopologyNodeData>) {
  return <TopologyNodeBase {...props} tone="hitl_gate" badge="HITL" />;
}
