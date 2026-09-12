import { ErrorEdge } from "./ErrorEdge";
import { HandoffEdge } from "./HandoffEdge";
import { RbacEdge } from "./RbacEdge";
import { ToolEdge } from "./ToolEdge";
import { TaskCategoryEdge } from "./TaskCategoryEdge";

export const TOPOLOGY_EDGE_TYPES = {
  handoffEdge: HandoffEdge,
  toolEdge: ToolEdge,
  rbacEdge: RbacEdge,
  errorEdge: ErrorEdge,
};

export const TASK_CATEGORY_EDGE_TYPES = {
  taskCategoryEdge: TaskCategoryEdge,
};
