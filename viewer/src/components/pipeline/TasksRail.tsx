
import { Card, CardContent, CardHeader, CardTitle, StatusBadge } from "../ui/primitives";
import { cx, toneForStatus } from "../ui/utils";
import { Lock, Unlock } from "../ui/icons";
import type { TaskListItem } from "./types";

interface TasksRailProps {
  tasks: TaskListItem[];
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
}

export function TasksRail({ tasks, selectedTaskId, onSelectTask }: TasksRailProps) {
  return (
    <Card className="card-bg border-border-c">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider">
            Active Tasks ({tasks.length})
          </CardTitle>
          <span className="text-[10px] text-slate-400">Auto-Refreshed</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 max-h-[600px] overflow-y-auto">
        {tasks.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-400">
            No active coding tasks. Click "New Coding Task" to begin.
          </div>
        ) : (
          tasks.map((t) => {
            const isSelected = t.task_id === selectedTaskId;
            return (
              <div
                key={t.task_id}
                role="button"
                tabIndex={0}
                onClick={() => onSelectTask(t.task_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectTask(t.task_id);
                  }
                }}
                className={cx(
                  "group cursor-pointer rounded-lg border p-3 transition-all",
                  isSelected
                    ? "border-indigo-500/50 bg-indigo-500/10 shadow-[0_0_16px_rgba(99,102,241,0.2)]"
                    : "border-white/5 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
                )}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className="font-mono text-xs font-bold text-slate-200">{t.task_id}</span>
                  <StatusBadge
                    tone={toneForStatus(t.status === "PASS" ? "completed" : t.stage)}
                  >
                    {t.stage}
                  </StatusBadge>
                </div>
                <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed mb-2">
                  {t.requirement}
                </p>
                <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                  <span className="truncate max-w-[140px]">{t.target_branch}</span>
                  {t.has_plan && !t.plan_approved && (
                    <span className="text-amber-400 flex items-center gap-1 font-semibold">
                      <Lock className="h-3 w-3" /> Gate Locked
                    </span>
                  )}
                  {t.plan_approved && (
                    <span className="text-emerald-400 flex items-center gap-1">
                      <Unlock className="h-3 w-3" /> Gate Approved
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
