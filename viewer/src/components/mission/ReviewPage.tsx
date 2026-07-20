import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { EVIDENCE_TYPE_COMPATIBILITY, GateStatus, type Mission, type MissionTransitionPage } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { StatusBadge, Surface, toneForStatus } from "../ui/primitives";
import { planDigest } from "./missionUtils";

function label(value: string): string { return value.replaceAll("_", " "); }

export function ReviewPage() {
  const { missionId = "" } = useParams<{ missionId: string }>();
  const decodedMissionId = decodeURIComponent(missionId);
  const [mission, setMission] = useState<Mission | null>(null);
  const [history, setHistory] = useState<MissionTransitionPage | null>(null);
  const [digest, setDigest] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([missionApi.get(decodedMissionId, controller.signal), missionApi.history(decodedMissionId, { signal: controller.signal })]).then(async ([nextMission, nextHistory]) => {
      setMission(nextMission);
      setHistory(nextHistory);
      setDigest(nextMission.execution_plan ? await planDigest(nextMission.execution_plan) : null);
    }).catch((cause: unknown) => {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError(cause instanceof MissionApiError ? cause.message : "Review data could not be loaded");
    });
    return () => controller.abort();
  }, [decodedMissionId]);

  async function loadMoreHistory(): Promise<void> {
    if (!history?.next_offset || loadingHistory) return;
    setLoadingHistory(true);
    try {
      const next = await missionApi.history(decodedMissionId, { offset: history.next_offset });
      setHistory({ ...next, items: [...history.items, ...next.items] });
    } catch (cause: unknown) { setError(cause instanceof MissionApiError ? cause.message : "More transition history could not be loaded"); }
    finally { setLoadingHistory(false); }
  }

  if (error) return <Surface elevated className="p-5" role="alert"><p className="font-semibold" style={{ color: "var(--danger)" }}>Review unavailable</p><p className="mt-2 text-sm t2">{error}</p></Surface>;
  if (!mission || !history) return <Surface elevated className="p-5 text-sm t2">Loading review evidence…</Surface>;
  const state = mission.current_state ?? "draft";
  const approvals = mission.approval_gates ?? [];
  const verifications = mission.verification_gates ?? [];
  const evidence = mission.evidence_records ?? [];
  const evidenceById = new Map(evidence.map((record) => [record.evidence_id, record]));
  const gateRows = (mission.required_verification ?? []).map((gate) => {
    const record = verifications.find((item) => item.gate === gate);
    const refs = record?.evidence_refs ?? [];
    const linkedEvidence = refs.map((ref) => evidenceById.get(ref));
    const refsValid = refs.length > 0 && linkedEvidence.every((item) => item !== undefined);
    const compatibleTypes = EVIDENCE_TYPE_COMPATIBILITY[gate] as readonly string[];
    const typesCompatible = linkedEvidence.every((item) => item !== undefined && compatibleTypes.includes(item.evidence_type));
    const pass = record?.status === GateStatus.PASSED && refsValid && linkedEvidence.every((item) => item?.verification_status === GateStatus.PASSED) && typesCompatible;
    return { gate, record, refs, linkedEvidence, pass, typesCompatible };
  });
  const unresolved = gateRows.filter((row) => !row.pass);
  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6">
    <header><Link to={`/missions/${encodeURIComponent(decodedMissionId)}`} className="text-xs font-semibold t3 hover:t1">← Mission detail</Link><p className="eyebrow-label mt-5">Evidence-backed review</p><div className="mt-2 flex flex-wrap items-center gap-3"><h1 className="text-2xl font-semibold t1">{mission.requirement}</h1><StatusBadge tone={toneForStatus(state)}>{label(state)}</StatusBadge></div><p className="mt-2 font-mono text-xs t3">{mission.mission_id} · {mission.repository_id} · revision {mission.revision}</p></header>
    <Surface elevated className="grid gap-4 p-5 md:grid-cols-4"><div><p className="eyebrow-label">Plan</p><p className="mt-2 font-mono text-xs t1">{mission.execution_plan?.plan_id ?? "not attached"}</p></div><div><p className="eyebrow-label">Plan revision</p><p className="mt-2 text-sm t1">{mission.execution_plan?.revision ?? "—"}</p></div><div className="md:col-span-2"><p className="eyebrow-label">Canonical SHA-256</p><p className="mt-2 break-all font-mono text-xs t2">{digest ?? "No plan digest recorded"}</p></div></Surface>
    <div className="grid gap-5 lg:grid-cols-2"><Surface elevated className="p-5"><h2 className="text-sm font-semibold t1">Approval subjects</h2><div className="mt-4 grid gap-3">{approvals.length === 0 ? <p className="text-sm t3">No approval decision recorded.</p> : approvals.map((gate) => <details key={gate.gate_id} className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}><summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm"><span className="t1">{gate.gate_type} · {gate.gate_id}</span><StatusBadge tone={toneForStatus(gate.status)}>{gate.status ?? "pending"}</StatusBadge></summary><div className="mt-3 grid gap-1 text-xs t2"><p>Subject: {gate.subject.kind}</p>{gate.subject.kind === "plan" && <><p>Plan: {gate.subject.plan_id} r{gate.subject.plan_revision}</p><p className="break-all font-mono">Digest: {gate.subject.plan_digest}</p></>}<p>Idempotency key: {gate.idempotency_key}</p><p>Evidence refs: {gate.evidence_refs?.join(", ") || "none"}</p></div></details>)}</div></Surface><Surface elevated className="p-5"><h2 className="text-sm font-semibold t1">Verification gates</h2><div className="mt-4 grid gap-2">{gateRows.map(({ gate, record, refs, linkedEvidence, pass, typesCompatible }) => <details key={gate} className="rounded-lg border p-3" style={{ borderColor: pass ? "var(--border-c)" : "var(--warning)" }}><summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm"><span className="t2">{gate}</span><StatusBadge tone={pass ? "success" : "warning"}>{pass ? GateStatus.PASSED : record?.status ?? GateStatus.PENDING}</StatusBadge></summary><div className="mt-2 grid gap-2 text-xs t3"><p>Gate status: {record?.status ?? GateStatus.PENDING}</p><p>Evidence refs: {refs.join(", ") || "none"}</p>{refs.length > 0 && linkedEvidence.map((item, index) => item ? <div key={item.evidence_id} className="grid gap-1 rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}><p>Evidence ID: {item.evidence_id}</p><p>Type: {item.evidence_type}</p><p>Source: {item.source}</p><p>Operation: {item.operation}</p><p>Verification status: {item.verification_status ?? GateStatus.PENDING}</p><p>Started: {item.started_at}</p><p>Finished: {item.finished_at}</p><p>Exit status: {item.exit_status ?? "not recorded"}</p><p>Bounded output summary: {item.bounded_output_summary || "not recorded"}</p><p>Artifact ref: {item.artifact_ref ?? "not recorded"}</p></div> : <p key={refs[index]} style={{ color: "var(--danger)" }}>Broken evidence reference: {refs[index]}</p>)}{!typesCompatible && <p style={{ color: "var(--danger)" }}>Evidence type is incompatible with this gate.</p>}{pass && <p>All linked evidence records are present, passed, and type-compatible.</p>}</div></details>)}</div>{unresolved.length > 0 && <p className="mt-4 rounded-lg border p-3 text-sm" style={{ borderColor: "var(--warning)", color: "var(--warning)", background: "var(--warning-bg)" }}>Residual uncertainty: {unresolved.map((gate) => gate.gate).join(", ")} is missing valid passed evidence linkage.</p>}</Surface></div>
    <Surface elevated className="p-5"><h2 className="text-sm font-semibold t1">Evidence records</h2><div className="mt-4 grid gap-3">{evidence.length === 0 ? <p className="text-sm t3">No evidence recorded.</p> : evidence.map((record) => <details key={record.evidence_id} className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}><summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm"><span className="font-mono text-xs t1">{record.evidence_id}</span><StatusBadge tone={toneForStatus(record.verification_status)}>{record.verification_status ?? "pending"}</StatusBadge></summary><div className="mt-3 grid gap-1 text-xs t2"><p>Type: {record.evidence_type} · source: {record.source}</p><p>Operation: {record.operation}</p><p>Producer: {record.producing_agent}</p><p>Exit status: {record.exit_status ?? "not recorded"}</p><p className="t1">{record.bounded_output_summary || "No bounded summary recorded."}</p><p>Tasks: {record.task_links?.join(", ") || "none"}</p></div></details>)}</div></Surface>
    <Surface elevated className="p-5"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-sm font-semibold t1">Transition history</h2>{history.next_offset != null && <button type="button" className="quiet-button rounded-lg px-3 py-2 text-xs font-semibold" onClick={() => void loadMoreHistory()} disabled={loadingHistory}>{loadingHistory ? "Loading…" : "Load more"}</button>}</div><div className="mt-4 grid gap-2">{history.items.length === 0 ? <p className="text-sm t3">No transitions recorded.</p> : history.items.map((item) => <div key={item.audit_id} className="grid gap-1 border-b pb-3 text-sm md:grid-cols-[1fr_auto]" style={{ borderColor: "var(--border-c)" }}><span className="font-mono t1">{label(item.event)}</span><span className="font-mono text-xs t3">r{item.from_revision} → r{item.to_revision}</span><span className="text-xs t3">{item.actor_id} · {item.occurred_at}</span></div>)}</div></Surface>
    <Surface elevated className="p-5"><h2 className="text-sm font-semibold t1">Delivery boundary</h2><p className="mt-2 text-sm t2">P1 does not create or publish a Draft PR. A final delivery subject will appear here only when a later, authorized integration records one.</p>{mission.final_draft_pr ? <p className="mt-3 font-mono text-xs t1">{mission.final_draft_pr.url}</p> : <p className="mt-3 text-xs t3">Draft PR delivery: not implemented</p>}</Surface>
  </section>;
}
