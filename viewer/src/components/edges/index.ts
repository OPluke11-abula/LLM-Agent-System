import { ErrorEdge } from "./ErrorEdge";
import { HandoffEdge } from "./HandoffEdge";
import { RbacEdge } from "./RbacEdge";
import { ToolEdge } from "./ToolEdge";

export const TOPOLOGY_EDGE_TYPES = {
  handoffEdge: HandoffEdge,
  toolEdge: ToolEdge,
  rbacEdge: RbacEdge,
  errorEdge: ErrorEdge,
};
