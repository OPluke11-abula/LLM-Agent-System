import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Mission } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { StatusBadge, Surface, toneForStatus } from "../ui/primitives";

export function ReviewIndexPage() {
  const [missions, setMissions] = useState<readonly Mission[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    missionApi.list({ signal: controller.signal }).then((page) => setMissions(page.items)).catch((cause: unknown) => {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError(cause instanceof MissionApiError ? cause.message : "Review queue could not be loaded");
    });
    return () => controller.abort();
  }, []);

  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6"><header><p className="eyebrow-label">Review queue</p><h1 className="mt-2 text-2xl font-semibold t1">Review</h1><p className="mt-2 max-w-2xl text-sm t2">Open a Mission review record to inspect approvals, verification, evidence, and audit history.</p></header>{error && <Surface elevated className="p-5" role="alert"><p className="font-semibold" style={{ color: "var(--danger)" }}>Review unavailable</p><p className="mt-2 text-sm t2">{error}</p></Surface>}{!error && missions.length === 0 && <Surface elevated className="p-8 text-center"><p className="text-lg font-semibold t1">No review records</p><p className="mt-2 text-sm t2">Missions will appear here once the authenticated API returns them.</p></Surface>}{!error && missions.length > 0 && <div className="grid gap-3">{missions.map((mission) => { const state = mission.current_state ?? "draft"; return <Link key={mission.mission_id} to={`/review/${encodeURIComponent(mission.mission_id)}`}><Surface elevated className="flex flex-wrap items-center justify-between gap-4 p-4"><div><p className="text-sm font-semibold t1">{mission.requirement}</p><p className="mt-1 font-mono text-xs t3">{mission.mission_id}</p></div><StatusBadge tone={toneForStatus(state)}>{state.replace(/_/g, " ")}</StatusBadge></Surface></Link>; })}</div>}</section>;
}
