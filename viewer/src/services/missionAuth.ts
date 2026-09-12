export type MissionRuntimeMode = "browser" | "tauri";

export interface MissionAuthProvider {
  readonly mode: MissionRuntimeMode;
  readonly configured: boolean;
  getHeaders(): Promise<Readonly<Record<string, string>>>;
  clear(): void;
}

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

class BrowserMissionAuthProvider implements MissionAuthProvider {
  readonly mode = "browser" as const;
  private credential: string;

  constructor() {
    this.credential = "";
  }

  get configured(): boolean {
    return this.credential.length > 0;
  }

  getHeaders(): Promise<Readonly<Record<string, string>>> {
    const headers: Readonly<Record<string, string>> = this.configured ? { "x-api-key": this.credential } : {};
    return Promise.resolve(headers);
  }

  syncHeaders(): Record<string, string> {
    return this.configured ? { "x-api-key": this.credential } : {};
  }

  setCredential(credential: string): void {
    this.credential = credential.trim();
  }

  clear(): void {
    this.setCredential("");
  }
}

class TauriMissionAuthProvider implements MissionAuthProvider {
  readonly mode = "tauri" as const;

  get configured(): boolean {
    return false;
  }

  getHeaders(): Promise<Readonly<Record<string, string>>> {
    return Promise.reject(new Error("Tauri Mission authentication is unavailable; use browser mode."));
  }

  clear(): void {
  }
}

const browserProvider = new BrowserMissionAuthProvider();
export const missionAuth: MissionAuthProvider = isTauriRuntime() ? new TauriMissionAuthProvider() : browserProvider;

export function setBrowserSessionCredential(credential: string): void {
  if (browserProvider.mode === missionAuth.mode) browserProvider.setCredential(credential);
}

export function browserSessionAuthHeaders(): Record<string, string> {
  return browserProvider.syncHeaders();
}

export function clearMissionSession(): void {
  missionAuth.clear();
}
