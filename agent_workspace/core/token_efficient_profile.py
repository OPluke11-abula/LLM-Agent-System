from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


VerificationProfile = Literal["focused", "surface", "full", "release"]


class HandoffThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    history_message_count: int | None = Field(default=None, ge=0)
    changed_file_count: int | None = Field(default=None, ge=0)
    evidence_ref_count: int | None = Field(default=None, ge=0)
    context_token_count: int | None = Field(default=None, ge=0)


class TokenEfficientProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bounded_memory_retrieval_limit: int | None = Field(default=None, ge=0, le=50)
    prefer_code_graph_lookup: bool = True
    max_tool_payload_tokens: int | None = Field(default=None, ge=1)
    verification_profile: VerificationProfile | None = None
    handoff_thresholds: HandoffThresholds | None = None
