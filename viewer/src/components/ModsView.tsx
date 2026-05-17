import type { Dispatch, SetStateAction } from "react";
import { ALL_SKILLS, CAT_KEYS } from "../constants";
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

  return (
    <div className="h-full overflow-y-auto rounded-2xl border p-6 shadow-xl panel-bg">
      <h2 className="mb-6 text-xl font-bold t1">{t.mods}</h2>

      <div className="card-bg mb-6 flex items-center justify-between gap-4 rounded-xl border p-5">
        <div>
          <p className="text-sm font-bold t1">{t.agentsMdToggle}</p>
          <p className="mt-0.5 text-xs t3">{t.agentsMdDesc}</p>
        </div>
        <button
          type="button"
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
      </div>

      <p className="mb-1 text-[10px] font-bold uppercase tracking-widest t3">{t.skillsTitle}</p>
      <p className="mb-5 text-xs t3">{t.skillsDesc}</p>
      <div className="space-y-6">
        {CAT_KEYS.map((category) => (
          <div key={category}>
            <p className="mb-2 px-1 text-[10px] font-bold uppercase tracking-widest t3">
              {categoryLabels[category]}
            </p>
            <div className="space-y-2">
              {ALL_SKILLS.filter((skill) => skill.cat === category).map((skill) => (
                <label
                  key={skill.id}
                  className="card-bg flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 transition-all hover:brightness-110"
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
                  <span className="text-sm t1">{lang === "zh" ? skill.zh : skill.en}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
