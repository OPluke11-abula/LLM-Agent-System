import type { EdgeProps } from "reactflow";
import type { TopologyEdgeData } from "../../types";
import { TopologyEdgeBase } from "./TopologyEdgeBase";

export function HandoffEdge(props: EdgeProps<TopologyEdgeData>) {
  return <TopologyEdgeBase {...props} tone="handoff" />;
}
