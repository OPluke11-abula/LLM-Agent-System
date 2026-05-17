import { useEffect, useState } from "react";

export function usePersistedState<T>(key: string, initial: T) {
  const [state, setState] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored !== null) {
        return JSON.parse(stored) as T;
      }
    } catch {
      // Ignore invalid localStorage payloads and fall back to defaults.
    }

    return initial;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(state));
  }, [key, state]);

  return [state, setState] as const;
}
