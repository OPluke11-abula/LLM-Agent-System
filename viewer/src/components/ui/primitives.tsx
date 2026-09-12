import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";

type Tone = "neutral" | "accent" | "success" | "warning" | "danger";

type SurfaceProps = HTMLAttributes<HTMLDivElement> & {
  as?: "div" | "section" | "aside";
  elevated?: boolean;
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "quiet" | "primary" | "danger" | "warning";
};

type StatusBadgeProps = {
  children: ReactNode;
  tone?: Tone;
  className?: string;
};

type MetricTileProps = {
  label: ReactNode;
  value: ReactNode;
  tone?: Tone;
  className?: string;
};

type ProgressBarProps = {
  value: number;
  tone?: Tone;
  className?: string;
  ariaLabel?: string;
};

export function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

const toneVar: Record<Tone, string> = {
  neutral: "var(--t3)",
  accent: "var(--accent)",
  success: "var(--success)",
  warning: "var(--warning)",
  danger: "var(--danger)",
};

const toneBgVar: Record<Tone, string> = {
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

export function Surface({ as = "div", elevated = false, className, ...props }: SurfaceProps) {
  const Component = as;
  return (
    <Component
      className={cx(elevated ? "control-surface" : "card-bg", className)}
      {...props}
    />
  );
}

export function Button({ variant = "quiet", className, ...props }: ButtonProps) {
  return (
    <button
      className={cx(
        "rounded-lg px-3 py-1.5 text-xs font-semibold transition-all disabled:opacity-50",
        variant === "primary" && "primary-button",
        variant === "quiet" && "quiet-button",
        variant === "danger" && "danger-button",
        variant === "warning" && "warning-button",
        className,
      )}
      {...props}
    />
  );
}

export function LinkButton({ to, variant = "quiet", children, className }: { to: string; variant?: ButtonProps["variant"]; children: ReactNode; className?: string }) {
  return <Link to={to} className={cx("rounded-lg px-3 py-1.5 text-xs font-semibold transition-all", variant === "primary" && "primary-button", variant === "quiet" && "quiet-button", variant === "danger" && "danger-button", variant === "warning" && "warning-button", className)}>{children}</Link>;
}

export function StatusBadge({ children, tone = "neutral", className }: StatusBadgeProps) {
  return (
    <span
      className={cx("inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.1em]", className)}
      style={{
        color: toneVar[tone],
        borderColor: `color-mix(in srgb, ${toneVar[tone]} 34%, transparent)`,
        background: toneBgVar[tone],
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: toneVar[tone] }} />
      {children}
    </span>
  );
}

export function MetricTile({ label, value, tone = "neutral", className }: MetricTileProps) {
  return (
    <div className={cx("metric-card p-2", className)}>
      <p className="text-lg font-semibold" style={{ color: tone === "neutral" ? "var(--t1)" : toneVar[tone] }}>{value}</p>
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] t3">{label}</p>
    </div>
  );
}

export function ProgressBar({ value, tone = "accent", className, ariaLabel = "Progress" }: ProgressBarProps) {
  const width = Math.max(0, Math.min(100, value));
  return (
    <div
      className={cx("progress-track", className)}
      role="progressbar"
      aria-label={ariaLabel}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={width}
    >
      <div
        className="progress-fill"
        style={{
          width: `${width}%`,
          background: toneVar[tone],
        }}
      />
    </div>
  );
}

export function Tooltip({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("surface-tooltip", className)}>
      {children}
    </div>
  );
}
