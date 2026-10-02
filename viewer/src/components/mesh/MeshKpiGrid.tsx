import React from "react";
import { Activity, Globe, Lock, Server, Vote, Zap } from "lucide-react";
import type { MeshStatus, PeerProfile, RaftStatus } from "./types";

interface MeshKpiGridProps {
  localNode?: PeerProfile;
  meshStatus: MeshStatus | null;
  connectedPeers: PeerProfile[];
  raftStatus: RaftStatus | null;
}

export const MeshKpiGrid: React.FC<MeshKpiGridProps> = ({
  localNode,
  meshStatus,
  connectedPeers,
  raftStatus,
}) => {
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
      <div className="rounded-xl border border-[var(--border-c)] bg-[var(--card-bg)] p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--t3)]">
          <span>Local Node</span>
          <Server className="h-4 w-4 text-cyan-400" />
        </div>
        <p className="mt-2 font-mono text-sm font-bold text-white truncate">
          {localNode?.node_id || "node-local"}
        </p>
        <p className="text-[11px] text-[var(--t3)] font-mono">
          {localNode?.host}:{localNode?.port} ({localNode?.role})
        </p>
      </div>

      <div className="rounded-xl border border-[var(--border-c)] bg-[var(--card-bg)] p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--t3)]">
          <span>Cluster Health</span>
          <Activity className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-xl font-bold text-emerald-400">
            {meshStatus?.cluster_health || "STANDALONE"}
          </span>
        </div>
        <p className="text-[11px] text-[var(--t3)]">
          {connectedPeers.length > 0 ? "P2P Mesh synchronized" : "Local-only standalone mode"}
        </p>
      </div>

      <div className="rounded-xl border border-[var(--border-c)] bg-[var(--card-bg)] p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--t3)]">
          <span>Mesh Peers</span>
          <Globe className="h-4 w-4 text-purple-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-xl font-bold text-white">{connectedPeers.length}</span>
          <span className="text-xs text-[var(--t3)]">/ {meshStatus?.peer_count || 0} registered</span>
        </div>
        <p className="text-[11px] text-[var(--t3)]">Active ECDH encrypted channels</p>
      </div>

      <div className="rounded-xl border border-[var(--border-c)] bg-[var(--card-bg)] p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--t3)]">
          <span>Zero-Trust PKI</span>
          <Lock className="h-4 w-4 text-indigo-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className={`text-xl font-bold ${meshStatus?.pki_status === "ACTIVE" ? "text-emerald-400" : "text-amber-400"}`}>
            {meshStatus?.pki_status || "ACTIVE"}
          </span>
        </div>
        <p className="text-[11px] text-[var(--t3)]">
          {meshStatus?.verified_peers_count || 0} / {connectedPeers.length} Peers Verified
        </p>
      </div>

      <div className="rounded-xl border border-[var(--border-c)] bg-[var(--card-bg)] p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--t3)]">
          <span>Raft Role</span>
          <Vote className="h-4 w-4 text-cyan-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span
            className={`text-lg font-bold ${
              raftStatus?.role === "LEADER"
                ? "text-cyan-400"
                : raftStatus?.role === "CANDIDATE"
                ? "text-amber-400"
                : "text-purple-400"
            }`}
          >
            {raftStatus?.role || "LEADER"}
          </span>
          <span className="text-[10px] text-[var(--t3)] font-mono">T:{raftStatus?.term || 0}</span>
        </div>
        <p className="text-[11px] text-[var(--t3)]">
          Commit: {raftStatus?.commit_index || 0} (Quorum: {raftStatus?.quorum_size || 1})
        </p>
      </div>

      <div className="rounded-xl border border-[var(--border-c)] bg-[var(--card-bg)] p-4 shadow-sm">
        <div className="flex items-center justify-between text-xs text-[var(--t3)]">
          <span>Avg Peer Latency</span>
          <Zap className="h-4 w-4 text-amber-400" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-xl font-bold text-amber-400">{meshStatus?.avg_latency_ms || 0}</span>
          <span className="text-xs text-[var(--t3)]">ms</span>
        </div>
        <p className="text-[11px] text-[var(--t3)]">Round-trip gossip heartbeat</p>
      </div>
    </div>
  );
};
