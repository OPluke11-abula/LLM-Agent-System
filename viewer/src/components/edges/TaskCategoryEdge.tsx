import { BaseEdge, getBezierPath, type EdgeProps } from "reactflow";

type TaskCategory = "dependency" | "data_flow" | "feedback_loop" | "parallel_trigger";

type TaskCategoryEdgeData = {
  category?: TaskCategory;
  isDimmed?: boolean;
};

const EDGE_PRESENTATION: Record<TaskCategory, { color: string; dash?: string; width: number }> = {
  dependency: { color: "#22d3ee", width: 2 },
  data_flow: { color: "#10b981", dash: "6 12", width: 2.2 },
  feedback_loop: { color: "#f59e0b", dash: "5 7", width: 2.6 },
  parallel_trigger: { color: "#eab308", dash: "2 14", width: 2.4 },
};

function categoryOf(value: unknown): TaskCategory {
  return value === "data_flow" || value === "feedback_loop" || value === "parallel_trigger"
    ? value
    : "dependency";
}

export function TaskCategoryEdge({
  id,
  sourceX,
  sourceY,
  sourcePosition,
  targetX,
  targetY,
  targetPosition,
  markerEnd,
  data,
  style,
}: EdgeProps<TaskCategoryEdgeData>) {
  const category = categoryOf(data?.category);
  const presentation = EDGE_PRESENTATION[category];
  const [edgePath] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });
  const opacity = data?.isDimmed ? 0.2 : 1;
  const edgeStyle = {
    ...style,
    stroke: presentation.color,
    strokeWidth: presentation.width,
    opacity,
    filter: `drop-shadow(0 0 6px ${presentation.color}55)`,
  };

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={edgeStyle} />
      {category === "feedback_loop" && (
        <path
          d={edgePath}
          fill="none"
          stroke={presentation.color}
          strokeWidth={presentation.width + 0.8}
          strokeDasharray={presentation.dash}
          className="feedback-loop-edge"
          style={{ opacity, pointerEvents: "none" }}
        />
      )}
      {(category === "data_flow" || category === "parallel_trigger") && (
        <path
          d={edgePath}
          fill="none"
          stroke={presentation.color}
          strokeWidth={presentation.width + 1}
          strokeDasharray={presentation.dash}
          className="animate-flow-particles"
          style={{ opacity, pointerEvents: "none" }}
        />
      )}
    </>
  );
}
