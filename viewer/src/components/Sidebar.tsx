import { Link, useLocation } from "react-router-dom";
import type { TranslationMessages } from "../types";

type SidebarProps = {
  t: TranslationMessages;
  relaunchOnboarding?: () => void;
};

export function Sidebar({ t, relaunchOnboarding }: SidebarProps) {
  const location = useLocation();
  const items = [
    { label: t.taskFlow, to: "/", kicker: "Flow" },
    { label: t.memoryTitle, to: "/memory", kicker: "Brain" },
    { label: t.rules, to: "/rules", kicker: "Policy" },
    { label: t.mods, to: "/mods", kicker: "Skills" },
    { label: t.settings, to: "/settings", kicker: "Config" },
    { label: t.adminConsole, to: "/admin", kicker: "Ops" },
  ];

  return (
    <aside
      className="relative z-50 flex w-full flex-col border-b p-4 md:fixed md:left-0 md:top-0 md:h-screen md:w-64 md:border-r md:border-b-0 md:p-5"
      style={{ background: "var(--sidebar)", borderColor: "var(--border-c)" }}
    >
      <div className="mb-4 px-1 md:mt-1 md:mb-8">
        <div className="mb-4 flex items-center gap-3">
          <div
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg border text-[11px] font-semibold tracking-[0.16em]"
            style={{ borderColor: "rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.055)", color: "white" }}
          >
            LAS
          </div>
          <div className="min-w-0">
            <span className="block truncate text-sm font-semibold leading-tight" style={{ color: "var(--t1)" }}>
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
      </div>

      <nav className="grid grid-cols-2 gap-1.5 sm:grid-cols-5 md:block md:flex-1 md:space-y-1.5">
        {items.map(({ label, to, kicker }) => {
          const active = location.pathname === to;

          return (
            <Link
              key={to}
              to={to}
              aria-current={active ? "page" : undefined}
              className={`nav-link ${active ? "nav-link-active" : ""} group flex min-w-0 items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-sm font-medium`}
            >
              <span className="min-w-0 truncate">{label}</span>
              <span className="shrink-0 text-right text-[9px] font-semibold uppercase tracking-[0.14em] opacity-45 group-hover:opacity-70">
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
            className="w-full rounded-lg border border-dashed py-2 text-center text-xs font-semibold transition-all hover:bg-white/5 active:translate-y-px"
            style={{ borderColor: "rgba(255,255,255,0.14)", color: "rgba(255,255,255,0.72)" }}
          >
            {t.relaunchTutorialBtn}
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
