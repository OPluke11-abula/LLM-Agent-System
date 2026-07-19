import type {
  ApprovalRecordRequest,
  EvidenceRecordRequest,
  Mission,
  MissionCapabilitiesResponse,
  MissionCreateRequest,
  MissionErrorResponse,
  MissionPage,
  MissionSystemCapabilities,
  MissionTransitionAPIRequest,
  MissionTransitionPage,
  MissionTransitionResponse,
  PlanAttachRequest,
  VerificationRecordRequest,
} from "../generated/missionContracts";
import { missionAuth, type MissionAuthProvider } from "./missionAuth";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
type MissionErrorCode = MissionErrorResponse["code"] | "network_error" | "unknown_server_error" | "auth_unavailable" | "aborted";
type Guard<T> = (value: unknown) => value is T;
type MissionListOptions = { readonly limit?: number; readonly offset?: number; readonly signal?: AbortSignal };

declare global {
  interface Window {
    __LAS_API_BASE_URL__?: string;
  }
}

export class MissionApiError extends Error {
  readonly code: MissionErrorCode;
  readonly status: number;

  constructor(code: MissionErrorCode, message: string, status: number) {
    super(message);
    this.name = "MissionApiError";
    this.code = code;
    this.status = status;
  }
}

const missionApiBaseUrl = typeof window !== "undefined" ? window.__LAS_API_BASE_URL__ ?? import.meta.env.VITE_LAS_API_URL ?? "http://127.0.0.1:8000" : import.meta.env.VITE_LAS_API_URL ?? "http://127.0.0.1:8000";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function isMissionState(value: unknown): boolean {
  return typeof value === "string" && ["draft", "planning", "awaiting_approval", "running", "needs_decision", "verifying", "review_ready", "draft_pr_created", "closed", "paused", "cancelled", "failed", "budget_exhausted", "scope_blocked", "ci_failed"].includes(value);
}

function isMissionEvent(value: unknown): boolean {
  return typeof value === "string" && ["start_planning", "submit_plan", "approve_plan", "reject_plan", "begin_verification", "complete_verification", "fail_ci", "retry_verification", "create_draft_pr", "request_scope_expansion", "block_scope", "approve_scope", "reject_scope", "pause", "resume", "cancel", "fail", "exhaust_budget", "close"].includes(value);
}

function isApprovalSubject(value: unknown): boolean {
  if (!isRecord(value) || !isString(value.kind)) return false;
  if (value.kind === "plan") return isString(value.plan_id) && isInteger(value.plan_revision) && isString(value.plan_digest);
  if (value.kind === "scope_expansion") return isString(value.scope_request_id);
  if (value.kind === "draft_pr") return isString(value.review_id) && isString(value.plan_id) && isInteger(value.plan_revision) && isString(value.branch) && isString(value.head_sha);
  return false;
}

function isMission(value: unknown): value is Mission {
  if (!isRecord(value) || !isString(value.mission_id) || !isString(value.requirement) || !isString(value.repository_id) || !isRecord(value.execution_policy)) return false;
  if (value.current_state !== undefined && !isMissionState(value.current_state)) return false;
  if (value.revision !== undefined && (!isInteger(value.revision) || value.revision < 0)) return false;
  if (value.approval_gates !== undefined && (!Array.isArray(value.approval_gates) || !value.approval_gates.every((gate) => isRecord(gate) && isString(gate.gate_id) && isString(gate.gate_type) && isApprovalSubject(gate.subject)))) return false;
  if (value.transition_audit !== undefined && (!Array.isArray(value.transition_audit) || !value.transition_audit.every((audit) => isRecord(audit) && isString(audit.audit_id) && isMissionEvent(audit.event) && isMissionState(audit.from_state) && isMissionState(audit.to_state) && isInteger(audit.from_revision) && isInteger(audit.to_revision)))) return false;
  return true;
}

function isPage(value: unknown, itemGuard: (value: unknown) => boolean): boolean {
  return isRecord(value) && Array.isArray(value.items) && value.items.every(itemGuard) && isInteger(value.limit) && value.limit > 0 && isInteger(value.offset) && value.offset >= 0 && (value.next_offset === null || isInteger(value.next_offset));
}

function isMissionPage(value: unknown): value is MissionPage {
  return isPage(value, isMission);
}

function isTransitionAudit(value: unknown): boolean {
  return isRecord(value) && isString(value.audit_id) && isMissionEvent(value.event) && isMissionState(value.from_state) && isMissionState(value.to_state) && isInteger(value.from_revision) && isInteger(value.to_revision) && isString(value.actor_id) && isString(value.idempotency_key);
}

function isTransitionPage(value: unknown): value is MissionTransitionPage {
  return isPage(value, isTransitionAudit);
}

function isTransitionResponse(value: unknown): value is MissionTransitionResponse {
  return isRecord(value) && isMission(value.mission) && isTransitionAudit(value.audit) && typeof value.replayed === "boolean";
}

function isCapabilities(value: unknown): value is MissionCapabilitiesResponse {
  return isRecord(value) && isString(value.mission_id) && isMissionState(value.current_state) && Array.isArray(value.allowed_events) && value.allowed_events.every(isMissionEvent) && isInteger(value.revision) && typeof value.plan_approval_required === "boolean" && typeof value.verification_incomplete === "boolean" && typeof value.draft_pr_permission_disabled === "boolean";
}

function isSystemCapabilities(value: unknown): value is MissionSystemCapabilities {
  return isRecord(value) && value.api_reachable === true && typeof value.authentication_valid === "boolean" && typeof value.workspace_root_available === "boolean" && typeof value.mission_store_available === "boolean" && isString(value.contract_schema_version) && isString(value.viewer_expected_schema_version) && typeof value.schema_compatible === "boolean" && ["configured", "not_configured", "unavailable"].includes(String(value.provider_configuration)) && value.git_integration === "not_implemented" && value.github_integration === "not_implemented" && value.repository_inspection === "not_implemented" && value.agent_execution === "not_implemented" && value.draft_pr_delivery === "not_implemented";
}

function errorCode(value: string): MissionErrorCode {
  const knownCodes: readonly string[] = ["auth_required", "invalid_contract", "mission_not_found", "duplicate_mission", "stale_revision", "idempotency_conflict", "invalid_pagination", "plan_required", "plan_mission_mismatch", "plan_revision_conflict", "immutable_plan_conflict", "approved_plan_locked", "duplicate_approval_gate", "immutable_decision_conflict", "approval_subject_mismatch", "duplicate_evidence", "evidence_integrity_violation", "invalid_aggregate_contract", "invalid_transition", "terminal_state", "plan_approval_required", "verification_required", "draft_pr_permission_required", "draft_pr_approval_required", "scope_decision_required", "approval_subject_required", "resume_state_missing", "corrupt_mission_payload", "corrupt_transition_receipt", "unsupported_contract_schema", "unsupported_store_schema", "store_corruption", "store_unavailable"];
  return knownCodes.includes(value) ? value as MissionErrorCode : "unknown_server_error";
}

function parseError(value: unknown, status: number): MissionApiError {
  if (isRecord(value) && isString(value.code) && isString(value.message)) return new MissionApiError(errorCode(value.code), value.message, status);
  return new MissionApiError("unknown_server_error", "Mission API returned an unrecognized error response", status);
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export class MissionApiClient {
  private readonly baseUrl: string;
  private readonly fetcher: Fetcher;
  readonly authProvider: MissionAuthProvider;

  constructor(baseUrl = missionApiBaseUrl, fetcher: Fetcher = (input, init) => globalThis.fetch(input, init), authProvider: MissionAuthProvider = missionAuth) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.fetcher = fetcher;
    this.authProvider = authProvider;
  }

  private async request<T>(path: string, guard: Guard<T>, init: RequestInit = {}): Promise<T> {
    let authHeaders: Readonly<Record<string, string>>;
    try {
      authHeaders = await this.authProvider.getHeaders();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Authentication provider is unavailable";
      throw new MissionApiError("auth_unavailable", message, 0);
    }
    let response: Response;
    try {
      response = await this.fetcher(`${this.baseUrl}${path}`, { ...init, headers: { Accept: "application/json", "Content-Type": "application/json", ...authHeaders, ...init.headers } });
    } catch (error: unknown) {
      if (isAbortError(error)) throw new MissionApiError("aborted", "Mission API request was aborted", 0);
      const message = error instanceof Error ? error.message : "Mission API request failed";
      throw new MissionApiError("network_error", message, 0);
    }
    const body: unknown = await response.json().catch((error: unknown) => {
      if (isAbortError(error)) throw new MissionApiError("aborted", "Mission API request was aborted", response.status);
      return null;
    });
    if (!response.ok) throw parseError(body, response.status);
    if (!guard(body)) throw new MissionApiError("unknown_server_error", "Mission API returned an invalid response", 502);
    return body;
  }

  async checkSystem(): Promise<MissionSystemCapabilities> {
    return this.request("/v1/system/capabilities", isSystemCapabilities);
  }

  create(payload: MissionCreateRequest, signal?: AbortSignal): Promise<Mission> { return this.request("/v1/missions", isMission, { method: "POST", body: JSON.stringify(payload), signal }); }
  list(options: MissionListOptions = {}): Promise<MissionPage> { const query = new URLSearchParams({ limit: String(options.limit ?? 50), offset: String(options.offset ?? 0) }); return this.request(`/v1/missions?${query.toString()}`, isMissionPage, { signal: options.signal }); }
  get(missionId: string, signal?: AbortSignal): Promise<Mission> { return this.request(`/v1/missions/${encodeURIComponent(missionId)}`, isMission, { signal }); }
  transition(missionId: string, payload: MissionTransitionAPIRequest, signal?: AbortSignal): Promise<MissionTransitionResponse> { return this.request(`/v1/missions/${encodeURIComponent(missionId)}/transitions`, isTransitionResponse, { method: "POST", body: JSON.stringify(payload), signal }); }
  attachPlan(missionId: string, payload: PlanAttachRequest, signal?: AbortSignal): Promise<Mission> { return this.request(`/v1/missions/${encodeURIComponent(missionId)}/plan`, isMission, { method: "PUT", body: JSON.stringify(payload), signal }); }
  recordApproval(missionId: string, payload: ApprovalRecordRequest, signal?: AbortSignal): Promise<Mission> { return this.request(`/v1/missions/${encodeURIComponent(missionId)}/approvals`, isMission, { method: "POST", body: JSON.stringify(payload), signal }); }
  recordEvidence(missionId: string, payload: EvidenceRecordRequest, signal?: AbortSignal): Promise<Mission> { return this.request(`/v1/missions/${encodeURIComponent(missionId)}/evidence`, isMission, { method: "POST", body: JSON.stringify(payload), signal }); }
  recordVerification(missionId: string, payload: VerificationRecordRequest, signal?: AbortSignal): Promise<Mission> { return this.request(`/v1/missions/${encodeURIComponent(missionId)}/verification-gates`, isMission, { method: "PUT", body: JSON.stringify(payload), signal }); }
  history(missionId: string, options: MissionListOptions = {}): Promise<MissionTransitionPage> { const query = new URLSearchParams({ limit: String(options.limit ?? 50), offset: String(options.offset ?? 0) }); return this.request(`/v1/missions/${encodeURIComponent(missionId)}/transitions?${query.toString()}`, isTransitionPage, { signal: options.signal }); }
  capabilities(missionId: string, signal?: AbortSignal): Promise<MissionCapabilitiesResponse> { return this.request(`/v1/missions/${encodeURIComponent(missionId)}/capabilities`, isCapabilities, { signal }); }
}

export const missionApi = new MissionApiClient();
