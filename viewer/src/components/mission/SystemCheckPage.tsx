import { useCallback, useEffect, useState } from "react";
import { missionApi } from "../../services/missionApi";
import { Button, StatusBadge, Surface } from "../ui/primitives";

type CheckState = "idle" | "checking" | "online" | "offline";

export function SystemCheckPage() {
  const [state, setState] = useState<CheckState>("idle");
  const [status, setStatus] = useState<number | null>(null);
  const check = useCallback((signal?: AbortSignal) => {
    setState("checking");
    return missionApi.checkConnection(signal).then((result) => {
      setStatus(result.status);
      setState(result.reachable ? "online" : "offline");
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void check(controller.signal);
    return () => controller.abort();
  }, [check]);

  const tone = state === "online" ? "success" : state === "offline" ? "danger" : "neutral";
  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6"><header><p className="eyebrow-label">Runtime verification</p><h1 className="mt-2 text-2xl font-semibold t1">System Check</h1><p className="mt-2 max-w-2xl text-sm t2">Connectivity only. This check does not start work, mutate a Mission, or claim provider readiness.</p></header><Surface elevated className="max-w-2xl p-5"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm font-semibold t1">Mission API</p><p className="mt-1 font-mono text-xs t3">HEAD /openapi.json</p></div><StatusBadge tone={tone}>{state}</StatusBadge></div><div className="mt-5 grid gap-2 border-t pt-4 text-sm" style={{ borderColor: "var(--border-c)" }}><div className="flex justify-between gap-4"><span className="t2">HTTP status</span><span className="font-mono t1">{status ?? "—"}</span></div><div className="flex justify-between gap-4"><span className="t2">Execution side effects</span><span className="t1">None</span></div></div><Button className="mt-5" onClick={() => void check()} disabled={state === "checking"}>{state === "checking" ? "Checking…" : "Run check again"}</Button></Surface></section>;
}
