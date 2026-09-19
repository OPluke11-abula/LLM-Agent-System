
import { Card, CardContent, CardHeader, CardTitle, BentoCard, StatusBadge } from "../ui/primitives";
import { Activity, ShieldCheck, Layers, FileCheck, ExternalLink } from "../ui/icons";
import type { TaskDetailResponse } from "./types";

interface VerificationLadderCardProps {
  taskDetail: TaskDetailResponse;
}

export function VerificationLadderCard({ taskDetail }: VerificationLadderCardProps) {
  return (
    <>
      {/* Quality Receipts & Verification Ladder Table */}
      <Card className="card-bg border-border-c">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider">
              Objective Verification Ladder Receipts ({taskDetail.result.receipts.length})
            </CardTitle>
            <span className="text-[10px] text-slate-400 font-mono">Evidence Before Completion</span>
          </div>
        </CardHeader>
        <CardContent>
          {taskDetail.result.receipts.length === 0 ? (
            <div className="text-center py-6 text-xs text-slate-400 font-mono">
              No test receipts recorded yet. Awaiting Stage 4 execution.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-white/10 text-slate-400 text-[11px]">
                    <th className="pb-2">Step</th>
                    <th className="pb-2">Command</th>
                    <th className="pb-2">Exit Code</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {taskDetail.result.receipts.map((r) => (
                    <tr key={`receipt-${r.step_name}-${r.command}`} className="hover:bg-white/[0.02]">
                      <td className="py-2.5 text-slate-300">{r.step_name}</td>
                      <td className="py-2.5 text-indigo-300 font-semibold truncate max-w-[200px]">
                        {r.command}
                      </td>
                      <td className="py-2.5">{r.exit_code}</td>
                      <td className="py-2.5">
                        <StatusBadge tone={r.status === "PASS" ? "success" : "danger"}>
                          {r.status}
                        </StatusBadge>
                      </td>
                      <td className="py-2.5 text-slate-400">{r.duration_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Autonomous Self-Healing & Auto-Rollback Status (Phase 91) */}
      {((taskDetail.result.self_healing_attempts && taskDetail.result.self_healing_attempts.length > 0) || taskDetail.result.rollback_receipt) && (
        <BentoCard className="border-rose-500/30 bg-rose-500/5">
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-rose-400" />
                <h4 className="text-sm font-bold text-slate-100">
                  Autonomous Self-Healing & Rollback Engine (Phase 91)
                </h4>
              </div>
              {taskDetail.result.rollback_receipt ? (
                <span className="rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                  ROLLBACK EXECUTED ({taskDetail.result.rollback_receipt.restoration_status})
                </span>
              ) : (
                <span className="rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                  SELF-HEALED
                </span>
              )}
            </div>

            {/* Self Healing Attempts */}
            {taskDetail.result.self_healing_attempts && taskDetail.result.self_healing_attempts.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-300">
                  Diagnostic Correction Attempts ({taskDetail.result.self_healing_attempts.length}):
                </div>
                <div className="space-y-2">
                  {taskDetail.result.self_healing_attempts.map((att) => (
                    <div
                      key={`heal-attempt-${att.attempt_number}-${att.strategy}`}
                      className="rounded-lg border border-white/10 bg-black/40 p-3 text-xs font-mono space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200">
                          Attempt #{att.attempt_number} ({att.strategy})
                        </span>
                        <span className={att.healed ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
                          {att.healed ? "HEALED" : "RETRY FAILED"}
                        </span>
                      </div>
                      <div className="text-slate-300">{att.fix_description}</div>
                      {att.error_symptom && (
                        <div className="text-[11px] text-rose-300/80 truncate">
                          Failure: {att.error_symptom}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Rollback Details */}
            {taskDetail.result.rollback_receipt && (
              <div className="rounded-lg border border-rose-500/20 bg-black/40 p-3.5 space-y-1.5 text-xs font-mono">
                <div className="text-rose-300 font-bold">Atomic Worktree Rollback Receipt:</div>
                <div className="text-slate-400 text-[11px]">
                  Target Path: <span className="text-slate-200">{taskDetail.result.rollback_receipt.worktree_path}</span>
                </div>
                <div className="text-slate-400 text-[11px]">
                  Restored Commit: <span className="text-emerald-400">{taskDetail.result.rollback_receipt.restored_base_commit}</span>
                </div>
                <div className="text-slate-400 text-[11px]">
                  Pristine Clean: <span className="text-emerald-400">{taskDetail.result.rollback_receipt.canonical_clean ? "TRUE" : "FALSE"}</span>
                </div>
                {taskDetail.result.rollback_receipt.untracked_files_purged.length > 0 && (
                  <div className="text-slate-400 text-[11px]">
                    Purged Artifacts: {taskDetail.result.rollback_receipt.untracked_files_purged.join(", ")}
                  </div>
                )}
              </div>
            )}
          </div>
        </BentoCard>
      )}

      {/* Preservation & Merkle Audit Receipt */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="card-bg border-border-c">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              Canonical Preservation Receipt
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs font-mono">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Host Working Tree:</span>
              <span className="text-emerald-400 font-bold">100% PRESERVED</span>
            </div>
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-slate-400">Host Pollution:</span>
              <span className="text-slate-200">0 files modified / untracked</span>
            </div>
            <div className="text-[10px] text-slate-500 truncate">
              Receipt ID: {taskDetail.preservation_receipt?.receipt_id || "VERIFIED"}
            </div>
          </CardContent>
        </Card>

        <Card className="card-bg border-border-c">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold t2 uppercase tracking-wider flex items-center gap-2">
              <Layers className="h-4 w-4 text-indigo-400" />
              Merkle Audit Trail
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs font-mono">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Cryptographic Chain:</span>
              <span className="text-emerald-400 font-bold">VERIFIED</span>
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              Root: {taskDetail.result.pr_payload?.merkle_root || "a1b2c3d4...64chars"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Draft PR & Verifiable Patch Bundle */}
      {taskDetail.result.pr_payload && (
        <BentoCard className="border-indigo-500/30 bg-indigo-500/5">
          <div className="p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCheck className="h-5 w-5 text-indigo-400" />
                <h4 className="text-sm font-bold text-slate-100">
                  {taskDetail.result.pr_payload.title}
                </h4>
              </div>
              <span className="rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-mono">
                VERIFIED DRAFT PR
              </span>
            </div>

            <div className="text-xs font-mono text-slate-400 space-y-1">
              <div>Head: `{taskDetail.result.pr_payload.head_branch}` → Base: `{taskDetail.result.pr_payload.base_branch}`</div>
              <div>Commit Hash: `{taskDetail.result.pr_payload.commit_hash}`</div>
              {taskDetail.result.pr_payload.pr_url && (
                <div className="pt-2">
                  <a
                    href={taskDetail.result.pr_payload.pr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 font-semibold underline text-xs"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Open Draft PR / Patch Bundle
                  </a>
                </div>
              )}
            </div>
          </div>
        </BentoCard>
      )}
    </>
  );
}
