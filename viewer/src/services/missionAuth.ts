import { invoke } from "@tauri-apps/api/core";

export type MissionRuntimeMode = "browser" | "tauri";

export interface MissionAuthProvider {
  readonly mode: MissionRuntimeMode;
  readonly configured: boolean;
  getHeaders(): Promise<Readonly<Record<string, string>>>;
  clear(): void;
}

declare global {
  interface Window {
    __LAS_BROWSER_SESSION_CREDENTIAL__?: string;
    __TAURI_INTERNALS__?: unknown;
  }
}

function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

function readBrowserCredential(): string {
  if (typeof window === "undefined") return "";
  return window.__LAS_BROWSER_SESSION_CREDENTIAL__?.trim() ?? "";
}

class BrowserMissionAuthProvider implements MissionAuthProvider {
  readonly mode = "browser" as const;
  private credential: string;

  constructor() {
    this.credential = readBrowserCredential();
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
    if (typeof window !== "undefined") {
      if (this.credential) window.__LAS_BROWSER_SESSION_CREDENTIAL__ = this.credential;
      else delete window.__LAS_BROWSER_SESSION_CREDENTIAL__;
    }
  }

  clear(): void {
    this.setCredential("");
  }
}

class TauriMissionAuthProvider implements MissionAuthProvider {
  readonly mode = "tauri" as const;
  private available = true;

  get configured(): boolean {
    return this.available;
  }

  async getHeaders(): Promise<Readonly<Record<string, string>>> {
    try {
      const headers = await invoke<Record<string, string>>("get_mission_auth_headers");
      if (Object.keys(headers).some((key) => key.toLowerCase() === "x-api-key")) {
        throw new Error("native auth provider returned a forbidden API-key header");
      }
      return headers;
    } catch (error: unknown) {
      this.available = false;
      const message = error instanceof Error ? error.message : "Native authentication is unavailable";
      throw new Error(message);
    }
  }

  clear(): void {
    void invoke("clear_mission_session").catch((error: unknown) => {
      if (error instanceof Error) return;
      return undefined;
    });
    this.available = false;
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
