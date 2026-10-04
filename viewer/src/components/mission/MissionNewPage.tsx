import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ExecutionPolicyPreset, type MissionCreateRequest, type MissionPolicy } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { Button, LinkButton, Card, CardContent } from "../ui/primitives";
import { Target, ShieldCheck, DollarSign, ArrowLeft } from "../ui/icons";

type PermissionName =
  | "dependency_change_permission"
  | "schema_change_permission"
  | "ci_change_permission"
  | "commit_permission"
  | "push_permission"
  | "draft_pr_permission";

type Permissions = Record<PermissionName, boolean>;

const DEFAULT_ALLOWED_PATHS = "agent_workspace\ndocs\nviewer";
const DEFAULT_PROTECTED_PATHS = ".agent\n.git";
const DEFAULT_PERMISSIONS: Permissions = {
  dependency_change_permission: false,
  schema_change_permission: false,
  ci_change_permission: false,
  commit_permission: false,
  push_permission: false,
  draft_pr_permission: false,
};

function splitPaths(value: string): string[] {
  return value.split(/\r?\n|,/).map((path) => path.trim()).filter(Boolean);
}

function invalidRelativePath(path: string): boolean {
  return path.startsWith("/") || path.startsWith("\\") || /^[A-Za-z]:[\\/]/.test(path) || path.split(/[\\/]/).includes("..");
}

const PERMISSION_CONFIG: readonly [PermissionName, string][] = [
  ["dependency_change_permission", "依賴版本變更授權 (Dependencies)"],
  ["schema_change_permission", "結構定義變更授權 (Schemas)"],
  ["ci_change_permission", "CI/CD 流水線變更授權 (CI/CD)"],
  ["commit_permission", "本機提交授權 (Git Commit)"],
  ["push_permission", "遠端推送授權 (Git Push)"],
  ["draft_pr_permission", "草稿 PR 發布授權 (Draft PR)"],
];

export function MissionNewPage() {
  const navigate = useNavigate();
  const [requirement, setRequirement] = useState("");
  const [repositoryId, setRepositoryId] = useState("");
  const [preset, setPreset] = useState<"conservative" | "balanced" | "exploratory">(ExecutionPolicyPreset.BALANCED);
  const [allowedPaths, setAllowedPaths] = useState(DEFAULT_ALLOWED_PATHS);
  const [protectedPaths, setProtectedPaths] = useState(DEFAULT_PROTECTED_PATHS);
  const [permissions, setPermissions] = useState<Permissions>(DEFAULT_PERMISSIONS);
  const [providerCallLimit, setProviderCallLimit] = useState("64");
  const [maxCost, setMaxCost] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<string[]>([]);

  function updatePermission(name: PermissionName, value: boolean): void {
    setPermissions((current) => ({ ...current, [name]: value }));
  }

  function validate(): string[] {
    const errors: string[] = [];
    if (!requirement.trim()) errors.push("任務需求描述不可為空。");
    if (!repositoryId.trim()) errors.push("儲存庫參照識別碼不可為空。");
    const paths = [...splitPaths(allowedPaths), ...splitPaths(protectedPaths)];
    if (paths.some(invalidRelativePath)) {
      errors.push("路徑必須為相對於儲存庫根目錄的相對路徑，且不可包含絕對路徑或 '..'。");
    }
    const calls = Number(providerCallLimit);
    if (!Number.isInteger(calls) || calls < 1) {
      errors.push("模型呼叫次數上限必須為正整數。");
    }
    if (maxCost && (!Number.isFinite(Number(maxCost)) || Number(maxCost) < 0)) {
      errors.push("預算上限必須為正數或留空。");
    }
    if (!/^[A-Z]{3}$/.test(currency)) {
      errors.push("貨幣代碼必須為 3 位大寫英文字母 (例如 USD、TWD)。");
    }
    return errors;
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const errors = validate();
    setValidation(errors);
    setError(null);
    if (errors.length > 0) return;

    setSubmitting(true);
    const scope = {
      allowed_paths: splitPaths(allowedPaths),
      protected_paths: splitPaths(protectedPaths),
      auto_merge_allowed: false as const,
      ...permissions,
    };
    const executionPolicy: MissionPolicy = { preset, scope };
    const payload: MissionCreateRequest = {
      requirement: requirement.trim(),
      repository_id: repositoryId.trim(),
      execution_policy: executionPolicy,
      budget_policy: {
        provider_call_limit: Number(providerCallLimit),
        max_cost: maxCost ? Number(maxCost) : null,
        currency,
      },
    };

    try {
      const mission = await missionApi.create(payload);
      navigate(`/missions/${encodeURIComponent(mission.mission_id)}`);
    } catch (cause: unknown) {
      if (cause instanceof MissionApiError) {
        const category =
          cause.status === 409
            ? "衝突錯誤"
            : cause.status === 422
              ? "契約格式錯誤"
              : cause.code === "auth_required"
                ? "認證失敗"
                : cause.code === "network_error"
                  ? "網路連線異常"
                  : "任務 API 錯誤";
        setError(`${category} (${cause.status || "無回應"}): ${cause.message}`);
      } else {
        setError("無法建立任務紀錄。");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex h-full min-h-0 max-w-4xl flex-col gap-5 overflow-y-auto p-4 md:p-6 pb-12" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <div className="border-b pb-4" style={{ borderColor: "var(--border-c)" }}>
        <LinkButton to="/missions" variant="quiet" size="sm" className="mb-3 inline-flex items-center gap-1.5">
          <ArrowLeft className="h-3 w-3" />
          <span>返回任務清單</span>
        </LinkButton>
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-[var(--accent)]" />
          <h1 className="text-lg font-semibold tracking-tight text-[var(--t1)]">
            建立新任務
          </h1>
        </div>
        <p className="mt-1 text-xs text-[var(--t3)] leading-relaxed">
          定義具備作用域邊界與授權限額的任務紀錄。遵循 PAP v3.8.0 契約，嚴格限制變更範圍與自動合併行為。
        </p>
      </div>

      <form className="space-y-5" onSubmit={(event) => void submit(event)} noValidate>
        {/* Core Specs Card */}
        <Card className="nordic-card">
          <CardContent className="p-5 space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t3)]">
              基本任務規格
            </h2>

            <div>
              <label htmlFor="mission-requirement-input" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
                任務需求描述 <span className="text-red-400">*</span>
              </label>
              <textarea
                id="mission-requirement-input"
                aria-label="任務需求描述"
                required
                minLength={1}
                maxLength={4000}
                value={requirement}
                onChange={(event) => setRequirement(event.target.value)}
                rows={3}
                placeholder="請具體描述開發者控制平面需完成之任務目標與交付驗收準則…"
                className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-3 text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)] leading-relaxed"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label htmlFor="mission-repository-input" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
                  儲存庫參照識別碼 <span className="text-red-400">*</span>
                </label>
                <input
                  id="mission-repository-input"
                  aria-label="儲存庫參照識別碼"
                  required
                  value={repositoryId}
                  onChange={(event) => setRepositoryId(event.target.value)}
                  placeholder="例如 owner/repo 或本機專案別名"
                  className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)]"
                />
                <span className="mt-1 block text-[10px] text-[var(--t3)]">
                  僅作識別參照，不接受絕對路徑。
                </span>
              </div>

              <div>
                <label htmlFor="mission-preset-select" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
                  執行策略預設
                </label>
                <select
                  id="mission-preset-select"
                  aria-label="執行策略預設"
                  value={preset}
                  onChange={(event) => setPreset(event.target.value as typeof preset)}
                  className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)] cursor-pointer"
                >
                  <option value="conservative">保守策略 (Conservative - 最小變更)</option>
                  <option value="balanced">平衡策略 (Balanced - 標準模式)</option>
                  <option value="exploratory">探索策略 (Exploratory - 擴展重構)</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Scope Policy Card */}
        <Card className="nordic-card">
          <CardContent className="p-5 space-y-4">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[var(--accent)]" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t3)]">
                作用域邊界規範 (Scope Policy)
              </h2>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label htmlFor="mission-allowed-paths-input" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
                  允許變更之相對路徑 (換行分隔)
                </label>
                <textarea
                  id="mission-allowed-paths-input"
                  aria-label="允許變更之相對路徑"
                  value={allowedPaths}
                  onChange={(event) => setAllowedPaths(event.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-2.5 font-mono text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)]"
                />
              </div>

              <div>
                <label htmlFor="mission-protected-paths-input" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
                  受保護之唯讀路徑 (換行分隔)
                </label>
                <textarea
                  id="mission-protected-paths-input"
                  aria-label="受保護之唯讀路徑"
                  value={protectedPaths}
                  onChange={(event) => setProtectedPaths(event.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-2.5 font-mono text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)]"
                />
              </div>
            </div>

            <div className="border-t pt-4" style={{ borderColor: "var(--border-c)" }}>
              <p className="text-xs font-medium text-[var(--t2)] mb-3">細粒度權限委派</p>
              <div className="grid gap-2.5 sm:grid-cols-2">
                {PERMISSION_CONFIG.map(([name, label]) => (
                  <label key={name} className="flex items-center gap-2.5 text-xs text-[var(--t2)] hover:text-[var(--t1)] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={permissions[name]}
                      onChange={(event) => updatePermission(name, event.target.checked)}
                      className="rounded border-[var(--border-c)]"
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>

              <div className="mt-4 rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] p-3 text-xs text-[var(--t3)]">
                <span className="font-semibold text-[var(--t1)]">自動合併 (Auto-merge)：協定永久停用。</span> 此為平台防腐與資安鐵律，嚴禁任何自動合併生產程式碼行為。
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Budget Policy Card */}
        <Card className="nordic-card">
          <CardContent className="p-5 space-y-4">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-[var(--accent)]" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--t3)]">
                預算與配額策略 (Budget Policy)
              </h2>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label htmlFor="mission-call-limit-input" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
                  模型呼叫上限 (次)
                </label>
                <input
                  id="mission-call-limit-input"
                  aria-label="模型呼叫上限"
                  type="number"
                  min="1"
                  step="1"
                  value={providerCallLimit}
                  onChange={(event) => setProviderCallLimit(event.target.value)}
                  className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)] font-mono"
                />
              </div>

              <div>
                <label htmlFor="mission-max-cost-input" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
                  最大開銷上限 (選填)
                </label>
                <input
                  id="mission-max-cost-input"
                  aria-label="最大開銷上限"
                  type="number"
                  min="0"
                  step="0.01"
                  value={maxCost}
                  onChange={(event) => setMaxCost(event.target.value)}
                  placeholder="不設上限"
                  className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)] font-mono"
                />
              </div>

              <div>
                <label htmlFor="mission-currency-input" className="block text-xs font-medium text-[var(--t2)] mb-1.5">
                  計價貨幣
                </label>
                <input
                  id="mission-currency-input"
                  aria-label="計價貨幣"
                  value={currency}
                  onChange={(event) => setCurrency(event.target.value.toUpperCase())}
                  maxLength={3}
                  className="w-full rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-3 py-2 text-xs text-[var(--t1)] outline-none focus:border-[var(--border-strong)] font-mono"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Validation Errors */}
        {validation.length > 0 && (
          <div className="rounded-md border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400 space-y-1" role="alert">
            {validation.map((msg) => (
              <p key={msg}>• {msg}</p>
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-md border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400" role="alert">
            {error}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 border-t pt-4" style={{ borderColor: "var(--border-c)" }}>
          <LinkButton to="/missions" variant="quiet">
            取消
          </LinkButton>
          <Button type="submit" variant="primary" disabled={submitting}>
            {submitting ? "正在建立…" : "建立任務"}
          </Button>
        </div>
      </form>
    </div>
  );
}
