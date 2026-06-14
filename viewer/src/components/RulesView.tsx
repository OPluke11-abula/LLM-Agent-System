import { useState, type Dispatch, type SetStateAction } from "react";
import { Modal } from "./Modal";
import { Button, MetricTile, StatusBadge, Surface } from "./ui/primitives";
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
    <Surface elevated className="flex h-full flex-col overflow-hidden p-6">
      <div className="mb-5 flex flex-shrink-0 flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] t3">{t.rulesIntroLabel}</p>
          <h2 className="mt-1 text-xl font-bold t1">{t.aiRules}</h2>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed t3">{t.rulesIntroBody}</p>
        </div>
        <Button
          type="button"
          onClick={() => setAddModalOpen(true)}
          variant="primary"
          className="self-start md:self-auto"
        >
          {t.addRule}
        </Button>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricTile label={t.rulesMetricRules} value={rules.length} />
        <MetricTile label={t.rulesMetricScope} value={t.rulesMetricScopeValue} tone="accent" />
        <MetricTile label={t.rulesMetricWriteback} value={t.rulesMetricWritebackValue} tone="success" />
        <MetricTile label={t.rulesMetricReview} value={t.rulesMetricReviewValue} tone="warning" />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {rules.length === 0 ? (
          <Surface className="flex min-h-[280px] flex-col items-center justify-center p-8 text-center">
            <StatusBadge tone="warning">{t.noRulesBadge}</StatusBadge>
            <p className="mt-4 text-sm font-semibold t1">{t.noRulesTitle}</p>
            <p className="mt-1 max-w-sm text-xs leading-relaxed t3">{t.noRulesBody}</p>
            <Button type="button" variant="primary" onClick={() => setAddModalOpen(true)} className="mt-5">
              {t.addRule}
            </Button>
          </Surface>
        ) : (
          <div className="space-y-3">
            {rules.map((rule, index) => (
              <Surface key={`${rule}-${index}`} className="flex items-start gap-3 p-4">
                <div
                  className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-[10px] font-black"
                  style={{ background: "var(--accent-bg)", color: "var(--accent)" }}
                >
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <StatusBadge tone="accent">{t.activeBadge}</StatusBadge>
                    <span className="text-[10px] font-mono t3">rule.{String(index + 1).padStart(2, "0")}</span>
                  </div>
                  <p className="text-sm leading-relaxed t1">{rule}</p>
                </div>
                <Button
                  type="button"
                  onClick={() => setDeleteTarget(index)}
                  variant="danger"
                  className="px-2 py-1 text-[10px]"
                >
                  {t.removeAction}
                </Button>
              </Surface>
            ))}
          </div>
        )}
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
            className="field-input w-full resize-none rounded-xl p-3 font-mono text-sm"
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
          <Surface className="mt-3 p-3 text-sm t2">
            {rules[deleteTarget]}
          </Surface>
        </Modal>
      )}
    </Surface>
  );
}
