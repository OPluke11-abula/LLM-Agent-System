import { Link } from "react-router-dom";
import { flattenTasks } from "../utils/graphUtils";
import { ReactHealthPanel } from "./ReactHealthPanel";
import { MetricTile, StatusBadge, Surface } from "./ui/primitives";
import type { AgentMemory, ConductorTrace, Lang, TopologyState } from "../types";

type IntelligenceMapViewProps = {
  memory: AgentMemory;
  sessions: TopologyState[];
  lastUpdatedSessionId: string | null;
  lang: Lang;
};

const COPY: Record<Lang, {
  eyebrow: string;
  title: string;
  subtitle: string;
  taskContext: string;
  impactedSymbols: string;
  linkedTests: string;
  evidence: string;
  decisions: string;
  noTrace: string;
  noRefs: string;
  openTasks: string;
  openTopology: string;
  openMemory: string;
  summary: string;
}> = {
  zh: {
    eyebrow: "STRUCTURAL INTELLIGENCE",
    title: "Intelligence Map",
    subtitle: "\u5c07\u4efb\u52d9\u3001\u7d50\u69cb\u8a18\u61b6\u3001code graph impact\u3001tests\u3001workflow evidence \u8207 prior decisions \u4e32\u6210\u4e00\u500b\u6aa2\u8996\u6d41\u7a0b\u3002",
    taskContext: "Task context",
    impactedSymbols: "Impacted symbols",
    linkedTests: "Linked tests",
    evidence: "Evidence refs",
    decisions: "Prior decisions",
    noTrace: "\u5c1a\u672a\u6536\u5230 conductor trace\u3002\u8acb\u5148\u57f7\u884c\u4efb\u52d9\u6216\u958b\u555f topology stream\u3002",
    noRefs: "\u76ee\u524d\u6c92\u6709\u53ef\u7528 refs\u3002",
    openTasks: "Open Task Flow",
    openTopology: "Open Topology",
    openMemory: "Open Memory",
    summary: "Inspection flow",
  },
  en: {
    eyebrow: "STRUCTURAL INTELLIGENCE",
    title: "Intelligence Map",
    subtitle: "Unifies tasks, structural memory, code graph impact, tests, workflow evidence, and decisions in one inspection flow.",
    taskContext: "Task context",
    impactedSymbols: "Impacted symbols",
    linkedTests: "Linked tests",
    evidence: "Evidence refs",
    decisions: "Prior decisions",
    noTrace: "No conductor trace received yet. Run a task or open the topology stream first.",
    noRefs: "No refs available yet.",
    openTasks: "Open Task Flow",
    openTopology: "Open Topology",
    openMemory: "Open Memory",
    summary: "Inspection flow",
  },
  ja: {
    eyebrow: "STRUCTURAL INTELLIGENCE",
    title: "Intelligence Map",
    subtitle: "Connects tasks, structural memory, code graph impact, tests, evidence, and decisions in one inspection flow.",
    taskContext: "Task context",
    impactedSymbols: "Impacted symbols",
    linkedTests: "Linked tests",
    evidence: "Evidence refs",
    decisions: "Prior decisions",
    noTrace: "No conductor trace received yet. Run a task or open the topology stream first.",
    noRefs: "No refs available yet.",
    openTasks: "Open Task Flow",
    openTopology: "Open Topology",
    openMemory: "Open Memory",
    summary: "Inspection flow",
  },
  fr: {
    eyebrow: "STRUCTURAL INTELLIGENCE",
    title: "Intelligence Map",
    subtitle: "Relie taches, memoire structurelle, code graph impact, tests, evidence workflow et decisions dans un seul flux.",
    taskContext: "Task context",
    impactedSymbols: "Impacted symbols",
    linkedTests: "Linked tests",
    evidence: "Evidence refs",
    decisions: "Prior decisions",
    noTrace: "Aucun conductor trace recu. Lancez une tache ou ouvrez le topology stream.",
    noRefs: "Aucun ref disponible.",
    openTasks: "Open Task Flow",
    openTopology: "Open Topology",
    openMemory: "Open Memory",
    summary: "Inspection flow",
  },
};

function latestSession(sessions: TopologyState[], lastUpdatedSessionId: string | null) {
  return sessions.find((session) => session.session_id === lastUpdatedSessionId) ?? sessions[0] ?? null;
}

function latestTrace(session: TopologyState | null): ConductorTrace | null {
  if (!session) return null;
  for (const node of [...session.nodes].reverse()) {
    const trace = node.payload?.conductor_trace;
    if (trace && typeof trace === "object" && "task_id" in trace) {
      return trace as ConductorTrace;
    }
  }
  return null;
}

function compactPath(path: string) {
  const parts = path.split(/[\\/]/).filter(Boolean);
  if (parts.length <= 3) return path;
  return `${parts[0]}/.../${parts.slice(-2).join("/")}`;
}

export function IntelligenceMapView({ memory, sessions, lastUpdatedSessionId, lang }: IntelligenceMapViewProps) {
  const copy = COPY[lang];
  const tasks = flattenTasks(memory.tasks);
  const session = latestSession(sessions, lastUpdatedSessionId);
  const trace = latestTrace(session);
  const impact = trace?.impact_summary ?? null;
  const codeRefs = trace?.code_graph_refs ?? [];
  const evidenceRefs = trace?.evidence_refs ?? [];
  const linkedTests = impact?.linked_test_count ?? 0;
  const securityPaths = impact?.security_relevant_paths ?? [];
  const activeTask =
    (trace ? tasks.find((task) => task.id === trace.task_id) : null)
    ?? tasks.find((task) => task.status === "in_progress")
    ?? tasks[0];
  const decision = trace?.decision_rationale ?? impact?.summary ?? copy.noTrace;

  const stages = [
    { label: copy.taskContext, value: activeTask?.id ?? "--", body: activeTask?.description ?? copy.noTrace, tone: activeTask ? "accent" as const : "warning" as const },
    { label: copy.impactedSymbols, value: impact?.impacted_symbol_count ?? codeRefs.length, body: impact?.summary ?? copy.noRefs, tone: codeRefs.length > 0 ? "success" as const : "neutral" as const },
    { label: copy.linkedTests, value: linkedTests, body: linkedTests > 0 ? `${linkedTests} linked verification targets` : copy.noRefs, tone: linkedTests > 0 ? "success" as const : "neutral" as const },
    { label: copy.evidence, value: evidenceRefs.length, body: evidenceRefs[0] ?? copy.noRefs, tone: evidenceRefs.length > 0 ? "success" as const : "neutral" as const },
  ];

  return (
    <main className="mission-control h-full min-h-0 overflow-y-auto">
      <div className="mx-auto flex max-w-[1480px] flex-col gap-4 pb-6">
        <Surface elevated className="intelligence-hero p-4 sm:p-5">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] accent-text">{copy.eyebrow}</p>
          <div className="mt-2 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <h1 className="text-4xl font-semibold leading-none t1 sm:text-5xl">{copy.title}</h1>
              <p className="mt-3 max-w-3xl text-sm leading-relaxed t2">{copy.subtitle}</p>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:w-[34rem]">
              <MetricTile label="Tasks" value={tasks.length} />
              <MetricTile label="Graph refs" value={codeRefs.length} tone={codeRefs.length > 0 ? "success" : "neutral"} />
              <MetricTile label="Tests" value={linkedTests} tone={linkedTests > 0 ? "success" : "neutral"} />
              <MetricTile label="Evidence" value={evidenceRefs.length} tone={evidenceRefs.length > 0 ? "success" : "neutral"} />
            </div>
          </div>
        </Surface>

        <section className="intelligence-map-grid" data-testid="intelligence-map">
          <Surface className="intelligence-flow p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{copy.summary}</p>
              <StatusBadge tone={trace ? "success" : "warning"}>{trace ? trace.execution_mode : "waiting"}</StatusBadge>
            </div>
            <div className="mt-4 grid gap-3 lg:grid-cols-4">
              {stages.map((stage, index) => (
                <div key={stage.label} className="intelligence-stage rounded-xl border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] t3">{String(index + 1).padStart(2, "0")}</span>
                    <StatusBadge tone={stage.tone}>{stage.value}</StatusBadge>
                  </div>
                  <h2 className="mt-3 text-sm font-semibold t1">{stage.label}</h2>
                  <p className="mt-2 line-clamp-4 text-xs leading-relaxed t2">{stage.body}</p>
                </div>
              ))}
            </div>
          </Surface>

          <ReactHealthPanel />

          <Surface className="p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{copy.impactedSymbols}</p>
            <div className="mt-3 space-y-2">
              {codeRefs.length > 0 ? codeRefs.slice(0, 8).map((ref) => (
                <div key={`${ref.path}:${ref.qualified_name ?? ref.symbol ?? ref.description ?? ""}`} className="intelligence-ref-card rounded-lg border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate font-mono text-[11px] t1" title={ref.qualified_name ?? ref.symbol ?? ref.path}>{ref.symbol ?? ref.qualified_name ?? compactPath(ref.path)}</p>
                    <StatusBadge tone="accent">{ref.ref_type ?? "ref"}</StatusBadge>
                  </div>
                  <p className="mt-1 truncate font-mono text-[10px] t3" title={ref.path}>{compactPath(ref.path)}</p>
                  {ref.description && <p className="mt-2 text-xs leading-relaxed t2">{ref.description}</p>}
                </div>
              )) : <p className="text-sm t3">{copy.noRefs}</p>}
            </div>
          </Surface>

          <Surface className="p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{copy.evidence}</p>
            <div className="mt-3 grid gap-2">
              {evidenceRefs.length > 0 ? evidenceRefs.slice(0, 6).map((ref) => (
                <p key={ref} className="intelligence-ref-row truncate rounded-lg border px-3 py-2 font-mono text-[11px] t2" title={ref}>{ref}</p>
              )) : <p className="text-sm t3">{copy.noRefs}</p>}
            </div>
            {securityPaths.length > 0 && (
              <div className="mt-4 border-t pt-3" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">Security paths</p>
                  <StatusBadge tone="warning">{securityPaths.length}</StatusBadge>
                </div>
                <div className="mt-2 space-y-1">
                  {securityPaths.slice(0, 4).map((path) => (
                    <p key={path} className="truncate font-mono text-[10px] t2" title={path}>{compactPath(path)}</p>
                  ))}
                </div>
              </div>
            )}
          </Surface>

          <Surface className="p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{copy.decisions}</p>
            <p className="mt-3 text-sm leading-relaxed t2">{decision}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/tasks" className="primary-button rounded-lg px-3 py-1.5 text-xs font-semibold">{copy.openTasks}</Link>
              <Link to="/topology" className="quiet-button rounded-lg px-3 py-1.5 text-xs font-semibold">{copy.openTopology}</Link>
              <Link to="/memory" className="quiet-button rounded-lg px-3 py-1.5 text-xs font-semibold">{copy.openMemory}</Link>
            </div>
          </Surface>
        </section>
      </div>
    </main>
  );
}
