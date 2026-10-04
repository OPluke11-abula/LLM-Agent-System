
import { Card, Button } from "../ui/primitives";
import { Lock, Unlock, Key } from "../ui/icons";
import type { TaskDetailResponse } from "./types";

interface ApprovalGateCardProps {
  taskDetail: TaskDetailResponse;
  approvalToken: string;
  setApprovalToken: (v: string) => void;
  loading: boolean;
  onApprove: () => void;
}

export function ApprovalGateCard({
  taskDetail,
  approvalToken,
  setApprovalToken,
  loading,
  onApprove,
}: ApprovalGateCardProps) {
  if (!taskDetail.plan) return null;
  const isAwaiting = !taskDetail.plan.human_approved && taskDetail.result.current_stage !== "COMPLETED";

  if (!isAwaiting) {
    if (!taskDetail.plan.human_approved) return null;

    return (
      <Card className="border-emerald-500/30 bg-emerald-500/5">
        <div className="p-4 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="p-1 rounded-md bg-emerald-500/15 text-emerald-400">
                <Unlock className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-xs font-semibold text-emerald-200">
                  Stop-and-Wait 架構閘門：已批准授權
                </h3>
                <p className="text-[11px] text-emerald-300/80">
                  變更範疇已驗證，執行已獲准。Token:{" "}
                  <span className="font-mono font-semibold text-emerald-300">
                    {taskDetail.plan.approval_token || "***VERIFIED"}
                  </span>
                </p>
              </div>
            </div>
            <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono text-emerald-300">
              GATE UNLOCKED
            </span>
          </div>
          <div className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-2.5 text-[11px] font-mono space-y-1 text-[var(--t2)]">
            <div>
              <span className="text-[var(--t3)]">授權角色 (Authorized Role): </span>
              <span className="text-emerald-400 font-semibold">{taskDetail.plan.assigned_role}</span>
            </div>
            <div>
              <span className="text-[var(--t3)]">目標修改檔案 (Target Files): </span>
              <span className="text-[var(--t1)]">{taskDetail.plan.target_files.join(", ")}</span>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="border-amber-500/30 bg-amber-500/5">
      <div className="p-4 sm:p-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-md bg-amber-500/15 text-amber-400">
              <Lock className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-amber-200">
                Stop-and-Wait 架構閘門：需要人機確認
              </h3>
              <p className="text-[11px] text-amber-300/80">
                Protocol Rule 0.2: 檔案編輯工具與代碼變更在取得確認前嚴格受阻。
              </p>
            </div>
          </div>
          <span className="rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-mono text-amber-300">
            閘門鎖定 (GATE LOCKED)
          </span>
        </div>

        <div className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-3 space-y-1.5 text-xs">
          <div>
            <span className="text-[var(--t3)] font-mono">架構計畫摘要: </span>
            <span className="text-[var(--t1)] font-medium">{taskDetail.plan.plan_summary}</span>
          </div>
          <div>
            <span className="text-[var(--t3)] font-mono">指派角色: </span>
            <span className="text-[var(--accent)] font-mono font-semibold">{taskDetail.plan.assigned_role}</span>
          </div>
          <div>
            <span className="text-[var(--t3)] font-mono">目標修改檔案: </span>
            <span className="text-[var(--t1)] font-mono">{taskDetail.plan.target_files.join(", ")}</span>
          </div>
          <div>
            <span className="text-[var(--t3)] font-mono">測試驗證策略: </span>
            <span className="text-emerald-400 font-mono">{taskDetail.plan.test_strategy.join("; ") || "Default ladder"}</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-2.5 pt-1">
          <div className="flex-1 w-full flex items-center gap-2">
            <Key className="h-4 w-4 text-amber-400 shrink-0" />
            <input
              type="text"
              aria-label="Approval token"
              value={approvalToken}
              onChange={(e) => setApprovalToken(e.target.value)}
              placeholder="輸入審批令牌 (Approval Token)..."
              className="w-full bg-[var(--bg-card)] border border-[var(--border-c)] rounded-md px-3 py-1.5 text-xs text-[var(--t1)] font-mono focus:outline-none focus:border-amber-500"
            />
          </div>
          <Button
            variant="warning"
            size="md"
            onClick={onApprove}
            disabled={loading || !approvalToken}
            className="w-full sm:w-auto text-xs px-3.5 py-1.5 font-medium"
          >
            <Unlock className="h-3.5 w-3.5 mr-1" />
            確認授權並執行
          </Button>
        </div>
      </div>
    </Card>
  );
}
