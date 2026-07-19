import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Mission, MissionCapabilitiesResponse } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { Button, LinkButton, StatusBadge, Surface, toneForStatus } from "../ui/primitives";

export function MissionDetailPage() {
  const { missionId = "" } = useParams<{ missionId: string }>();
  const decodedMissionId = decodeURIComponent(missionId);
  const [mission, setMission] = useState<Mission | null>(null);
  const [capabilities, setCapabilities] = useState<MissionCapabilitiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback((signal?: AbortSignal) => {
    setLoading(true);
    return Promise.all([missionApi.get(decodedMissionId, signal), missionApi.capabilities(decodedMissionId, signal)]).then(([nextMission, nextCapabilities]) => {
      setMission(nextMission);
      setCapabilities(nextCapabilities);
      setError(null);
    }).catch((cause: unknown) => {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError(cause instanceof MissionApiError ? cause.message : "Mission details could not be loaded");
    }).finally(() => setLoading(false));
  }, [decodedMissionId]);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  async function startPlanning() {
    setWorking(true);
    setError(null);
    try {
      await missionApi.transition(decodedMissionId, { event: "start_planning", idempotency_key: `viewer-start-${crypto.randomUUID()}`, expected_revision: mission?.revision ?? 0 });
      await refresh();
    } catch (cause: unknown) {
      setError(cause instanceof MissionApiError ? cause.message : "Transition could not be submitted");
    } finally {
      setWorking(false);
    }
  }

  if (loading && !mission) return <Surface elevated className="p-5 text-sm t2">Loading Mission detail…</Surface>;
  if (error && !mission) return <Surface elevated className="p-5" role="alert"><p className="font-semibold" style={{ color: "var(--danger)" }}>Mission unavailable</p><p className="mt-2 text-sm t2">{error}</p></Surface>;
  if (!mission) return <Surface elevated className="p-5 text-sm t2">Mission not found.</Surface>;

  const state = mission.current_state ?? "draft";
  const canStartPlanning = capabilities?.allowed_events.includes("start_planning") ?? false;
  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6"><header className="flex flex-wrap items-start justify-between gap-4"><div><Link to="/missions" className="text-xs font-semibold t3 hover:t1">← Missions</Link><p className="eyebrow-label mt-5">Mission record</p><h1 className="mt-2 max-w-3xl text-2xl font-semibold t1">{mission.requirement}</h1><p className="mt-2 font-mono text-xs t3">{mission.mission_id} · {mission.repository_id}</p></div><StatusBadge tone={toneForStatus(state)}>{state.replace(/_/g, " ")}</StatusBadge></header>{error && <p className="text-sm" style={{ color: "var(--danger)" }} role="alert">{error}</p>}<div className="grid gap-3 md:grid-cols-3"><Surface elevated className="p-4"><p className="text-[10px] font-semibold uppercase tracking-[0.14em] t3">Revision</p><p className="mt-2 font-mono text-xl t1">r{mission.revision ?? 0}</p></Surface><Surface elevated className="p-4"><p className="text-[10px] font-semibold uppercase tracking-[0.14em] t3">Evidence</p><p className="mt-2 font-mono text-xl t1">{mission.evidence_records?.length ?? 0}</p></Surface><Surface elevated className="p-4"><p className="text-[10px] font-semibold uppercase tracking-[0.14em] t3">Verification</p><p className="mt-2 font-mono text-xl t1">{mission.verification_gates?.length ?? 0}/{mission.required_verification?.length ?? 0}</p></Surface></div><Surface elevated className="p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold t1">Capabilities</p><p className="mt-1 text-xs t2">Read from the backend state machine for revision {capabilities?.revision ?? mission.revision}.</p></div>{canStartPlanning && <Button variant="primary" disabled={working} onClick={() => void startPlanning()}>{working ? "Submitting…" : "Start planning"}</Button>}</div>{capabilities?.blocked_reason && <p className="mt-4 rounded-lg border p-3 text-sm" style={{ borderColor: "var(--warning)", color: "var(--warning)", background: "var(--warning-bg)" }}>Blocked by {capabilities.blocked_reason.replace(/_/g, " ")}.</p>}<div className="mt-4 flex flex-wrap gap-2" aria-label="Allowed Mission events">{capabilities?.allowed_events.map((event) => <StatusBadge key={event} tone="neutral">{event.replace(/_/g, " ")}</StatusBadge>)}{capabilities?.allowed_events.length === 0 && <span className="text-sm t3">No state transition is currently available.</span>}</div></Surface><div className="flex flex-wrap gap-3"><LinkButton to={`/review/${encodeURIComponent(decodedMissionId)}`}>Open review</LinkButton><LinkButton to="/system">System Check</LinkButton></div></section>;
}
