import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Target,
  Workflow,
  FileCheck,
  Terminal,
  Boxes,
  Share2,
  Network,
  Brain,
  Database,
  ShieldCheck,
  Cpu,
  Activity,
  Settings,
} from "./ui/icons";
import type { TranslationMessages } from "../types";

type SidebarProps = {
  t: TranslationMessages;
  relaunchOnboarding?: () => void;
  onOpenCommandPalette?: () => void;
  onToggleCompanion?: () => void;
};

type NavItem = {
  label: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
};

type NavSection = {
  label: string;
  items: NavItem[];
  mobileHidden?: boolean;
};

export function Sidebar({ t, relaunchOnboarding, onOpenCommandPalette, onToggleCompanion }: SidebarProps) {
  const location = useLocation();

  const sections: NavSection[] = [
    {
      label: "任務指揮",
      items: [
        { label: "控制總覽", to: "/workspace", icon: LayoutDashboard },
        { label: "任務清單", to: "/missions", icon: Target },
        { label: "任務圖譜", to: "/tasks", icon: Workflow },
        { label: "審核驗收", to: "/review", icon: FileCheck },
      ],
    },
    {
      label: "自主編程",
      items: [
        { label: "編程流水線", to: "/pipeline", icon: Terminal },
        { label: "軟體工廠", to: "/factory", icon: Boxes },
        { label: "分散式網格", to: "/mesh", icon: Share2 },
      ],
    },
    {
      label: "架構記憶",
      items: [
        { label: "架構拓撲", to: "/topology", icon: Network },
        { label: "情境記憶", to: "/memory", icon: Brain },
        { label: "專案知識庫", to: "/knowledge", icon: Database },
      ],
    },
    {
      label: "系統治理",
      items: [
        { label: "規範守則", to: "/rules", icon: ShieldCheck },
        { label: "技能模組", to: "/mods", icon: Cpu },
        { label: "系統診斷", to: "/system", icon: Activity },
        { label: "偏好設定", to: "/settings", icon: Settings },
      ],
    },
  ];

  return (
    <aside
      className="relative z-50 flex w-full flex-col border-b p-4 md:fixed md:left-0 md:top-0 md:h-screen md:w-64 md:border-r md:border-b-0 md:p-5 overflow-y-auto"
      style={{ background: "var(--sidebar)", borderColor: "var(--border-c)" }}
    >
      {/* Brand Header */}
      <div className="mb-4 px-1 md:mt-1 md:mb-6">
        <div className="mb-4 flex items-center gap-3">
          <div
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg border text-[11px] font-bold tracking-[0.16em] bg-indigo-500/10 border-indigo-500/30 text-indigo-300"
          >
            LAS
          </div>
          <div className="min-w-0">
            <span className="block truncate text-sm font-bold leading-tight" style={{ color: "var(--t1)" }}>
              {t.appTitle || "控制中心"}
            </span>
            <span className="mt-0.5 block text-[10px] font-medium tracking-wider text-slate-400">
              代理人控制中樞
            </span>
          </div>
        </div>

        {onOpenCommandPalette && (
          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="quiet-button flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold"
          >
            <span>命令面板</span>
            <span className="font-mono text-[10px] t3">Ctrl K</span>
          </button>
        )}

        {onToggleCompanion && (
          <button
            type="button"
            onClick={onToggleCompanion}
            className="quiet-button flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold mt-1.5 text-cyan-300 border-cyan-500/20 bg-cyan-500/5 hover:bg-cyan-500/10"
          >
            <span>隨行助手</span>
            <span className="font-mono text-[10px] text-cyan-400">HITL</span>
          </button>
        )}
      </div>

      {/* Navigation Sections */}
      <nav className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:block md:flex-1 md:space-y-4" aria-label="主要導覽">
        {sections.map((section) => (
          <div key={section.label} className={section.mobileHidden ? "hidden md:block" : undefined}>
            <p className="mb-1.5 px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              {section.label}
            </p>
            <div className="space-y-0.5">
              {section.items.map(({ label, to, icon: Icon }) => {
                const active =
                  location.pathname === to ||
                  (to !== "/" &&
                    location.pathname.startsWith(`${to}/`));

                return (
                  <Link
                    key={to}
                    to={to}
                    aria-current={active ? "page" : undefined}
                    className={`nav-link ${
                      active ? "nav-link-active" : ""
                    } group flex min-w-0 items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors`}
                  >
                    <Icon className={`h-4 w-4 shrink-0 ${active ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200"}`} />
                    <span className="min-w-0 truncate leading-normal">{label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer Meta */}
      <div className="hidden space-y-2.5 border-t pt-4 md:block" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
        {relaunchOnboarding && (
          <button
            type="button"
            onClick={relaunchOnboarding}
            className="w-full rounded-lg border border-dashed py-1.5 text-center text-xs font-medium transition-colors hover:bg-white/5 active:translate-y-px"
            style={{ borderColor: "rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.7)" }}
          >
            {t.relaunchTutorialBtn || "重新開啟新手教學"}
          </button>
        )}
        <div className="flex items-center justify-between text-[10px] font-medium tracking-wide text-slate-500">
          <span>協定基準線</span>
          <span className="font-mono text-indigo-400/80">PAP v3.8.0</span>
        </div>
      </div>
    </aside>
  );
}

