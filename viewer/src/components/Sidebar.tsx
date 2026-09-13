import { Link, useLocation } from "react-router-dom";
import type { TranslationMessages } from "../types";
import { cx } from "./ui/primitives";
import {
  LayoutDashboard,
  GitFork,
  Network,
  Compass,
  Brain,
  ShieldCheck,
  Cpu,
  Settings,
  Terminal,
  Search,
  HelpCircle,
  Workflow,
} from "./ui/icons";

type SidebarProps = {
  t: TranslationMessages;
  relaunchOnboarding?: () => void;
  onOpenCommandPalette?: () => void;
};

export function Sidebar({ t, relaunchOnboarding, onOpenCommandPalette }: SidebarProps) {
  const location = useLocation();
  const items = [
    { label: t.appTitle, to: "/", icon: LayoutDashboard },
    { label: t.taskFlow, to: "/tasks", icon: GitFork },
    { label: "Coding Pipeline", to: "/pipeline", icon: Workflow },
    { label: "Topology", to: "/topology", icon: Network },
    { label: "Intelligence", to: "/intelligence", icon: Compass },
    { label: t.memoryTitle, to: "/memory", icon: Brain },
    { label: t.rules, to: "/rules", icon: ShieldCheck },
    { label: t.mods, to: "/mods", icon: Cpu },
    { label: t.settings, to: "/settings", icon: Settings },
    { label: t.adminConsole, to: "/admin", icon: Terminal },
  ];

  return (
    <aside
      className="acrylic-surface relative z-50 flex w-full flex-col p-3 md:fixed md:left-0 md:top-0 md:h-screen md:w-64 md:border-r md:border-b-0 md:p-4 shadow-[4px_0_24px_rgba(0,0,0,0.4)]"
      style={{ background: "var(--sidebar)", borderColor: "var(--border-c)" }}
    >
      <div className="mb-3 px-1 md:mt-0.5 md:mb-4">
        <div className="mb-3 flex items-center justify-between gap-2.5">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 via-blue-600 to-cyan-500 text-[11px] font-bold text-white shadow-[0_0_12px_rgba(99,102,241,0.4)]">
              FA
            </div>
            <div className="min-w-0">
              <span className="block truncate text-xs font-semibold leading-tight t1 tracking-tight">
                FindAi Studio
              </span>
              <span className="block truncate text-[10px] font-mono leading-tight text-slate-400">
                Agent System
              </span>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Ready
          </span>
        </div>

        {onOpenCommandPalette && (
          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="group flex h-8 w-full items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] px-2.5 text-xs text-slate-400 transition-colors hover:border-indigo-500/40 hover:text-slate-100 hover:bg-white/[0.06] hover:shadow-[0_0_12px_rgba(99,102,241,0.15)] cursor-pointer"
          >
            <div className="flex items-center gap-2 min-w-0">
              <Search className="h-3.5 w-3.5 shrink-0 text-slate-400 group-hover:text-indigo-400 transition-colors" />
              <span className="truncate">Search...</span>
            </div>
            <kbd className="font-mono text-[9px] px-1.5 py-0.5 rounded border border-white/10 bg-white/5 text-slate-400 leading-none shrink-0 group-hover:border-indigo-500/30">Ctrl K</kbd>
          </button>
        )}
      </div>

      <nav className="grid grid-cols-2 gap-1 sm:grid-cols-4 md:block md:flex-1 md:space-y-1">
        {items.map(({ label, to, icon: Icon }) => {
          const active = location.pathname === to;

          return (
            <Link
              key={to}
              to={to}
              aria-current={active ? "page" : undefined}
              className={cx(
                "group relative flex min-w-0 items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition-colors duration-200",
                active
                  ? "bg-indigo-500/15 text-white border border-indigo-500/30 shadow-[0_0_16px_rgba(99,102,241,0.2)]"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
              )}
            >
              {active && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-gradient-to-b from-indigo-400 to-cyan-400 shadow-[0_0_8px_#6366f1]" />
              )}
              <Icon className={cx("h-4 w-4 shrink-0 transition-colors", active ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200")} />
              <span className="truncate leading-tight">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="hidden border-t border-white/10 pt-3 md:block">
        {relaunchOnboarding && (
          <button
            type="button"
            onClick={relaunchOnboarding}
            className="flex items-center justify-center gap-2 w-full rounded-lg border border-white/10 bg-white/[0.02] py-1.5 text-center text-xs font-medium text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-white hover:border-white/20 cursor-pointer"
          >
            <HelpCircle className="h-3.5 w-3.5 text-slate-400" />
            <span>{t.relaunchTutorialBtn}</span>
          </button>
        )}
        <div className="mt-2.5 flex items-center justify-between px-1 text-[10px] font-mono text-slate-500">
          <span>Engine Status</span>
          <span className="text-emerald-400/80">v1.2.0 • Online</span>
        </div>
      </div>
    </aside>
  );
}
