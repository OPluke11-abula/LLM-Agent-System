const ADMIN_API_KEY_STORAGE_KEY = "las_admin_api_key";
const API_BASE_URL = "http://localhost:8000";

function readAdminApiKey(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(ADMIN_API_KEY_STORAGE_KEY)?.trim() ?? "";
}

export function adminAuthHeaders(): Record<string, string> {
  const apiKey = readAdminApiKey();
  return apiKey ? { "x-api-key": apiKey } : {};
}

export function adminJsonHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...adminAuthHeaders(),
  };
}

export function adminApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export function adminWsUrl(path: string): string {
  const url = new URL(path, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const apiKey = readAdminApiKey();
  if (apiKey) {
    url.searchParams.set("api_key", apiKey);
  }
  return url.toString();
}
