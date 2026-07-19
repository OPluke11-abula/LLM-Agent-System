import type {
  ApprovalRecordRequest,
  EvidenceRecordRequest,
  Mission,
  MissionCapabilitiesResponse,
  MissionCreateRequest,
  MissionErrorResponse,
  MissionPage,
  MissionTransitionAPIRequest,
  MissionTransitionPage,
  MissionTransitionResponse,
  PlanAttachRequest,
  VerificationRecordRequest,
} from "../generated/missionContracts";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
type MissionErrorCode = MissionErrorResponse["code"] | "network_error";
type Guard<T> = (value: unknown) => value is T;
type MissionListOptions = { readonly limit?: number; readonly offset?: number; readonly signal?: AbortSignal };

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

const missionApiBaseUrl = import.meta.env.VITE_LAS_API_URL ?? "http://127.0.0.1:8000";
const missionApiKey = import.meta.env.VITE_LAS_API_KEY;

function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null; }
function isString(value: unknown): value is string { return typeof value === "string"; }
function isInteger(value: unknown): value is number { return typeof value === "number" && Number.isInteger(value); }
function isMission(value: unknown): value is Mission { return isRecord(value) && isString(value.mission_id) && isString(value.requirement) && isString(value.repository_id) && isRecord(value.execution_policy); }
function isMissionPage(value: unknown): value is MissionPage { return isRecord(value) && Array.isArray(value.items) && value.items.every(isMission) && isInteger(value.limit) && isInteger(value.offset); }
function isTransitionResponse(value: unknown): value is MissionTransitionResponse { return isRecord(value) && isMission(value.mission) && isRecord(value.audit) && typeof value.replayed === "boolean"; }
function isTransitionPage(value: unknown): value is MissionTransitionPage { return isRecord(value) && Array.isArray(value.items) && value.items.every(isRecord) && isInteger(value.limit) && isInteger(value.offset); }
function isCapabilities(value: unknown): value is MissionCapabilitiesResponse { return isRecord(value) && isString(value.mission_id) && isString(value.current_state) && Array.isArray(value.allowed_events) && value.allowed_events.every(isString) && isInteger(value.revision) && typeof value.plan_approval_required === "boolean" && typeof value.verification_incomplete === "boolean" && typeof value.draft_pr_permission_disabled === "boolean"; }

function errorCode(value: string): MissionErrorCode {
  switch (value) {
    case "auth_required": case "invalid_contract": case "mission_not_found": case "duplicate_mission": case "stale_revision": case "idempotency_conflict": case "invalid_pagination": case "plan_required": case "plan_mission_mismatch": case "plan_revision_conflict": case "immutable_plan_conflict": case "approved_plan_locked": case "duplicate_approval_gate": case "immutable_decision_conflict": case "approval_subject_mismatch": case "duplicate_evidence": case "evidence_integrity_violation": case "invalid_aggregate_contract": case "invalid_transition": case "terminal_state": case "plan_approval_required": case "verification_required": case "draft_pr_permission_required": case "draft_pr_approval_required": case "scope_decision_required": case "approval_subject_required": case "resume_state_missing": case "corrupt_mission_payload": case "corrupt_transition_receipt": case "unsupported_contract_schema": case "unsupported_store_schema": case "store_corruption": case "store_unavailable":
      return value;
    default:
      return "network_error";
  }
}

function parseError(value: unknown, status: number): MissionApiError {
  if (isRecord(value) && isString(value.code) && isString(value.message)) return new MissionApiError(errorCode(value.code), value.message, status);
  return new MissionApiError("network_error", "Mission API returned an invalid error response", status);
}

export class MissionApiClient {
  private readonly baseUrl: string;
  private readonly fetcher: Fetcher;

  constructor(baseUrl = missionApiBaseUrl, fetcher: Fetcher = (input, init) => globalThis.fetch(input, init)) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.fetcher = fetcher;
  }

  private async request<T>(path: string, guard: Guard<T>, init: RequestInit = {}): Promise<T> {
    let response: Response;
    try {
      response = await this.fetcher(`${this.baseUrl}${path}`, { ...init, headers: { Accept: "application/json", "Content-Type": "application/json", ...(missionApiKey ? { "x-api-key": missionApiKey } : {}), ...init.headers } });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Mission API request failed";
      throw new MissionApiError("network_error", message, 0);
    }
    const body: unknown = await response.json().catch(() => null);
    if (!response.ok) throw parseError(body, response.status);
    if (!guard(body)) throw new MissionApiError("network_error", "Mission API returned an invalid response", 502);
    return body;
  }

  async checkConnection(signal?: AbortSignal): Promise<{ readonly reachable: boolean; readonly status: number }> {
    try {
      const response = await this.fetcher(`${this.baseUrl}/openapi.json`, { method: "HEAD", signal });
      return { reachable: response.status < 500, status: response.status };
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === "AbortError") throw error;
      return { reachable: false, status: 0 };
    }
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
