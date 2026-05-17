import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { TopologyState } from "../types";

function isTopologyState(value: unknown): value is TopologyState {
  if (!value || typeof value !== "object") return false;
  const state = value as Partial<TopologyState>;
  return (
    state.schema_version === "1.0.0" &&
    typeof state.session_id === "string" &&
    Array.isArray(state.nodes) &&
    Array.isArray(state.edges) &&
    typeof state.stats === "object"
  );
}

export function useTopology() {
  const [sessions, setSessions] = useState<Record<string, TopologyState>>({});
  const [lastUpdatedSessionId, setLastUpdatedSessionId] = useState<string | null>(null);
  const isTauriAvailable = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

  useEffect(() => {
    if (!isTauriAvailable) return;

    let cancelled = false;
    let disposeListener: (() => void) | undefined;

    invoke<unknown>("load_topology_state")
      .then((payload) => {
        if (cancelled || !isTopologyState(payload)) return;
        setSessions((current) => ({ ...current, [payload.session_id]: payload }));
        setLastUpdatedSessionId(payload.session_id);
      })
      .catch(() => undefined);

    listen<unknown>("topology_updated", (event) => {
      const payload = event.payload;
      if (cancelled || !isTopologyState(payload)) return;
      setSessions((current) => ({ ...current, [payload.session_id]: payload }));
      setLastUpdatedSessionId(payload.session_id);
    })
      .then((dispose) => {
        disposeListener = dispose;
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
      disposeListener?.();
    };
  }, [isTauriAvailable]);

  const sessionList = useMemo(
    () => Object.values(sessions).sort((a, b) => b.updated_at.localeCompare(a.updated_at)),
    [sessions],
  );

  return {
    sessions,
    sessionList,
    hasTopology: sessionList.length > 0,
    lastUpdatedSessionId,
  };
}
