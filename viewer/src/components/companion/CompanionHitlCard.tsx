import { FileCode, Key, Unlock } from "../ui/icons";
import type { CompanionTask } from "../../hooks/useAmbientCompanion";

interface CompanionHitlCardProps {
  activeTask: CompanionTask;
  approvalToken: string;
  submitting: boolean;
  onTokenChange: (token: string) => void;
  onApprove: () => void;
  onDeny: () => void;
}

export function CompanionHitlCard({
  activeTask,
  approvalToken,
  submitting,
  onTokenChange,
  onApprove,
  onDeny,
}: CompanionHitlCardProps) {
  return (
    <div
      data-testid="companion-hitl-card"
      className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-3 space-y-2.5 transition-colors shadow-inner"
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold font-mono tracking-wider text-amber-300 uppercase px-1.5 py-0.5 rounded bg-amber-500/20 border border-amber-500/30">
          人機協同審批請求 (HITL)
        </span>
        <span className="text-[10px] font-mono text-[var(--t3)]">{activeTask.taskId}</span>
      </div>

      <div className="space-y-1 text-xs">
        <p className="text-[var(--t1)] font-medium text-[11px] line-clamp-2">
          {activeTask.planSummary || "等待架構閘門核准簽署。"}
        </p>
        {activeTask.targetFiles && activeTask.targetFiles.length > 0 && (
          <div className="flex items-center gap-1 text-[10px] font-mono text-amber-200/90 truncate">
            <FileCode className="h-3 w-3 shrink-0 text-amber-400" />
            <span>{activeTask.targetFiles.join(", ")}</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-1.5 pt-1">
        <Key className="h-3 w-3 text-amber-400 shrink-0" />
        <input
          type="password"
          aria-label="HITL Approval Token"
          value={approvalToken}
          onChange={(e) => onTokenChange(e.target.value)}
          placeholder="輸入審批令牌..."
          className="w-full bg-[var(--bg-base)] border border-[var(--border-c)] rounded px-2 py-1 text-[11px] text-[var(--t1)] font-mono focus:outline-none focus:border-amber-400"
        />
      </div>

      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={onApprove}
          disabled={submitting}
          aria-label="Allow (PO Luke)"
          title="Allow (PO Luke)"
          className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-950/50 transition-colors disabled:opacity-50"
        >
          <Unlock className="h-3.5 w-3.5" />
          <span>{submitting ? "核准中..." : "核准執行 Allow (PO Luke)"}</span>
        </button>

        <button
          type="button"
          onClick={onDeny}
          disabled={submitting}
          aria-label="Deny mutation"
          className="inline-flex items-center justify-center px-3 py-1.5 rounded-lg bg-rose-950/60 hover:bg-rose-900 border border-rose-800/60 text-rose-300 font-medium text-xs transition-colors disabled:opacity-50"
        >
          <span>拒絕</span>
        </button>
      </div>
    </div>
  );
}
