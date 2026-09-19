
import { Card, CardContent, CardHeader, CardTitle } from "../ui/primitives";
import { cx } from "../ui/utils";
import { STAGES, type TaskDetailResponse } from "./types";

interface PipelineStageStepperProps {
  taskDetail: TaskDetailResponse;
}

export function PipelineStageStepper({ taskDetail }: PipelineStageStepperProps) {
  const currentStageIndex = () => {
    const stage = taskDetail.result.current_stage;
    if (stage === "COMPLETED") return STAGES.length;
    return STAGES.findIndex((s) => s.id === stage);
  };

  const curIdx = currentStageIndex();

  return (
    <Card className="card-bg border-border-c">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider">
            Execution Stepper: {taskDetail.task_id}
          </CardTitle>
          <span className="font-mono text-xs text-slate-400">
            Target: {taskDetail.request.target_branch}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-7 gap-2">
          {STAGES.map((s, idx) => {
            const isPast = curIdx > idx || taskDetail.result.current_stage === "COMPLETED";
            const isCurrent = curIdx === idx && taskDetail.result.current_stage !== "COMPLETED";

            return (
              <div
                key={s.id}
                className={cx(
                  "rounded-lg border p-2.5 text-center flex flex-col items-center justify-center transition-all",
                  isPast
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                    : isCurrent
                    ? "border-indigo-500 bg-indigo-500/20 text-white shadow-[0_0_16px_rgba(99,102,241,0.3)] animate-pulse"
                    : "border-white/5 bg-white/[0.02] text-slate-500"
                )}
              >
                <div className="mb-1 text-[10px] font-mono">Step {idx + 1}</div>
                <div className="text-xs font-bold leading-tight">{s.label}</div>
                <div className="mt-1 text-[9px] opacity-70 leading-tight hidden md:block">
                  {s.desc}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
