import type { NodeProps } from "reactflow";
import type { TopologyNodeData } from "../../types";
import { TopologyNodeBase } from "./TopologyNodeBase";

export function ToolNode(props: NodeProps<TopologyNodeData>) {
  return <TopologyNodeBase {...props} tone="tool_call" badge="Tool" />;
}
