
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
    <Card className="card-bg border-[var(--border-c)]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider">
            流水線執行階段進度：{taskDetail.task_id}
          </CardTitle>
          <span className="font-mono text-xs text-[var(--t3)]">
            目標分支: {taskDetail.request.target_branch}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 xl:grid-cols-9 gap-2">
          {STAGES.map((s, idx) => {
            const isPast = curIdx > idx || taskDetail.result.current_stage === "COMPLETED";
            const isCurrent = curIdx === idx && taskDetail.result.current_stage !== "COMPLETED";

            return (
              <div
                key={s.id}
                className={cx(
                  "rounded-md border p-2 text-center flex flex-col items-center justify-center transition-colors",
                  isPast
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                    : isCurrent
                    ? "border-[var(--accent)] bg-[var(--bg-elevated)] text-[var(--accent)] font-medium"
                    : "border-[var(--border-c)] bg-[var(--bg-muted)] text-[var(--t3)]"
                )}
              >
                <div className="mb-0.5 text-[10px] font-mono">Step {idx + 1}</div>
                <div className="text-xs font-semibold leading-tight">{s.label}</div>
                <div className="mt-0.5 text-[9px] opacity-70 leading-tight hidden md:block">
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
