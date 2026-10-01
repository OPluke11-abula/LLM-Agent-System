import { Layers } from "../ui/icons";
import type { CompanionStatus } from "../../hooks/useAmbientCompanion";

interface CompanionStageTrackerProps {
  stage: string;
  currentStageIndex: number;
  totalStages: number;
  status: CompanionStatus;
}

export function CompanionStageTracker({
  stage,
  currentStageIndex,
  totalStages,
  status,
}: CompanionStageTrackerProps) {
  return (
    <div
      data-testid="companion-stage-tracker"
      className="space-y-1.5 p-2 rounded-xl bg-white/[0.03] border border-white/5"
    >
      <div className="flex items-center justify-between text-[10px] font-mono">
        <span className="text-slate-400 flex items-center gap-1">
          <Layers className="h-3 w-3 text-cyan-400" />
          <span>STAGE</span>
        </span>
        <span className="font-bold text-cyan-300">{stage}</span>
        <span className="text-slate-500">
          ({currentStageIndex >= 0 ? currentStageIndex + 1 : 1}/{totalStages})
        </span>
      </div>
      <div className="grid grid-cols-9 gap-1 h-1.5 rounded-full overflow-hidden bg-slate-900">
        {Array.from({ length: totalStages }).map((_, idx) => {
          const isDone = currentStageIndex > idx || status === "verified";
          const isCurrent = currentStageIndex === idx;
          return (
            <div
              key={idx}
              className={`h-full transition-colors duration-300 ${
                isDone
                  ? "bg-emerald-500"
                  : isCurrent
                  ? "bg-cyan-400 animate-pulse"
                  : "bg-slate-800"
              }`}
            />
          );
        })}
      </div>
    </div>
  );
}
