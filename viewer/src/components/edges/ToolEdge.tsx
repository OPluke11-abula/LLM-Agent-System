import type { EdgeProps } from "reactflow";
import type { TopologyEdgeData } from "../../types";
import { TopologyEdgeBase } from "./TopologyEdgeBase";

export function ToolEdge(props: EdgeProps<TopologyEdgeData>) {
  return <TopologyEdgeBase {...props} tone="tool" />;
}
