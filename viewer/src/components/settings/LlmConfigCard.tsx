import React, { type Dispatch, type SetStateAction } from "react";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, StatusBadge } from "../ui/primitives";
import { Cpu } from "../ui/icons";
import type { LlmConfig, LlmConfigPayload, TranslationMessages } from "../../types";

interface LlmConfigCardProps {
  t: TranslationMessages;
  llmConfig: LlmConfig | null;
  llmPayload: LlmConfigPayload;
  setLlmPayload: Dispatch<SetStateAction<LlmConfigPayload>>;
  saveStatus: string;
  onSaveLlmConfig: () => void;
}

export const LlmConfigCard: React.FC<LlmConfigCardProps> = ({
  t,
  llmConfig,
  llmPayload,
  setLlmPayload,
  saveStatus,
  onSaveLlmConfig,
}) => {
  return (
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
          <Button type="button" onClick={onSaveLlmConfig} variant="primary" className="px-4 py-2 text-xs font-semibold">
            {t.saveConfigBtn}
          </Button>
          {saveStatus && <StatusBadge tone="success">{saveStatus}</StatusBadge>}
        </div>
      </CardContent>
    </Card>
  );
};
