import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";

import { type Tone, cx, toneVar, toneBgVar } from "./utils";
export type { Tone };

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
        "rounded-md font-medium transition-all disabled:opacity-50 inline-flex items-center justify-center gap-1.5 cursor-pointer active:scale-[0.98]",
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

export function LinkButton({ to, variant = "quiet", children, className }: { to: string; variant?: ButtonProps["variant"]; children: ReactNode; className?: string }) {
  return <Link to={to} className={cx("rounded-lg px-3 py-1.5 text-xs font-semibold transition-all", variant === "primary" && "primary-button", variant === "quiet" && "quiet-button", variant === "danger" && "danger-button", variant === "warning" && "warning-button", className)}>{children}</Link>;
}

/* =========================================================================
   Status Badges & Metrics
   ========================================================================= */

type StatusBadgeProps = {
  children: ReactNode;
  tone?: Tone;
  className?: string;
  pulse?: boolean;
};

export function StatusBadge({ children, tone = "neutral", className, pulse = false }: StatusBadgeProps) {
  return (
    <span
      className={cx("inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-none", className)}
      style={{
        color: toneVar[tone],
        borderColor: `color-mix(in srgb, ${toneVar[tone]} 28%, transparent)`,
        background: toneBgVar[tone],
      }}
    >
      <span
        className={cx("h-1.5 w-1.5 rounded-full shrink-0", pulse && "animate-pulse")}
        style={{ background: toneVar[tone] }}
      />
      <span>{children}</span>
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
    <div className={cx("card-bg rounded-lg border p-3.5", className)} style={{ borderColor: "var(--border-c)" }}>
      <div className="text-xs font-medium text-[var(--t2)]">{label}</div>
      <div className="mt-1 font-mono text-2xl font-semibold tracking-tight" style={{ color: tone ? toneVar[tone] : "var(--t1)" }}>
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

/* =========================================================================
   Modern 4-Star+ Dynamic UI Primitives (Aceternity, Magic UI, OriginKit)
   ========================================================================= */

/**
 * Magic UI - BorderBeam: Infinite rotating gradient beam around container
 */
export function BorderBeam({
  className,
  colorFrom = "rgba(99, 102, 241, 0.9)",
  colorTo = "rgba(6, 182, 212, 0.9)",
  duration = "8s",
}: {
  className?: string;
  colorFrom?: string;
  colorTo?: string;
  duration?: string;
}) {
  return (
    <div className={cx("pointer-events-none absolute -inset-[1px] rounded-[inherit] overflow-hidden", className)}>
      <div
        className="absolute -inset-[100%] origin-center opacity-70"
        style={{
          background: `conic-gradient(from 0deg, transparent 0 330deg, ${colorFrom} 345deg, ${colorTo} 360deg)`,
          animation: `borderBeamRotate ${duration} linear infinite`,
        }}
      />
    </div>
  );
}

/**
 * Magic UI - ShimmerButton: High-impact primary action button with metallic gleam
 */
export function ShimmerButton({
  children,
  className,
  shimmerColor = "rgba(255, 255, 255, 0.28)",
  ...props
}: ButtonProps & { shimmerColor?: string }) {
  return (
    <button
      className={cx(
        "group relative overflow-hidden rounded-lg px-3.5 py-1.5 text-xs font-semibold text-white",
        "bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-600 bg-[length:200%_100%]",
        "shadow-[0_0_20px_rgba(99,102,241,0.35)] transition-all duration-300 hover:shadow-[0_0_28px_rgba(99,102,241,0.55)] hover:scale-[1.01] active:scale-[0.98] cursor-pointer",
        className
      )}
      {...props}
    >
      <span className="relative z-10 flex items-center justify-center gap-1.5">{children}</span>
      <span
        className="absolute inset-0 -translate-x-full group-hover:animate-[shimmerSlide_1.5s_ease-in-out_infinite]"
        style={{
          background: `linear-gradient(90deg, transparent, ${shimmerColor}, transparent)`,
        }}
      />
    </button>
  );
}

/**
 * OriginKit - MagneticButton: Elastic cursor-tracking interaction
 */
export function MagneticButton({
  children,
  className,
  strength = 0.25,
  ...props
}: HTMLAttributes<HTMLDivElement> & { strength?: number }) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [transform, setTransform] = React.useState("translate(0px, 0px)");

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = (e.clientX - (rect.left + rect.width / 2)) * strength;
    const y = (e.clientY - (rect.top + rect.height / 2)) * strength;
    setTransform(`translate(${x}px, ${y}px)`);
  };

  const handleMouseLeave = () => {
    setTransform("translate(0px, 0px)");
  };

  return (
    <div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      role="presentation"
      className={cx("inline-block transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]", className)}
      style={{ transform }}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * Magic UI - BentoCard: Asymmetric modular card with spotlight & border beam
 */
export function BentoCard({
  children,
  className,
  borderBeam = false,
  spotlight = true,
  ...props
}: HTMLAttributes<HTMLDivElement> & { borderBeam?: boolean; spotlight?: boolean }) {
  return (
    <div
      className={cx(
        "group relative overflow-hidden rounded-xl border border-white/10 bg-[#0d1017]/80 backdrop-blur-xl p-5",
        "transition-all duration-300 hover:border-white/20 hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)]",
        spotlight && "hover:bg-[#121622]/90",
        className
      )}
      {...props}
    >
      {borderBeam && <BorderBeam />}
      <div className="relative z-10 h-full">{children}</div>
    </div>
  );
}

/**
 * OriginKit & Motion-Primitives - TextScramble: Kinetic decrypt text effect
 */
export function TextScramble({
  text,
  className,
  as = "span",
}: {
  text: string;
  className?: string;
  as?: "span" | "h1" | "h2" | "h3" | "p";
}) {
  const [display, setDisplay] = React.useState(text);
  const Component = as;

  React.useEffect(() => {
    const chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/0123456789";
    let iteration = 0;
    const interval = setInterval(() => {
      setDisplay(
        text
          .split("")
          .map((char, idx) => {
            if (char === " ") return " ";
            if (idx < iteration) return text[idx];
            return chars[Math.floor(Math.random() * chars.length)];
          })
          .join("")
      );
      if (iteration >= text.length) {
        clearInterval(interval);
      }
      iteration += 1 / 2;
    }, 28);

    return () => clearInterval(interval);
  }, [text]);

  return <Component className={className}>{display}</Component>;
}

/**
 * Aceternity UI - LampContainer: Cinematic ceiling spotlight container
 */
export function LampContainer({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cx("relative flex flex-col items-center justify-center overflow-hidden w-full isolate z-0", className)}>
      {/* Top Conic Beams */}
      <div className="relative flex w-full flex-1 items-center justify-center isolate z-0 pointer-events-none">
        {/* Left cone */}
        <div
          className="absolute inset-auto right-1/2 h-36 w-[22rem] opacity-60"
          style={{
            background: "conic-gradient(from 70deg at 100% 0%, #6366f1, transparent 55%)",
            filter: "blur(20px)",
          }}
        />
        {/* Right cone */}
        <div
          className="absolute inset-auto left-1/2 h-36 w-[22rem] opacity-60"
          style={{
            background: "conic-gradient(from 290deg at 0% 0%, transparent 45%, #6366f1)",
            filter: "blur(20px)",
          }}
        />
        {/* Center horizontal neon filament */}
        <div className="absolute top-1/2 h-16 w-72 -translate-y-4 rounded-full bg-cyan-400/30 blur-2xl" />
        <div className="absolute top-1/2 h-0.5 w-64 -translate-y-6 bg-cyan-400 shadow-[0_0_20px_#06b6d4]" />
      </div>
      <div className="relative z-10 w-full">{children}</div>
    </div>
  );
}
