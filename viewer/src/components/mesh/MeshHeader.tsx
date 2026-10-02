import React from "react";
import { Network, Plus, RefreshCw } from "lucide-react";

interface MeshHeaderProps {
  loading: boolean;
  onRefresh: () => void;
  onOpenJoinModal: () => void;
}

export const MeshHeader: React.FC<MeshHeaderProps> = ({
  loading,
  onRefresh,
  onOpenJoinModal,
}) => {
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-c)] pb-5">
      <div>
        <div className="flex items-center gap-2">
          <Network className="h-6 w-6 text-cyan-400" />
          <h1 className="text-xl font-bold tracking-tight">Distributed P2P Mesh & Worktree Cluster</h1>
          <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 text-xs font-semibold text-cyan-400">
            Phase 87 - 91 (Zero-Trust mTLS, Raft Consensus, Vector Memory & Chaos Resilience)
          </span>
        </div>
        <p className="mt-1 text-xs text-[var(--t3)]">
          Decentralized peer capability advertising, zero-trust mutual attestation, Raft replicated consensus, and chaos fault injection
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-[var(--border-c)] bg-[var(--card-bg)] px-3 py-1.5 text-xs font-medium hover:bg-white/5 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
        <button
          type="button"
          onClick={onOpenJoinModal}
          className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white shadow hover:bg-cyan-500 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Join Seed Node
        </button>
      </div>
    </div>
  );
};
