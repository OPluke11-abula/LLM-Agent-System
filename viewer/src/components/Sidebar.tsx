import { Link, useLocation } from "react-router-dom";
import type { TranslationMessages } from "../types";
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
  HelpCircle
} from "./ui/icons";

type SidebarProps = {
  t: TranslationMessages;
  relaunchOnboarding?: () => void;
  onOpenCommandPalette?: () => void;
};

export function Sidebar({ t, relaunchOnboarding, onOpenCommandPalette }: SidebarProps) {
  const location = useLocation();
  const items = [
    { label: t.appTitle, to: "/", kicker: "Live", icon: LayoutDashboard },
    { label: t.taskFlow, to: "/tasks", kicker: "Flow", icon: GitFork },
    { label: "Topology", to: "/topology", kicker: "Graph", icon: Network },
    { label: "Intelligence", to: "/intelligence", kicker: "Map", icon: Compass },
    { label: t.memoryTitle, to: "/memory", kicker: "Brain", icon: Brain },
    { label: t.rules, to: "/rules", kicker: "Policy", icon: ShieldCheck },
    { label: t.mods, to: "/mods", kicker: "Skills", icon: Cpu },
    { label: t.settings, to: "/settings", kicker: "Config", icon: Settings },
    { label: t.adminConsole, to: "/admin", kicker: "Ops", icon: Terminal },
  ];

  return (
    <aside
      className="relative z-50 flex w-full flex-col border-b p-4 md:fixed md:left-0 md:top-0 md:h-screen md:w-64 md:border-r md:border-b-0 md:p-5"
      style={{ background: "var(--sidebar)", borderColor: "var(--border-c)" }}
    >
      <div className="mb-4 px-1 md:mt-1 md:mb-6">
        <div className="mb-4 flex items-center gap-3">
          <div
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl border text-[11px] font-bold tracking-[0.16em] shadow-sm"
            style={{ borderColor: "rgba(255,255,255,0.14)", background: "rgba(255,255,255,0.06)", color: "white" }}
          >
            LAS
          </div>
          <div className="min-w-0">
            <span className="block truncate text-sm font-semibold leading-tight t1">
              {t.appTitle}
            </span>
            <span
              className="mt-1 block text-[10px] font-medium uppercase tracking-[0.18em]"
              style={{ color: "rgba(255,255,255,0.42)" }}
            >
              Agent Runtime
            </span>
          </div>
        </div>
        {onOpenCommandPalette && (
          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="quiet-button flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold group cursor-pointer transition-colors hover:bg-white/5"
          >
            <div className="flex items-center gap-2">
              <Search className="h-3.5 w-3.5 t3 group-hover:text-[var(--accent)] transition-colors" />
              <span className="t2 group-hover:text-[var(--t1)] transition-colors">Command Palette</span>
            </div>
            <kbd className="font-mono text-[9px] px-1.5 py-0.5 rounded border border-[var(--border-c)] bg-[var(--bg-muted)] t3">Ctrl K</kbd>
          </button>
        )}
      </div>

      <nav className="grid grid-cols-2 gap-1 sm:grid-cols-4 md:block md:flex-1 md:space-y-1">
        {items.map(({ label, to, kicker, icon: Icon }) => {
          const active = location.pathname === to;

          return (
            <Link
              key={to}
              to={to}
              aria-current={active ? "page" : undefined}
              className={`nav-link ${active ? "nav-link-active font-semibold" : "font-medium"} group flex min-w-0 items-center justify-between gap-2.5 rounded-lg px-3 py-2 text-xs transition-all`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Icon className={`h-4 w-4 shrink-0 transition-transform group-hover:scale-110 ${active ? "text-[var(--accent)]" : "t3 group-hover:text-[var(--t1)]"}`} />
                <span className="truncate leading-tight">{label}</span>
              </div>
              <span className="shrink-0 text-right text-[9px] font-semibold uppercase tracking-[0.14em] opacity-40 group-hover:opacity-75">
                {kicker}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="hidden space-y-3 border-t pt-4 md:block" style={{ borderColor: "rgba(255,255,255,0.09)" }}>
        {relaunchOnboarding && (
          <button
            type="button"
            onClick={relaunchOnboarding}
            className="flex items-center justify-center gap-2 w-full rounded-lg border border-dashed py-2 text-center text-xs font-semibold transition-colors hover:bg-white/5 cursor-pointer active:translate-y-px"
            style={{ borderColor: "rgba(255,255,255,0.14)", color: "rgba(255,255,255,0.72)" }}
          >
            <HelpCircle className="h-3.5 w-3.5" />
            <span>{t.relaunchTutorialBtn}</span>
          </button>
        )}
        <p
          className="text-[9px] font-medium uppercase leading-relaxed tracking-[0.16em]"
          style={{ color: "rgba(255,255,255,0.36)" }}
        >
          Visual Control Plane
          <br />
          Tauri 2.0 / TS 5.8 / ReactFlow 11
        </p>
      </div>
    </aside>
  );
}
