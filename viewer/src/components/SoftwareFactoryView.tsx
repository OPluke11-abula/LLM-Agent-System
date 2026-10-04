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
    <div className="flex h-full flex-col overflow-y-auto p-4 md:p-6 space-y-5" style={{ background: "var(--bg-base)" }}>
      {/* Top Banner */}
      <div
        className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-lg border p-4 sm:p-5 card-bg"
        style={{ borderColor: "var(--border-c)" }}
      >
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500" />
            <h1 className="text-base font-semibold tracking-tight text-[var(--t1)] flex items-center gap-2">
              <Boxes className="h-4 w-4 text-[var(--accent)]" />
              自主軟體工廠協同叢集
            </h1>
            <span className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-2 py-0.5 text-xs font-mono text-[var(--t2)]">
              PAP v3.8.0
            </span>
            <span
              className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-2 py-0.5 text-[11px] font-mono text-[var(--t3)] truncate max-w-[220px]"
              title={overview.merkle_root}
            >
              Merkle: {overview.merkle_root.slice(0, 8)}... (零漂移保證)
            </span>
          </div>
          <p className="mt-1.5 text-xs text-[var(--t3)] leading-relaxed">
            企業級代碼現代化流水線：AST 複雜度分析 → 作用域隔離工作樹 → 紅藍對抗審核 → 經驗蒸餾閉環。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => fetchOverview()}
            className="quiet-button inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium"
          >
            <RefreshCw className="h-3.5 w-3.5 text-[var(--t3)]" />
            <span>重新整理</span>
          </button>
          <button
            type="button"
            disabled={running}
            onClick={handleRunPipeline}
            className="primary-button inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium"
          >
            <Play className="h-3.5 w-3.5" />
            <span>{running ? "執行中..." : "啟動流水線"}</span>
          </button>
        </div>
      </div>

      {/* Balanced 4-Card KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="rounded-lg border p-3.5 card-bg transition-colors hover:border-[var(--border-strong)]" style={{ borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium text-[var(--t3)] uppercase tracking-wider">已重構代碼量 (LOC)</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-[var(--t1)]">{overview.total_modernized_loc.toLocaleString()}</div>
          <div className="mt-1 text-[11px] text-[var(--t3)]">AST 語法樹解析與量化</div>
        </div>

        <div className="rounded-lg border p-3.5 card-bg transition-colors hover:border-[var(--border-strong)]" style={{ borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium text-[var(--t3)] uppercase tracking-wider">活躍工作樹波次</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-[var(--t1)]">{overview.total_waves} 個波次</div>
          <div className="mt-1 text-[11px] text-emerald-400">100% 作用域實體隔離</div>
        </div>

        <div className="rounded-lg border p-3.5 card-bg transition-colors hover:border-[var(--border-strong)]" style={{ borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium text-[var(--t3)] uppercase tracking-wider">仲裁審核通過率</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-emerald-400">{overview.quorum_success_rate}%</div>
          <div className="mt-1 text-[11px] text-[var(--t3)]">{overview.quorum_approved} 通過 / {overview.quorum_rejected} 阻擋</div>
        </div>

        <div className="rounded-lg border p-3.5 card-bg transition-colors hover:border-[var(--border-strong)]" style={{ borderColor: "var(--border-c)" }}>
          <div className="text-[11px] font-medium text-[var(--t3)] uppercase tracking-wider">已蒸餾架構模式</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-[var(--t1)]">{overview.distilled_patterns_count} 組經驗</div>
          <div className="mt-1 text-[11px] text-[var(--t3)]">Obsidian 雙向鏈結同步</div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b" style={{ borderColor: "var(--border-c)" }}>
        <button
          type="button"
          onClick={() => setActiveTab("waves")}
          className={`flex items-center gap-1.5 px-3.5 py-2 text-xs transition border-b-2 ${
            activeTab === "waves"
              ? "border-[var(--accent)] text-[var(--accent)] font-medium"
              : "border-transparent text-[var(--t3)] hover:text-[var(--t2)]"
          }`}
        >
          <GitFork className="h-3.5 w-3.5" />
          <span>並行工作樹與波次</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("debate")}
          className={`flex items-center gap-1.5 px-3.5 py-2 text-xs transition border-b-2 ${
            activeTab === "debate"
              ? "border-[var(--accent)] text-[var(--accent)] font-medium"
              : "border-transparent text-[var(--t3)] hover:text-[var(--t2)]"
          }`}
        >
          <ShieldCheck className="h-3.5 w-3.5" />
          <span>紅藍對抗審核辯論</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("patterns")}
          className={`flex items-center gap-1.5 px-3.5 py-2 text-xs transition border-b-2 ${
            activeTab === "patterns"
              ? "border-[var(--accent)] text-[var(--accent)] font-medium"
              : "border-transparent text-[var(--t3)] hover:text-[var(--t2)]"
          }`}
        >
          <Cpu className="h-3.5 w-3.5" />
          <span>架構模式經驗庫 ({patterns.length})</span>
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "waves" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl border p-4 space-y-3 card-bg" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold tracking-wider text-[var(--t1)]">波次 1：高優先級解耦重構</span>
              <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono text-emerald-400 border border-emerald-500/20">
                執行中
              </span>
            </div>
            <div className="space-y-2">
              <div className="rounded-lg border p-3 text-xs bg-[var(--bg-muted)]" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[var(--t1)]">巨石核心引擎拆分解耦</span>
                  <span className="rounded bg-indigo-500/15 px-1.5 py-0.5 text-[9px] font-mono text-indigo-400">模組解耦</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-[var(--t3)]">作用域: agent_workspace/core/engine.py</div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-[var(--accent)]">
                  <span>指派代理人: REASONING_ENGINE (Cloud-DeepSeek-R1)</span>
                </div>
              </div>
              <div className="rounded-lg border p-3 text-xs bg-[var(--bg-muted)]" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[var(--t1)]">異步非阻塞 I/O 全面重構</span>
                  <span className="rounded bg-cyan-500/15 px-1.5 py-0.5 text-[9px] font-mono text-cyan-400">異步遷移</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-[var(--t3)]">作用域: agent_workspace/core/audit_ledger.py</div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-cyan-400">
                  <span>指派節點: SANDBOX_MUTATION (Edge-Worker-01)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border p-4 space-y-3 card-bg" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold tracking-wider text-[var(--t1)]">波次 2：契約強化與多階驗證</span>
              <span className="rounded bg-amber-500/10 px-2 py-0.5 text-[10px] font-mono text-amber-400 border border-amber-500/20">
                排隊中
              </span>
            </div>
            <div className="space-y-2">
              <div className="rounded-lg border p-3 text-xs bg-[var(--bg-muted)]" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[var(--t1)]">端到端驗證天梯擴充</span>
                  <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[9px] font-mono text-amber-400">測試擴充</span>
                </div>
                <div className="mt-1 text-[11px] font-mono text-[var(--t3)]">作用域: agent_workspace/tests/test_factory_decomposition_p101.py</div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-amber-400">
                  <span>指派節點: TEST_RUNNER (CI-Runner-01)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "debate" && (
        <div className="rounded-xl border p-5 space-y-4 card-bg" style={{ borderColor: "var(--border-c)" }}>
          <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-[var(--t1)]">對抗性審核：異步非阻塞管線</span>
              <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-mono text-emerald-400 border border-emerald-500/30">
                仲裁全票批准 (100.0/100)
              </span>
            </div>
            <span className="text-xs font-mono text-[var(--t3)]">契約 ID: shc-f9e5b105</span>
          </div>
          <div className="space-y-3 text-xs">
            <div className="rounded-lg border p-3 border-rose-500/20 bg-rose-500/5">
              <span className="font-semibold text-rose-400">回合 1 & 2 - 藍隊資安攻擊者探針：</span>
              <p className="mt-1 text-[var(--t2)] leading-relaxed">
                檢測到併發競態風險 (CONCURRENCY_RACE)：若於協程中直接調用同步 sqlite3，在高負載下將引發事件迴圈阻塞。
              </p>
            </div>
            <div className="rounded-lg border p-3 border-blue-500/20 bg-blue-500/5">
              <span className="font-semibold text-[var(--accent)]">回合 3 - 藍隊 QA 回歸防衛者斷言：</span>
              <p className="mt-1 text-[var(--t2)] leading-relaxed">
                硬性約束：16 租戶並發壓力下，非阻塞執行時長必須維持 &lt; 500ms，全套階梯測試必須 100% 回傳 Exit Code 0。
              </p>
            </div>
            <div className="rounded-lg border p-3 border-emerald-500/20 bg-emerald-500/5">
              <span className="font-semibold text-emerald-400">回合 4 & 5 - 紅隊防禦性修復與仲裁裁決：</span>
              <p className="mt-1 text-[var(--t2)] leading-relaxed">
                防禦補丁：所有資料庫事務均封裝於 asyncio.to_thread 與 threading.RLock()。仲裁全票批准，無未處置之重大缺陷。
              </p>
            </div>
          </div>
        </div>
      )}

      {activeTab === "patterns" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {patterns.map((pat) => (
            <div key={pat.entry_id} className="rounded-xl border p-4 space-y-2 card-bg" style={{ borderColor: "var(--border-c)" }}>
              <div className="flex items-center justify-between">
                <span className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold ${pat.category === "PATTERN" ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"}`}>
                  {pat.category === "PATTERN" ? "架構最佳實踐" : "陷阱警示"}
                </span>
                <span className="text-[10px] font-mono text-[var(--t3)]">雜湊: {pat.content_hash.slice(0, 10)}</span>
              </div>
              <p className="text-xs leading-relaxed text-[var(--t2)]">{pat.content}</p>
              <div className="flex items-center justify-between pt-2 text-[10px] text-[var(--t3)] border-t" style={{ borderColor: "var(--border-c)" }}>
                <span>關聯任務: {pat.task_id}</span>
                <span className="text-[var(--accent)]">Obsidian 雙向鏈結已同步</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

