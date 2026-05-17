import { useState, type Dispatch, type SetStateAction } from "react";
import { Modal } from "./Modal";
import type { TranslationMessages } from "../types";

type RulesViewProps = {
  t: TranslationMessages;
  rules: string[];
  setRules: Dispatch<SetStateAction<string[]>>;
};

export function RulesView({ t, rules, setRules }: RulesViewProps) {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);
  const [newRule, setNewRule] = useState("");

  function handleAddRule() {
    if (!newRule.trim()) {
      return;
    }

    setRules((current) => [...current, newRule.trim()]);
    setNewRule("");
    setAddModalOpen(false);
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border p-6 shadow-xl panel-bg">
      <div className="mb-5 flex flex-shrink-0 items-center justify-between">
        <h2 className="text-xl font-bold t1">{t.aiRules}</h2>
        <button
          type="button"
          onClick={() => setAddModalOpen(true)}
          className="rounded-lg border px-4 py-2 text-xs font-bold transition-all"
          style={{ color: "var(--accent)", borderColor: "var(--accent)", background: "var(--accent-bg)" }}
        >
          {t.addRule}
        </button>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto">
        {rules.map((rule, index) => (
          <div key={`${rule}-${index}`} className="card-bg flex items-start gap-3 rounded-xl border p-4">
            <div
              className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded text-[10px] font-black"
              style={{ background: "var(--accent-bg)", color: "var(--accent)" }}
            >
              {String(index + 1).padStart(2, "0")}
            </div>
            <p className="flex-1 text-sm leading-relaxed t1">{rule}</p>
            <button
              type="button"
              onClick={() => setDeleteTarget(index)}
              className="t3 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold transition-colors hover:bg-red-900/30 hover:text-red-400"
            >
              −
            </button>
          </div>
        ))}
      </div>

      {addModalOpen && (
        <Modal
          title={t.addRuleTitle}
          onConfirm={handleAddRule}
          onCancel={() => {
            setAddModalOpen(false);
            setNewRule("");
          }}
          confirmText={t.confirm}
          cancelText={t.cancel}
        >
          <textarea
            autoFocus
            value={newRule}
            onChange={(event) => setNewRule(event.target.value)}
            placeholder={t.addRulePlaceholder}
            rows={4}
            className="w-full resize-none rounded-xl border p-3 text-sm font-mono focus:outline-none focus:ring-1 t1"
            style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                handleAddRule();
              }
            }}
          />
        </Modal>
      )}

      {deleteTarget !== null && (
        <Modal
          title={t.deleteRuleTitle}
          onConfirm={() => {
            setRules((current) => current.filter((_, index) => index !== deleteTarget));
            setDeleteTarget(null);
          }}
          onCancel={() => setDeleteTarget(null)}
          confirmText={t.confirm}
          cancelText={t.cancel}
          danger
        >
          <p className="text-sm t2">{t.deleteRuleConfirm}</p>
          <div
            className="mt-3 rounded-lg border p-3 text-sm t2"
            style={{ background: "var(--bg-card)", borderColor: "var(--border-c)" }}
          >
            {rules[deleteTarget]}
          </div>
        </Modal>
      )}
    </div>
  );
}
