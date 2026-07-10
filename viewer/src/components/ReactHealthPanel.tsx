import reactDoctorSummary from "../data/react-doctor-summary.json";
import { MetricTile, StatusBadge, Surface } from "./ui/primitives";

type Tone = "neutral" | "accent" | "success" | "warning" | "danger";

type ReactHealthFinding = {
  readonly category: string;
  readonly line?: number;
  readonly message: string;
  readonly path: string;
  readonly rule: string;
  readonly severity: string;
};

type ReactHealthTopFile = {
  readonly findings: number;
  readonly path: string;
};

type ReactHealthReport = {
  readonly affected_phase67_surfaces: readonly string[];
  readonly changed_file_regressions: readonly ReactHealthFinding[];
  readonly error_findings: readonly ReactHealthFinding[];
  readonly generated_at: string;
  readonly next_fix_queue: readonly ReactHealthFinding[];
  readonly source_report: string;
  readonly top_files: readonly ReactHealthTopFile[];
  readonly totals: {
    readonly by_category: Record<string, number>;
    readonly by_severity: Record<string, number>;
    readonly total_findings: number;
  };
};

const report: ReactHealthReport = reactDoctorSummary;

function compactPath(path: string) {
  const parts = path.split(/[\\/]/).filter(Boolean);
  if (parts.length <= 3) return path;
  return `${parts[0]}/.../${parts.slice(-2).join("/")}`;
}

function healthTone(errors: number, regressions: number): Tone {
  if (errors > 0) return "danger";
  if (regressions > 0) return "warning";
  return "success";
}

function categoryTone(category: string): Tone {
  if (category === "Bugs") return "warning";
  if (category === "Accessibility") return "accent";
  if (category === "Performance") return "success";
  return "neutral";
}

function severityTone(severity: string): Tone {
  if (severity === "error") return "danger";
  if (severity === "warning") return "warning";
  return "neutral";
}

function findingKey(finding: ReactHealthFinding) {
  return `${finding.path}:${finding.line ?? 0}:${finding.rule}`;
}

function lineLabel(finding: ReactHealthFinding) {
  return finding.line ? `${compactPath(finding.path)}:${finding.line}` : compactPath(finding.path);
}

export function ReactHealthPanel() {
  const errorCount = report.totals.by_severity.error ?? 0;
  const warningCount = report.totals.by_severity.warning ?? 0;
  const regressionCount = report.changed_file_regressions.length;
  const statusTone = healthTone(errorCount, regressionCount);
  const statusLabel = errorCount > 0 ? "errors" : regressionCount > 0 ? "changed warnings" : "stable";
  const categoryEntries = Object.entries(report.totals.by_category);

  return (
    <Surface className="react-health-panel intelligence-flow p-4" data-testid="react-health-panel">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] accent-text">React Health</p>
            <StatusBadge tone={statusTone}>{statusLabel}</StatusBadge>
          </div>
          <h2 className="mt-2 text-xl font-semibold t1">Verification intelligence layer</h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed t2">
            LAS parser output links React Doctor category load, affected files, current errors, changed-scope regressions,
            and the next fix queue into the evidence path.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:w-[38rem]">
          <MetricTile label="Findings" value={report.totals.total_findings} tone={warningCount > 0 ? "warning" : "success"} />
          <MetricTile label="Errors" value={errorCount} tone={errorCount > 0 ? "danger" : "success"} />
          <MetricTile label="Changed" value={regressionCount} tone={regressionCount > 0 ? "warning" : "success"} />
          <MetricTile label="Surfaces" value={report.affected_phase67_surfaces.length} tone="accent" />
        </div>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-[0.84fr_1.16fr]">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
          <section className="react-health-node rounded-xl border p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">Category counts</p>
              <StatusBadge tone="accent">{categoryEntries.length}</StatusBadge>
            </div>
            <div className="mt-3 grid gap-2">
              {categoryEntries.map(([category, count]) => (
                <div key={category} className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
                  <span className="text-xs font-semibold t2">{category}</span>
                  <StatusBadge tone={categoryTone(category)}>{count}</StatusBadge>
                </div>
              ))}
            </div>
          </section>

          <section className="react-health-node rounded-xl border p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">Top affected files</p>
              <StatusBadge tone="warning">{report.top_files.length}</StatusBadge>
            </div>
            <div className="mt-3 space-y-2">
              {report.top_files.slice(0, 6).map((file) => (
                <div key={file.path} className="react-health-route rounded-lg border px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate font-mono text-[11px] t1" title={file.path}>{compactPath(file.path)}</p>
                    <span className="font-mono text-[10px] font-bold t3">{file.findings}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <section className="react-health-node rounded-xl border p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">Current errors</p>
              <StatusBadge tone={errorCount > 0 ? "danger" : "success"}>{errorCount}</StatusBadge>
            </div>
            <div className="mt-3 space-y-2">
              {report.error_findings.length > 0 ? (
                report.error_findings.slice(0, 4).map((finding) => (
                  <FindingRow key={findingKey(finding)} finding={finding} />
                ))
              ) : (
                <p className="rounded-lg border px-3 py-2 text-xs t2" style={{ borderColor: "var(--border-c)", background: "var(--success-bg)" }}>
                  No error-severity React Doctor findings in the latest LAS summary.
                </p>
              )}
            </div>
          </section>

          <section className="react-health-node rounded-xl border p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">Changed-file regressions</p>
              <StatusBadge tone={regressionCount > 0 ? "warning" : "success"}>{regressionCount}</StatusBadge>
            </div>
            <div className="mt-3 space-y-2">
              {report.changed_file_regressions.slice(0, 4).map((finding) => (
                <FindingRow key={findingKey(finding)} finding={finding} />
              ))}
            </div>
          </section>

          <section className="react-health-node rounded-xl border p-3 lg:col-span-2">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">Next fix queue</p>
              <StatusBadge tone="accent">{report.next_fix_queue.length}</StatusBadge>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {report.next_fix_queue.slice(0, 6).map((finding) => (
                <FindingRow key={findingKey(finding)} finding={finding} />
              ))}
            </div>
          </section>
        </div>
      </div>
    </Surface>
  );
}

function FindingRow({ finding }: { readonly finding: ReactHealthFinding }) {
  return (
    <div className="react-health-route rounded-lg border px-3 py-2">
      <div className="flex items-center justify-between gap-3">
        <p className="truncate font-mono text-[11px] t1" title={lineLabel(finding)}>{lineLabel(finding)}</p>
        <StatusBadge tone={severityTone(finding.severity)}>{finding.rule}</StatusBadge>
      </div>
      <p className="mt-1 line-clamp-2 text-xs leading-relaxed t2" title={finding.message}>{finding.message}</p>
    </div>
  );
}
