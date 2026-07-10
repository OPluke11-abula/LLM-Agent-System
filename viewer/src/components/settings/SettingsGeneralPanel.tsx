import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { ALL_LANGS, THEME_LIST } from "../../constants";
import type { Lang, LlmConfig, LlmConfigPayload, ThemeId, TranslationMessages, Workspace } from "../../types";
import { logUiDiagnostic } from "../../utils/logger";
import { Button, StatusBadge, Surface } from "../ui/primitives";

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
      .then((res) => res.json())
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
    <>
      <Surface as="section" className="mb-7 p-5">
        <p className="mb-3 text-[10px] font-bold uppercase tracking-widest t3">{t.langLabel}</p>
        <div className="flex flex-wrap gap-3">
          {(["zh", "en", "ja", "fr"] as const).map((item) => (
            <Button
              key={item}
              type="button"
              onClick={() => setLang(item)}
              variant={lang === item ? "primary" : "quiet"}
              className="px-5 py-2 text-sm"
            >
              {LANG_NAMES[item]}
            </Button>
          ))}
        </div>
      </Surface>

      <Surface as="section" className="mb-7 p-5">
        <p className="mb-3 text-[10px] font-bold uppercase tracking-widest t3">{t.relaunchTutorialBtn}</p>
        <Button type="button" onClick={relaunchOnboarding} variant="primary" className="px-5 py-2.5 text-sm">
          {t.relaunchTutorialBtn}
        </Button>
      </Surface>

      <Surface as="section" className="mb-7 p-5">
        <p className="mb-3 text-[10px] font-bold uppercase tracking-widest t3">{t.themeLabel}</p>
        <div className="flex flex-wrap gap-2">
          {THEME_LIST.map(({ id }) => (
            <Button
              key={id}
              type="button"
              onClick={() => setTheme(id)}
              variant={theme === id ? "primary" : "quiet"}
              className="px-4 py-2"
            >
              {t.themes[id]}
            </Button>
          ))}
        </div>
      </Surface>

      <Surface as="section" className="mb-7 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[10px] font-bold uppercase tracking-widest t3">{t.llmConfigTitle}</p>
          {llmConfig?.api_key_set && <StatusBadge tone="success">{t.envKeySetBadge}</StatusBadge>}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="llm-provider" className="mb-1 block text-xs font-bold t2">{t.llmProviderLabel}</label>
            <select
              id="llm-provider"
              value={llmPayload.provider || ""}
              onChange={(e) => setLlmPayload({ ...llmPayload, provider: e.target.value })}
              className="field-input w-full rounded-lg px-3 py-2 text-sm"
            >
              <option value="google-genai">Google GenAI (Gemini)</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama (Local)</option>
            </select>
          </div>
          <div>
            <label htmlFor="llm-model" className="mb-1 block text-xs font-bold t2">{t.llmModelLabel}</label>
            <input
              id="llm-model"
              type="text"
              value={llmPayload.model || ""}
              onChange={(e) => setLlmPayload({ ...llmPayload, model: e.target.value })}
              placeholder="e.g. gemini-2.5-flash"
              className="field-input w-full rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div className="md:col-span-2">
            <label htmlFor="llm-api-key" className="mb-1 block text-xs font-bold t2">{t.llmApiKeyLabel}</label>
            <input
              id="llm-api-key"
              type="password"
              value={llmPayload.api_key || ""}
              onChange={(e) => setLlmPayload({ ...llmPayload, api_key: e.target.value })}
              placeholder={llmConfig?.api_key_set ? "Current key is set. Leave blank to keep it." : "Enter API Key..."}
              className="field-input w-full rounded-lg px-3 py-2 text-sm"
            />
          </div>
          {(llmPayload.provider === "ollama" || llmPayload.provider === "openai") && (
            <div className="md:col-span-2">
              <label htmlFor="llm-base-url" className="mb-1 block text-xs font-bold t2">{t.llmBaseUrlLabel}</label>
              <input
                id="llm-base-url"
                type="text"
                value={llmPayload.base_url || ""}
                onChange={(e) => setLlmPayload({ ...llmPayload, base_url: e.target.value })}
                placeholder="e.g. http://127.0.0.1:11434"
                className="field-input w-full rounded-lg px-3 py-2 text-sm"
              />
            </div>
          )}
        </div>
        <div className="mt-5 flex items-center gap-4">
          <Button type="button" onClick={saveLlmConfig} variant="primary" className="px-5 py-2 text-sm">
            {t.saveConfigBtn}
          </Button>
          {saveStatus && <StatusBadge tone="success">{saveStatus}</StatusBadge>}
        </div>
      </Surface>

      <section className="mb-7">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-[10px] font-bold uppercase tracking-widest t3">{t.workspaces}</p>
          <Button type="button" onClick={addWorkspace} variant="primary">
            {t.addWorkspace}
          </Button>
        </div>
        <Surface className="mb-4 flex gap-3 p-4">
          <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: "var(--accent)" }} />
          <div>
            <p className="text-xs font-bold" style={{ color: "var(--accent)" }}>
              {t.aiHowTitle}
            </p>
            <p className="mt-1 text-xs leading-relaxed t2">{t.aiHowBody}</p>
          </div>
        </Surface>
        <div className="space-y-4">
          {workspaces.map((workspace) => (
            <Surface key={workspace.id} className="space-y-3 p-4">
              <div className="flex items-center gap-3">
                <input
                  aria-label={`${t.wsName}: ${workspace.name}`}
                  value={workspace.name}
                  onChange={(event) => updateWorkspace(workspace.id, "name", event.target.value)}
                  placeholder={t.wsName}
                  className="field-input min-w-0 flex-1 rounded-lg px-3 py-2 text-sm"
                />
                <select
                  aria-label={`${workspace.name} language`}
                  value={workspace.lang}
                  onChange={(event) => updateWorkspace(workspace.id, "lang", event.target.value)}
                  className="field-input rounded-lg px-2 py-2 text-sm"
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
                    className="flex-shrink-0"
                  >
                    {t.removeWs}
                  </Button>
                )}
              </div>
              <div className="flex gap-2">
                <input
                  aria-label={`${workspace.name} ${t.wsPathPlaceholder}`}
                  value={draftPaths[workspace.id] ?? workspace.path}
                  onChange={(event) =>
                    setDraftPaths((current) => ({
                      ...current,
                      [workspace.id]: event.target.value,
                    }))
                  }
                  placeholder={t.wsPathPlaceholder}
                  className="field-input w-full rounded-lg px-3 py-2 font-mono text-xs"
                />
                <Button
                  type="button"
                  onClick={() =>
                    draftPaths[workspace.id] !== undefined &&
                    updateWorkspace(workspace.id, "path", draftPaths[workspace.id])
                  }
                  variant="primary"
                  className="px-3 py-2"
                  disabled={draftPaths[workspace.id] === undefined || draftPaths[workspace.id] === workspace.path}
                >
                  {t.confirm}
                </Button>
              </div>
            </Surface>
          ))}
        </div>
      </section>
    </>
  );
}
