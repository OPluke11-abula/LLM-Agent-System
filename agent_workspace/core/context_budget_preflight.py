from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .token_counter import TokenCounter
from .token_efficient_profile import TokenEfficientProfile


class ContextBudgetReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_tokens: dict[str, int]
    estimated_total_tokens: int = Field(ge=0)
    estimated_reduction_tokens: int = Field(ge=0)
    estimated_reduction_ratio: float = Field(ge=0, le=1)
    memory_ref_count: int = Field(ge=0)
    code_graph_ref_count: int = Field(ge=0)
    handoff_recommended: bool
    report_only: Literal[True] = True
    trimming_applied: Literal[False] = False


def build_context_budget_preflight(
    *,
    system_prompt: str,
    messages: list[dict[str, Any]],
    memory_context: str,
    tool_schemas: list[dict[str, Any]],
    task_context: str,
    memory_refs: list[str],
    code_graph_refs: list[str],
    profile: TokenEfficientProfile | None = None,
    model_name: str | None = None,
) -> ContextBudgetReport:
    estimates = TokenCounter.estimate_components(
        system_prompt=system_prompt,
        messages=messages,
        memory_context=memory_context,
        tool_schemas=tool_schemas,
        model_name=model_name,
    )
    components = {name: int(value["count"]) for name, value in estimates.items()}
    components["task_context"] = TokenCounter.count_text(task_context, model_name).count
    components["memory_refs"] = TokenCounter.count_text("\n".join(memory_refs), model_name).count
    components["code_graph_refs"] = TokenCounter.count_text("\n".join(code_graph_refs), model_name).count
    total = sum(components.values())

    reduction = 0
    if profile and profile.max_tool_payload_tokens is not None:
        reduction += max(0, components["tool_schemas"] - profile.max_tool_payload_tokens)
    if profile and profile.bounded_memory_retrieval_limit is not None:
        excess_refs = max(0, len(memory_refs) - profile.bounded_memory_retrieval_limit)
        if excess_refs and memory_refs:
            average_memory_tokens = math.ceil(components["memory_context"] / len(memory_refs))
            reduction += average_memory_tokens * excess_refs
    reduction = min(total, reduction)
    handoff_threshold = profile.handoff_thresholds.context_token_count if profile and profile.handoff_thresholds else None

    return ContextBudgetReport(
        component_tokens=components,
        estimated_total_tokens=total,
        estimated_reduction_tokens=reduction,
        estimated_reduction_ratio=reduction / total if total else 0,
        memory_ref_count=len(memory_refs),
        code_graph_ref_count=len(code_graph_refs),
        handoff_recommended=handoff_threshold is not None and total >= handoff_threshold,
    )
