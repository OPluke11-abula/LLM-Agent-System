import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from "reactflow";
import type { TopologyEdgeData, TopologyEdgeType } from "../../types";
import { EDGE_COLORS } from "../../utils/topologyUtils";

type TopologyEdgeBaseProps = EdgeProps<TopologyEdgeData> & {
  tone: TopologyEdgeType;
};

export function TopologyEdgeBase({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  data,
  tone,
}: TopologyEdgeBaseProps) {
  const color = EDGE_COLORS[tone];
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: color,
          strokeWidth: tone === "error" ? 2.8 : 2.2,
          filter: `drop-shadow(0 0 8px ${color}55)`,
        }}
      />
      {(tone === "handoff" || tone === "tool" || tone === "hitl" || tone === "rbac") && (
        <path
          d={edgePath}
          fill="none"
          stroke={color}
          strokeWidth={3.2}
          strokeDasharray="8 16"
          className="animate-flow-particles"
          style={{
            opacity: 0.85,
            pointerEvents: "none",
          }}
        />
      )}
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan absolute rounded-md border px-2 py-1 text-[10px] font-bold shadow-lg"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              background: "var(--bg-panel)",
              borderColor: `${color}88`,
              color,
            }}
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
