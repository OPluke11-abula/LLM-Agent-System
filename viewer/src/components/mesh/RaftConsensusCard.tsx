import React from "react";
import { AlertTriangle, CheckCircle2, FileText, GitCommit, RefreshCw, Vote } from "lucide-react";
import type { RaftLogEntry, RaftStatus } from "./types";

interface RaftConsensusCardProps {
  raftStatus: RaftStatus | null;
  raftLogs: RaftLogEntry[];
  electing: boolean;
  onTriggerElection: () => void;
}

export const RaftConsensusCard: React.FC<RaftConsensusCardProps> = ({
  raftStatus,
  raftLogs,
  electing,
  onTriggerElection,
}) => {
  return (
    <div className="mb-6 rounded-xl border border-cyan-500/30 bg-gradient-to-r from-cyan-950/20 via-[var(--card-bg)] to-blue-950/20 p-4">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-c)] pb-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-cyan-500/10 p-2 border border-cyan-500/20 text-cyan-400">
            <Vote className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">
                Raft Replicated Committee Debate Ledger
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-cyan-500/10 px-2 py-0.5 text-[10px] font-semibold text-cyan-400">
                <GitCommit className="h-3 w-3" />
                State Machine Applied: {raftStatus?.last_applied || 0}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-[var(--t2)]">
              Deterministic quorum commits over committee debate speech turns, security critique scores, and patch Merkle roots
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-[var(--t3)] font-mono">
            Leader: {raftStatus?.leader_id || "Self"}
          </span>
          <button
            type="button"
            onClick={onTriggerElection}
            disabled={electing}
            className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${electing ? "animate-spin" : ""}`} />
            Trigger Raft Election
          </button>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-[var(--border-c)] text-[var(--t3)] uppercase tracking-wider text-[10px]">
              <th className="pb-2 font-mono">Idx</th>
              <th className="pb-2 font-mono">Term</th>
              <th className="pb-2">Type</th>
              <th className="pb-2 font-mono">Author</th>
              <th className="pb-2">Payload Summary</th>
              <th className="pb-2 text-right">Quorum Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-c)] font-mono">
            {raftLogs.slice(-6).map((log) => {
              const isCommitted = log.index <= (raftStatus?.commit_index ?? 0);
              return (
                <tr key={`${log.index}-${log.term}`} className="hover:bg-white/5 transition-colors">
                  <td className="py-2 text-cyan-400 font-bold">{log.index}</td>
                  <td className="py-2 text-[var(--t3)]">{log.term}</td>
                  <td className="py-2 font-sans font-semibold text-[var(--t1)]">
                    <span className="inline-flex items-center gap-1 rounded bg-white/5 px-2 py-0.5 text-[10px]">
                      <FileText className="h-3 w-3 text-cyan-400" />
                      {log.entry_type}
                    </span>
                  </td>
                  <td className="py-2 text-[var(--t2)] truncate max-w-[120px]" title={log.author_node_id}>
                    {log.author_node_id}
                  </td>
                  <td className="py-2 font-sans text-[var(--t3)] text-[11px] truncate max-w-xs" title={JSON.stringify(log.payload)}>
                    {log.payload.task_id ? `[${log.payload.task_id}] ` : ""}
                    {log.payload.content || log.payload.decision || log.payload.desc || "Log payload"}
                  </td>
                  <td className="py-2 text-right">
                    {isCommitted ? (
                      <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                        <CheckCircle2 className="h-3 w-3" />
                        COMMITTED
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
                        <AlertTriangle className="h-3 w-3" />
                        UNCOMMITTED
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
