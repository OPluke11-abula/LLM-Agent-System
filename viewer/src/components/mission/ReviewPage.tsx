import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  EVIDENCE_TYPE_COMPATIBILITY,
  GateStatus,
  type Mission,
  type MissionTransitionPage,
} from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { StatusBadge, Card, CardContent } from "../ui/primitives";
import { toneForStatus } from "../ui/utils";
import { planDigest } from "./missionUtils";
import { ArrowLeft, ShieldCheck, CheckCircle2, AlertTriangle, FileText, Clock } from "../ui/icons";

function label(value: string): string {
  const map: Record<string, string> = {
    draft: "草稿",
    planning: "規劃中",
    plan_submitted: "計畫已提交",
    plan_approved: "計畫已核准",
    running: "執行中",
    verifying: "驗證中",
    review_ready: "待審核驗收",
    completed: "已完成",
    paused: "已暫停",
    failed: "已失敗",
    cancelled: "已取消",
    passed: "已通過",
    failed_gate: "未通過",
    pending: "等待中",
    not_applicable: "不適用",
  };
  return map[value] || value.replaceAll("_", " ");
}

function computeGateRows(mission: Mission) {
  const verifications = mission.verification_gates ?? [];
  const evidence = mission.evidence_records ?? [];
  const evidenceById = new Map(evidence.map((record) => [record.evidence_id, record]));
  const gateRows = (mission.required_verification ?? []).map((gate) => {
    const record = verifications.find((item) => item.gate === gate);
    const refs = record?.evidence_refs ?? [];
    const linkedEvidence = refs.map((ref) => evidenceById.get(ref));
    const refsValid = refs.length > 0 && linkedEvidence.every((item) => item !== undefined);
    const compatibleTypes = new Set(EVIDENCE_TYPE_COMPATIBILITY[gate] as readonly string[]);
    const typesCompatible = linkedEvidence.every((item) => item !== undefined && compatibleTypes.has(item.evidence_type));
    const pass =
      record?.status === GateStatus.PASSED &&
      refsValid &&
      linkedEvidence.every((item) => item?.verification_status === GateStatus.PASSED) &&
      typesCompatible;
    const notApplicable = record?.status === GateStatus.NOT_APPLICABLE;
    return {
      gate,
      record,
      refs,
      linkedEvidence,
      pass,
      resolved: pass || notApplicable,
      typesCompatible,
      compatibilityWarning: record?.status === GateStatus.PASSED && !typesCompatible,
    };
  });
  const unresolved = gateRows.filter((row) => !row.resolved);
  return { gateRows, unresolved, approvals: mission.approval_gates ?? [], evidence };
}

function ReviewApprovalsCard({ approvals }: { approvals: readonly any[] }) {
  return (
    <Card className="nordic-card">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-3 border-b pb-3" style={{ borderColor: "var(--border-c)" }}>
          <ShieldCheck className="h-4 w-4 text-[var(--accent)]" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)]">
            人機審核主體 (Approval Subjects)
          </h2>
        </div>
        <div className="space-y-3">
          {approvals.length === 0 ? (
            <p className="text-xs text-[var(--t3)]">尚未記錄任何審核決定。</p>
          ) : (
            approvals.map((gate) => (
              <details key={gate.gate_id} className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-3 text-xs">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                  <span className="font-medium text-[var(--t1)]">{gate.gate_type} · {gate.gate_id}</span>
                  <StatusBadge tone={toneForStatus(gate.status)}>{gate.status ?? "pending"}</StatusBadge>
                </summary>
                <div className="mt-3 space-y-1 text-xs text-[var(--t3)] border-t border-[var(--border-c)] pt-2">
                  <p>審核標的: {gate.subject.kind}</p>
                  {gate.subject.kind === "plan" && (
                    <>
                      <p>計畫 ID: {gate.subject.plan_id} (修訂版 r{gate.subject.plan_revision})</p>
                      <p className="break-all font-mono text-[10px]">雜湊: {gate.subject.plan_digest}</p>
                    </>
                  )}
                  <p className="font-mono text-[10px]">冪等鍵: {gate.idempotency_key}</p>
                  <p>關聯證據參照: {gate.evidence_refs?.join(", ") || "無"}</p>
                </div>
              </details>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ReviewVerificationGatesCard({
  gateRows,
  unresolved,
}: {
  gateRows: any[];
  unresolved: any[];
}) {
  return (
    <Card className="nordic-card">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-3 border-b pb-3" style={{ borderColor: "var(--border-c)" }}>
          <CheckCircle2 className="h-4 w-4 text-[var(--accent)]" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)]">
            驗證閘門查核 (Verification Gates)
          </h2>
        </div>
        <div className="space-y-2">
          {gateRows.map(({ gate, record, refs, linkedEvidence, pass, resolved, compatibilityWarning }) => {
            const displayStatus = pass ? GateStatus.PASSED : record?.status ?? GateStatus.PENDING;
            return (
              <details
                key={gate}
                className="rounded-md border p-3 text-xs"
                style={{
                  borderColor: resolved ? "var(--border-c)" : "rgba(245, 158, 11, 0.4)",
                  background: "var(--bg-muted)",
                }}
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                  <span className="font-medium text-[var(--t1)]">{gate}</span>
                  <StatusBadge tone={pass ? "success" : resolved ? "neutral" : "warning"}>
                    {label(displayStatus)}
                  </StatusBadge>
                </summary>
                <div className="mt-3 space-y-1.5 border-t border-[var(--border-c)] pt-2 text-[11px] text-[var(--t3)]">
                  <p>閘門狀態: {label(displayStatus)}</p>
                  <p>關聯證據 ID: {refs.join(", ") || "無"}</p>
                  {refs.length > 0 &&
                    linkedEvidence.map((item: any, index: number) =>
                      item ? (
                        <div key={item.evidence_id} className="mt-2 rounded border border-[var(--border-c)] bg-[var(--bg-card)] p-2 space-y-1">
                          <p className="font-mono text-[10px] text-[var(--t1)]">ID: {item.evidence_id}</p>
                          <p>類型: {item.evidence_type} · 來源: {item.source}</p>
                          <p>操作指令: {item.operation}</p>
                          <p>驗證狀態: {item.verification_status ?? GateStatus.PENDING}</p>
                          <p className="text-[var(--t2)]">輸出摘要: {item.bounded_output_summary || "未記錄"}</p>
                        </div>
                      ) : (
                        <p key={refs[index]} className="text-red-400">失效的證據參照: {refs[index]}</p>
                      )
                    )}
                  {compatibilityWarning && <p className="text-red-400">證據類型與此閘門不相容。</p>}
                  {pass && <p className="text-emerald-400">所有關聯之客觀驗證證據皆已齊全並通過查核。</p>}
                </div>
              </details>
            );
          })}
        </div>

        {unresolved.length > 0 && (
          <div className="mt-4 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-400 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">殘餘不確定性：</span>
              <span>以下閘門尚未鏈結有效通過的證據：{unresolved.map((g) => g.gate).join(", ")}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ReviewEvidenceCard({ evidence }: { evidence: readonly any[] }) {
  return (
    <Card className="nordic-card">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-3 border-b pb-3" style={{ borderColor: "var(--border-c)" }}>
          <FileText className="h-4 w-4 text-[var(--accent)]" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)]">
            驗證證據紀錄明細 (Evidence Records)
          </h2>
        </div>
        <div className="space-y-2.5">
          {evidence.length === 0 ? (
            <p className="text-xs text-[var(--t3)]">尚未記錄任何驗證證據。</p>
          ) : (
            evidence.map((record) => (
              <details key={record.evidence_id} className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-3 text-xs">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                  <span className="font-mono text-[11px] text-[var(--t1)]">{record.evidence_id}</span>
                  <StatusBadge tone={toneForStatus(record.verification_status)}>
                    {record.verification_status ?? "pending"}
                  </StatusBadge>
                </summary>
                <div className="mt-3 space-y-1 border-t border-[var(--border-c)] pt-2 text-[11px] text-[var(--t3)]">
                  <p>類型: {record.evidence_type} · 來源: {record.source}</p>
                  <p className="font-mono text-[10px]">操作: {record.operation}</p>
                  <p>產出者: {record.producing_agent}</p>
                  <p>結束代碼: {record.exit_status ?? "未記錄"}</p>
                  <p className="text-[var(--t2)] leading-relaxed">{record.bounded_output_summary || "無輸出摘要"}</p>
                  <p>關聯任務: {record.task_links?.join(", ") || "無"}</p>
                </div>
              </details>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ReviewHistoryCard({
  history,
  loadingHistory,
  onLoadMore,
}: {
  history: MissionTransitionPage;
  loadingHistory: boolean;
  onLoadMore: () => void;
}) {
  return (
    <Card className="nordic-card">
      <CardContent className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3 mb-3" style={{ borderColor: "var(--border-c)" }}>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-[var(--accent)]" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)]">
              狀態躍遷審計歷程 (Transition History)
            </h2>
          </div>
          {history.next_offset != null && (
            <button
              type="button"
              className="quiet-button rounded px-2.5 py-1 text-xs font-medium"
              onClick={onLoadMore}
              disabled={loadingHistory}
            >
              {loadingHistory ? "載入中…" : "載入更多歷程"}
            </button>
          )}
        </div>
        <div className="space-y-2">
          {history.items.length === 0 ? (
            <p className="text-xs text-[var(--t3)]">尚未記錄任何狀態躍遷。</p>
          ) : (
            history.items.map((item) => (
              <div
                key={item.audit_id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-[var(--border-c)] pb-2 text-xs last:border-none"
              >
                <span className="font-mono font-medium text-[var(--t1)]">{label(item.event)}</span>
                <span className="font-mono text-[11px] text-[var(--t3)]">
                  r{item.from_revision} → r{item.to_revision} · {item.actor_id}
                </span>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ReviewDeliveryBoundaryCard({ finalDraftPr }: { finalDraftPr?: { url: string } | null }) {
  return (
    <Card className="nordic-card">
      <CardContent className="p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)] mb-2">
          交付邊界與產物 (Delivery Boundary)
        </h2>
        <p className="text-xs text-[var(--t3)] leading-relaxed">
          遵循 PAP v3.8.0 契約，系統不擅自發布或合併 Draft PR。唯有在後續具備授權之整合管線記錄時，方在此呈現最終交付主體。
        </p>
        {finalDraftPr ? (
          <p className="mt-3 font-mono text-xs text-[var(--t1)]">{finalDraftPr.url}</p>
        ) : (
          <p className="mt-3 text-[11px] text-[var(--t3)] font-mono">Draft PR 交付：依規範停用 (Not implemented by design)</p>
        )}
      </CardContent>
    </Card>
  );
}

export function ReviewPage() {
  const { missionId = "" } = useParams<{ missionId: string }>();
  const decodedMissionId = decodeURIComponent(missionId);
  const [mission, setMission] = useState<Mission | null>(null);
  const [history, setHistory] = useState<MissionTransitionPage | null>(null);
  const [digest, setDigest] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    let isSubscribed = true;
    const controller = new AbortController();

    async function loadData() {
      try {
        const [nextMission, nextHistory] = await Promise.all([
          missionApi.get(decodedMissionId, controller.signal),
          missionApi.history(decodedMissionId, { signal: controller.signal }),
        ]);
        const computedDigest = nextMission.execution_plan ? await planDigest(nextMission.execution_plan) : null;
        if (isSubscribed) {
          setMission(nextMission);
          setHistory(nextHistory);
          setDigest(computedDigest);
        }
      } catch (cause: unknown) {
        if (isSubscribed) {
          if (cause instanceof DOMException && cause.name === "AbortError") return;
          setError(cause instanceof MissionApiError ? cause.message : "無法載入審核資料");
        }
      }
    }

    loadData();
    return () => {
      isSubscribed = false;
      controller.abort();
    };
  }, [decodedMissionId]);

  async function loadMoreHistory(): Promise<void> {
    if (!history?.next_offset || loadingHistory) return;
    setLoadingHistory(true);
    try {
      const next = await missionApi.history(decodedMissionId, { offset: history.next_offset });
      setHistory({ ...next, items: [...history.items, ...next.items] });
    } catch (cause: unknown) {
      setError(cause instanceof MissionApiError ? cause.message : "無法載入更多審核歷程");
    } finally {
      setLoadingHistory(false);
    }
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-md border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-400" role="alert">
          <p className="font-semibold">審核驗收頁面無法載入</p>
          <p className="mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!mission || !history) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-xs text-[var(--t3)]">
        正在載入審核證據…
      </div>
    );
  }

  const state = mission.current_state ?? "draft";
  const { gateRows, unresolved, approvals, evidence } = computeGateRows(mission);

  return (
    <div className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto p-4 md:p-6 pb-12" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <div className="border-b pb-4" style={{ borderColor: "var(--border-c)" }}>
        <Link
          to={`/missions/${encodeURIComponent(decodedMissionId)}`}
          className="inline-flex items-center gap-1.5 text-xs text-[var(--t3)] hover:text-[var(--t1)] mb-3"
        >
          <ArrowLeft className="h-3 w-3" />
          <span>返回任務詳情</span>
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-[var(--t1)]">
              {mission.requirement}
            </h1>
            <p className="mt-1 font-mono text-[11px] text-[var(--t3)]">
              ID: {mission.mission_id} · Repo: {mission.repository_id} · 修訂版 r{mission.revision}
            </p>
          </div>
          <StatusBadge tone={toneForStatus(state)}>{label(state)}</StatusBadge>
        </div>
      </div>

      {/* Stats Summary Cards */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="nordic-card">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--t3)]">執行計畫</span>
            <p className="mt-1 font-mono text-xs font-semibold text-[var(--t1)] truncate">
              {mission.execution_plan?.plan_id ?? "未附加"}
            </p>
          </CardContent>
        </Card>
        <Card className="nordic-card">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--t3)]">計畫修訂版</span>
            <p className="mt-1 font-mono text-xs font-semibold text-[var(--t1)]">
              {mission.execution_plan?.revision ? `r${mission.execution_plan.revision}` : "—"}
            </p>
          </CardContent>
        </Card>
        <Card className="nordic-card">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--t3)]">計畫 SHA-256 摘要</span>
            <p className="mt-1 font-mono text-[11px] text-[var(--t2)] break-all truncate">
              {digest ?? "無計畫摘要記錄"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid */}
      <div className="grid gap-5 lg:grid-cols-2">
        <ReviewApprovalsCard approvals={approvals} />
        <ReviewVerificationGatesCard gateRows={gateRows} unresolved={unresolved} />
      </div>

      <ReviewEvidenceCard evidence={evidence} />
      <ReviewHistoryCard history={history} loadingHistory={loadingHistory} onLoadMore={() => void loadMoreHistory()} />
      <ReviewDeliveryBoundaryCard finalDraftPr={mission.final_draft_pr} />
    </div>
  );
}
