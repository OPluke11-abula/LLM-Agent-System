from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional

class ChatRequest(BaseModel):
    msg: str = Field(..., min_length=1)
    session: str = "default-session"
    allowed_tools: list[str] | None = None
    account_id: str | None = Field(None, description="Optional LLM account ID to route the call")


class ChatResponse(BaseModel):
    session: str
    response: str


class TaskRequest(ChatRequest):
    task_id: str | None = None


class TaskSubmitResponse(BaseModel):
    task_id: str
    session: str
    status: str


class ConfigUpdateRequest(BaseModel):
    provider: str | None = Field(None, description="e.g. google-genai, openai, anthropic, ollama")
    model: str | None = Field(None, description="e.g. gemini-2.5-flash")
    api_key: str | None = Field(None, description="API Key. Will be written to .env securely.")
    base_url: str | None = Field(None, description="Optional Base URL for Ollama or custom endpoints.")


class AccountCreateRequest(BaseModel):
    id: str = Field(..., description="Unique identifier for the account")
    provider: str = Field(..., description="e.g. google-genai, openai, anthropic, ollama")
    model: str = Field(..., description="e.g. gemini-2.5-flash")
    api_key: str = Field(..., description="API key literal, or env:VAR_NAME")
    base_url: str | None = Field("", description="Optional custom base URL")
    token_budget: int | None = Field(-1, description="Token limit, -1 for unlimited")
    tokens_used: int | None = Field(0, description="Tokens used")
    is_active: bool | None = Field(False, description="Set as active account")


class ActiveAccountSelectRequest(BaseModel):
    account_id: str = Field(..., description="The ID of the account to activate")


class PreferenceRequest(BaseModel):
    session: str = Field(..., description="The session ID to attach this preference to")
    preference: str = Field(..., description="The preference text")
    confidence: float = 1.0
    expires_at: str | None = None
    category: str = "general"


class AuthTokenRequest(BaseModel):
    tenant_id: str


class CrossCloudRevokeRequest(BaseModel):
    client_cert_sha: str | None = None
    cloud_name: str | None = None


class CrossCloudReinstateRequest(BaseModel):
    client_cert_sha: str


class CrewRegisterRequest(BaseModel):
    session_id: str
    node_id: str | None = None
    role: str
    parent_node_id: str | None = None
    status: str = "pending"
    description: str = ""
    input_parameters: dict | None = None
    security_restrictions: dict | None = None
    mock_directives: dict | None = None
    validation_assertions: list[str] | None = None


class BuilderAgentRequest(BaseModel):
    name: str
    role: str
    description: str
    guidelines: list[str]
    system_template: str
    template_variables: dict | None = None
    allowed_tools: list[str] | None = None
    telemetry_gateways: list[dict] | None = None


class BuilderTestRequest(BaseModel):
    agent_config: dict
    test_input: str
    session_id: str | None = None
    variables: dict | None = None


class BillingPolicyRequest(BaseModel):
    routing_policy: str | None = None
    credits: float | None = None
    max_budget: float | None = None


class SandboxExecuteRequest(BaseModel):
    code_content: str
    sandbox_type: str = "ast"
    globals_dict: dict[str, Any] | None = None
    locals_dict: dict[str, Any] | None = None


class AuditVerifyProofRequest(BaseModel):
    event_hash: str
    proof: list[dict[str, str]]
    root_hash: str


class ScaleRequest(BaseModel):
    role: str
    direction: str


class RotateKeyRequest(BaseModel):
    tenant_id: str


class UpdateSubRequest(BaseModel):
    tenant_id: str
    status: str


class HijackRequest(BaseModel):
    hijack_value: str


class ResumeSessionRequest(BaseModel):
    session_id: str


class ReplayCleanRequest(BaseModel):
    ttl_days: int | None = 7


class GovernanceVoteRequest(BaseModel):
    proposal_id: str
    role: str
    vote: str
    signature: str


class MemoryUpdateRequest(BaseModel):
    session_id: str
    key: str
    summary: str
    domain: str
    category: str
    confidence: float = 1.0
    expires_at: str | None = None
    citations: list[str] | None = None


class MemoryBatchMoveItem(BaseModel):
    session_id: str
    key: str


class MemoryBatchMoveRequest(BaseModel):
    items: list[MemoryBatchMoveItem]
    new_category: str
