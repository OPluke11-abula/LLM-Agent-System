import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApprovalStatus, ApprovalType, EvidenceType, GateStatus, MissionEvent, type EvidenceRecord, type Mission, type MissionCapabilitiesResponse, type MissionTransitionAPIRequest, type PlanApprovalSubject, type VerificationGateName } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { Button, LinkButton, StatusBadge, Surface, toneForStatus } from "../ui/primitives";
import { planDigest } from "./missionUtils";

const REQUIRED_GATES: readonly VerificationGateName[] = ["requirement", "scope", "architecture", "tests", "security", "quality", "ci", "cost"];
const EVIDENCE_TYPES: Record<VerificationGateName, EvidenceRecord["evidence_type"]> = { requirement: EvidenceType.TEST, scope: EvidenceType.SCOPE, architecture: EvidenceType.ARCHITECTURE, tests: EvidenceType.TEST, security: EvidenceType.SECURITY, quality: EvidenceType.QUALITY, ci: EvidenceType.CI, cost: EvidenceType.COST };

function eventLabel(event: string): string { return event.replaceAll("_", " "); }

function isAllowed(capabilities: MissionCapabilitiesResponse | null, event: MissionEvent): boolean { return capabilities?.allowed_events.includes(event) ?? false; }

export function MissionDetailPage() {
  const { missionId = "" } = useParams<{ missionId: string }>();
  const decodedMissionId = decodeURIComponent(missionId);
  const [mission, setMission] = useState<Mission | null>(null);
  const [capabilities, setCapabilities] = useState<MissionCapabilitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [planTitle, setPlanTitle] = useState("Inspect repository contract");

  const refresh = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const [nextMission, nextCapabilities] = await Promise.all([missionApi.get(decodedMissionId), missionApi.capabilities(decodedMissionId)]);
      setMission(nextMission);
      setCapabilities(nextCapabilities);
      setError(null);
    } catch (cause: unknown) {
      if (cause instanceof MissionApiError && cause.code === "aborted") return;
      setError(cause instanceof MissionApiError ? cause.message : "Mission details could not be loaded");
    } finally { setLoading(false); }
  }, [decodedMissionId]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function submitTransition(event: MissionEvent, approvalSubject?: MissionTransitionAPIRequest["approval_subject"], missionOverride?: Mission): Promise<void> {
    const sourceMission = missionOverride ?? mission;
    if (!sourceMission) return;
    setWorking(event);
    setError(null);
    try {
      await missionApi.transition(decodedMissionId, { event, idempotency_key: `viewer-${event}-${crypto.randomUUID()}`, expected_revision: sourceMission.revision ?? 0, approval_subject: approvalSubject });
      await refresh();
    } catch (cause: unknown) {
      setError(cause instanceof MissionApiError && cause.code === "stale_revision" ? "Mission changed elsewhere. The latest revision has been reloaded." : cause instanceof MissionApiError ? cause.message : "Mission transition failed");
      await refresh();
    } finally { setWorking(null); }
  }

  async function attachPlan(): Promise<void> {
    if (!mission) return;
    setWorking("attach_plan");
    const plan = { schema_version: "1.0", plan_id: `plan-${mission.mission_id}`, mission_id: mission.mission_id, revision: 1, tasks: [{ task_id: "task-1", title: planTitle.trim() || "Inspect repository contract", description: "Deterministic P1 control-plane task. No Agent execution is performed.", order: 1, dependencies: [], expected_paths: ["agent_workspace", "viewer"], verification_requirements: ["tests"], estimated_risk: "low", estimated_provider_calls_min: 0, estimated_provider_calls_max: 0, approval_status: "pending" }], approval_status: "pending", required_verification: REQUIRED_GATES, estimated_risk: "low" } as const;
    try { await missionApi.attachPlan(mission.mission_id, { execution_plan: plan, expected_revision: mission.revision ?? 0 }); await refresh(); }
    catch (cause: unknown) { setError(cause instanceof MissionApiError ? cause.message : "Plan attachment failed"); await refresh(); }
    finally { setWorking(null); }
  }

  async function approvePlan(): Promise<void> {
    if (!mission?.execution_plan) return;
    setWorking("approve_plan");
    try {
      const subject: PlanApprovalSubject = { kind: "plan", plan_id: mission.execution_plan.plan_id, plan_revision: mission.execution_plan.revision ?? 1, plan_digest: await planDigest(mission.execution_plan) };
      const approved = await missionApi.recordApproval(mission.mission_id, { gate_id: `approval-${crypto.randomUUID()}`, gate_type: ApprovalType.PLAN, subject, status: ApprovalStatus.APPROVED, evidence_refs: [], idempotency_key: `viewer-approval-${crypto.randomUUID()}`, expected_revision: mission.revision ?? 0 });
      setMission(approved);
      await submitTransition(MissionEvent.APPROVE_PLAN, subject, approved);
    } catch (cause: unknown) { setError(cause instanceof MissionApiError ? cause.message : "Plan approval failed"); await refresh(); }
    finally { setWorking(null); }
  }

  async function recordEvidenceAndVerify(): Promise<void> {
    if (!mission) return;
    setWorking("evidence");
    try {
      let current = mission;
      for (const gate of REQUIRED_GATES) {
        const timestamp = new Date().toISOString();
        const evidence: EvidenceRecord = { evidence_id: `evidence-${gate}-${crypto.randomUUID()}`, evidence_type: EVIDENCE_TYPES[gate], source: "viewer-p1-control", operation: `deterministic ${gate} verification`, started_at: timestamp, finished_at: timestamp, exit_status: 0, bounded_output_summary: `P1 deterministic control evidence for ${gate}; no provider or Git side effect.`, producing_agent: "viewer-p1-control", requirement_links: [current.requirement], task_links: current.execution_plan?.tasks.map((task) => task.task_id) ?? [], plan_revision: current.plan_revision ?? 1, verification_status: GateStatus.PASSED };
        current = await missionApi.recordEvidence(current.mission_id, { evidence, expected_revision: current.revision ?? 0 });
      }
      for (const gate of REQUIRED_GATES) current = await missionApi.recordVerification(current.mission_id, { gate: { gate, status: GateStatus.PASSED, evidence_refs: current.evidence_records?.filter((record) => record.evidence_type === EVIDENCE_TYPES[gate]).map((record) => record.evidence_id) ?? [] }, expected_revision: current.revision ?? 0 });
      current = (await missionApi.transition(current.mission_id, { event: MissionEvent.BEGIN_VERIFICATION, idempotency_key: `viewer-begin-verification-${crypto.randomUUID()}`, expected_revision: current.revision ?? 0 })).mission;
      current = (await missionApi.transition(current.mission_id, { event: MissionEvent.COMPLETE_VERIFICATION, idempotency_key: `viewer-complete-verification-${crypto.randomUUID()}`, expected_revision: current.revision ?? 0 })).mission;
      setMission(current);
      await refresh();
    } catch (cause: unknown) { setError(cause instanceof MissionApiError ? cause.message : "Deterministic evidence recording failed"); await refresh(); }
    finally { setWorking(null); }
  }

  if (loading && !mission) return <Surface elevated className="p-5 text-sm t2">Loading Mission detail…</Surface>;
  if (error && !mission) return <Surface elevated className="p-5" role="alert"><p className="font-semibold" style={{ color: "var(--danger)" }}>Mission unavailable</p><p className="mt-2 text-sm t2">{error}</p></Surface>;
  if (!mission) return <Surface elevated className="p-5 text-sm t2">Mission not found.</Surface>;
  const state = mission.current_state ?? "draft";
  const digest = mission.execution_plan ? "Plan digest available in Review" : "No plan attached";
  const transitionButtons: readonly [MissionEvent, string][] = [[MissionEvent.START_PLANNING, "Start planning"], [MissionEvent.SUBMIT_PLAN, "Submit plan"], [MissionEvent.BEGIN_VERIFICATION, "Begin verification"], [MissionEvent.COMPLETE_VERIFICATION, "Complete verification"], [MissionEvent.RETRY_VERIFICATION, "Retry CI verification"], [MissionEvent.PAUSE, "Pause"], [MissionEvent.RESUME, "Resume"], [MissionEvent.CANCEL, "Cancel"], [MissionEvent.CLOSE, "Close review-ready Mission"]];
  const scope = mission.execution_policy.scope;
  const usage = mission.usage_summary;
  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6">
    <header className="flex flex-wrap items-start justify-between gap-4"><div><Link to="/missions" className="text-xs font-semibold t3 hover:t1">← Missions</Link><p className="eyebrow-label mt-5">Mission record</p><h1 className="mt-2 max-w-3xl text-2xl font-semibold t1">{mission.requirement}</h1><p className="mt-2 font-mono text-xs t3">{mission.mission_id} · {mission.repository_id}</p></div><StatusBadge tone={toneForStatus(state)}>{eventLabel(state)}</StatusBadge></header>
    {error && <p className="text-sm" style={{ color: "var(--danger)" }} role="alert">{error}</p>}
    <Surface elevated className="grid gap-4 p-5 md:grid-cols-4"><div><p className="eyebrow-label">Revision</p><p className="mt-2 font-mono text-xl t1">r{mission.revision ?? 0}</p></div><div><p className="eyebrow-label">Updated</p><p className="mt-2 text-sm t1">{mission.updated_at ?? "Not recorded"}</p></div><div><p className="eyebrow-label">Preset</p><p className="mt-2 text-sm t1">{mission.execution_policy.preset ?? "balanced"}</p></div><div><p className="eyebrow-label">Usage</p><p className="mt-2 font-mono text-sm t1">{usage?.provider_calls ?? 0} calls{usage?.actual_cost == null ? "" : ` · ${usage.actual_cost} ${usage.currency ?? "USD"}`}</p></div></Surface>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(300px,0.8fr)]"><div className="grid gap-5"><Surface elevated className="p-5"><h2 className="text-sm font-semibold t1">State-machine capabilities</h2><p className="mt-1 text-xs t2">All legal actions below come from the backend capability response at revision {capabilities?.revision ?? mission.revision}.</p><div className="mt-4 flex flex-wrap gap-2">{transitionButtons.filter(([event]) => isAllowed(capabilities, event)).map(([event, label]) => <Button key={event} variant={event === MissionEvent.START_PLANNING || event === MissionEvent.COMPLETE_VERIFICATION ? "primary" : "quiet"} disabled={working !== null} onClick={() => void submitTransition(event)}>{working === event ? "Working…" : label}</Button>)}{capabilities?.allowed_events.length === 0 && <span className="text-sm t3">No legal human action is available.</span>}</div>{capabilities?.blocked_reason && <p className="mt-4 rounded-lg border p-3 text-sm" style={{ borderColor: "var(--warning)", color: "var(--warning)", background: "var(--warning-bg)" }}>Blocked reason: {eventLabel(capabilities.blocked_reason)}</p>}</Surface>
    <Surface elevated className="p-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-sm font-semibold t1">Execution plan</h2><p className="mt-1 text-xs t2">P1 control operation only. This attaches deterministic plan data; it never runs an Agent.</p></div>{!mission.execution_plan && state === "planning" && <Button variant="primary" disabled={working !== null} onClick={() => void attachPlan()}>{working === "attach_plan" ? "Attaching…" : "Attach deterministic P1 plan"}</Button>}{mission.execution_plan && state === "awaiting_approval" && <Button variant="primary" disabled={working !== null} onClick={() => void approvePlan()}>{working === "approve_plan" ? "Approving…" : "Approve exact plan"}</Button>}</div>{mission.execution_plan ? <div className="mt-4 grid gap-4"><div className="grid gap-2 text-sm md:grid-cols-3"><span className="font-mono t1">{mission.execution_plan.plan_id}</span><span className="t2">Revision {mission.execution_plan.revision}</span><span className="t2">{digest}</span></div><div className="grid gap-3">{mission.execution_plan.tasks.map((task) => <div key={task.task_id} className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}><div className="flex flex-wrap justify-between gap-2 text-sm"><span className="font-semibold t1">{task.order}. {task.title}</span><span className="font-mono text-xs t3">{task.task_id}</span></div><p className="mt-2 text-sm t2">{task.description}</p><p className="mt-2 text-xs t3">Dependencies: {task.dependencies?.join(", ") || "none"}</p></div>)}</div></div> : <div className="mt-4 grid gap-3"><label className="grid gap-2 text-sm font-semibold t1">Deterministic plan task title<input value={planTitle} onChange={(event) => setPlanTitle(event.target.value)} className="rounded-lg border bg-[var(--bg-muted)] px-3 py-2 text-sm font-normal t1" style={{ borderColor: "var(--border-c)" }} /></label><p className="text-sm t3">No execution, code generation, commit, push, Draft PR, or merge action is available.</p></div>}</Surface>
    <Surface elevated className="p-5"><h2 className="text-sm font-semibold t1">Scope and budget policy</h2><div className="mt-4 grid gap-4 text-sm md:grid-cols-2"><div><p className="eyebrow-label">Allowed paths</p><p className="mt-2 font-mono text-xs t2">{scope?.allowed_paths?.join(", ") || "none"}</p><p className="mt-4 eyebrow-label">Protected paths</p><p className="mt-2 font-mono text-xs t2">{scope?.protected_paths?.join(", ") || "none"}</p></div><div><p className="eyebrow-label">Permissions</p><p className="mt-2 text-xs t2">{Object.entries(scope ?? {}).filter(([key, value]) => key.endsWith("permission") && value === true).map(([key]) => eventLabel(key)).join(", ") || "No mutation permissions"}</p><p className="mt-4 eyebrow-label">Budget</p><p className="mt-2 font-mono text-xs t2">{mission.budget_policy?.provider_call_limit ?? 64} calls · {mission.budget_policy?.max_cost == null ? "no cost limit" : `${mission.budget_policy.max_cost} ${mission.budget_policy.currency ?? "USD"}`}</p></div></div></Surface>
    </div><aside className="grid content-start gap-5"><Surface elevated className="p-5"><h2 className="text-sm font-semibold t1">P1 development controls</h2><p className="mt-1 text-xs t2">Explicitly labeled deterministic evidence operation for local verification only.</p>{isAllowed(capabilities, MissionEvent.APPROVE_PLAN) && <Button className="mt-4 w-full" variant="primary" disabled={working !== null} onClick={() => void approvePlan()}>Approve exact plan subject</Button>}{state === "running" && <Button className="mt-3 w-full" disabled={working !== null} onClick={() => void recordEvidenceAndVerify()}>{working === "evidence" ? "Recording evidence…" : "Record deterministic evidence + gates"}</Button>}<div className="mt-4 grid gap-2 text-xs t3"><p>Repository connection not implemented</p><p>Repository inspection not implemented</p><p>Agent execution not implemented</p><p>Git mutation not implemented</p><p>Draft PR delivery not implemented</p><p>Auto-merge disabled</p></div></Surface><Surface elevated className="p-5"><h2 className="text-sm font-semibold t1">Evidence records</h2><div className="mt-4 grid gap-3">{mission.evidence_records?.length ? mission.evidence_records.map((record) => <div key={record.evidence_id} className="border-b pb-3 text-xs" style={{ borderColor: "var(--border-c)" }}><div className="flex justify-between gap-2"><StatusBadge tone={record.verification_status === GateStatus.PASSED ? "success" : "neutral"}>{record.verification_status ?? "pending"}</StatusBadge><span className="font-mono t3">{record.evidence_type}</span></div><p className="mt-2 t2">{record.bounded_output_summary}</p><p className="mt-1 font-mono t3">{record.operation}</p></div>) : <p className="text-sm t3">No evidence recorded.</p>}</div></Surface><Surface elevated className="p-5"><h2 className="text-sm font-semibold t1">Verification gates</h2><div className="mt-4 grid gap-2">{(mission.required_verification ?? REQUIRED_GATES).map((gate) => { const record = mission.verification_gates?.find((item) => item.gate === gate); return <div key={gate} className="flex justify-between gap-3 text-sm"><span className="t2">{gate}</span><StatusBadge tone={record?.status === GateStatus.PASSED ? "success" : "neutral"}>{record?.status ?? "pending"}</StatusBadge></div>; })}</div></Surface><LinkButton to={`/review/${encodeURIComponent(decodedMissionId)}`} className="w-full justify-center">Open evidence-backed Review</LinkButton></aside></div>
  </section>;
}
