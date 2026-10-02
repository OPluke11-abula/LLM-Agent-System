import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Mission } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { LinkButton, StatusBadge, Surface } from "../ui/primitives";
import { toneForStatus } from "../ui/utils";

export function MissionListPage() {
  const [missions, setMissions] = useState<readonly Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    missionApi.list({ signal: controller.signal }).then((page) => {
      setMissions(page.items);
      setError(null);
    }).catch((cause: unknown) => {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError(cause instanceof MissionApiError ? cause.message : "Mission list could not be loaded");
    }).finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow-label">任務調度中樞</p><h1 className="mt-2 text-2xl font-semibold t1">任務清單</h1><p className="mt-2 max-w-2xl text-sm t2">持久化工作記錄、人機審批、驗證收據與安全防護。</p></div><LinkButton to="/missions/new" variant="primary">新增任務</LinkButton></header>
    {loading && <Surface elevated className="p-5 text-sm t2">載入任務記錄中…</Surface>}
    {error && <Surface elevated className="border border-[color:var(--danger)] p-5" role="alert"><p className="text-sm font-semibold" style={{ color: "var(--danger)" }}>任務 API 服務離線</p><p className="mt-2 text-sm t2">{error}</p><p className="mt-3 text-xs t3">請從「系統診斷」檢查 API 連線狀態。</p></Surface>}
    {!loading && !error && missions.length === 0 && <Surface elevated className="p-8 text-center"><p className="text-lg font-semibold t1">尚無任務記錄</p><p className="mx-auto mt-2 max-w-md text-sm t2">建立任務以開啟可驗證、作用域受限的自主工作流。</p><LinkButton to="/missions/new" variant="primary" className="mt-5 inline-flex">建立第一個任務</LinkButton></Surface>}
    {!loading && !error && missions.length > 0 && <div className="grid gap-3">{missions.map((mission) => { const state = mission.current_state ?? "draft"; return <Link key={mission.mission_id} to={`/missions/${encodeURIComponent(mission.mission_id)}`}><Surface elevated className="flex flex-wrap items-center justify-between gap-4 p-4 transition-colors hover:border-[color:var(--border-strong)]"><div className="min-w-0"><p className="truncate text-sm font-semibold t1">{mission.requirement}</p><p className="mt-1 font-mono text-[11px] t3">{mission.mission_id} · {mission.repository_id}</p></div><div className="flex items-center gap-3"><StatusBadge tone={toneForStatus(state)}>{state.replace(/_/g, " ")}</StatusBadge><span className="font-mono text-xs t3">r{mission.revision ?? 0}</span></div></Surface></Link>; })}</div>}
  </section>;
}
