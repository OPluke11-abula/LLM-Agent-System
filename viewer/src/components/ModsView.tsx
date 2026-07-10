import type { Dispatch, SetStateAction } from "react";
import { ALL_SKILLS, CAT_KEYS } from "../constants";
import { MetricTile, StatusBadge, Surface } from "./ui/primitives";
import type { Lang, TranslationMessages } from "../types";

type ModsViewProps = {
  t: TranslationMessages;
  lang: Lang;
  agentsEnabled: boolean;
  setAgentsEnabled: Dispatch<SetStateAction<boolean>>;
  activeSkills: Record<string, boolean>;
  setActiveSkills: Dispatch<SetStateAction<Record<string, boolean>>>;
};

export function ModsView({
  t,
  lang,
  agentsEnabled,
  setAgentsEnabled,
  activeSkills,
  setActiveSkills,
}: ModsViewProps) {
  const categoryLabels = {
    backend: t.catBackend,
    mobile: t.catMobile,
    testing: t.catTesting,
    quality: t.catQuality,
  };
  const enabledCount = Object.values(activeSkills).filter(Boolean).length;

  return (
    <Surface elevated className="h-full overflow-y-auto p-6">
      <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] t3">{t.modsIntroLabel}</p>
          <h2 className="mt-1 text-xl font-bold t1">{t.mods}</h2>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed t3">{t.modsIntroBody}</p>
        </div>
        <StatusBadge tone={agentsEnabled ? "success" : "warning"}>
          {agentsEnabled ? t.writebackOnBadge : t.writebackOffBadge}
        </StatusBadge>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricTile label={t.modsMetricSkills} value={ALL_SKILLS.length} />
        <MetricTile label={t.modsMetricEnabled} value={enabledCount} tone={enabledCount > 0 ? "success" : "neutral"} />
        <MetricTile label={t.modsMetricCategories} value={CAT_KEYS.length} tone="accent" />
        <MetricTile
          label={t.agentsMdMetricLabel}
          value={agentsEnabled ? t.onState : t.offState}
          tone={agentsEnabled ? "success" : "warning"}
        />
      </div>

      <Surface className="mb-6 flex items-center justify-between gap-4 p-5">
        <div>
          <p className="text-sm font-bold t1">{t.agentsMdToggle}</p>
          <p className="mt-0.5 text-xs t3">{t.agentsMdDesc}</p>
        </div>
        <button
          type="button"
          aria-label={t.agentsMdToggle}
          onClick={() => setAgentsEnabled((current) => !current)}
          className="relative h-6 w-12 flex-shrink-0 rounded-full transition-colors duration-300"
          style={{
            background: agentsEnabled ? "var(--accent)" : "var(--bg-card)",
            border: "1px solid var(--border-c)",
          }}
        >
          <span
            className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform duration-300 ${
              agentsEnabled ? "translate-x-6" : "translate-x-0"
            }`}
          />
        </button>
      </Surface>

      <p className="mb-1 text-[10px] font-bold uppercase tracking-widest t3">{t.skillsTitle}</p>
      <p className="mb-5 text-xs t3">{t.skillsDesc}</p>
      <div className="grid gap-4 xl:grid-cols-2">
        {CAT_KEYS.map((category) => (
          <Surface key={category} className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[10px] font-bold uppercase tracking-widest t3">
                {categoryLabels[category]}
              </p>
              <StatusBadge tone="neutral">
                {ALL_SKILLS.filter((skill) => skill.cat === category && activeSkills[skill.id]).length}/
                {ALL_SKILLS.filter((skill) => skill.cat === category).length}
              </StatusBadge>
            </div>
            <div className="grid gap-2">
              {ALL_SKILLS.filter((skill) => skill.cat === category).map((skill, index) => (
                <label
                  key={skill.id}
                  className="group flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-3 transition-all"
                  style={{
                    background: activeSkills[skill.id] ? "var(--accent-bg)" : "var(--bg-panel)",
                    borderColor: activeSkills[skill.id] ? "var(--accent)" : "var(--border-c)",
                  }}
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 flex-shrink-0"
                    style={{ accentColor: "var(--accent)" }}
                    checked={Boolean(activeSkills[skill.id])}
                    onChange={(event) =>
                      setActiveSkills((current) => ({
                        ...current,
                        [skill.id]: event.target.checked,
                      }))
                    }
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[9px] t3">
                        {category.slice(0, 2).toUpperCase()}-{String(index + 1).padStart(2, "0")}
                      </span>
                      {activeSkills[skill.id] && <StatusBadge tone="success">{t.activeBadge}</StatusBadge>}
                    </div>
                    <span className="mt-1 block text-sm leading-snug t1">{lang === "zh" ? skill.zh : skill.en}</span>
                  </div>
                </label>
              ))}
            </div>
          </Surface>
        ))}
      </div>
    </Surface>
  );
}
