
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
    <Card className="card-bg border-[var(--border-c)]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider">
            活躍編程任務 ({tasks.length})
          </CardTitle>
          <span className="text-[10px] text-[var(--t3)]">自動同步更新</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 max-h-[600px] overflow-y-auto">
        {tasks.length === 0 ? (
          <div className="text-center py-8 text-xs text-[var(--t3)]">
            目前無進行中之編程任務。點擊「建立編程任務」以開始。
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
                  "group cursor-pointer rounded-md border p-3 transition-colors",
                  isSelected
                    ? "border-[var(--accent)] bg-[var(--bg-elevated)]"
                    : "border-[var(--border-c)] bg-[var(--bg-card)] hover:border-[var(--border-strong)]"
                )}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className="font-mono text-xs font-semibold text-[var(--t1)]">{t.task_id}</span>
                  <StatusBadge
                    tone={toneForStatus(t.status === "PASS" ? "completed" : t.stage)}
                  >
                    {t.stage}
                  </StatusBadge>
                </div>
                <p className="text-xs text-[var(--t2)] line-clamp-2 leading-relaxed mb-2">
                  {t.requirement}
                </p>
                <div className="flex items-center justify-between text-[10px] text-[var(--t3)] font-mono">
                  <span className="truncate max-w-[140px]">{t.target_branch}</span>
                  {t.has_plan && !t.plan_approved && (
                    <span className="text-amber-400 flex items-center gap-1 font-semibold">
                      <Lock className="h-3 w-3" /> 閘門待審
                    </span>
                  )}
                  {t.plan_approved && (
                    <span className="text-emerald-400 flex items-center gap-1">
                      <Unlock className="h-3 w-3" /> 閘門已核准
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
