import { browserSessionAuthHeaders } from "./missionAuth";

const API_BASE_URL = "http://localhost:8000";

export function adminAuthHeaders(): Record<string, string> {
  return browserSessionAuthHeaders();
}

export function adminJsonHeaders(): Record<string, string> {
  return { "Content-Type": "application/json", ...adminAuthHeaders() };
}

export function adminApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export function adminWsUrl(path: string): string {
  const url = new URL(path, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}
