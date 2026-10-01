"""Runtime tool implementation for delegate_to_advisor (Phase 105 Task C).

Exposes the delegate_to_advisor tool to the agent runtime, allowing local executors
to generate a desensitized, token-budgeted (< 2000 tokens) DelegationPacket
and consult an external Advisor via MCP or Zero-Risk manual mode.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from agent_workspace.core.delegation_packet import (
    AdvisorMode,
    AdvisorTaskType,
    DelegationManager,
)

logger = logging.getLogger(__name__)


class DelegateToAdvisorArgs(BaseModel):
    task_id: str = Field(
        ...,
        description="Target task ID requesting advisor consultation.",
    )
    task_type: str = Field(
        default="ARCHITECTURE_DESIGN",
        description="Classification: ARCHITECTURE_DESIGN, CODE_REVIEW, REFACTORING_STRATEGY, GENERAL_REASONING.",
    )
    objective: str = Field(
        ...,
        description="Core technical objective or problem statement for the advisor.",
    )
    files: Dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary of relevant file paths to code content snippets.",
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="List of constraints, invariants, or non-negotiables.",
    )
    questions: List[str] = Field(
        default_factory=list,
        description="List of specific questions for the advisor to answer.",
    )
    mode: str = Field(
        default="AUTOMATED_MCP",
        description="Consultation mode: 'AUTOMATED_MCP' or 'ZERO_RISK_MANUAL'.",
    )


def delegate_to_advisor(args: DelegateToAdvisorArgs) -> str:
    """
    Delegate a high-order reasoning problem to an external Advisor via structured DelegationPacket.
    Scrubs secrets, enforces a 2000 token budget, and supports Zero-Risk manual copy-paste mode.
    """
    manager = DelegationManager()

    # Parse task type
    try:
        t_type = AdvisorTaskType(args.task_type.upper())
    except ValueError:
        t_type = AdvisorTaskType.ARCHITECTURE_DESIGN

    # Parse mode
    try:
        a_mode = AdvisorMode(args.mode.upper())
    except ValueError:
        a_mode = AdvisorMode.AUTOMATED_MCP

    packet = manager.create_packet(
        task_id=args.task_id,
        task_type=t_type,
        objective=args.objective,
        files=args.files,
        constraints=args.constraints,
        questions=args.questions,
        mode=a_mode,
    )

    if a_mode == AdvisorMode.ZERO_RISK_MANUAL:
        markdown_packet = packet.to_clipboard_markdown()
        logger.info("[delegate_to_advisor] Created Zero-Risk delegation packet: %s", packet.packet_id)
        return json.dumps({
            "status": "SUCCESS",
            "mode": "ZERO_RISK_MANUAL",
            "packet_id": packet.packet_id,
            "estimated_tokens": packet.estimated_tokens,
            "clipboard_payload": markdown_packet,
            "instruction": "Zero-Risk Mode: Copy the clipboard_payload and consult external Advisor manually.",
        }, ensure_ascii=False)

    # Automated delegation execution
    response = manager.execute_delegation(packet=packet)
    logger.info("[delegate_to_advisor] Advisor response for %s: success=%s", packet.packet_id, response.success)

    return json.dumps({
        "status": "SUCCESS" if response.success else "FAIL",
        "packet_id": response.packet_id,
        "advisor_model": response.advisor_model,
        "fallback_triggered": response.fallback_triggered,
        "recommendations": response.recommendations,
        "proposed_plan": response.proposed_plan,
        "code_patches": response.code_patches,
        "error": response.error,
    }, ensure_ascii=False)
