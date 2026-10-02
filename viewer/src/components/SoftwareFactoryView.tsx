import { useState } from "react";
import { useSoftwareFactory } from "../hooks/useSoftwareFactory";

export function SoftwareFactoryView() {
  const {
    overview,
    patterns,
    running,
    fetchOverview,
    handleRunPipeline,
  } = useSoftwareFactory();

  const [activeTab, setActiveTab] = useState<"waves" | "debate" | "patterns">("waves");

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4 md:p-6 space-y-6" style={{ background: "var(--bg)" }}>
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-xl border p-5 shadow-sm" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-3 w-3 rounded-full bg-emerald-500 animate-pulse" />
            <h1 className="text-xl font-bold tracking-tight" style={{ color: "var(--t1)" }}>
              Autonomous Software Factory Swarm
            </h1>
            <span className="rounded-md border px-2 py-0.5 text-xs font-mono font-medium text-emerald-400 border-emerald-500/30 bg-emerald-500/10">
              Protocol v3.8.0
            </span>
          </div>
          <p className="mt-1 text-xs" style={{ color: "var(--t2)" }}>
            Enterprise code modernization pipeline: AST Complexity &rarr; Scope-Isolated DAG &rarr; Red/Blue Debate &rarr; Closed-Loop Experience Distillation.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => fetchOverview()}
            className="rounded-lg border px-3 py-1.5 text-xs font-medium transition hover:bg-white/5 active:translate-y-px"
            style={{ borderColor: "var(--border-c)", color: "var(--t1)" }}
          >
            Refresh Telemetry
          </button>
          <button
            type="button"
            disabled={running}
            onClick={handleRunPipeline}
            className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white shadow transition hover:bg-emerald-500 active:translate-y-px disabled:opacity-50"
          >
            {running ? "Modernizing..." : "Run Factory Pipeline"}
          </button>
        </div>
      </div>

      {/* KPI Banner */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <div className="rounded-xl border p-4 shadow-sm" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium uppercase tracking-wider" style={{ color: "var(--t2)" }}>Modernized LOC</div>
          <div className="mt-2 text-2xl font-bold font-mono" style={{ color: "var(--t1)" }}>{overview.total_modernized_loc.toLocaleString()}</div>
          <div className="mt-1 text-[10px] text-emerald-400">AST Parsed & Quantified</div>
        </div>
        <div className="rounded-xl border p-4 shadow-sm" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium uppercase tracking-wider" style={{ color: "var(--t2)" }}>Active Waves</div>
          <div className="mt-2 text-2xl font-bold font-mono" style={{ color: "var(--t1)" }}>{overview.total_waves}</div>
          <div className="mt-1 text-[10px] text-emerald-400">100% Scope Isolated</div>
        </div>
        <div className="rounded-xl border p-4 shadow-sm" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium uppercase tracking-wider" style={{ color: "var(--t2)" }}>Quorum Approval</div>
          <div className="mt-2 text-2xl font-bold font-mono text-emerald-400">{overview.quorum_success_rate}%</div>
          <div className="mt-1 text-[10px]" style={{ color: "var(--t2)" }}>{overview.quorum_approved} Approved / {overview.quorum_rejected} Blocked</div>
        </div>
        <div className="rounded-xl border p-4 shadow-sm" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium uppercase tracking-wider" style={{ color: "var(--t2)" }}>Distilled Patterns</div>
          <div className="mt-2 text-2xl font-bold font-mono text-indigo-400">{overview.distilled_patterns_count}</div>
          <div className="mt-1 text-[10px]" style={{ color: "var(--t2)" }}>Living Architecture Synapses</div>
        </div>
        <div className="rounded-xl border p-4 shadow-sm" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium uppercase tracking-wider" style={{ color: "var(--t2)" }}>Merkle Tree Root</div>
          <div className="mt-2 text-sm font-mono truncate text-amber-400" title={overview.merkle_root}>
            {overview.merkle_root.slice(0, 12)}...
          </div>
          <div className="mt-1 text-[10px] text-amber-500/80">SHA-256 Proven Drift-Free</div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b" style={{ borderColor: "var(--border-c)" }}>
        <button
          type="button"
          onClick={() => setActiveTab("waves")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${activeTab === "waves" ? "border-emerald-500 text-emerald-400" : "border-transparent opacity-60 hover:opacity-100"}`}
        >
          Parallel Waves & Worktrees
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("debate")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${activeTab === "debate" ? "border-emerald-500 text-emerald-400" : "border-transparent opacity-60 hover:opacity-100"}`}
        >
          Red/Blue Adversarial Debate
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("patterns")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${activeTab === "patterns" ? "border-emerald-500 text-emerald-400" : "border-transparent opacity-60 hover:opacity-100"}`}
        >
          Vector Memory OS Patterns ({patterns.length})
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "waves" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl border p-4 space-y-3" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--t1)" }}>Wave 1: High Priority Decoupling</span>
              <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono text-emerald-400">EXECUTING</span>
            </div>
            <div className="space-y-2">
              <div className="rounded-lg border p-3 text-xs" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">Decompose giant core engine</span>
                  <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-[9px] font-mono text-indigo-300">MODULARIZE</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-gray-400">Scope: agent_workspace/core/engine.py</div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-emerald-400">
                  <span>Assigned: REASONING_ENGINE (Cloud-DeepSeek-R1)</span>
                </div>
              </div>
              <div className="rounded-lg border p-3 text-xs" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">Async I/O non-blocking rewrite</span>
                  <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[9px] font-mono text-cyan-300">ASYNC_MIGRATION</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-gray-400">Scope: agent_workspace/core/audit_ledger.py</div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-emerald-400">
                  <span>Assigned: SANDBOX_MUTATION (Edge-Worker-01)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border p-4 space-y-3" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--t1)" }}>Wave 2: Contract Hardening & Verification</span>
              <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-mono text-amber-400">QUEUED</span>
            </div>
            <div className="space-y-2">
              <div className="rounded-lg border p-3 text-xs" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">E2E Verification Ladder Expansion</span>
                  <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-mono text-amber-300">TEST_EXPANSION</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-gray-400">Scope: agent_workspace/tests/test_factory_decomposition_p101.py</div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-amber-400">
                  <span>Assigned: TEST_RUNNER (CI-Runner-01)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "debate" && (
        <div className="rounded-xl border p-5 space-y-4" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
          <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold" style={{ color: "var(--t1)" }}>Adversarial Audit: Async Non-blocking Pipeline</span>
              <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-mono text-emerald-400">QUORUM APPROVED (100.0/100)</span>
            </div>
            <span className="text-xs font-mono text-gray-400">Contract: shc-f9e5b105</span>
          </div>
          <div className="space-y-3 text-xs">
            <div className="rounded-lg border p-3 border-rose-500/30 bg-rose-500/5">
              <span className="font-bold text-rose-400">Turn 1 & 2 - Blue Team Security Attacker Probe:</span>
              <p className="mt-1 text-gray-300">Detected CONCURRENCY_RACE: Potential event loop lockup if synchronous sqlite3 calls are made directly inside coroutines.</p>
            </div>
            <div className="rounded-lg border p-3 border-blue-500/30 bg-blue-500/5">
              <span className="font-bold text-blue-400">Turn 3 - Blue Team QA Regression Guardian Assertion:</span>
              <p className="mt-1 text-gray-300">Mandated: Non-blocking execution duration must remain &lt; 500ms under 16-tenant load. Exit code 0 on all ladder tests.</p>
            </div>
            <div className="rounded-lg border p-3 border-emerald-500/30 bg-emerald-500/5">
              <span className="font-bold text-emerald-400">Turn 4 & 5 - Red Team Defense & Quorum Arbiter Decision:</span>
              <p className="mt-1 text-gray-300">Defensive patch: All database transactions wrapped with asyncio.to_thread and threading.RLock(). Quorum achieved with 0 unresolved critical defects.</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === "patterns" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {patterns.map((pat) => (
            <div key={pat.entry_id} className="rounded-xl border p-4 space-y-2" style={{ background: "var(--card-bg)", borderColor: "var(--border-c)" }}>
              <div className="flex items-center justify-between">
                <span className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold ${pat.category === "PATTERN" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}>
                  {pat.category}
                </span>
                <span className="text-[10px] font-mono text-gray-400">SHA: {pat.content_hash.slice(0, 10)}</span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "var(--t1)" }}>{pat.content}</p>
              <div className="flex items-center justify-between pt-2 text-[10px] text-gray-500 border-t" style={{ borderColor: "var(--border-c)" }}>
                <span>Task: {pat.task_id}</span>
                <span>Obsidian Backlink Synced</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
