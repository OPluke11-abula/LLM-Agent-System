export function logUiDiagnostic(message: string, error?: unknown): void {
  if (import.meta.env.DEV && import.meta.env.VITE_VERBOSE_UI_LOGS === "1") {
    console.warn(message, error);
  }
}
