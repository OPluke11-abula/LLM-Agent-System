import { Link, useLocation } from "react-router-dom";
import type { TranslationMessages } from "../types";

type SidebarProps = {
  t: TranslationMessages;
};

export function Sidebar({ t }: SidebarProps) {
  const location = useLocation();
  const items = [
    { label: t.taskFlow, to: "/" },
    { label: t.rules, to: "/rules" },
    { label: t.mods, to: "/mods" },
    { label: t.settings, to: "/settings" },
  ];

  return (
    <aside
      className="fixed left-0 top-0 z-50 flex h-screen w-56 flex-col border-r p-5"
      style={{ background: "var(--sidebar)", borderColor: "var(--border-c)" }}
    >
      <div className="mt-1 mb-8 flex items-center gap-3 px-1">
        <div
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg"
          style={{ background: "var(--accent)", boxShadow: "0 4px 16px var(--accent-bg)" }}
        >
          <div
            className="h-2.5 w-2.5 rounded-full bg-white/90"
            style={{ boxShadow: "0 0 8px rgba(255,255,255,0.9)" }}
          />
        </div>
        <span className="text-sm font-extrabold leading-tight tracking-wide" style={{ color: "var(--t1)" }}>
          {t.appTitle}
        </span>
      </div>
      <nav className="flex-1 space-y-1">
        {items.map(({ label, to }) => {
          const active = location.pathname === to;

          return (
            <Link
              key={to}
              to={to}
              className="flex items-center rounded-xl px-4 py-2.5 text-sm font-bold transition-all duration-200"
              style={
                active
                  ? {
                      background: "var(--accent-bg)",
                      color: "var(--accent)",
                      border: "1px solid var(--accent)",
                      marginLeft: "4px",
                    }
                  : { color: "var(--t3)", border: "1px solid transparent" }
              }
            >
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t pt-4" style={{ borderColor: "var(--border-c)" }}>
        <p className="text-[9px] font-semibold uppercase tracking-wider leading-relaxed t3">
          AI Agent Topology Viewer
          <br />
          Tauri 2.0 · TS 5.8 · ReactFlow 11
        </p>
      </div>
    </aside>
  );
}
