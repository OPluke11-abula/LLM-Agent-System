import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export type Tone = "neutral" | "accent" | "success" | "warning" | "danger";

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

/* =========================================================================
   Surfaces & Containers
   ========================================================================= */

type SurfaceProps = HTMLAttributes<HTMLDivElement> & {
  as?: "div" | "section" | "aside";
  elevated?: boolean;
};

export function Surface({ as = "div", elevated = false, className, ...props }: SurfaceProps) {
  const Component = as;
  return (
    <Component
      className={cx(elevated ? "control-surface" : "card-bg", className)}
      {...props}
    />
  );
}

/* =========================================================================
   Buttons
   ========================================================================= */

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "quiet" | "primary" | "danger" | "warning" | "outline" | "ghost";
  size?: "sm" | "md" | "lg" | "icon";
};

const BUTTON_SIZE_CLASSES = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-3 py-1.5 text-xs",
  lg: "px-4 py-2 text-sm",
  icon: "h-8 w-8 p-0 flex items-center justify-center",
} as const;

export function Button({ variant = "quiet", size = "md", className, ...props }: ButtonProps) {
  return (
    <button
      className={cx(
        "rounded-lg font-semibold transition-colors disabled:opacity-50 inline-flex items-center justify-center gap-1.5 cursor-pointer active:translate-y-px",
        BUTTON_SIZE_CLASSES[size],
        variant === "primary" && "primary-button",
        variant === "quiet" && "quiet-button",
        variant === "danger" && "danger-button",
        variant === "warning" && "warning-button",
        variant === "outline" && "border border-[var(--border-c)] hover:bg-white/5 t1",
        variant === "ghost" && "hover:bg-white/5 t2 hover:text-[var(--t1)]",
        className
      )}
      {...props}
    />
  );
}

/* =========================================================================
   Status Badges & Metrics
   ========================================================================= */

type StatusBadgeProps = {
  children: ReactNode;
  tone?: Tone;
  className?: string;
};

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
      <span className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: toneVar[tone] }} />
      {children}
    </span>
  );
}

type MetricTileProps = {
  label: ReactNode;
  value: ReactNode;
  tone?: Tone;
  className?: string;
};

export function MetricTile({ label, value, tone, className }: MetricTileProps) {
  return (
    <div className={cx("card-bg rounded-xl border p-4", className)} style={{ borderColor: "var(--border-c)" }}>
      <div className="text-[10px] font-semibold uppercase tracking-[0.14em] t3">{label}</div>
      <div className="mt-1 text-xl font-bold tracking-tight" style={{ color: tone ? toneVar[tone] : "var(--t1)" }}>
        {value}
      </div>
    </div>
  );
}

type ProgressBarProps = {
  value: number;
  tone?: Tone;
  className?: string;
  ariaLabel?: string;
};

export function ProgressBar({ value, tone = "accent", className, ariaLabel = "Progress" }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div
      role="progressbar"
      aria-label={ariaLabel}
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cx("h-1.5 w-full overflow-hidden rounded-full bg-[var(--bg-muted)]", className)}
    >
      <div
        className="h-full transition-[width] duration-300 rounded-full"
        style={{ width: `${clamped}%`, background: toneVar[tone] }}
      />
    </div>
  );
}

/* =========================================================================
   Card Components (shadcn-compatible)
   ========================================================================= */

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx("rounded-xl border card-bg shadow-sm transition-all", className)}
      style={{ borderColor: "var(--border-c)" }}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx("flex flex-col space-y-1.5 p-5", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cx("text-base font-semibold leading-none tracking-tight t1", className)} {...props} />;
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cx("text-xs t3 mt-1", className)} {...props} />;
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx("p-5 pt-0", className)} {...props} />;
}

export function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx("flex items-center p-5 pt-0", className)} {...props} />;
}

/* =========================================================================
   Form Controls: Input & Switch
   ========================================================================= */

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cx(
        "flex h-9 w-full rounded-lg border bg-[var(--bg-card)] px-3 py-1.5 text-xs t1 shadow-sm transition-colors",
        "placeholder:text-[var(--t3)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      style={{ borderColor: "var(--border-c)" }}
      {...props}
    />
  );
}

export function Switch({
  checked,
  onCheckedChange,
  disabled,
  className,
  id,
}: {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  id?: string;
}) {
  return (
    <SwitchPrimitive.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      className={cx(
        "peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "bg-[var(--accent)]" : "bg-[var(--bg-muted)] border-[var(--border-c)]",
        className
      )}
    >
      <SwitchPrimitive.Thumb
        className={cx(
          "pointer-events-none block h-4 w-4 rounded-full bg-white shadow-md ring-0 transition-transform",
          checked ? "translate-x-4" : "translate-x-0"
        )}
      />
    </SwitchPrimitive.Root>
  );
}

/* =========================================================================
   Radix Tabs
   ========================================================================= */

export const Tabs = TabsPrimitive.Root;

export function TabsList({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cx(
        "inline-flex h-9 items-center justify-center rounded-lg p-1 text-[var(--t2)] border",
        className
      )}
      style={{ background: "var(--bg-muted)", borderColor: "var(--border-c)" }}
      {...props}
    />
  );
}

export function TabsTrigger({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cx(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-xs font-semibold transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:pointer-events-none disabled:opacity-50",
        "data-[state=active]:bg-[var(--bg-elevated)] data-[state=active]:text-[var(--t1)] data-[state=active]:shadow-sm cursor-pointer",
        className
      )}
      {...props}
    />
  );
}

export const TabsContent = TabsPrimitive.Content;

/* =========================================================================
   Radix Tooltip
   ========================================================================= */

export const TooltipProvider = TooltipPrimitive.Provider;
export const Tooltip = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export function TooltipContent({
  className,
  sideOffset = 4,
  ...props
}: React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Content
      sideOffset={sideOffset}
      className={cx(
        "z-50 overflow-hidden rounded-md border px-2.5 py-1 text-[11px] font-medium shadow-md backdrop-blur-md",
        className
      )}
      style={{
        background: "var(--bg-elevated)",
        borderColor: "var(--border-c)",
        color: "var(--t1)",
      }}
      {...props}
    />
  );
}

/* =========================================================================
   Radix Dialog (Accessible Modal)
   ========================================================================= */

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogPortal = DialogPrimitive.Portal;
export const DialogClose = DialogPrimitive.Close;

export function DialogOverlay({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Overlay
      className={cx("fixed inset-0 z-50 bg-black/65 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0", className)}
      {...props}
    />
  );
}

export function DialogContent({
  className,
  children,
  ...props
}: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>) {
  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Content
        className={cx(
          "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 p-6 shadow-2xl rounded-2xl border",
          "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          className
        )}
        style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)" }}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPortal>
  );
}

export function DialogHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx("flex flex-col space-y-1.5 text-left", className)} {...props} />;
}

export function DialogFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 gap-2 mt-4", className)} {...props} />;
}

export const DialogTitle = DialogPrimitive.Title;
export const DialogDescription = DialogPrimitive.Description;

/* =========================================================================
   Radix Dropdown Menu
   ========================================================================= */

export const DropdownMenu = DropdownMenuPrimitive.Root;
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
export const DropdownMenuGroup = DropdownMenuPrimitive.Group;
export const DropdownMenuPortal = DropdownMenuPrimitive.Portal;
export const DropdownMenuSub = DropdownMenuPrimitive.Sub;
export const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup;

export function DropdownMenuContent({
  className,
  sideOffset = 4,
  ...props
}: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Content>) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        sideOffset={sideOffset}
        className={cx(
          "z-50 min-w-[8rem] overflow-hidden rounded-xl border p-1 shadow-lg backdrop-blur-md",
          className
        )}
        style={{ background: "var(--bg-panel)", borderColor: "var(--border-c)", color: "var(--t1)" }}
        {...props}
      />
    </DropdownMenuPrimitive.Portal>
  );
}

export function DropdownMenuItem({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item>) {
  return (
    <DropdownMenuPrimitive.Item
      className={cx(
        "relative flex cursor-pointer select-none items-center rounded-lg px-2.5 py-1.5 text-xs font-medium outline-none transition-colors",
        "focus:bg-[var(--accent-bg)] focus:text-[var(--accent)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className
      )}
      {...props}
    />
  );
}

export function DropdownMenuSeparator({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Separator>) {
  return (
    <DropdownMenuPrimitive.Separator
      className={cx("-mx-1 my-1 h-px bg-[var(--border-c)]", className)}
      {...props}
    />
  );
}
