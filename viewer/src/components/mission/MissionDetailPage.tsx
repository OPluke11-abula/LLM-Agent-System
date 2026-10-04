import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ApprovalStatus,
  ApprovalType,
  EvidenceType,
  GateStatus,
  MissionEvent,
  type Mission,
  type MissionCapabilitiesResponse,
  type MissionTransitionAPIRequest,
  type PlanApprovalSubject,
  type VerificationGateName,
} from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { Button, LinkButton, StatusBadge, Card, CardContent } from "../ui/primitives";
import { toneForStatus } from "../ui/utils";
import { planDigest } from "./missionUtils";
import { ArrowLeft, ArrowRight, ShieldCheck } from "../ui/icons";

function eventLabel(event: string): string {
  const map: Record<string, string> = {
    draft: "草稿 (Draft)",
    planning: "規劃中 (Planning)",
    plan_submitted: "計畫已提交",
    plan_approved: "計畫已核准",
    running: "執行中 (Running)",
    verifying: "驗證中 (Verifying)",
    review_ready: "待審核 (Review Ready)",
    completed: "已完成 (Completed)",
    paused: "已暫停 (Paused)",
    failed: "已失敗 (Failed)",
    cancelled: "已取消 (Cancelled)",
  };
  return map[event] || event.replaceAll("_", " ");
}

function isAllowed(capabilities: MissionCapabilitiesResponse | null, event: MissionEvent): boolean {
  return capabilities?.allowed_events.includes(event) ?? false;
}

function MissionExecutionPlanSection({
  executionPlan,
  planTitle,
  setPlanTitle,
  canStartPlanning,
  canApprovePlan,
  working,
  onStartPlanning,
  onAttachPlan,
  onApprovePlan,
}: {
  executionPlan?: Mission["execution_plan"];
  planTitle: string;
  setPlanTitle: (v: string) => void;
  canStartPlanning: boolean;
  canApprovePlan: boolean;
  working: string | null;
  onStartPlanning: () => void;
  onAttachPlan: () => void;
  onApprovePlan: () => void;
}) {
  return (
    <Card className="nordic-card">
      <CardContent className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3" style={{ borderColor: "var(--border-c)" }}>
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)]">執行計畫 (Execution Plan)</h2>
            <p className="mt-0.5 text-xs text-[var(--t3)]">在進行任何後續整合前，必須先附加上下文並由 PO 核准確切計畫主體。</p>
          </div>
          {executionPlan && (
            <StatusBadge tone={toneForStatus(executionPlan.approval_status)}>
              {executionPlan.approval_status ?? "pending"}
            </StatusBadge>
          )}
        </div>

        <div className="mt-4">
          <label htmlFor="plan-task-title-input" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
            計畫任務標題
          </label>
          <input
            id="plan-task-title-input"
            aria-label="計畫任務標題"
            value={planTitle}
            onChange={(e) => setPlanTitle(e.target.value)}
            className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)]"
          />
        </div>

        <div className="mt-4 flex flex-wrap gap-2.5">
          {canStartPlanning && (
            <Button size="sm" onClick={onStartPlanning} disabled={working !== null}>
              開始規劃
            </Button>
          )}
          {!executionPlan && (
            <Button size="sm" onClick={onAttachPlan} disabled={working !== null}>
              附加計畫
            </Button>
          )}
          {canApprovePlan && (
            <Button size="sm" variant="primary" onClick={onApprovePlan} disabled={working !== null}>
              核准確切計畫主體
            </Button>
          )}
        </div>

        <div className="mt-4 space-y-2">
          {executionPlan?.tasks.map((task) => (
            <div key={task.task_id} className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-3 text-xs">
              <div className="flex justify-between items-center gap-3">
                <span className="font-semibold text-[var(--t1)]">{task.title}</span>
                <span className="font-mono text-[10px] text-[var(--t3)]">{task.task_id}</span>
              </div>
              <p className="mt-1 text-xs text-[var(--t3)]">{task.description}</p>
            </div>
          )) ?? <p className="text-xs text-[var(--t3)]">尚未附加任何執行計畫。</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function MissionTransitionControlsSection({
  capabilities,
  working,
  transitionButtons,
  onSubmitTransition,
}: {
  capabilities: MissionCapabilitiesResponse | null;
  working: string | null;
  transitionButtons: readonly [MissionEvent, string][];
  onSubmitTransition: (event: MissionEvent) => void;
}) {
  const allowed = transitionButtons.filter(([event]) => isAllowed(capabilities, event));
  if (allowed.length === 0) return null;

  return (
    <Card className="nordic-card">
      <CardContent className="p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)] mb-3">
          狀態躍遷控制 (Transition Controls)
        </h2>
        <div className="flex flex-wrap gap-2">
          {allowed.map(([event, label]) => (
            <Button
              key={event}
              size="sm"
              onClick={() => onSubmitTransition(event)}
              disabled={working !== null}
            >
              {working === event ? "處理中…" : label}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function MissionRecordEvidenceForm({
  evidenceGate,
  setEvidenceGate,
  requiredVerification,
  evidenceType,
  setEvidenceType,
  evidenceSource,
  setEvidenceSource,
  evidenceOperation,
  setEvidenceOperation,
  evidenceStatus,
  setEvidenceStatus,
  evidenceSummary,
  setEvidenceSummary,
  evidenceArtifactRef,
  setEvidenceArtifactRef,
  evidenceExitStatus,
  setEvidenceExitStatus,
  evidenceId,
  working,
  onSubmitEvidence,
}: {
  evidenceGate: string;
  setEvidenceGate: (v: string) => void;
  requiredVerification?: readonly string[];
  evidenceType: EvidenceType;
  setEvidenceType: (v: EvidenceType) => void;
  evidenceSource: string;
  setEvidenceSource: (v: string) => void;
  evidenceOperation: string;
  setEvidenceOperation: (v: string) => void;
  evidenceStatus: GateStatus;
  setEvidenceStatus: (v: GateStatus) => void;
  evidenceSummary: string;
  setEvidenceSummary: (v: string) => void;
  evidenceArtifactRef: string;
  setEvidenceArtifactRef: (v: string) => void;
  evidenceExitStatus: string;
  setEvidenceExitStatus: (v: string) => void;
  evidenceId: string;
  working: string | null;
  onSubmitEvidence: () => void;
}) {
  return (
    <Card className="nordic-card">
      <CardContent className="p-5">
        <div className="border-b pb-3 mb-4" style={{ borderColor: "var(--border-c)" }}>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)]">
            記錄有界驗證證據 (Record Bounded Evidence)
          </h2>
          <p className="mt-0.5 text-xs text-[var(--t3)]">
            記錄單筆明確的使用者/系統驗證證據，並將其鏈結至特定查核閘口。
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label htmlFor="evidence-gate-select" className="block text-[11px] font-medium text-[var(--t2)] mb-1">驗證閘口</label>
            <select
              id="evidence-gate-select"
              aria-label="驗證閘口"
              value={evidenceGate || requiredVerification?.[0] || ""}
              onChange={(e) => setEvidenceGate(e.target.value)}
              className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none"
            >
              <option value="">選擇所需驗證閘口</option>
              {(requiredVerification ?? []).map((gate) => (
                <option key={gate} value={gate}>{gate}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="evidence-type-select" className="block text-[11px] font-medium text-[var(--t2)] mb-1">證據類型</label>
            <select
              id="evidence-type-select"
              aria-label="證據類型"
              value={evidenceType}
              onChange={(e) => setEvidenceType(e.target.value as EvidenceType)}
              className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none"
            >
              {Object.values(EvidenceType).map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="evidence-source-input" className="block text-[11px] font-medium text-[var(--t2)] mb-1">來源 (Source)</label>
            <input
              id="evidence-source-input"
              aria-label="來源"
              required
              value={evidenceSource}
              onChange={(e) => setEvidenceSource(e.target.value)}
              placeholder="例如 command, test runner 或 review"
              className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none"
            />
          </div>

          <div>
            <label htmlFor="evidence-operation-input" className="block text-[11px] font-medium text-[var(--t2)] mb-1">操作指令 / 行為 (Operation)</label>
            <input
              id="evidence-operation-input"
              aria-label="操作指令 / 行為"
              required
              value={evidenceOperation}
              onChange={(e) => setEvidenceOperation(e.target.value)}
              placeholder="例如 npm test 或 pytest"
              className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none"
            />
          </div>

          <div>
            <label htmlFor="evidence-status-select" className="block text-[11px] font-medium text-[var(--t2)] mb-1">驗證狀態</label>
            <select
              id="evidence-status-select"
              aria-label="驗證狀態"
              value={evidenceStatus}
              onChange={(e) => setEvidenceStatus(e.target.value as GateStatus)}
              className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none"
            >
              {Object.values(GateStatus).map((statusValue) => (
                <option key={statusValue} value={statusValue}>{statusValue}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="evidence-exit-status-input" className="block text-[11px] font-medium text-[var(--t2)] mb-1">結束代碼 (選填)</label>
            <input
              id="evidence-exit-status-input"
              aria-label="結束代碼"
              type="number"
              value={evidenceExitStatus}
              onChange={(e) => setEvidenceExitStatus(e.target.value)}
              placeholder="0 代表成功"
              className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none font-mono"
            />
          </div>

          <div className="md:col-span-2">
            <label htmlFor="evidence-artifact-ref-input" className="block text-[11px] font-medium text-[var(--t2)] mb-1">產物參照 (選填)</label>
            <input
              id="evidence-artifact-ref-input"
              aria-label="產物參照"
              value={evidenceArtifactRef}
              onChange={(e) => setEvidenceArtifactRef(e.target.value)}
              placeholder="例如 artifacts/report.json"
              className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none font-mono"
            />
          </div>

          <div className="md:col-span-2">
            <label htmlFor="evidence-summary-input" className="block text-[11px] font-medium text-[var(--t2)] mb-1">有界輸出摘要 (Summary)</label>
            <textarea
              id="evidence-summary-input"
              aria-label="有界輸出摘要"
              required
              value={evidenceSummary}
              onChange={(e) => setEvidenceSummary(e.target.value)}
              placeholder="請輸入測試或操作輸出的摘要內容…"
              rows={2}
              className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none"
            />
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <Button variant="primary" size="sm" onClick={onSubmitEvidence} disabled={working !== null}>
            記錄驗證證據
          </Button>
          {evidenceId && <p className="font-mono text-[10px] text-[var(--t3)]">最新記錄 ID: {evidenceId}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function MissionSidebarSection({
  mission,
  decodedMissionId,
}: {
  mission: Mission;
  decodedMissionId: string;
}) {
  return (
    <aside className="space-y-4">
      {/* Verification Gates */}
      <Card className="nordic-card">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="h-4 w-4 text-[var(--accent)]" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)]">
              驗證閘門 (Verification Gates)
            </h2>
          </div>
          <div className="space-y-2">
            {(mission.required_verification ?? []).map((gate) => {
              const record = mission.verification_gates?.find((item) => item.gate === gate);
              return (
                <div key={gate} className="flex justify-between items-center text-xs py-1 border-b border-[var(--border-c)] last:border-none">
                  <span className="text-[var(--t2)]">{gate}</span>
                  <StatusBadge tone={record?.status === GateStatus.PASSED ? "success" : "neutral"}>
                    {record?.status ?? "pending"}
                  </StatusBadge>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Evidence Records */}
      <Card className="nordic-card">
        <CardContent className="p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t2)] mb-3">
            已記錄證據 ({mission.evidence_records?.length || 0})
          </h2>
          <div className="space-y-2.5 max-h-[300px] overflow-y-auto">
            {mission.evidence_records?.length ? (
              mission.evidence_records.map((record) => (
                <div key={record.evidence_id} className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-2.5 text-xs">
                  <div className="flex justify-between items-center gap-2">
                    <StatusBadge tone={record.verification_status === GateStatus.PASSED ? "success" : "neutral"}>
                      {record.verification_status ?? "pending"}
                    </StatusBadge>
                    <span className="font-mono text-[10px] text-[var(--t3)]">{record.evidence_type}</span>
                  </div>
                  <p className="mt-1.5 text-xs text-[var(--t2)] leading-relaxed">{record.bounded_output_summary}</p>
                  <p className="mt-1 font-mono text-[10px] text-[var(--t3)] truncate">{record.operation}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-[var(--t3)]">尚無任何證據記錄。</p>
            )}
          </div>
        </CardContent>
      </Card>

      <LinkButton
        to={`/review/${encodeURIComponent(decodedMissionId)}`}
        variant="primary"
        className="w-full justify-center text-xs py-2"
      >
        <span>開啟完整審核驗收</span>
        <ArrowRight className="h-3.5 w-3.5 ml-1" />
      </LinkButton>
    </aside>
  );
}

export function MissionDetailPage() {
  const { missionId = "" } = useParams<{ missionId: string }>();
  const decodedMissionId = decodeURIComponent(missionId);
  const [mission, setMission] = useState<Mission | null>(null);
  const [capabilities, setCapabilities] = useState<MissionCapabilitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [planTitle, setPlanTitle] = useState("檢視儲存庫架構契約");
  const [evidenceGate, setEvidenceGate] = useState("");
  const [evidenceType, setEvidenceType] = useState<EvidenceType>(EvidenceType.COMMAND);
  const [evidenceSource, setEvidenceSource] = useState("");
  const [evidenceOperation, setEvidenceOperation] = useState("");
  const [evidenceStatus, setEvidenceStatus] = useState<GateStatus>(GateStatus.PENDING);
  const [evidenceSummary, setEvidenceSummary] = useState("");
  const [evidenceArtifactRef, setEvidenceArtifactRef] = useState("");
  const [evidenceExitStatus, setEvidenceExitStatus] = useState("");

  const refresh = useCallback(async (): Promise<boolean> => {
    setLoading(true);
    try {
      const [nextMission, nextCapabilities] = await Promise.all([
        missionApi.get(decodedMissionId),
        missionApi.capabilities(decodedMissionId),
      ]);
      setMission(nextMission);
      setCapabilities(nextCapabilities);
      setError(null);
      return true;
    } catch (cause: unknown) {
      if (cause instanceof MissionApiError && cause.code === "aborted") return false;
      setError(cause instanceof MissionApiError ? cause.message : "無法載入任務詳情");
      return false;
    } finally {
      setLoading(false);
    }
  }, [decodedMissionId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function submitTransition(
    event: MissionEvent,
    approvalSubject?: MissionTransitionAPIRequest["approval_subject"],
    missionOverride?: Mission
  ): Promise<void> {
    const sourceMission = missionOverride ?? mission;
    if (!sourceMission) return;
    setWorking(event);
    setError(null);
    try {
      await missionApi.transition(decodedMissionId, {
        event,
        idempotency_key: `viewer-${event}-${crypto.randomUUID()}`,
        expected_revision: sourceMission.revision ?? 0,
        approval_subject: approvalSubject,
      });
      await refresh();
    } catch (cause: unknown) {
      setError(
        cause instanceof MissionApiError && cause.code === "stale_revision"
          ? "任務已在其他工作區更新，已重新載入最新修訂版。"
          : cause instanceof MissionApiError
            ? cause.message
            : "狀態躍遷失敗"
      );
      await refresh();
    } finally {
      setWorking(null);
    }
  }

  async function attachPlan(): Promise<void> {
    if (!mission) return;
    setWorking("attach_plan");
    const plan = {
      schema_version: "1.0",
      plan_id: `plan-${mission.mission_id}`,
      mission_id: mission.mission_id,
      revision: 1,
      tasks: [
        {
          task_id: "task-1",
          title: planTitle.trim() || "檢視儲存庫架構契約",
          description: "確定性控制平面任務。遵循 PAP 協定邊界，無外部模型副作用。",
          order: 1,
          dependencies: [],
          expected_paths: ["agent_workspace", "viewer"],
          verification_requirements: ["tests"],
          estimated_risk: "low",
          estimated_provider_calls_min: 0,
          estimated_provider_calls_max: 0,
          approval_status: "pending",
        },
      ],
      approval_status: "pending",
      required_verification: mission.required_verification ?? [],
      estimated_risk: "low",
    } as const;
    try {
      await missionApi.attachPlan(mission.mission_id, {
        execution_plan: plan,
        expected_revision: mission.revision ?? 0,
      });
      await refresh();
    } catch (cause: unknown) {
      setError(cause instanceof MissionApiError ? cause.message : "附加計畫失敗");
      await refresh();
    } finally {
      setWorking(null);
    }
  }

  async function approvePlan(): Promise<void> {
    if (!mission?.execution_plan) return;
    setWorking("approve_plan");
    try {
      const subject: PlanApprovalSubject = {
        kind: "plan",
        plan_id: mission.execution_plan.plan_id,
        plan_revision: mission.execution_plan.revision ?? 1,
        plan_digest: await planDigest(mission.execution_plan),
      };
      const approved = await missionApi.recordApproval(mission.mission_id, {
        gate_id: `approval-${crypto.randomUUID()}`,
        gate_type: ApprovalType.PLAN,
        subject,
        status: ApprovalStatus.APPROVED,
        evidence_refs: [],
        idempotency_key: `viewer-approval-${crypto.randomUUID()}`,
        expected_revision: mission.revision ?? 0,
      });
      setMission(approved);
      await submitTransition(MissionEvent.APPROVE_PLAN, subject, approved);
    } catch (cause: unknown) {
      setError(cause instanceof MissionApiError ? cause.message : "核准計畫失敗");
      await refresh();
    } finally {
      setWorking(null);
    }
  }

  async function recordExplicitEvidence(): Promise<void> {
    if (!mission || state !== "running") return;
    const gate = (evidenceGate || mission.required_verification?.[0] || "") as VerificationGateName;
    const source = evidenceSource.trim();
    const operation = evidenceOperation.trim();
    const summary = evidenceSummary.trim();
    if (source === "test_fixture") {
      setError("test_fixture 為保留來源，僅供測試腳手架使用。");
      return;
    }
    if (!gate || !source || !operation || !summary) {
      setError("閘口、證據類型、來源、操作指令與摘要皆為必填項。");
      return;
    }
    const exitStatus = evidenceExitStatus.trim() === "" ? undefined : Number(evidenceExitStatus);
    if (exitStatus !== undefined && !Number.isInteger(exitStatus)) {
      setError("結束狀態碼若填寫必須為整數。");
      return;
    }
    setWorking("record_evidence");
    setError(null);
    const timestamp = new Date().toISOString();
    let recorded: Mission;
    try {
      recorded = await missionApi.recordEvidence(decodedMissionId, {
        expected_revision: mission.revision ?? 0,
        evidence: {
          evidence_id: `evidence-${crypto.randomUUID()}`,
          evidence_type: evidenceType,
          source,
          operation,
          started_at: timestamp,
          finished_at: timestamp,
          exit_status: exitStatus,
          bounded_output_summary: summary,
          artifact_ref: evidenceArtifactRef.trim() || undefined,
          producing_agent: "viewer-browser",
          requirement_links: [mission.requirement],
          task_links: [],
          plan_revision: mission.plan_revision ?? mission.execution_plan?.revision ?? undefined,
          verification_status: evidenceStatus,
        },
      });
    } catch (cause: unknown) {
      const detail = cause instanceof MissionApiError ? cause.message : "Viewer 無法儲存證據紀錄。";
      setError(`證據記錄失敗: ${detail}`);
      setWorking(null);
      return;
    }
    try {
      const verified = await missionApi.recordVerification(decodedMissionId, {
        expected_revision: recorded.revision ?? 0,
        gate: {
          gate,
          status: evidenceStatus,
          evidence_refs: [
            recorded.evidence_records?.[recorded.evidence_records.length - 1]?.evidence_id ?? "",
          ],
        },
      });
      setMission(verified);
      setEvidenceGate(gate);
      setEvidenceSource("");
      setEvidenceOperation("");
      setEvidenceSummary("");
      setEvidenceArtifactRef("");
      setEvidenceExitStatus("");
      const refreshed = await refresh();
      if (!refreshed) setError("證據與閘門鏈結已儲存，但狀態更新失敗。請手動重新整理。");
    } catch {
      setMission(recorded);
      const refreshed = await refresh();
      setError(
        refreshed
          ? "證據紀錄已儲存，但閘門鏈結失敗。"
          : "證據紀錄已儲存，但閘門鏈結及狀態更新失敗。請手動重新整理。"
      );
    } finally {
      setWorking(null);
    }
  }

  if (loading && !mission) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-xs text-[var(--t3)]">
        正在載入任務詳情…
      </div>
    );
  }

  if (error && !mission) {
    return (
      <div className="p-6">
        <div className="rounded-md border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-400" role="alert">
          <p className="font-semibold">任務無法載入</p>
          <p className="mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!mission) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-xs text-[var(--t3)]">
        找不到指定任務紀錄。
      </div>
    );
  }

  const state = mission.current_state ?? "draft";
  const digest = mission.execution_plan ? "計畫摘要已就緒 (可於審核頁檢視)" : "尚未附加計畫";
  const transitionButtons: readonly [MissionEvent, string][] = [
    [MissionEvent.START_PLANNING, "開始規劃"],
    [MissionEvent.SUBMIT_PLAN, "提交計畫"],
    [MissionEvent.BEGIN_VERIFICATION, "開始驗證"],
    [MissionEvent.COMPLETE_VERIFICATION, "完成驗證"],
    [MissionEvent.RETRY_VERIFICATION, "重試 CI 驗證"],
    [MissionEvent.PAUSE, "暫停任務"],
    [MissionEvent.RESUME, "恢復任務"],
    [MissionEvent.CANCEL, "取消任務"],
    [MissionEvent.CLOSE, "結案任務"],
  ];
  const usage = mission.usage_summary;
  const evidenceId =
    mission.evidence_records?.[mission.evidence_records.length - 1]?.evidence_id ?? "";

  return (
    <div className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto p-4 md:p-6 pb-12" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <div className="border-b pb-4" style={{ borderColor: "var(--border-c)" }}>
        <Link to="/missions" className="inline-flex items-center gap-1.5 text-xs text-[var(--t3)] hover:text-[var(--t1)] mb-3">
          <ArrowLeft className="h-3 w-3" />
          <span>返回任務清單</span>
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-[var(--t1)]">
              {mission.requirement}
            </h1>
            <p className="mt-1 font-mono text-[11px] text-[var(--t3)]">
              ID: {mission.mission_id} · Repo: {mission.repository_id}
            </p>
          </div>
          <StatusBadge tone={toneForStatus(state)}>{eventLabel(state)}</StatusBadge>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400" role="alert">
          {error}
        </div>
      )}

      {/* Stats Summary Card */}
      <div className="grid gap-3 sm:grid-cols-4">
        <Card className="nordic-card">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--t3)]">版本修訂</span>
            <p className="mt-1 font-mono text-base font-bold text-[var(--t1)]">r{mission.revision ?? 0}</p>
          </CardContent>
        </Card>
        <Card className="nordic-card">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--t3)]">計畫狀態</span>
            <p className="mt-1 text-xs font-medium text-[var(--t1)] truncate">{mission.execution_plan?.plan_id ?? "未附加"}</p>
          </CardContent>
        </Card>
        <Card className="nordic-card">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--t3)]">計畫摘要</span>
            <p className="mt-1 text-xs text-[var(--t2)] truncate">{digest}</p>
          </CardContent>
        </Card>
        <Card className="nordic-card">
          <CardContent className="p-3.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--t3)]">模型呼叫次數</span>
            <p className="mt-1 font-mono text-base font-bold text-[var(--t1)]">{usage?.provider_calls ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid */}
      <div className="grid gap-5 lg:grid-cols-[1.35fr_.65fr]">
        <div className="space-y-5">
          <MissionExecutionPlanSection
            executionPlan={mission.execution_plan}
            planTitle={planTitle}
            setPlanTitle={setPlanTitle}
            canStartPlanning={isAllowed(capabilities, MissionEvent.START_PLANNING)}
            canApprovePlan={isAllowed(capabilities, MissionEvent.APPROVE_PLAN)}
            working={working}
            onStartPlanning={() => void submitTransition(MissionEvent.START_PLANNING)}
            onAttachPlan={() => void attachPlan()}
            onApprovePlan={() => void approvePlan()}
          />

          <MissionTransitionControlsSection
            capabilities={capabilities}
            working={working}
            transitionButtons={transitionButtons}
            onSubmitTransition={(evt) => void submitTransition(evt)}
          />

          {state === "running" && (
            <MissionRecordEvidenceForm
              evidenceGate={evidenceGate}
              setEvidenceGate={setEvidenceGate}
              requiredVerification={mission.required_verification}
              evidenceType={evidenceType}
              setEvidenceType={setEvidenceType}
              evidenceSource={evidenceSource}
              setEvidenceSource={setEvidenceSource}
              evidenceOperation={evidenceOperation}
              setEvidenceOperation={setEvidenceOperation}
              evidenceStatus={evidenceStatus}
              setEvidenceStatus={setEvidenceStatus}
              evidenceSummary={evidenceSummary}
              setEvidenceSummary={setEvidenceSummary}
              evidenceArtifactRef={evidenceArtifactRef}
              setEvidenceArtifactRef={setEvidenceArtifactRef}
              evidenceExitStatus={evidenceExitStatus}
              setEvidenceExitStatus={setEvidenceExitStatus}
              evidenceId={evidenceId}
              working={working}
              onSubmitEvidence={() => void recordExplicitEvidence()}
            />
          )}
        </div>

        <MissionSidebarSection mission={mission} decodedMissionId={decodedMissionId} />
      </div>
    </div>
  );
}
