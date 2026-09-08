import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { ALL_LANGS, THEME_LIST } from "../../constants";
import type { Lang, LlmConfig, LlmConfigPayload, ThemeId, TranslationMessages, Workspace } from "../../types";
import { logUiDiagnostic } from "../../utils/logger";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, StatusBadge, Surface } from "../ui/primitives";
import { Cpu, Folder, Globe, Palette, Plus, RotateCcw, Sparkles, Trash2 } from "../ui/icons";

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

type WorkspaceField = "name" | "lang" | "path";

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
  const [draftPaths, setDraftPaths] = useState<Record<string, string>>({});
  const [llmConfig, setLlmConfig] = useState<LlmConfig | null>(null);
  const [llmPayload, setLlmPayload] = useState<LlmConfigPayload>({});
  const [saveStatus, setSaveStatus] = useState("");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/v1/config")
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load LLM config: HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setLlmConfig(data as LlmConfig);
        setLlmPayload({
          provider: data.provider,
          model: data.model,
          base_url: data.base_url,
          api_key: "",
        });
      })
      .catch((err) => {
        setSaveStatus("Failed to load LLM config");
        logUiDiagnostic("Failed to load config", err);
      });
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
          <div className="flex flex-wrap gap-2.5">
            {(["zh", "en", "ja", "fr"] as const).map((item) => (
              <Button
                key={item}
                type="button"
                onClick={() => setLang(item)}
                variant={lang === item ? "primary" : "quiet"}
                className="px-4 py-2 text-xs font-semibold"
              >
                {LANG_NAMES[item]}
              </Button>
            ))}
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
            {THEME_LIST.map(({ id }) => (
              <Button
                key={id}
                type="button"
                onClick={() => setTheme(id)}
                variant={theme === id ? "primary" : "quiet"}
                className="px-3.5 py-1.5 text-xs font-medium"
              >
                {t.themes[id]}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-[var(--accent)]" />
              <CardTitle>{t.llmConfigTitle}</CardTitle>
            </div>
            {llmConfig?.api_key_set && <StatusBadge tone="success">{t.envKeySetBadge}</StatusBadge>}
          </div>
          <CardDescription>配置底層推理由模型供應商、端點位址與授權憑證</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="llm-provider" className="mb-1.5 block text-xs font-semibold t2">
                {t.llmProviderLabel}
              </label>
              <select
                id="llm-provider"
                value={llmPayload.provider || ""}
                onChange={(e) => setLlmPayload({ ...llmPayload, provider: e.target.value })}
                className="flex h-9 w-full rounded-lg border bg-[var(--bg-card)] px-3 py-1.5 text-xs t1 shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                style={{ borderColor: "var(--border-c)" }}
              >
                <option value="google-genai">Google GenAI (Gemini)</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
            <div>
              <label htmlFor="llm-model" className="mb-1.5 block text-xs font-semibold t2">
                {t.llmModelLabel}
              </label>
              <Input
                id="llm-model"
                type="text"
                value={llmPayload.model || ""}
                onChange={(e) => setLlmPayload({ ...llmPayload, model: e.target.value })}
                placeholder="e.g. gemini-2.5-flash"
              />
            </div>
            <div className="md:col-span-2">
              <label htmlFor="llm-api-key" className="mb-1.5 block text-xs font-semibold t2">
                {t.llmApiKeyLabel}
              </label>
              <Input
                id="llm-api-key"
                type="password"
                value={llmPayload.api_key || ""}
                onChange={(e) => setLlmPayload({ ...llmPayload, api_key: e.target.value })}
                placeholder={llmConfig?.api_key_set ? "Current key is set. Leave blank to keep it." : "Enter API Key..."}
              />
            </div>
            {(llmPayload.provider === "ollama" || llmPayload.provider === "openai") && (
              <div className="md:col-span-2">
                <label htmlFor="llm-base-url" className="mb-1.5 block text-xs font-semibold t2">
                  {t.llmBaseUrlLabel}
                </label>
                <Input
                  id="llm-base-url"
                  type="text"
                  value={llmPayload.base_url || ""}
                  onChange={(e) => setLlmPayload({ ...llmPayload, base_url: e.target.value })}
                  placeholder="e.g. http://127.0.0.1:11434"
                />
              </div>
            )}
          </div>
          <div className="mt-5 flex items-center gap-3">
            <Button type="button" onClick={saveLlmConfig} variant="primary" className="px-4 py-2 text-xs font-semibold">
              {t.saveConfigBtn}
            </Button>
            {saveStatus && <StatusBadge tone="success">{saveStatus}</StatusBadge>}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Folder className="h-4 w-4 text-[var(--accent)]" />
              <CardTitle>{t.workspaces}</CardTitle>
            </div>
            <Button type="button" onClick={addWorkspace} variant="primary" className="flex items-center gap-1.5 px-3 py-1.5 text-xs">
              <Plus className="h-3.5 w-3.5" />
              <span>{t.addWorkspace}</span>
            </Button>
          </div>
          <CardDescription>管理參與 Swarm 運作的多個專案工作區路徑與技術棧</CardDescription>
        </CardHeader>
        <CardContent>
          <Surface className="mb-4 flex items-start gap-3 rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}>
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent)]" />
            <div>
              <p className="text-xs font-bold" style={{ color: "var(--accent)" }}>
                {t.aiHowTitle}
              </p>
              <p className="mt-1 text-xs leading-relaxed t2">{t.aiHowBody}</p>
            </div>
          </Surface>

          <div className="space-y-3">
            {workspaces.map((workspace) => (
              <Surface key={workspace.id} className="space-y-2.5 rounded-lg border p-3.5" style={{ borderColor: "var(--border-c)", background: "var(--bg-card)" }}>
                <div className="flex items-center gap-2.5">
                  <Input
                    aria-label={`${t.wsName}: ${workspace.name}`}
                    value={workspace.name}
                    onChange={(event) => updateWorkspace(workspace.id, "name", event.target.value)}
                    placeholder={t.wsName}
                    className="min-w-0 flex-1"
                  />
                  <select
                    aria-label={`${workspace.name} language`}
                    value={workspace.lang}
                    onChange={(event) => updateWorkspace(workspace.id, "lang", event.target.value)}
                    className="flex h-9 rounded-lg border bg-[var(--bg-card)] px-2 py-1.5 text-xs t1 shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    style={{ borderColor: "var(--border-c)" }}
                  >
                    {ALL_LANGS.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                  {workspaces.length > 1 && (
                    <Button
                      type="button"
                      onClick={() => removeWorkspace(workspace.id)}
                      variant="danger"
                      className="flex h-9 shrink-0 items-center justify-center px-2.5"
                      title={t.removeWs}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
                <div className="flex gap-2">
                  <Input
                    aria-label={`${workspace.name} ${t.wsPathPlaceholder}`}
                    value={draftPaths[workspace.id] ?? workspace.path}
                    onChange={(event) =>
                      setDraftPaths((current) => ({
                        ...current,
                        [workspace.id]: event.target.value,
                      }))
                    }
                    placeholder={t.wsPathPlaceholder}
                    className="font-mono"
                  />
                  <Button
                    type="button"
                    onClick={() =>
                      draftPaths[workspace.id] !== undefined &&
                      updateWorkspace(workspace.id, "path", draftPaths[workspace.id])
                    }
                    variant="primary"
                    className="px-3 py-1.5 text-xs font-semibold"
                    disabled={draftPaths[workspace.id] === undefined || draftPaths[workspace.id] === workspace.path}
                  >
                    {t.confirm}
                  </Button>
                </div>
              </Surface>
            ))}
          </div>
        </CardContent>
      </Card>

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
