import { useState } from "react";
import { useSoftwareFactory } from "../hooks/useSoftwareFactory";
import { Boxes, RefreshCw, Play, ShieldCheck, GitFork, Cpu } from "./ui/icons";

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
    <div className="flex h-full flex-col overflow-y-auto p-4 md:p-6 space-y-6" style={{ background: "var(--bg-base)" }}>
      {/* Top Banner */}
      <div
        className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-xl border p-5 shadow-sm acrylic-surface"
        style={{ borderColor: "var(--border-c)" }}
      >
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Boxes className="h-5 w-5 text-indigo-400" />
              自主軟體工廠協同叢集
            </h1>
            <span className="rounded-md border px-2 py-0.5 text-xs font-mono font-medium text-indigo-300 border-indigo-500/30 bg-indigo-500/10">
              協定基準線 v3.8.0
            </span>
            <span
              className="rounded-md border px-2 py-0.5 text-[11px] font-mono text-amber-300/90 border-amber-500/30 bg-amber-500/10 truncate max-w-[240px]"
              title={overview.merkle_root}
            >
              Merkle 根雜湊: {overview.merkle_root.slice(0, 10)}... (無漂移保證)
            </span>
          </div>
          <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
            企業級代碼現代化流水線：AST 複雜度分析 → 作用域隔離工作樹 → 紅藍對抗審核 → 經驗蒸餾閉環。
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => fetchOverview()}
            className="quiet-button inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium"
          >
            <RefreshCw className="h-3.5 w-3.5 text-slate-400" />
            <span>重新整理遙測</span>
          </button>
          <button
            type="button"
            disabled={running}
            onClick={handleRunPipeline}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-500 active:translate-y-px disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" />
            <span>{running ? "現代化執行中..." : "啟動工廠流水線"}</span>
          </button>
        </div>
      </div>

      {/* Balanced 4-Card KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border p-4 shadow-sm acrylic-surface" style={{ borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium text-slate-400 tracking-wider">已重構代碼量 (LOC)</div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-100">{overview.total_modernized_loc.toLocaleString()}</div>
          <div className="mt-1 text-[11px] text-indigo-400">AST 語法樹解析與量化</div>
        </div>

        <div className="rounded-xl border p-4 shadow-sm acrylic-surface" style={{ borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium text-slate-400 tracking-wider">活躍工作樹波次</div>
          <div className="mt-2 text-2xl font-bold font-mono text-slate-100">{overview.total_waves} 個波次</div>
          <div className="mt-1 text-[11px] text-emerald-400">100% 作用域實體隔離</div>
        </div>

        <div className="rounded-xl border p-4 shadow-sm acrylic-surface" style={{ borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium text-slate-400 tracking-wider">仲裁審核通過率</div>
          <div className="mt-2 text-2xl font-bold font-mono text-emerald-400">{overview.quorum_success_rate}%</div>
          <div className="mt-1 text-[11px] text-slate-400">{overview.quorum_approved} 通過 / {overview.quorum_rejected} 阻擋</div>
        </div>

        <div className="rounded-xl border p-4 shadow-sm acrylic-surface" style={{ borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium text-slate-400 tracking-wider">已蒸餾架構模式</div>
          <div className="mt-2 text-2xl font-bold font-mono text-indigo-400">{overview.distilled_patterns_count} 組經驗</div>
          <div className="mt-1 text-[11px] text-slate-400">Obsidian 雙向鏈結同步</div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b" style={{ borderColor: "var(--border-c)" }}>
        <button
          type="button"
          onClick={() => setActiveTab("waves")}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === "waves"
              ? "border-indigo-500 text-indigo-300"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <GitFork className="h-3.5 w-3.5" />
          <span>並行工作樹與波次</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("debate")}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === "debate"
              ? "border-indigo-500 text-indigo-300"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <ShieldCheck className="h-3.5 w-3.5" />
          <span>紅藍對抗審核辯論</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("patterns")}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold border-b-2 transition ${
            activeTab === "patterns"
              ? "border-indigo-500 text-indigo-300"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="h-3.5 w-3.5" />
          <span>架構模式經驗庫 ({patterns.length})</span>
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "waves" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl border p-4 space-y-3 acrylic-surface" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold tracking-wider text-slate-200">波次 1：高優先級解耦重構</span>
              <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono text-emerald-400 border border-emerald-500/20">
                執行中
              </span>
            </div>
            <div className="space-y-2">
              <div className="rounded-lg border p-3 text-xs bg-slate-900/40" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-100">巨石核心引擎拆分解耦</span>
                  <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-[9px] font-mono text-indigo-300">模組解耦</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-slate-400">作用域: agent_workspace/core/engine.py</div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-indigo-400">
                  <span>指派代理人: REASONING_ENGINE (Cloud-DeepSeek-R1)</span>
                </div>
              </div>
              <div className="rounded-lg border p-3 text-xs bg-slate-900/40" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-100">異步非阻塞 I/O 全面重構</span>
                  <span className="rounded bg-cyan-500/20 px-1.5 py-0.5 text-[9px] font-mono text-cyan-300">異步遷移</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-slate-400">作用域: agent_workspace/core/audit_ledger.py</div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-cyan-400">
                  <span>指派節點: SANDBOX_MUTATION (Edge-Worker-01)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border p-4 space-y-3 acrylic-surface" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold tracking-wider text-slate-200">波次 2：契約強化與多階驗證</span>
              <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-mono text-amber-400 border border-amber-500/20">
                排隊中
              </span>
            </div>
            <div className="space-y-2">
              <div className="rounded-lg border p-3 text-xs bg-slate-900/40" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-100">端到端驗證天梯擴充</span>
                  <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-mono text-amber-300">測試擴充</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-slate-400">作用域: agent_workspace/tests/test_factory_decomposition_p101.py</div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-amber-400">
                  <span>指派節點: TEST_RUNNER (CI-Runner-01)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "debate" && (
        <div className="rounded-xl border p-5 space-y-4 acrylic-surface" style={{ borderColor: "var(--border-c)" }}>
          <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-100">對抗性審核：異步非阻塞管線</span>
              <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-mono text-emerald-400 border border-emerald-500/30">
                仲裁全票批准 (100.0/100)
              </span>
            </div>
            <span className="text-xs font-mono text-slate-400">契約 ID: shc-f9e5b105</span>
          </div>
          <div className="space-y-3 text-xs">
            <div className="rounded-lg border p-3 border-rose-500/30 bg-rose-500/5">
              <span className="font-bold text-rose-400">回合 1 & 2 - 藍隊資安攻擊者探針：</span>
              <p className="mt-1 text-slate-300 leading-relaxed">
                檢測到併發競態風險 (CONCURRENCY_RACE)：若於協程中直接調用同步 sqlite3，在高負載下將引發事件迴圈阻塞。
              </p>
            </div>
            <div className="rounded-lg border p-3 border-blue-500/30 bg-blue-500/5">
              <span className="font-bold text-blue-400">回合 3 - 藍隊 QA 回歸防衛者斷言：</span>
              <p className="mt-1 text-slate-300 leading-relaxed">
                硬性約束：16 租戶並發壓力下，非阻塞執行時長必須維持 &lt; 500ms，全套階梯測試必須 100% 回傳 Exit Code 0。
              </p>
            </div>
            <div className="rounded-lg border p-3 border-emerald-500/30 bg-emerald-500/5">
              <span className="font-bold text-emerald-400">回合 4 & 5 - 紅隊防禦性修復與仲裁裁決：</span>
              <p className="mt-1 text-slate-300 leading-relaxed">
                防禦補丁：所有資料庫事務均封裝於 asyncio.to_thread 與 threading.RLock()。仲裁全票批准，無未處置之重大缺陷。
              </p>
            </div>
          </div>
        </div>
      )}

      {activeTab === "patterns" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {patterns.map((pat) => (
            <div key={pat.entry_id} className="rounded-xl border p-4 space-y-2 acrylic-surface" style={{ borderColor: "var(--border-c)" }}>
              <div className="flex items-center justify-between">
                <span className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold ${pat.category === "PATTERN" ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}>
                  {pat.category === "PATTERN" ? "架構最佳實踐" : "陷阱警示"}
                </span>
                <span className="text-[10px] font-mono text-slate-400">雜湊: {pat.content_hash.slice(0, 10)}</span>
              </div>
              <p className="text-xs leading-relaxed text-slate-200">{pat.content}</p>
              <div className="flex items-center justify-between pt-2 text-[10px] text-slate-400 border-t" style={{ borderColor: "var(--border-c)" }}>
                <span>關聯任務: {pat.task_id}</span>
                <span className="text-indigo-400">Obsidian 雙向鏈結已同步</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

