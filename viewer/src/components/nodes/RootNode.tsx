import type { NodeProps } from "reactflow";
import type { TopologyNodeData } from "../../types";
import { TopologyNodeBase } from "./TopologyNodeBase";

export function RootNode(props: NodeProps<TopologyNodeData>) {
  return <TopologyNodeBase {...props} tone="session_root" badge="Session" />;
}
