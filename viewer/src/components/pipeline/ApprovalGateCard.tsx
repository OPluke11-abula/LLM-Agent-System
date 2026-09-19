
import { BentoCard, ShimmerButton } from "../ui/primitives";
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
  if (!isAwaiting) return null;

  return (
    <BentoCard className="border-amber-500/40 bg-amber-500/10 shadow-[0_0_24px_rgba(245,158,11,0.15)]">
      <div className="p-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400">
              <Lock className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-amber-200">
                Stop-and-Wait Architecture Gate: Human Approval Required
              </h3>
              <p className="text-xs text-amber-300/80">
                Protocol Rule 0.2: Code changes and file-editing tools are blocked until explicit confirmation.
              </p>
            </div>
          </div>
          <span className="rounded border border-amber-500/40 bg-amber-500/20 px-2 py-0.5 text-[10px] font-mono text-amber-300">
            GATE LOCKED
          </span>
        </div>

        <div className="rounded-lg border border-amber-500/20 bg-black/40 p-3.5 space-y-2 text-xs">
          <div>
            <span className="text-slate-400 font-mono">Plan Summary: </span>
            <span className="text-slate-200 font-medium">{taskDetail.plan.plan_summary}</span>
          </div>
          <div>
            <span className="text-slate-400 font-mono">Assigned Role: </span>
            <span className="text-indigo-400 font-mono font-bold">{taskDetail.plan.assigned_role}</span>
          </div>
          <div>
            <span className="text-slate-400 font-mono">Target Files: </span>
            <span className="text-slate-200 font-mono">{taskDetail.plan.target_files.join(", ")}</span>
          </div>
          <div>
            <span className="text-slate-400 font-mono">Test Strategy: </span>
            <span className="text-emerald-400 font-mono">{taskDetail.plan.test_strategy.join("; ") || "Default ladder"}</span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <div className="flex-1 w-full flex items-center gap-2">
            <Key className="h-4 w-4 text-amber-400 shrink-0" />
            <input
              type="text"
              aria-label="Approval token"
              value={approvalToken}
              onChange={(e) => setApprovalToken(e.target.value)}
              placeholder="Enter approval token..."
              className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-amber-500"
            />
          </div>
          <ShimmerButton
            onClick={onApprove}
            disabled={loading || !approvalToken}
            className="w-full sm:w-auto text-xs px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white font-bold"
          >
            <Unlock className="h-3.5 w-3.5 mr-1.5" />
            Authorize & Execute Pipeline
          </ShimmerButton>
        </div>
      </div>
    </BentoCard>
  );
}
