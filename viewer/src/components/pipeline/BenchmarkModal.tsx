
import { Button, StatusBadge } from "../ui/primitives";
import { Activity, Play } from "../ui/icons";

interface BenchmarkModalProps {
  isOpen: boolean;
  onClose: () => void;
  lang?: string;
  runningBenchmark: boolean;
  onRunBenchmark: () => void;
  benchmarkScorecard: any;
}

interface BenchmarkScorecardProps {
  scorecard: any;
}

function BenchmarkKpiGrid({ scorecard }: BenchmarkScorecardProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      <div className="p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)]">
        <div className="text-[10px] text-[var(--t3)] uppercase font-mono">1. Mission Completion Rate</div>
        <div className="text-lg font-bold text-emerald-400 mt-1">
          {(scorecard.mission_completion_rate * 100).toFixed(1)}%
        </div>
        <div className="text-[10px] text-[var(--t3)] mt-0.5">
          {scorecard.successful_scenarios} / {scorecard.total_scenarios} scenarios verified
        </div>
      </div>

      <div className="p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)]">
        <div className="text-[10px] text-[var(--t3)] uppercase font-mono">2. Avg Verified Latency</div>
        <div className="text-lg font-bold text-sky-400 mt-1">
          {scorecard.avg_time_to_verified_completion_ms.toFixed(1)} ms
        </div>
        <div className="text-[10px] text-[var(--t3)] mt-0.5">Target &lt; 10,000 ms</div>
      </div>

      <div className="p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)]">
        <div className="text-[10px] text-[var(--t3)] uppercase font-mono">3. Scope Containment</div>
        <div className="text-lg font-bold text-purple-400 mt-1">
          {(scorecard.scope_containment_rate * 100).toFixed(1)}%
        </div>
        <div className="text-[10px] text-[var(--t3)] mt-0.5">
          {scorecard.total_scope_violations_blocked} mutations blocked
        </div>
      </div>

      <div className="p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)]">
        <div className="text-[10px] text-[var(--t3)] uppercase font-mono">4. Review Freshness</div>
        <div className="text-lg font-bold text-teal-400 mt-1">
          {scorecard.review_freshness_verified ? "VERIFIED" : "STALE"}
        </div>
        <div className="text-[10px] text-[var(--t3)] mt-0.5">HEAD hash matched</div>
      </div>

      <div className="p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)]">
        <div className="text-[10px] text-[var(--t3)] uppercase font-mono">5. Host Preservation</div>
        <div className="text-lg font-bold text-emerald-400 mt-1">
          {scorecard.canonical_host_preservation_pass ? "100% CLEAN" : "DIRTY"}
        </div>
        <div className="text-[10px] text-[var(--t3)] mt-0.5">0 Host Mutations</div>
      </div>

      <div className="p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)]">
        <div className="text-[10px] text-[var(--t3)] uppercase font-mono">6. Context Efficiency</div>
        <div className="text-lg font-bold text-[var(--accent)] mt-1">
          ~{scorecard.context_token_efficiency_kb} KB
        </div>
        <div className="text-[10px] text-[var(--t3)] mt-0.5">Allocated per task</div>
      </div>
    </div>
  );
}

function BenchmarkScenarioTable({ receipts }: { receipts?: any[] }) {
  return (
    <div className="rounded-lg border border-[var(--border-c)] overflow-hidden">
      <table className="w-full text-left font-mono">
        <thead className="bg-[var(--bg-muted)] text-[11px] text-[var(--t3)] border-b border-[var(--border-c)]">
          <tr>
            <th className="p-2.5">場景名稱</th>
            <th className="p-2.5">抵達階段</th>
            <th className="p-2.5">結果</th>
            <th className="p-2.5">耗時</th>
            <th className="p-2.5">阻擋違規</th>
            <th className="p-2.5">Merkle 根雜湊</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border-c)] text-[11px]">
          {receipts?.map((sc: any) => (
            <tr key={`bench-sc-${sc.name}`} className="hover:bg-[var(--bg-muted)]">
              <td className="p-2.5 font-sans font-medium text-[var(--t1)]">{sc.name}</td>
              <td className="p-2.5 text-[var(--t2)]">{sc.stage_reached}</td>
              <td className="p-2.5">
                <StatusBadge tone={sc.success ? "success" : "danger"}>
                  {sc.success ? "PASS" : "FAIL"}
                </StatusBadge>
              </td>
              <td className="p-2.5 text-[var(--t3)]">{sc.duration_ms.toFixed(1)}ms</td>
              <td className="p-2.5 text-[var(--t3)]">{sc.scope_violations_blocked}</td>
              <td className="p-2.5 text-[var(--accent)] font-mono">
                {sc.merkle_root ? `${sc.merkle_root.slice(0, 10)}...` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BenchmarkContent({
  benchmarkScorecard,
  runningBenchmark,
}: {
  benchmarkScorecard: any;
  runningBenchmark: boolean;
}) {
  if (!benchmarkScorecard) {
    return (
      <div className="py-12 text-center text-[var(--t3)] text-xs">
        {runningBenchmark
          ? "正在獨立臨時 Git 工作樹中執行 3 組黃金標準基準測試..."
          : "尚未記錄基準測試結果。點擊「一鍵運行標竿測試」以開始。"}
      </div>
    );
  }

  return (
    <div className="space-y-4 text-xs">
      <div className="flex items-center justify-between p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)]">
        <div>
          <span className="text-[var(--t3)] font-mono">測試套件編號: </span>
          <span className="font-mono text-[var(--t1)]">{benchmarkScorecard.suite_id}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[var(--t3)] font-mono">裁決結果: </span>
          <StatusBadge
            tone={benchmarkScorecard.advisory_verdict === "GOLDEN_FLOW_VERIFIED" ? "success" : "warning"}
          >
            {benchmarkScorecard.advisory_verdict}
          </StatusBadge>
        </div>
      </div>
      <BenchmarkKpiGrid scorecard={benchmarkScorecard} />
      <BenchmarkScenarioTable receipts={benchmarkScorecard.scenario_receipts} />
    </div>
  );
}

export function BenchmarkModal({
  isOpen,
  onClose,
  lang,
  runningBenchmark,
  onRunBenchmark,
  benchmarkScorecard,
}: BenchmarkModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-[var(--bg-card)] border border-[var(--border-c)] rounded-xl max-w-3xl w-full p-6 space-y-5 shadow-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-[var(--border-c)] pb-3">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-[var(--accent)]" />
            <h3 className="text-base font-semibold text-[var(--t1)]">
              {lang === "zh" ? "黃金研發流基準測試 (ADR-006 / P4)" : "Golden Flow Benchmark Scorecard (ADR-006 / P4)"}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={onRunBenchmark}
              disabled={runningBenchmark}
            >
              <Play className="h-3.5 w-3.5 mr-1" />
              {runningBenchmark
                ? (lang === "zh" ? "測試執行中..." : "Running Suite...")
                : (lang === "zh" ? "一鍵運行標竿測試" : "Run Benchmark Suite")}
            </Button>
            <Button variant="outline" size="sm" onClick={onClose}>
              ✕
            </Button>
          </div>
        </div>

        <BenchmarkContent
          benchmarkScorecard={benchmarkScorecard}
          runningBenchmark={runningBenchmark}
        />
      </div>
    </div>
  );
}
