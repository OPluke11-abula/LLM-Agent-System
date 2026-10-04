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
      className="relative z-50 flex w-full flex-col border-b p-3 sm:p-4 md:fixed md:left-0 md:top-0 md:h-screen md:w-60 md:border-r md:border-b-0 md:p-4 overflow-y-auto"
      style={{ background: "var(--sidebar)", borderColor: "var(--border-c)" }}
    >
      {/* Brand Header */}
      <div className="mb-4 px-1 md:mt-1 md:mb-5">
        <div className="mb-3.5 flex items-center gap-2.5">
          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-[var(--t1)] text-[var(--bg-base)] font-mono text-xs font-bold tracking-tight shadow-xs">
            L
          </div>
          <div className="min-w-0">
            <span className="block truncate text-xs font-semibold leading-tight text-[var(--t1)]">
              {t.appTitle || "LAS 控制中樞"}
            </span>
            <span className="mt-0.5 block text-[10px] font-mono text-[var(--t3)]">
              v3.8.0 協定核心
            </span>
          </div>
        </div>

        {onOpenCommandPalette && (
          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="group flex w-full items-center justify-between rounded-md border border-[var(--border-c)] bg-[var(--bg-card)] px-2.5 py-1.5 text-xs text-[var(--t2)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--t1)]"
          >
            <span className="font-medium text-[11px]">命令面板</span>
            <kbd className="rounded border border-[var(--border-c)] bg-[var(--bg-muted)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--t3)] group-hover:text-[var(--t2)]">
              Ctrl K
            </kbd>
          </button>
        )}

        {onToggleCompanion && (
          <button
            type="button"
            onClick={onToggleCompanion}
            className="mt-1.5 flex w-full items-center justify-between rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-2.5 py-1.5 text-xs text-[var(--t2)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--t1)]"
          >
            <span className="font-medium text-[11px] flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
              隨行助手
            </span>
            <span className="font-mono text-[10px] text-[var(--t3)]">HITL</span>
          </button>
        )}
      </div>

      {/* Navigation Sections */}
      <nav className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:block md:flex-1 md:space-y-4" aria-label="主要導覽">
        {sections.map((section) => (
          <div key={section.label} className={section.mobileHidden ? "hidden md:block" : undefined}>
            <p className="mb-1 px-2 text-[11px] font-medium tracking-tight text-[var(--t3)]">
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
                    className={`group flex min-w-0 items-center gap-2 rounded-md px-2.5 py-1.5 text-xs transition-colors ${
                      active
                        ? "bg-[var(--bg-elevated)] font-medium text-[var(--t1)] border border-[var(--border-strong)] shadow-xs"
                        : "text-[var(--t2)] hover:bg-[var(--bg-muted)] hover:text-[var(--t1)] border border-transparent"
                    }`}
                  >
                    <Icon className={`h-3.5 w-3.5 shrink-0 ${active ? "text-[var(--accent)]" : "text-[var(--t3)] group-hover:text-[var(--t2)]"}`} />
                    <span className="min-w-0 truncate leading-normal">{label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer Meta */}
      <div className="hidden space-y-2 border-t pt-3 md:block" style={{ borderColor: "var(--border-c)" }}>
        {relaunchOnboarding && (
          <button
            type="button"
            onClick={relaunchOnboarding}
            className="w-full rounded-md border border-dashed border-[var(--border-c)] py-1 text-center text-[11px] text-[var(--t3)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--t2)]"
          >
            {t.relaunchTutorialBtn || "新手引導"}
          </button>
        )}
        <div className="flex items-center justify-between text-[10px] font-mono text-[var(--t3)]">
          <span>協定基準</span>
          <span className="text-[var(--t2)]">PAP v3.8.0</span>
        </div>
      </div>
    </aside>
  );
}

