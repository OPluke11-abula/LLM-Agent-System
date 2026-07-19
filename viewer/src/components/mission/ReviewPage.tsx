import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Mission, MissionTransitionPage } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { StatusBadge, Surface, toneForStatus } from "../ui/primitives";

export function ReviewPage() {
  const { missionId = "" } = useParams<{ missionId: string }>();
  const decodedMissionId = decodeURIComponent(missionId);
  const [mission, setMission] = useState<Mission | null>(null);
  const [history, setHistory] = useState<MissionTransitionPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([missionApi.get(decodedMissionId, controller.signal), missionApi.history(decodedMissionId, { signal: controller.signal })]).then(([nextMission, nextHistory]) => {
      setMission(nextMission);
      setHistory(nextHistory);
    }).catch((cause: unknown) => {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError(cause instanceof MissionApiError ? cause.message : "Review data could not be loaded");
    });
    return () => controller.abort();
  }, [decodedMissionId]);

  if (error) return <Surface elevated className="p-5" role="alert"><p className="font-semibold" style={{ color: "var(--danger)" }}>Review unavailable</p><p className="mt-2 text-sm t2">{error}</p></Surface>;
  if (!mission || !history) return <Surface elevated className="p-5 text-sm t2">Loading review evidence…</Surface>;
  const state = mission.current_state ?? "draft";
  const approvals = mission.approval_gates ?? [];
  const verifications = mission.verification_gates ?? [];
  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6"><header><Link to={`/missions/${encodeURIComponent(decodedMissionId)}`} className="text-xs font-semibold t3 hover:t1">← Mission detail</Link><p className="eyebrow-label mt-5">Review surface</p><div className="mt-2 flex flex-wrap items-center gap-3"><h1 className="text-2xl font-semibold t1">Review record</h1><StatusBadge tone={toneForStatus(state)}>{state.replace(/_/g, " ")}</StatusBadge></div><p className="mt-2 max-w-2xl text-sm t2">Auditable plan, approval, evidence, and transition context. No merge or execution action is exposed here.</p></header><div className="grid gap-3 lg:grid-cols-2"><Surface elevated className="p-5"><p className="text-sm font-semibold t1">Approval gates</p><div className="mt-4 grid gap-2">{approvals.length === 0 ? <p className="text-sm t3">No approval decision recorded.</p> : approvals.map((gate) => <div key={gate.gate_id} className="flex items-center justify-between gap-3 border-b pb-2 text-sm" style={{ borderColor: "var(--border-c)" }}><span className="t2">{gate.gate_type}</span><StatusBadge tone={toneForStatus(gate.status)}>{gate.status ?? "pending"}</StatusBadge></div>)}</div></Surface><Surface elevated className="p-5"><p className="text-sm font-semibold t1">Verification gates</p><div className="mt-4 grid gap-2">{verifications.length === 0 ? <p className="text-sm t3">No verification result recorded.</p> : verifications.map((gate) => <div key={gate.gate} className="flex items-center justify-between gap-3 border-b pb-2 text-sm" style={{ borderColor: "var(--border-c)" }}><span className="t2">{gate.gate}</span><StatusBadge tone={toneForStatus(gate.status)}>{gate.status ?? "pending"}</StatusBadge></div>)}</div></Surface></div><Surface elevated className="p-5"><p className="text-sm font-semibold t1">Transition history</p><div className="mt-4 grid gap-2">{history.items.length === 0 ? <p className="text-sm t3">No transitions recorded.</p> : history.items.map((item) => <div key={item.audit_id} className="grid gap-1 border-b pb-3 text-sm md:grid-cols-[1fr_auto]" style={{ borderColor: "var(--border-c)" }}><span className="font-mono t1">{item.event}</span><span className="font-mono text-xs t3">r{item.from_revision} → r{item.to_revision}</span><span className="text-xs t3">{item.actor_id} · {item.occurred_at}</span></div>)}</div></Surface></section>;
}
