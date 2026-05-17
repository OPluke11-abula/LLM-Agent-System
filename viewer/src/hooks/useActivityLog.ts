import { useCallback, useState } from "react";
import type { ActivityLogEntry, ActivityLogInput } from "../types";

const DEFAULT_ACTIVITY_LIMIT = 40;

function createActivityId() {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }

  return `activity-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useActivityLog(limit = DEFAULT_ACTIVITY_LIMIT) {
  const [activityEntries, setActivityEntries] = useState<ActivityLogEntry[]>([]);

  const recordActivity = useCallback(
    (activity: ActivityLogInput) => {
      setActivityEntries((current) =>
        [
          {
            ...activity,
            id: createActivityId(),
            timestamp: new Date().toISOString(),
          },
          ...current,
        ].slice(0, limit),
      );
    },
    [limit],
  );

  const clearActivityLog = useCallback(() => {
    setActivityEntries([]);
  }, []);

  return {
    activityEntries,
    recordActivity,
    clearActivityLog,
  };
}
