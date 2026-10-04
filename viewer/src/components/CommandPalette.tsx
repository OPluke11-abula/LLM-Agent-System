import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, StatusBadge } from "./ui/primitives";
import { Search, Copy, Check, X } from "./ui/icons";
import type { Lang } from "../types";

type CommandPaletteProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  lang: Lang;
};

type CommandTone = "accent" | "success" | "warning" | "danger" | "neutral";

type CommandItem = {
  id: string;
  group: string;
  title: string;
  description: string;
  route: string;
  preview: string;
  tone: CommandTone;
  keywords: string;
};

const COPY: Record<Lang, {
  title: string;
  subtitle: string;
  placeholder: string;
  empty: string;
  preview: string;
  copy: string;
  copied: string;
  close: string;
  shortcut: string;
  commands: CommandItem[];
}> = {
  zh: {
    title: "命令面板",
    subtitle: "搜尋工作區、驗證、交接摘要、PAP 協定同步與核心視圖。",
    placeholder: "輸入 驗證、交接、PAP、記憶、拓撲、流水線...",
    empty: "沒有符合的指令。",
    preview: "指令預覽",
    copy: "複製指令",
    copied: "已複製",
    close: "關閉",
    shortcut: "Ctrl K / Cmd K",
    commands: [
      { id: "mission", group: "導覽視圖", title: "控制總覽", description: "回到即時任務、風險與記憶總覽中樞。", route: "/workspace", preview: "open /workspace", tone: "accent", keywords: "控制 總覽 儀表板 首頁 dashboard home" },
      { id: "mission-list", group: "導覽視圖", title: "任務清單", description: "檢視各階段任務清單與篩選過濾器。", route: "/missions", preview: "open /missions", tone: "accent", keywords: "任務 清單 missions list filter" },
      { id: "tasks", group: "導覽視圖", title: "任務圖譜", description: "檢查任務 DAG 依賴、狀態與交接線索。", route: "/tasks", preview: "open /tasks", tone: "accent", keywords: "任務 圖譜 flow dependency dag" },
      { id: "review", group: "導覽視圖", title: "審核驗收", description: "人機協作審批閘門、變更審查與驗收簽署。", route: "/review", preview: "open /review", tone: "warning", keywords: "審核 驗收 hitl approval review gates" },
      { id: "pipeline", group: "導覽視圖", title: "編程流水線", description: "進入自主編程、工作樹變更與驗證天梯。", route: "/pipeline", preview: "open /pipeline", tone: "accent", keywords: "編程 流水線 pipeline code worktree" },
      { id: "factory", group: "導覽視圖", title: "軟體工廠", description: "進入 Swarm 協同叢集與紅藍對抗審核。", route: "/factory", preview: "open /factory", tone: "accent", keywords: "工廠 factory swarm waves debate" },
      { id: "mesh", group: "導覽視圖", title: "分散式網格", description: "P2P 節點連線狀態、聯邦網格與跨節點同步。", route: "/mesh", preview: "open /mesh", tone: "accent", keywords: "網格 節點 mesh federated p2p sync" },
      { id: "topology", group: "導覽視圖", title: "架構拓撲", description: "查看 runtime agent graph 與編排軌跡。", route: "/topology", preview: "open /topology", tone: "success", keywords: "拓撲 架構 graph inspect agent conductor" },
      { id: "intelligence", group: "導覽視圖", title: "情報地圖", description: "連接任務、代碼圖譜影響、測試與驗證證據。", route: "/intelligence", preview: "open /intelligence", tone: "accent", keywords: "情報 地圖 map impact tests evidence" },
      { id: "memory", group: "導覽視圖", title: "情境記憶", description: "檢視長期記憶庫存、歷史經驗與架構突觸。", route: "/memory", preview: "open /memory", tone: "success", keywords: "記憶 memory evidence brain" },
      { id: "knowledge", group: "導覽視圖", title: "專案知識庫", description: "三層式認知接力知識庫、文檔與參考規格。", route: "/knowledge", preview: "open /knowledge", tone: "success", keywords: "知識庫 knowledge wiki relay cognitive" },
      { id: "rules", group: "導覽視圖", title: "規範守則", description: "檢視 AI 指令原則、行為規範與政策。", route: "/rules", preview: "open /rules", tone: "warning", keywords: "規則 守則 policy rules governance" },
      { id: "mods", group: "導覽視圖", title: "技能模組", description: "外掛擴充、MCP 伺服器整合與動態載入模組。", route: "/mods", preview: "open /mods", tone: "accent", keywords: "模組 技能 mods plugins mcp extensions" },
      { id: "system", group: "導覽視圖", title: "系統診斷", description: "系統健康檢查、周邊設備感知與連線診斷。", route: "/system", preview: "open /system", tone: "warning", keywords: "系統 診斷 system check health diagnostics" },
      { id: "settings", group: "導覽視圖", title: "偏好設定", description: "外觀主題、語言切換與本機設定調整。", route: "/settings", preview: "open /settings", tone: "neutral", keywords: "設定 偏好 settings preferences theme" },
      { id: "verify", group: "系統操作", title: "完整驗證工作區", description: "開啟任務流並預覽完整驗證命令。", route: "/tasks", preview: ".\\scripts\\verify.cmd", tone: "success", keywords: "驗證 verify tests build scripts" },
      { id: "latest-failure", group: "系統操作", title: "檢視 UI 驗證", description: "前往任務流並預覽 UI 截圖驗證命令。", route: "/tasks", preview: "npm.cmd --prefix viewer run verify:ui:screenshots", tone: "warning", keywords: "截圖 ui visual qa" },
      { id: "impacted-symbols", group: "系統操作", title: "追蹤變更影響符號", description: "前往情報地圖，追蹤代碼圖譜衝擊分析。", route: "/intelligence", preview: "python -m agent_workspace.skills.tool_codebase_memory code_detect_change_impact", tone: "accent", keywords: "符號 影響 impact symbols code graph" },
      { id: "sync-pap", group: "系統操作", title: "同步 PAP 協定契約", description: "驗證工作區結構與 PAP 契約完整性。", route: "/settings", preview: "python agent_workspace/pap_validate.py .", tone: "accent", keywords: "pap 協定 驗證 contract manifest" },
    ],
  },
  en: {
    title: "Command Palette",
    subtitle: "Search workspace, verification, handoff, PAP sync, and core views.",
    placeholder: "Type verify, handoff, PAP, memory, topology...",
    empty: "No matching commands.",
    preview: "Command preview",
    copy: "Copy command",
    copied: "Copied",
    close: "Close",
    shortcut: "Ctrl K / Cmd K",
    commands: [
      { id: "mission", group: "Navigate", title: "Mission Control", description: "Return to live mission, risk, and memory overview.", route: "/workspace", preview: "open /workspace", tone: "accent", keywords: "mission control live dashboard home" },
      { id: "mission-list", group: "Navigate", title: "Mission List", description: "Inspect mission registry, status filters, and runs.", route: "/missions", preview: "open /missions", tone: "accent", keywords: "missions list registry filter" },
      { id: "tasks", group: "Navigate", title: "Task Flow", description: "Inspect task dependencies, status, and handoff clues.", route: "/tasks", preview: "open /tasks", tone: "accent", keywords: "task flow dependency handoff" },
      { id: "review", group: "Navigate", title: "Review & Signoff", description: "Human-in-the-loop review gate, evidence, and signoff.", route: "/review", preview: "open /review", tone: "warning", keywords: "review signoff hitl approval gate" },
      { id: "pipeline", group: "Navigate", title: "Code Pipeline", description: "Autonomous code generation, worktree mutation, and ladder.", route: "/pipeline", preview: "open /pipeline", tone: "accent", keywords: "pipeline code worktree ladder" },
      { id: "factory", group: "Navigate", title: "Software Factory", description: "Swarm worktree waves and red-blue debate quorum.", route: "/factory", preview: "open /factory", tone: "accent", keywords: "factory swarm waves debate" },
      { id: "mesh", group: "Navigate", title: "Federated Mesh", description: "P2P nodes, network health, and cross-node sync.", route: "/mesh", preview: "open /mesh", tone: "accent", keywords: "mesh federated p2p nodes" },
      { id: "topology", group: "Navigate", title: "Inspect Topology", description: "View runtime agent graph and conductor trace.", route: "/topology", preview: "open /topology", tone: "success", keywords: "topology graph inspect agent conductor" },
      { id: "intelligence", group: "Navigate", title: "Intelligence Map", description: "Connect tasks, code graph impact, tests, and evidence.", route: "/intelligence", preview: "open /intelligence", tone: "accent", keywords: "intelligence map code graph evidence tests decisions" },
      { id: "memory", group: "Navigate", title: "Cognitive Memory", description: "Open long-term memory, evidence, and recent records.", route: "/memory", preview: "open /memory", tone: "success", keywords: "memory evidence structural graph impact" },
      { id: "knowledge", group: "Navigate", title: "Project Knowledge", description: "Three-tier cognitive relay knowledge base and specs.", route: "/knowledge", preview: "open /knowledge", tone: "success", keywords: "knowledge wiki relay docs" },
      { id: "rules", group: "Navigate", title: "Rules & Policies", description: "Review governance rules, invariants, and constraints.", route: "/rules", preview: "open /rules", tone: "warning", keywords: "governance security risk audit rules" },
      { id: "mods", group: "Navigate", title: "Skill Modules", description: "Dynamic modules, plugins, and MCP server extensions.", route: "/mods", preview: "open /mods", tone: "accent", keywords: "mods skills plugins mcp extensions" },
      { id: "system", group: "Navigate", title: "System Diagnostics", description: "Health checks, telemetry, peripheral companion status.", route: "/system", preview: "open /system", tone: "warning", keywords: "system health diagnostics check companion" },
      { id: "settings", group: "Navigate", title: "Preferences", description: "Theme appearance, language, and workspace configs.", route: "/settings", preview: "open /settings", tone: "neutral", keywords: "settings preferences theme appearance" },
      { id: "verify", group: "Operations", title: "Verify workspace", description: "Open Task Flow and preview the full verification command.", route: "/tasks", preview: ".\\scripts\\verify.cmd", tone: "success", keywords: "verify tests build scripts verify cmd" },
      { id: "latest-failure", group: "Operations", title: "Open latest failure", description: "Go to Task Flow and preview the UI screenshot verification command.", route: "/tasks", preview: "npm.cmd --prefix viewer run verify:ui:screenshots", tone: "warning", keywords: "failure screenshot ui visual qa" },
      { id: "impacted-symbols", group: "Operations", title: "Show impacted symbols", description: "Go to Intelligence Map for code graph impact, tests, and evidence.", route: "/intelligence", preview: "python -m agent_workspace.skills.tool_codebase_memory code_detect_change_impact", tone: "accent", keywords: "impact symbols code graph tests evidence intelligence" },
      { id: "sync-pap", group: "Operations", title: "Sync PAP contract", description: "Open Settings and preview the PAP validator.", route: "/settings", preview: "python agent_workspace/pap_validate.py .", tone: "accent", keywords: "pap sync validate contract manifest" },
    ],
  },
  ja: {
    title: "Command Palette",
    subtitle: "workspace、検証、handoff、PAP sync、主要画面を検索します。",
    placeholder: "verify、handoff、PAP、memory、topology...",
    empty: "一致するコマンドはありません。",
    preview: "Command preview",
    copy: "コピー",
    copied: "コピー済み",
    close: "閉じる",
    shortcut: "Ctrl K / Cmd K",
    commands: [],
  },
  fr: {
    title: "Command Palette",
    subtitle: "Recherche workspace, vérification, handoff, sync PAP et vues clés.",
    placeholder: "verify, handoff, PAP, memory, topology...",
    empty: "Aucune commande trouvée.",
    preview: "Command preview",
    copy: "Copier",
    copied: "Copié",
    close: "Fermer",
    shortcut: "Ctrl K / Cmd K",
    commands: [],
  },
};

function commandsForLanguage(lang: Lang) {
  if (COPY[lang].commands.length > 0) return COPY[lang].commands;
  return COPY.en.commands;
}

export function CommandPalette({ open, onOpenChange, lang }: CommandPaletteProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const [recent, setRecent] = useState<CommandItem[]>([]);
  const [copied, setCopied] = useState(false);
  const copy = COPY[lang];
  const commands = commandsForLanguage(lang);

  const visibleCommands = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return commands;
    return commands.filter((command) => {
      const haystack = `${command.group} ${command.title} ${command.description} ${command.preview} ${command.keywords}`.toLowerCase();
      return haystack.includes(normalized);
    });
  }, [commands, query]);

  const activeCommand = visibleCommands[activeIndex] ?? visibleCommands[0] ?? recent[0] ?? commands[0];

  const onOpenChangeRef = useRef(onOpenChange);
  useEffect(() => {
    onOpenChangeRef.current = onOpenChange;
  }, [onOpenChange]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChangeRef.current(true);
        return;
      }
      if (event.key === "Escape" && open) {
        event.preventDefault();
        onOpenChangeRef.current(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }, [open]);

  if (!open) return null;

  function runCommand(command: CommandItem) {
    setRecent((current) => [command, ...current.filter((item) => item.id !== command.id)].slice(0, 4));
    navigate(command.route);
    onOpenChange(false);
    setQuery("");
  }

  function copyPreview() {
    if (!activeCommand?.preview || !navigator.clipboard) return;
    navigator.clipboard.writeText(activeCommand.preview).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    }).catch(() => undefined);
  }

  function handleListKeyDown(event: ReactKeyboardEvent<HTMLElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => Math.min(index + 1, Math.max(visibleCommands.length - 1, 0)));
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    }
    if (event.key === "Enter" && activeCommand) {
      event.preventDefault();
      runCommand(activeCommand);
    }
  }

  const grouped = visibleCommands.reduce<Record<string, CommandItem[]>>((acc, command) => {
    acc[command.group] = [...(acc[command.group] ?? []), command];
    return acc;
  }, {});

  return (
    <div className="command-palette-overlay" role="presentation" onMouseDown={() => onOpenChange(false)}>
      <dialog
        className="command-palette-shell block m-0 p-[18px] text-inherit border"
        open
        aria-label={copy.title}
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={handleListKeyDown}
      >
        <div className="command-palette-header flex items-start justify-between pb-3 border-b" style={{ borderColor: "var(--border-c)" }}>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold t1">{copy.title}</h2>
              <span className="rounded border border-[var(--border-c)] bg-[var(--bg-muted)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--t3)]">
                {copy.shortcut}
              </span>
            </div>
            <p className="mt-1 text-xs t2">{copy.subtitle}</p>
          </div>
          <Button type="button" variant="quiet" size="sm" onClick={() => onOpenChange(false)} className="gap-1 text-xs">
            <X className="h-3.5 w-3.5" />
            <span>{copy.close}</span>
          </Button>
        </div>

        <div className="relative mt-3">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--t3)]" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActiveIndex(0);
            }}
            className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-card)] pl-9 pr-3 py-2 text-xs text-[var(--t1)] placeholder:text-[var(--t3)] focus:border-[var(--border-strong)] focus:outline-none transition-colors"
            placeholder={copy.placeholder}
            aria-label={copy.placeholder}
          />
        </div>

        <div className="mt-4 grid min-h-0 gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="command-palette-list min-h-0 overflow-y-auto pr-1" role="listbox" aria-label={copy.title}>
            {visibleCommands.length === 0 ? (
              <div className="rounded-xl border border-dashed px-4 py-8 text-center text-sm t3" style={{ borderColor: "var(--border-c)" }}>{copy.empty}</div>
            ) : (
              Object.entries(grouped).map(([group, items]) => (
                <div key={group} className="mb-3">
                  <p className="mb-1.5 px-1 text-[11px] font-medium text-[var(--t3)] tracking-tight">{group}</p>
                  <div className="space-y-1.5">
                    {items.map((command) => {
                      const commandIndex = visibleCommands.findIndex((item) => item.id === command.id);
                      const active = commandIndex === activeIndex;
                      const current = location.pathname === command.route;
                      return (
                        <button
                          key={command.id}
                          type="button"
                          role="option"
                          aria-selected={active}
                          className={`w-full text-left rounded-md border p-2 transition-colors ${
                            active
                              ? "bg-[var(--bg-elevated)] border-[var(--border-strong)]"
                              : "bg-[var(--bg-card)] border-[var(--border-c)] hover:border-[var(--border-strong)]"
                          }`}
                          onMouseEnter={() => setActiveIndex(commandIndex)}
                          onClick={() => runCommand(command)}
                        >
                          <div className="flex items-start justify-between gap-2.5">
                            <div className="min-w-0">
                              <p className="truncate text-xs font-semibold t1">{command.title}</p>
                              <p className="mt-0.5 line-clamp-1 text-[11px] t2">{command.description}</p>
                            </div>
                            <StatusBadge tone={current ? "success" : command.tone}>{current ? "目前" : command.group}</StatusBadge>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))
            )}
          </div>

          <aside className="command-preview min-h-[14rem] rounded-lg border border-[var(--border-c)] bg-[var(--bg-card)] p-4 flex flex-col justify-between">
            <div>
              <p className="text-[11px] font-medium tracking-tight text-[var(--t3)]">{copy.preview}</p>
              <h3 className="mt-1.5 text-xs font-semibold t1">{activeCommand?.title}</h3>
              <p className="mt-1 text-xs t2 leading-relaxed">{activeCommand?.description}</p>
              <pre className="mt-3 max-h-32 overflow-auto rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-2.5 font-mono text-[11px] leading-relaxed t2">{activeCommand?.preview}</pre>
            </div>
            <div>
              <Button type="button" variant="primary" className="mt-3 w-full flex items-center justify-center gap-1.5" onClick={copyPreview}>{copied ? <><Check className="h-3.5 w-3.5" /><span>{copy.copied}</span></> : <><Copy className="h-3.5 w-3.5" /><span>{copy.copy}</span></>}</Button>
              {recent.length > 0 && (
                <div className="mt-3 pt-3 border-t border-[var(--border-c)]">
                  <p className="text-[10px] font-mono text-[var(--t3)]">最近使用</p>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {recent.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className="quiet-button rounded-md px-2 py-1 text-[10px] font-semibold"
                        onClick={() => runCommand(item)}
                      >
                        {item.title}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </aside>
        </div>
      </dialog>
    </div>
  );
}
