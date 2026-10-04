import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Mission } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { StatusBadge, Card } from "../ui/primitives";
import { toneForStatus } from "../ui/utils";
import { FileCheck, AlertCircle, Inbox } from "../ui/icons";

export function ReviewIndexPage() {
  const [missions, setMissions] = useState<readonly Mission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    missionApi
      .list({ signal: controller.signal })
      .then((page) => {
        setMissions(page.items);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof MissionApiError ? cause.message : "無法載入審核隊列");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  return (
    <section className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto p-4 md:p-6 pb-8">
      {/* Header */}
      <header className="border-b border-[var(--border-c)] pb-4">
        <div className="flex items-center gap-1.5 text-xs font-mono text-[var(--t3)]">
          <FileCheck className="h-3.5 w-3.5 text-blue-400" />
          <span>任務指揮</span>
          <span>/</span>
          <span className="text-[var(--t2)]">審核驗收隊列</span>
        </div>
        <h1 className="mt-1 text-lg font-bold tracking-tight t1">審核確認</h1>
        <p className="mt-0.5 max-w-2xl text-xs t2">
          檢視任務審核記錄，確認人工審批、天梯驗證、收據憑證與審計歷史。
        </p>
      </header>

      {/* Loading State */}
      {loading && (
        <Card className="p-6 text-center text-xs t2">
          <p>載入審核隊列中…</p>
        </Card>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-rose-500/30 bg-rose-500/5 p-4" role="alert">
          <div className="flex items-center gap-2 text-rose-400">
            <AlertCircle className="h-4 w-4" />
            <p className="text-xs font-semibold">審核服務離線</p>
          </div>
          <p className="mt-1.5 text-xs text-rose-300/80">{error}</p>
        </Card>
      )}

      {/* Empty State */}
      {!loading && !error && missions.length === 0 && (
        <Card className="flex flex-col items-center justify-center p-12 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] text-[var(--t3)]">
            <Inbox className="h-5 w-5" />
          </div>
          <p className="mt-3 text-sm font-semibold t1">尚無待審核記錄</p>
          <p className="mt-1 max-w-sm text-xs t2">
            當任務進入審核狀態後，將即時呈現於此清單中。
          </p>
        </Card>
      )}

      {/* Mission Review List */}
      {!loading && !error && missions.length > 0 && (
        <div className="grid gap-2.5">
          {missions.map((mission) => {
            const state = mission.current_state ?? "draft";
            return (
              <Link
                key={mission.mission_id}
                to={`/review/${encodeURIComponent(mission.mission_id)}`}
                className="group block"
              >
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-card)] p-3.5 transition-colors hover:border-[var(--border-strong)]">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold t1 group-hover:text-blue-400 transition-colors">
                      {mission.requirement}
                    </p>
                    <p className="mt-1 font-mono text-[11px] text-[var(--t3)]">
                      {mission.mission_id}
                    </p>
                  </div>
                  <StatusBadge tone={toneForStatus(state)}>
                    {state.replace(/_/g, " ")}
                  </StatusBadge>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}
