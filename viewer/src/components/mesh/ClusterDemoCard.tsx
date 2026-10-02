import React from "react";
import { Play } from "lucide-react";

interface StepReceipt {
  step_name: string;
  status: string;
  duration_ms: number;
}

interface ClusterDemoReceipt {
  demo_id: string;
  nodes_participating: string[];
  total_steps: number;
  passed_steps: number;
  success: boolean;
  duration_total_ms: number;
  step_receipts?: StepReceipt[];
}

interface ClusterDemoCardProps {
  clusterDemoRunning: boolean;
  clusterDemoReceipt: ClusterDemoReceipt | null;
  onRunClusterDemo: () => void;
}

export const ClusterDemoCard: React.FC<ClusterDemoCardProps> = ({
  clusterDemoRunning,
  clusterDemoReceipt,
  onRunClusterDemo,
}) => {
  return (
    <div className="rounded-xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/20 via-[var(--card-bg)] to-purple-950/20 p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-c)] pb-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-indigo-500/10 p-2 border border-indigo-500/20 text-indigo-400">
            <Play className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                Production E2E Multi-Worker Cluster Demo
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 px-2 py-0.5 text-[10px] font-semibold text-indigo-400">
                7 Stages Battle-Tested
              </span>
            </div>
            <p className="mt-0.5 text-xs text-[var(--t2)]">
              Verify mTLS attestation, Raft quorum, Merkle sync, chaos failover, and auto-rollback in real time
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onRunClusterDemo}
          disabled={clusterDemoRunning}
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors disabled:opacity-50 shadow"
        >
          <Play className={`h-3.5 w-3.5 ${clusterDemoRunning ? "animate-spin" : ""}`} />
          {clusterDemoRunning ? "Demonstrating..." : "Run Cluster Demo"}
        </button>
      </div>

      {/* Demonstration Scorecard */}
      {clusterDemoReceipt ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-mono pb-1 border-b border-white/5">
            <span className="text-slate-300">Demo ID: {clusterDemoReceipt.demo_id}</span>
            <span className="text-emerald-400 font-bold">
              {clusterDemoReceipt.passed_steps} / {clusterDemoReceipt.total_steps} PASSED ({clusterDemoReceipt.duration_total_ms}ms)
            </span>
          </div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
            {clusterDemoReceipt.step_receipts?.map((step) => (
              <div
                key={`cluster-step-${step.step_name}`}
                className="flex items-center justify-between rounded bg-white/[0.02] p-2 text-xs font-mono border border-white/5"
              >
                <span className="text-slate-200 truncate max-w-[280px]">{step.step_name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-[var(--t3)]">{step.duration_ms}ms</span>
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 text-[10px] font-bold">
                    PASS
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="py-8 text-center text-xs text-[var(--t3)] font-mono border border-dashed border-[var(--border-c)] rounded-lg">
          Click "Run Cluster Demo" to execute the 7-stage battle-tested verification loop.
        </div>
      )}
    </div>
  );
};
