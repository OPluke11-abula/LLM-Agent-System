import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ExecutionPolicyPreset, type MissionCreateRequest, type MissionPolicy } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { Button, LinkButton } from "../ui/primitives";

type PermissionName = "dependency_change_permission" | "schema_change_permission" | "ci_change_permission" | "commit_permission" | "push_permission" | "draft_pr_permission";
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

function fieldClass(): string {
  return "rounded-lg border bg-[var(--bg-muted)] px-3 py-2.5 text-sm font-normal t1 outline-none focus:ring-2";
}

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
    if (!requirement.trim()) errors.push("Requirement is required.");
    if (!repositoryId.trim()) errors.push("Repository reference ID is required.");
    const paths = [...splitPaths(allowedPaths), ...splitPaths(protectedPaths)];
    if (paths.some(invalidRelativePath)) errors.push("Paths must be repository-relative and cannot contain absolute paths or '..'.");
    const calls = Number(providerCallLimit);
    if (!Number.isInteger(calls) || calls < 1) errors.push("Provider-call limit must be a positive whole number.");
    if (maxCost && (!Number.isFinite(Number(maxCost)) || Number(maxCost) < 0)) errors.push("Cost limit must be empty or a non-negative number.");
    if (!/^[A-Z]{3}$/.test(currency)) errors.push("Currency must be a three-letter code.");
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
      budget_policy: { provider_call_limit: Number(providerCallLimit), max_cost: maxCost ? Number(maxCost) : null, currency },
    };
    try {
      const mission = await missionApi.create(payload);
      navigate(`/missions/${encodeURIComponent(mission.mission_id)}`);
    } catch (cause: unknown) {
      if (cause instanceof MissionApiError) {
        const category = cause.status === 409 ? "Conflict" : cause.status === 422 ? "Contract validation" : cause.code === "auth_required" ? "Authentication" : cause.code === "network_error" ? "Network" : "Mission API";
        setError(`${category} error (${cause.status || "no response"}): ${cause.message}`);
      } else {
        setError("Mission could not be created.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const permissionLabels: readonly [PermissionName, string][] = [
    ["dependency_change_permission", "Dependency changes"],
    ["schema_change_permission", "Schema changes"],
    ["ci_change_permission", "CI changes"],
    ["commit_permission", "Commit permission"],
    ["push_permission", "Push permission"],
    ["draft_pr_permission", "Draft PR permission"],
  ];
  return <section className="mx-auto flex h-full min-h-0 max-w-4xl flex-col gap-5 overflow-auto pb-6">
    <header><p className="eyebrow-label">Mission intake</p><h1 className="mt-2 text-2xl font-semibold t1">New mission</h1><p className="mt-2 max-w-2xl text-sm t2">Define a bounded, owner-scoped control record. P1 does not connect repositories, execute agents, mutate Git, or create Draft PRs.</p></header>
    <form className="control-surface grid gap-6 p-5" onSubmit={(event) => void submit(event)} noValidate>
      <div className="grid gap-5 md:grid-cols-2"><label className="grid gap-2 text-sm font-semibold t1 md:col-span-2">Requirement<textarea required minLength={1} maxLength={4000} value={requirement} onChange={(event) => setRequirement(event.target.value)} className={`${fieldClass()} min-h-32`} style={{ borderColor: "var(--border-c)", outlineColor: "var(--accent)" }} placeholder="What should the developer control plane accomplish?" /></label><label className="grid gap-2 text-sm font-semibold t1">Repository reference ID<input required value={repositoryId} onChange={(event) => setRepositoryId(event.target.value)} className={fieldClass()} style={{ borderColor: "var(--border-c)", outlineColor: "var(--accent)" }} placeholder="owner/repository or local reference ID" /><span className="text-xs font-normal t3">Reference only in P1. Absolute local paths are not accepted.</span></label><label className="grid gap-2 text-sm font-semibold t1">Execution preset<select value={preset} onChange={(event) => setPreset(event.target.value as typeof preset)} className={fieldClass()} style={{ borderColor: "var(--border-c)", outlineColor: "var(--accent)" }}><option value="conservative">Conservative</option><option value="balanced">Balanced</option><option value="exploratory">Exploratory</option></select></label></div>
      <details open className="border-t pt-5" style={{ borderColor: "var(--border-c)" }}><summary className="cursor-pointer text-sm font-semibold t1">Scope policy</summary><div className="mt-4 grid gap-5 md:grid-cols-2"><label className="grid gap-2 text-sm font-semibold t1">Allowed repository-relative paths<textarea value={allowedPaths} onChange={(event) => setAllowedPaths(event.target.value)} className={`${fieldClass()} min-h-24`} style={{ borderColor: "var(--border-c)" }} /></label><label className="grid gap-2 text-sm font-semibold t1">Protected repository-relative paths<textarea value={protectedPaths} onChange={(event) => setProtectedPaths(event.target.value)} className={`${fieldClass()} min-h-24`} style={{ borderColor: "var(--border-c)" }} /></label><div className="grid gap-3 md:col-span-2"><p className="text-xs font-semibold uppercase tracking-[0.14em] t3">Permissions</p>{permissionLabels.map(([name, label]) => <label key={name} className="flex items-center gap-3 text-sm t1"><input type="checkbox" checked={permissions[name]} onChange={(event) => updatePermission(name, event.target.checked)} />{label}</label>)}<div className="mt-2 rounded-lg border p-3 text-sm t2" style={{ borderColor: "var(--border-c)" }}><span className="font-semibold t1">Auto-merge: disabled permanently in P1.</span> This is a product guarantee, not an editable control.</div></div></div></details>
      <details className="border-t pt-5" style={{ borderColor: "var(--border-c)" }}><summary className="cursor-pointer text-sm font-semibold t1">Budget policy</summary><div className="mt-4 grid gap-5 md:grid-cols-3"><label className="grid gap-2 text-sm font-semibold t1">Provider-call limit<input type="number" min="1" step="1" value={providerCallLimit} onChange={(event) => setProviderCallLimit(event.target.value)} className={fieldClass()} style={{ borderColor: "var(--border-c)" }} /></label><label className="grid gap-2 text-sm font-semibold t1">Optional cost limit<input type="number" min="0" step="0.01" value={maxCost} onChange={(event) => setMaxCost(event.target.value)} className={fieldClass()} style={{ borderColor: "var(--border-c)" }} placeholder="No limit" /></label><label className="grid gap-2 text-sm font-semibold t1">Currency<input value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} maxLength={3} className={fieldClass()} style={{ borderColor: "var(--border-c)" }} /></label></div></details>
      <details className="border-t pt-5" style={{ borderColor: "var(--border-c)" }}><summary className="cursor-pointer text-sm font-semibold t1">Unavailable P1 features</summary><ul className="mt-4 grid gap-2 text-sm t2"><li>Repository connection not implemented</li><li>Execution not implemented</li><li>Git mutation not implemented</li><li>Draft PR side effect not implemented</li></ul></details>
      {validation.length > 0 && <div role="alert" className="grid gap-1 text-sm" style={{ color: "var(--danger)" }}>{validation.map((message) => <p key={message}>{message}</p>)}</div>}{error && <p className="text-sm" style={{ color: "var(--danger)" }} role="alert">{error}</p>}
      <div className="flex flex-wrap items-center justify-end gap-3 border-t pt-4" style={{ borderColor: "var(--border-c)" }}><LinkButton to="/missions">Cancel</LinkButton><Button type="submit" variant="primary" disabled={submitting}>{submitting ? "Creating…" : "Create mission"}</Button></div>
    </form>
  </section>;
}
