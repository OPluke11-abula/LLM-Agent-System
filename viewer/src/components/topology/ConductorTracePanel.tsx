import type { ConductorTrace, Lang } from "../../types";
import { MetricTile, ProgressBar, StatusBadge, Surface } from "../ui/primitives";

function asMetricRecord(value: unknown): Record<string, any> {
  return value && typeof value === "object" ? (value as Record<string, any>) : {};
}

function compactWorkflowRef(value?: string | null) {
  if (!value) return "--";
  const normalized = value.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  return parts.slice(-2).join("/") || normalized;
}

function safeCount(value: unknown) {
  const count = Number(value ?? 0);
  return Number.isFinite(count) && count > 0 ? count : 0;
}

function compactCodeGraphRef(path?: string | null, symbol?: string | null) {
  const compactPath = compactWorkflowRef(path);
  if (!symbol) return compactPath;
  const compactSymbol = symbol.split(".").slice(-2).join(".");
  return `${compactSymbol} @ ${compactPath}`;
}

function WorkflowGateSection({
  workflowStage,
  workflowCheckpoint,
  evidenceRefs,
  reviewGateTone,
  reviewGateLabel,
  lang,
}: {
  workflowStage: string | null;
  workflowCheckpoint: string | null;
  evidenceRefs: string[];
  reviewGateTone: "warning" | "success" | "neutral";
  reviewGateLabel: string;
  lang: Lang;
}) {
  const hasWorkflowSignal = Boolean(
    workflowStage || workflowCheckpoint || evidenceRefs.length > 0
  );

  return (
    <div className="space-y-1.5 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
      <div className="flex items-center justify-between">
        <span className="text-[8px] font-bold uppercase tracking-[0.14em] t3">
          Workflow Gate
        </span>
        <StatusBadge tone={reviewGateTone} className="text-[8px]">
          {reviewGateLabel}
        </StatusBadge>
      </div>
      <div className="grid grid-cols-3 gap-1.5 text-center font-mono">
        <MetricTile
          label="Stage"
          value={workflowStage ? workflowStage.split("-").slice(-1)[0] : "--"}
          tone={workflowStage ? "accent" : "neutral"}
          className="p-1"
        />
        <MetricTile
          label="Checkpoint"
          value={workflowCheckpoint ? "set" : "--"}
          tone={workflowCheckpoint ? "success" : "neutral"}
          className="p-1"
        />
        <MetricTile
          label="Evidence"
          value={evidenceRefs.length}
          tone={evidenceRefs.length > 0 ? "success" : "neutral"}
          className="p-1"
        />
      </div>
      {hasWorkflowSignal ? (
        <div className="space-y-1 font-mono text-[8px]">
          <div className="flex items-center justify-between gap-2">
            <span className="shrink-0 font-bold uppercase tracking-[0.14em] t3">Stage</span>
            <span className="truncate text-right t2" title={workflowStage ?? ""}>
              {workflowStage ?? "--"}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="shrink-0 font-bold uppercase tracking-[0.14em] t3">Checkpoint</span>
            <span className="truncate text-right t2" title={workflowCheckpoint ?? ""}>
              {compactWorkflowRef(workflowCheckpoint)}
            </span>
          </div>
          <div className="max-h-14 space-y-1 overflow-y-auto pr-1">
            {evidenceRefs.slice(0, 3).map((ref) => (
              <div key={ref} className="flex items-center justify-between gap-2">
                <span className="shrink-0 font-bold uppercase tracking-[0.14em] t3">Ref</span>
                <span className="truncate text-right t2" title={ref}>
                  {compactWorkflowRef(ref)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-[8px] leading-relaxed t3">
          {lang === "zh"
            ? "No workflow stage, checkpoint, or evidence refs published yet."
            : "No workflow stage, checkpoint, or evidence refs published yet."}
        </p>
      )}
    </div>
  );
}

function StructuralMemorySection({
  codeGraphRefs,
  impactSummary,
  structuralTone,
  changedFileCount,
  impactedSymbolCount,
  linkedTestCount,
  securityRelevantPaths,
  lang,
}: {
  codeGraphRefs: any[];
  impactSummary: any;
  structuralTone: "warning" | "success" | "neutral";
  changedFileCount: number;
  impactedSymbolCount: number;
  linkedTestCount: number;
  securityRelevantPaths: string[];
  lang: Lang;
}) {
  const hasStructuralSignal = Boolean(codeGraphRefs.length > 0 || impactSummary);

  return (
    <div
      className="space-y-1.5 border-t pt-2"
      style={{ borderColor: "var(--border-c)" }}
      data-testid="structural-memory-surface"
    >
      <div className="flex items-center justify-between">
        <span className="text-[8px] font-bold uppercase tracking-[0.14em] t3">
          Structural Memory
        </span>
        <StatusBadge tone={structuralTone} className="text-[8px]">
          {codeGraphRefs.length > 0 ? "graph" : "open"}
        </StatusBadge>
      </div>
      <div className="grid grid-cols-4 gap-1.5 text-center font-mono">
        <MetricTile
          label="Refs"
          value={codeGraphRefs.length}
          tone={codeGraphRefs.length > 0 ? "success" : "neutral"}
          className="p-1"
        />
        <MetricTile
          label="Files"
          value={changedFileCount}
          tone={changedFileCount > 0 ? "accent" : "neutral"}
          className="p-1"
        />
        <MetricTile
          label="Symbols"
          value={impactedSymbolCount}
          tone={impactedSymbolCount > 0 ? "accent" : "neutral"}
          className="p-1"
        />
        <MetricTile
          label="Tests"
          value={linkedTestCount}
          tone={linkedTestCount > 0 ? "success" : "neutral"}
          className="p-1"
        />
      </div>
      {hasStructuralSignal ? (
        <div className="space-y-1 font-mono text-[8px]">
          {impactSummary?.summary && (
            <p className="line-clamp-2 leading-relaxed t3" title={impactSummary.summary}>
              {impactSummary.summary}
            </p>
          )}
          <div className="max-h-20 space-y-1 overflow-y-auto pr-1">
            {codeGraphRefs.slice(0, 3).map((ref) => (
              <div
                key={`ref-${ref.path}-${ref.ref_type ?? "ref"}-${ref.symbol ?? "sym"}`}
                className="flex items-center justify-between gap-2"
              >
                <span className="shrink-0 font-bold uppercase tracking-[0.14em] t3">
                  {ref.ref_type || "ref"}
                </span>
                <span
                  className="truncate text-right t2"
                  title={ref.qualified_name || ref.symbol || ref.path}
                >
                  {compactCodeGraphRef(ref.path, ref.symbol)}
                </span>
              </div>
            ))}
            {securityRelevantPaths.slice(0, 3).map((path) => (
              <div key={path} className="flex items-center justify-between gap-2">
                <span className="shrink-0 font-bold uppercase tracking-[0.14em] t3">Risk</span>
                <span className="truncate text-right t2" title={path}>
                  {compactWorkflowRef(path)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-[8px] leading-relaxed t3">
          {lang === "zh"
            ? "No code graph refs or impact summary published yet."
            : "No code graph refs or impact summary published yet."}
        </p>
      )}
    </div>
  );
}

function computeConductorMetrics(
  trace: ConductorTrace,
  telemetry: unknown,
  ledger: { total_cost: number; cost_threshold: number } | null
) {
  const metric = asMetricRecord(telemetry);
  const selectedModel = trace.selected_models?.[0];
  const verification = trace.verification_strategy;
  const latencyValue =
    metric.latency_ms ?? metric.latencyMs ?? metric.ws_latency_ms ?? metric.wsLatencyMs;
  const latency = Number.isFinite(Number(latencyValue))
    ? `${Number(latencyValue).toFixed(0)}ms`
    : "--";
  const cost = ledger ? `$${ledger.total_cost.toFixed(5)}` : "--";
  const costLimit = ledger?.cost_threshold ?? trace.budget?.cost_limit ?? null;
  const memoryHits = trace.routing_memory_hints ?? [];

  let verifierTone: "warning" | "accent" | "success" = "success";
  if (verification?.approval_required) {
    verifierTone = "warning";
  } else if (verification?.required) {
    verifierTone = "accent";
  }

  const workflowStage = trace.workflow_stage_id || null;
  const workflowCheckpoint = trace.workflow_checkpoint_ref || null;
  const evidenceRefs = trace.evidence_refs ?? [];
  const codeGraphRefs = trace.code_graph_refs ?? [];
  const impactSummary = trace.impact_summary ?? null;
  const changedFileCount = safeCount(impactSummary?.changed_file_count);
  const impactedSymbolCount = safeCount(impactSummary?.impacted_symbol_count);
  const linkedTestCount = safeCount(impactSummary?.linked_test_count);
  const securityRelevantPaths = impactSummary?.security_relevant_paths ?? [];

  let reviewGateTone: "warning" | "success" | "neutral" = "neutral";
  let reviewGateLabel = "open";
  if (verification?.approval_required) {
    reviewGateTone = "warning";
    reviewGateLabel = "review";
  } else if (evidenceRefs.length > 0) {
    reviewGateTone = "success";
    reviewGateLabel = "evidence";
  }

  let structuralTone: "warning" | "success" | "neutral" = "neutral";
  if (securityRelevantPaths.length > 0) {
    structuralTone = "warning";
  } else if (codeGraphRefs.length > 0) {
    structuralTone = "success";
  }

  return {
    selectedModel,
    verification,
    latency,
    cost,
    costLimit,
    memoryHits,
    verifierTone,
    workflowStage,
    workflowCheckpoint,
    evidenceRefs,
    codeGraphRefs,
    impactSummary,
    changedFileCount,
    impactedSymbolCount,
    linkedTestCount,
    securityRelevantPaths,
    reviewGateTone,
    reviewGateLabel,
    structuralTone,
  };
}

function ConductorActiveBody({
  trace,
  telemetry,
  ledger,
  lang,
}: {
  trace: ConductorTrace;
  telemetry: unknown;
  ledger: { total_cost: number; cost_threshold: number } | null;
  lang: Lang;
}) {
  const {
    selectedModel,
    verification,
    latency,
    cost,
    costLimit,
    memoryHits,
    verifierTone,
    workflowStage,
    workflowCheckpoint,
    evidenceRefs,
    codeGraphRefs,
    impactSummary,
    changedFileCount,
    impactedSymbolCount,
    linkedTestCount,
    securityRelevantPaths,
    reviewGateTone,
    reviewGateLabel,
    structuralTone,
  } = computeConductorMetrics(trace, telemetry, ledger);

  return (
    <>
      <div className="grid grid-cols-3 gap-1.5 text-center font-mono">
        <MetricTile
          label="Memory"
          value={memoryHits.length}
          tone={memoryHits.length > 0 ? "success" : "neutral"}
          className="p-1"
        />
        <MetricTile label="Cost" value={cost} tone="success" className="p-1" />
        <MetricTile label="Latency" value={latency} tone="accent" className="p-1" />
      </div>

      <div
        className="space-y-1.5 border-t pt-2 font-mono text-[8px]"
        style={{ borderColor: "var(--border-c)" }}
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-bold uppercase tracking-[0.14em] t3">Model</span>
          <span
            className="truncate text-right t1"
            title={selectedModel ? `${selectedModel.provider}/${selectedModel.model}` : ""}
          >
            {selectedModel ? `${selectedModel.provider}/${selectedModel.model}` : "--"}
          </span>
        </div>
        <p className="line-clamp-2 leading-relaxed t2">
          {selectedModel?.selection_reason || trace.decision_rationale}
        </p>
      </div>

      <div className="space-y-1.5 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
        <div className="flex items-center justify-between">
          <span className="text-[8px] font-bold uppercase tracking-[0.14em] t3">Verification</span>
          <StatusBadge tone={verifierTone} className="text-[8px]">
            {verification?.kind ?? "none"}
          </StatusBadge>
        </div>
        <p className="text-[8px] leading-relaxed t3">
          {verification?.success_criteria?.[0] || "No verifier criteria published yet."}
        </p>
      </div>

      <WorkflowGateSection
        workflowStage={workflowStage}
        workflowCheckpoint={workflowCheckpoint}
        evidenceRefs={evidenceRefs}
        reviewGateTone={reviewGateTone}
        reviewGateLabel={reviewGateLabel}
        lang={lang}
      />

      <StructuralMemorySection
        codeGraphRefs={codeGraphRefs}
        impactSummary={impactSummary}
        structuralTone={structuralTone}
        changedFileCount={changedFileCount}
        impactedSymbolCount={impactedSymbolCount}
        linkedTestCount={linkedTestCount}
        securityRelevantPaths={securityRelevantPaths}
        lang={lang}
      />

      <div className="space-y-1.5 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
        <span className="text-[8px] font-bold uppercase tracking-[0.14em] t3">
          Task Breakdown
        </span>
        <div className="max-h-20 space-y-1 overflow-y-auto pr-1">
          {trace.subtasks.slice(0, 4).map((subtask) => (
            <div
              key={subtask.id}
              className="flex items-start justify-between gap-2 font-mono text-[8px]"
            >
              <span
                className="min-w-0 flex-1 truncate t2"
                title={subtask.description || subtask.title}
              >
                {subtask.title}
              </span>
              <span className="shrink-0 t3">{subtask.role_id || "worker"}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-1.5 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
        <div className="flex items-center justify-between font-mono text-[8px]">
          <span className="font-bold uppercase tracking-[0.14em] t3">Budget</span>
          <span className="t2">
            {trace.budget?.max_iterations ?? "--"} loops /{" "}
            {trace.budget?.max_tool_calls ?? "--"} tools
          </span>
        </div>
        {costLimit !== null && (
          <ProgressBar
            value={ledger ? (ledger.total_cost / Math.max(costLimit, 0.00001)) * 100 : 0}
            tone={ledger && ledger.total_cost > costLimit * 0.8 ? "warning" : "success"}
          />
        )}
      </div>

      {memoryHits.length > 0 && (
        <div className="space-y-1.5 border-t pt-2" style={{ borderColor: "var(--border-c)" }}>
          <span className="text-[8px] font-bold uppercase tracking-[0.14em] t3">
            Memory Hits
          </span>
          <div className="max-h-20 space-y-1 overflow-y-auto pr-1 font-mono text-[8px]">
            {memoryHits.slice(0, 3).map((hint) => (
              <div
                key={hint.record_id || `${hint.task_type}-${hint.latency_ms}`}
                className="flex items-center justify-between gap-2"
              >
                <span className="truncate t2">
                  {hint.task_type} / {hint.execution_mode}
                </span>
                <span style={{ color: hint.success ? "var(--success)" : "var(--danger)" }}>
                  {hint.success ? "ok" : hint.error_type || "fail"} {hint.latency_ms}ms
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

export function ConductorTracePanel({
  trace,
  telemetry,
  ledger,
  lang,
}: {
  trace: ConductorTrace | null;
  telemetry: unknown;
  ledger: { total_cost: number; cost_threshold: number } | null;
  lang: Lang;
}) {
  return (
    <Surface className="group/conductor relative mx-3 mb-3 flex flex-col gap-2 p-3">
      <div className="flex items-center justify-between">
        <p
          className="text-[10px] font-bold uppercase tracking-[0.14em]"
          style={{ color: "var(--accent)" }}
        >
          Conductor Trace
        </p>
        <StatusBadge tone={trace ? "accent" : "warning"} className="text-[8px]">
          {trace ? trace.execution_mode : "WAITING"}
        </StatusBadge>
      </div>

      {trace ? (
        <ConductorActiveBody
          trace={trace}
          telemetry={telemetry}
          ledger={ledger}
          lang={lang}
        />
      ) : (
        <p className="text-[9px] leading-relaxed t3">
          {lang === "zh"
            ? "尚無 Conductor Trace。發起任務後將即時呈現模型決策、結構記憶關聯、驗證策略與預算消耗。"
            : "No conductor trace active. Real-time model routing, code graph refs, verifiers, and budget telemetry appear upon execution."}
        </p>
      )}
    </Surface>
  );
}
