import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { THEME_LIST } from "../../constants";
import type { Lang, LlmConfig, LlmConfigPayload, ThemeId, TranslationMessages, Workspace } from "../../types";
import { logUiDiagnostic } from "../../utils/logger";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, Button } from "../ui/primitives";
import { cx } from "../ui/utils";
import { Globe, Palette, RotateCcw } from "../ui/icons";
import { LlmConfigCard } from "./LlmConfigCard";
import { WorkspacesConfigCard, type WorkspaceField } from "./WorkspacesConfigCard";

type SettingsGeneralPanelProps = {
  readonly lang: Lang;
  readonly setLang: (lang: Lang) => void;
  readonly theme: ThemeId;
  readonly setTheme: (theme: ThemeId) => void;
  readonly workspaces: readonly Workspace[];
  readonly setWorkspaces: Dispatch<SetStateAction<Workspace[]>>;
  readonly t: TranslationMessages;
  readonly relaunchOnboarding: () => void;
};

const LANG_NAMES: Record<Lang, string> = {
  zh: "繁體中文",
  en: "English",
  ja: "日本語",
  fr: "Français",
} as const;

export function SettingsGeneralPanel({
  lang,
  setLang,
  theme,
  setTheme,
  workspaces,
  setWorkspaces,
  t,
  relaunchOnboarding,
}: SettingsGeneralPanelProps) {
  const [llmConfig, setLlmConfig] = useState<LlmConfig | null>(null);
  const [llmPayload, setLlmPayload] = useState<LlmConfigPayload>({});
  const [saveStatus, setSaveStatus] = useState("");

  useEffect(() => {
    let isSubscribed = true;
    const controller = new AbortController();

    fetch("http://127.0.0.1:8000/v1/config", { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load LLM config: HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!isSubscribed) return;
        setLlmConfig(data as LlmConfig);
        setLlmPayload({
          provider: data.provider,
          model: data.model,
          base_url: data.base_url,
          api_key: "",
        });
      })
      .catch((err) => {
        if (!isSubscribed) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        setSaveStatus("Failed to load LLM config");
        logUiDiagnostic("Failed to load config", err);
      });

    return () => {
      isSubscribed = false;
      controller.abort();
    };
  }, []);

  async function saveLlmConfig() {
    try {
      const res = await fetch("http://127.0.0.1:8000/v1/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(llmPayload),
      });
      if (res.ok) {
        setSaveStatus(t.configSavedToast);
        setTimeout(() => setSaveStatus(""), 3000);
      } else {
        setSaveStatus(`Failed to save config (${res.status})`);
      }
    } catch (err) {
      setSaveStatus("Failed to save LLM config");
      logUiDiagnostic("Failed to save config", err);
    }
  }

  function addWorkspace() {
    setWorkspaces((current) => [
      ...current,
      {
        id: `ws-${Date.now()}`,
        name: `Project ${current.length + 1}`,
        lang: "TypeScript",
        path: "",
      },
    ]);
  }

  function removeWorkspace(id: string) {
    setWorkspaces((current) => current.filter((workspace) => workspace.id !== id));
  }

  function updateWorkspace(id: string, field: WorkspaceField, value: string) {
    setWorkspaces((current) =>
      current.map((workspace) => (workspace.id === id ? { ...workspace, [field]: value } : workspace)),
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-[var(--accent)]" />
            <CardTitle>{t.langLabel}</CardTitle>
          </div>
          <CardDescription>選擇介面顯示語言與本地化訊息格式</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {(["zh", "en", "ja", "fr"] as const).map((item) => {
              const active = lang === item;
              return (
                <button
                  key={item}
                  type="button"
                  onClick={() => setLang(item)}
                  className={cx(
                    "rounded-md px-3.5 py-1.5 text-xs font-medium transition-all cursor-pointer border",
                    active
                      ? "bg-[var(--bg-elevated)] text-[var(--t1)] font-semibold shadow-sm border-[var(--border-strong)]"
                      : "bg-[var(--bg-card)] text-[var(--t3)] hover:text-[var(--t2)] border-[var(--border-c)] hover:border-[var(--border-strong)]"
                  )}
                >
                  {LANG_NAMES[item]}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Palette className="h-4 w-4 text-[var(--accent)]" />
            <CardTitle>{t.themeLabel}</CardTitle>
          </div>
          <CardDescription>選擇適合您開發環境的暗色或高對比配色方案</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {THEME_LIST.map(({ id }) => {
              const active = theme === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setTheme(id)}
                  className={cx(
                    "rounded-md px-3.5 py-1.5 text-xs font-medium transition-all cursor-pointer border",
                    active
                      ? "bg-[var(--bg-elevated)] text-[var(--t1)] font-semibold shadow-sm border-[var(--border-strong)]"
                      : "bg-[var(--bg-card)] text-[var(--t3)] hover:text-[var(--t2)] border-[var(--border-c)] hover:border-[var(--border-strong)]"
                  )}
                >
                  {t.themes[id]}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <LlmConfigCard
        t={t}
        llmConfig={llmConfig}
        llmPayload={llmPayload}
        setLlmPayload={setLlmPayload}
        saveStatus={saveStatus}
        onSaveLlmConfig={saveLlmConfig}
      />

      <WorkspacesConfigCard
        t={t}
        workspaces={workspaces}
        onAddWorkspace={addWorkspace}
        onRemoveWorkspace={removeWorkspace}
        onUpdateWorkspace={updateWorkspace}
      />

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <RotateCcw className="h-4 w-4 text-[var(--accent)]" />
            <CardTitle>{t.relaunchTutorialBtn}</CardTitle>
          </div>
          <CardDescription>重新啟動新手導引教學精靈以檢視功能介紹</CardDescription>
        </CardHeader>
        <CardContent>
          <Button type="button" onClick={relaunchOnboarding} variant="primary" className="flex items-center gap-2 px-4 py-2 text-xs font-semibold">
            <RotateCcw className="h-3.5 w-3.5" />
            <span>{t.relaunchTutorialBtn}</span>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
