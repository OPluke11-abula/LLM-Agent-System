import React from "react";
import {
  AlertTriangle,
  Network,
  Plus,
  RefreshCw,
  ShieldCheck,
  Zap,
} from "lucide-react";
import type { PeerProfile } from "./types";

interface ConnectedPeersSectionProps {
  connectedPeers: PeerProfile[];
  attestingNode: string | null;
  onAttestPeer: (peer: PeerProfile) => void;
  onOpenJoinModal: () => void;
}

export const ConnectedPeersSection: React.FC<ConnectedPeersSectionProps> = ({
  connectedPeers,
  attestingNode,
  onAttestPeer,
  onOpenJoinModal,
}) => {
  return (
    <div className="flex-1">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--t2)]">
          Connected Mesh Peers ({connectedPeers.length})
        </h2>
      </div>

      {connectedPeers.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[var(--border-c)] p-12 text-center">
          <Network className="h-10 w-10 text-[var(--t3)] opacity-40 mb-3" />
          <h3 className="text-sm font-semibold text-white">No Remote Mesh Peers Connected</h3>
          <p className="mt-1 max-w-md text-xs text-[var(--t3)] leading-relaxed">
            This node is operating in local standalone mode. To offload committee debate reasoning or heavy test
            verification ladders across your local network or cluster, click "Join Seed Node".
          </p>
          <button
            type="button"
            onClick={onOpenJoinModal}
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500"
          >
            <Plus className="h-4 w-4" />
            Connect to Seed Peer
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {connectedPeers.map((peer) => (
            <div
              key={peer.node_id}
              className="flex flex-col justify-between rounded-xl border border-[var(--border-c)] bg-[var(--card-bg)] p-4 shadow-sm hover:border-cyan-500/40 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-white truncate max-w-[160px]" title={peer.node_id}>
                    {peer.node_id}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {peer.attestation_status === "VERIFIED" ? (
                      <span
                        className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400"
                        title="Zero-Trust mTLS Attested"
                      >
                        <ShieldCheck className="h-3 w-3" />
                        ATTESTED
                      </span>
                    ) : (
                      <span
                        className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-400"
                        title="Attestation Pending"
                      >
                        <AlertTriangle className="h-3 w-3" />
                        {peer.attestation_status || "PENDING"}
                      </span>
                    )}
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      {peer.status}
                    </span>
                  </div>
                </div>

                <div className="mt-2 text-[11px] text-[var(--t3)] font-mono">
                  {peer.host}:{peer.port} • <span className="capitalize">{peer.role}</span>
                </div>

                {/* Capabilities */}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {peer.capabilities.map((cap) => (
                    <span
                      key={cap}
                      className="rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-[var(--t2)]"
                    >
                      {cap}
                    </span>
                  ))}
                </div>

                {/* PKI Fingerprint */}
                {peer.cert_fingerprint && (
                  <div className="mt-2.5 text-[10px] font-mono text-[var(--t3)] truncate" title={peer.cert_fingerprint}>
                    <span className="text-indigo-400">SHA256:</span> {peer.cert_fingerprint.slice(0, 16)}...
                  </div>
                )}

                {/* Attest Action for non-verified peers */}
                {peer.attestation_status !== "VERIFIED" && (
                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={() => onAttestPeer(peer)}
                      disabled={attestingNode === peer.node_id}
                      className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition-colors disabled:opacity-50"
                    >
                      {attestingNode === peer.node_id ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          Verifying Nonce...
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="h-3.5 w-3.5" />
                          Attest Peer Now
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>

              {/* Telemetry Footer */}
              <div className="mt-4 border-t border-[var(--border-c)] pt-3 flex items-center justify-between text-xs text-[var(--t3)]">
                <div className="flex items-center gap-1">
                  <Zap className="h-3 w-3 text-amber-400" />
                  <span>{peer.latency_ms.toFixed(1)}ms</span>
                </div>
                <div>
                  <span>Load: </span>
                  <span className="font-mono text-white">{(peer.load_score * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
