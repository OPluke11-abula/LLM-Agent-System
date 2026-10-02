import React from "react";
import {
  CheckCircle,
  CheckCircle2,
  Flame,
  Radio,
  ShieldAlert,
  ZapOff,
} from "lucide-react";
import type { ChaosFault, PeerProfile } from "./types";

interface ChaosConsoleCardProps {
  chaosFaults: ChaosFault[];
  chaosLoading: boolean;
  localNode?: PeerProfile;
  onInjectFault: (payload: any) => void;
  onClearChaos: (ruleId?: string) => void;
}

export const ChaosConsoleCard: React.FC<ChaosConsoleCardProps> = ({
  chaosFaults,
  chaosLoading,
  localNode,
  onInjectFault,
  onClearChaos,
}) => {
  return (
    <div className="rounded-xl border border-rose-500/30 bg-gradient-to-r from-rose-950/20 via-[var(--card-bg)] to-amber-950/20 p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-c)] pb-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-rose-500/10 p-2 border border-rose-500/20 text-rose-400">
            <Flame className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-rose-300">
                Chaos Fault Injection Console (ADR-006)
              </span>
              {chaosFaults.length > 0 ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/20 border border-rose-500/40 px-2 py-0.5 text-[10px] font-bold text-rose-400 animate-pulse">
                  <ShieldAlert className="h-3 w-3" />
                  {chaosFaults.length} FAULT(S) ACTIVE
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                  <CheckCircle className="h-3 w-3" />
                  NOMINAL
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-[var(--t2)]">
              Inject network partitions, latency spikes, and node isolation to test Raft failover & resilience
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onClearChaos()}
          disabled={chaosLoading || chaosFaults.length === 0}
          className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-40 transition-colors"
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          Clear Faults
        </button>
      </div>

      {/* Quick Action Buttons */}
      <div className="mb-4 grid grid-cols-1 sm:grid-cols-3 gap-2">
        <button
          type="button"
          onClick={() =>
            onInjectFault({
              fault_type: "NETWORK_PARTITION",
              source_node_ids: ["cluster-node-1"],
              target_node_ids: ["cluster-node-2", "cluster-node-3"],
              duration_seconds: 60,
              description: "Split-brain network partition isolating leader",
            })
          }
          disabled={chaosLoading}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-2.5 py-2 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition-colors disabled:opacity-50"
        >
          <ZapOff className="h-3.5 w-3.5 text-rose-400" />
          Split-Brain Partition
        </button>
        <button
          type="button"
          onClick={() =>
            onInjectFault({
              fault_type: "LATENCY_SPIKE",
              latency_ms: 500,
              duration_seconds: 60,
              description: "Cross-WAN artificial latency spike",
            })
          }
          disabled={chaosLoading}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition-colors disabled:opacity-50"
        >
          <Radio className="h-3.5 w-3.5 text-amber-400" />
          +500ms Latency
        </button>
        <button
          type="button"
          onClick={() =>
            onInjectFault({
              fault_type: "NODE_ISOLATION",
              source_node_ids: [localNode?.node_id || "cluster-node-1"],
              target_node_ids: [],
              duration_seconds: 60,
              description: "Physical ingress/egress node isolation",
            })
          }
          disabled={chaosLoading}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-purple-500/30 bg-purple-500/10 px-2.5 py-2 text-xs font-semibold text-purple-300 hover:bg-purple-500/20 transition-colors disabled:opacity-50"
        >
          <ShieldAlert className="h-3.5 w-3.5 text-purple-400" />
          Isolate Node
        </button>
      </div>

      {/* Active Rules List */}
      {chaosFaults.length === 0 ? (
        <div className="py-6 text-center text-xs text-[var(--t3)] font-mono border border-dashed border-[var(--border-c)] rounded-lg">
          No active chaos faults. Cluster transport running at wire speed.
        </div>
      ) : (
        <div className="space-y-2">
          {chaosFaults.map((f) => (
            <div
              key={f.rule_id}
              className="flex items-center justify-between rounded-lg border border-rose-500/30 bg-black/40 p-2.5 text-xs font-mono"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-rose-400">{f.fault_type}</span>
                  <span className="text-[10px] text-[var(--t3)]">{f.rule_id}</span>
                </div>
                <div className="text-[11px] text-slate-300 mt-0.5">
                  Scope: {f.source_node_ids?.length ? f.source_node_ids.join(",") : "*"} →{" "}
                  {f.target_node_ids?.length ? f.target_node_ids.join(",") : "*"}
                  {f.latency_ms > 0 && ` (${f.latency_ms}ms delay)`}
                </div>
              </div>
              <button
                type="button"
                onClick={() => onClearChaos(f.rule_id)}
                className="text-[11px] text-slate-400 hover:text-rose-300 px-2 py-1 rounded bg-white/5 hover:bg-white/10 transition-colors"
              >
                Clear
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
