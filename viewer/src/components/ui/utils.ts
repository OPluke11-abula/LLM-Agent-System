export type Tone = "neutral" | "accent" | "success" | "warning" | "danger";

export function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export const toneVar: Record<Tone, string> = {
  neutral: "var(--t3)",
  accent: "var(--accent)",
  success: "var(--success)",
  warning: "var(--warning)",
  danger: "var(--danger)",
};

export const toneBgVar: Record<Tone, string> = {
  neutral: "var(--bg-muted)",
  accent: "var(--accent-bg)",
  success: "var(--success-bg)",
  warning: "var(--warning-bg)",
  danger: "var(--danger-bg)",
};

export function toneForStatus(status?: string): Tone {
  const value = status?.toLowerCase() ?? "";
  if (["active", "healthy", "connected", "completed", "done", "allowed"].includes(value)) return "success";
  if (["paused", "pending", "frozen", "review", "awaiting_approval", "optimizing"].includes(value)) return "warning";
  if (["blocked", "canceled", "tampered", "offline", "error", "failed"].includes(value)) return "danger";
  return "neutral";
}
