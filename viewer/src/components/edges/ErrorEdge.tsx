import type { EdgeProps } from "reactflow";
import type { TopologyEdgeData } from "../../types";
import { TopologyEdgeBase } from "./TopologyEdgeBase";

export function ErrorEdge(props: EdgeProps<TopologyEdgeData>) {
  return <TopologyEdgeBase {...props} tone="error" />;
}
