import type { EdgeProps } from "reactflow";
import type { TopologyEdgeData } from "../../types";
import { TopologyEdgeBase } from "./TopologyEdgeBase";

export function RbacEdge(props: EdgeProps<TopologyEdgeData>) {
  const tone = props.data?.edgeType === "hitl" ? "hitl" : "rbac";
  return <TopologyEdgeBase {...props} tone={tone} />;
}
