"""Executor vs. Advisor Structured Delegation Packet (Phase 105 Task C).

Decouples local execution (fast, local execution) from expensive reasoning (Advisor consultation).
Implements context budgeting, credential and path scrubbing, Zero-Risk manual copy-paste mode,
and automated MCP delegation with graceful degradation to local models.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Patterns for secret and credential scrubbing
SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # OpenAI & generic API keys
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED_OPENAI_KEY]"),
    # Google API keys (AIza...)
    (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"), "[REDACTED_GEMINI_KEY]"),
    # GitHub Personal Access Tokens
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    # Bearer tokens
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-\.]{20,}\b"), "Bearer [REDACTED_BEARER_TOKEN]"),
    # Specific assignments with quotes (e.g. DB_PASSWORD='...')
    (re.compile(r"(?i)\b([a-zA-Z0-9_]*(?:password|passwd|secret|api_key|token|private_key))\s*[:=]\s*['\"][^'\"]*['\"]"), r"\1='[REDACTED_SECRET]'"),
    # Unquoted assignments
    (re.compile(r"(?i)\b([a-zA-Z0-9_]*(?:password|passwd|secret|api_key|token|private_key))\s*[:=]\s*[^\s,;]{4,}"), r"\1=[REDACTED_SECRET]"),
)

# Host path patterns for scrubbing local machine specifics
PATH_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Windows absolute paths (e.g. C:\Users\... or D:\GitHub\...)
    (re.compile(r"[A-Za-z]:\\[^\s,;\"']+"), "[WORKSPACE]"),
    # POSIX home directory paths (e.g. /home/... or /Users/...)
    (re.compile(r"/(?:home|Users)/[^\s,;\"']+"), "[WORKSPACE]"),
)


class AdvisorMode(str, Enum):
    """Operation mode for external advisor consultation."""
    AUTOMATED_MCP = "AUTOMATED_MCP"        # Automated external MCP or bridge call
    ZERO_RISK_MANUAL = "ZERO_RISK_MANUAL"  # Copy-paste clipboard packet; 0 automated egress
    INTERNAL_FALLBACK = "INTERNAL_FALLBACK"# Degraded execution via internal standard model


class AdvisorTaskType(str, Enum):
    """Classification of tasks delegated to high-order Advisors."""
    ARCHITECTURE_DESIGN = "ARCHITECTURE_DESIGN"
    CODE_REVIEW = "CODE_REVIEW"
    REFACTORING_STRATEGY = "REFACTORING_STRATEGY"
    GENERAL_REASONING = "GENERAL_REASONING"


class SanitizedContextExtractor:
    """Extracts, redacts, and bounds context files and prompts under 2000 tokens."""

    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens

    def scrub_sensitive_data(self, text: str) -> str:
        """Redact API keys, passwords, bearer tokens, and local host directory paths."""
        scrubbed = text
        for pattern, replacement in SECRET_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        for pattern, replacement in PATH_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text string."""
        try:
            from agent_workspace.core.token_counter import TokenCounter
            return TokenCounter.count_text(text).count
        except Exception:
            return max(1, len(text) // 4)

    def extract_and_bound_files(
        self,
        files: Dict[str, str],
        max_total_tokens: int = 1500,
    ) -> Dict[str, str]:
        """
        Scrub and proportionally bound dictionary of files so total tokens stay strictly within budget.
        """
        scrubbed_files: Dict[str, str] = {}
        for path, content in files.items():
            scrubbed_files[path] = self.scrub_sensitive_data(content)

        if not scrubbed_files:
            return {}

        total_tokens = sum(self.estimate_tokens(c) for c in scrubbed_files.values())
        if total_tokens <= max_total_tokens:
            return scrubbed_files

        # Proportionally bound file sizes
        bounded_files: Dict[str, str] = {}
        per_file_budget = max(50, max_total_tokens // len(scrubbed_files))

        for path, content in scrubbed_files.items():
            file_tokens = self.estimate_tokens(content)
            if file_tokens <= per_file_budget:
                bounded_files[path] = content
            else:
                lines = content.splitlines()
                retained_lines: list[str] = []
                cur_text = ""
                truncation_notice = "# [TRUNCATED: remaining lines omitted for token containment]"
                notice_tokens = self.estimate_tokens(truncation_notice)
                target_budget = max(20, per_file_budget - notice_tokens)

                for line in lines:
                    candidate = (cur_text + "\n" + line).strip()
                    if self.estimate_tokens(candidate) > target_budget:
                        break
                    cur_text = candidate
                    retained_lines.append(line)

                while retained_lines and self.estimate_tokens("\n".join(retained_lines + [truncation_notice])) > per_file_budget:
                    retained_lines.pop()

                retained_lines.append(truncation_notice)
                bounded_files[path] = "\n".join(retained_lines)

        return bounded_files


class DelegationPacket(BaseModel):
    """Structured, token-bounded container for delegating cognitive work to Advisors."""

    model_config = ConfigDict(extra="ignore")

    packet_id: str = Field(default_factory=lambda: f"del_{uuid.uuid4().hex[:8]}")
    task_id: str
    task_type: AdvisorTaskType
    objective: str
    mode: AdvisorMode = AdvisorMode.AUTOMATED_MCP
    sanitized_files: Dict[str, str] = Field(default_factory=dict)
    constraints: List[str] = Field(default_factory=list)
    questions_for_advisor: List[str] = Field(default_factory=list)
    token_budget: int = Field(default=2000, le=2048)
    estimated_tokens: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_clipboard_markdown(self) -> str:
        """Render a formatted, desensitized Markdown payload suitable for Zero-Risk clipboard."""
        lines = [
            f"# LAS External Advisor Consultation Packet [{self.mode.value}]",
            f"- **Packet ID**: `{self.packet_id}`",
            f"- **Task ID**: `{self.task_id}`",
            f"- **Task Type**: `{self.task_type.value}`",
            f"- **Mode**: `{self.mode.value}` (Mode: {self.mode.value})",
            f"- **Estimated Tokens**: `{self.estimated_tokens}` / `{self.token_budget}`",
            "",
            "## 1. Primary Objective",
            self.objective,
            "",
        ]

        if self.constraints:
            lines.append("## 2. Constraints & Invariants")
            for c in self.constraints:
                lines.append(f"- {c}")
            lines.append("")

        if self.questions_for_advisor:
            lines.append("## 3. Specific Questions for Advisor")
            for q in self.questions_for_advisor:
                lines.append(f"- {q}")
            lines.append("")

        if self.sanitized_files:
            lines.append("## 4. Context Source Files (Sanitized)")
            for path, code in self.sanitized_files.items():
                lines.append(f"### File: `{path}`")
                lines.append("```")
                lines.append(code)
                lines.append("```")
                lines.append("")

        lines.extend([
            "---",
            "### Instructions for Advisor:",
            "Please analyze the objective, constraints, and questions. Respond with structured advice containing:",
            "1. Architectural recommendations",
            "2. Implementation plan step-by-step",
            "3. Code diffs / patch proposals if applicable",
        ])

        return "\n".join(lines)

    def to_mcp_arguments(self) -> Dict[str, Any]:
        """Convert into a dictionary suitable for external MCP tool execution."""
        return {
            "packet_id": self.packet_id,
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "objective": self.objective,
            "constraints": self.constraints,
            "questions": self.questions_for_advisor,
            "files": self.sanitized_files,
            "token_budget": self.token_budget,
        }


class AdvisorResponse(BaseModel):
    """Structured response from the external Advisor or degraded fallback."""

    model_config = ConfigDict(extra="ignore")

    packet_id: str
    success: bool
    advisor_model: str
    recommendations: List[str] = Field(default_factory=list)
    proposed_plan: Optional[str] = None
    code_patches: List[Dict[str, str]] = Field(default_factory=list)
    raw_content: str = ""
    fallback_triggered: bool = False
    error: Optional[str] = None
    duration_ms: int = 0


class DelegationManager:
    """Orchestrates creation, validation, and dispatch of DelegationPackets."""

    def __init__(self, extractor: Optional[SanitizedContextExtractor] = None):
        self.extractor = extractor or SanitizedContextExtractor()

    def create_packet(
        self,
        task_id: str,
        task_type: AdvisorTaskType,
        objective: str,
        files: Optional[Dict[str, str]] = None,
        constraints: Optional[List[str]] = None,
        questions: Optional[List[str]] = None,
        mode: AdvisorMode = AdvisorMode.AUTOMATED_MCP,
        max_tokens: int = 2000,
    ) -> DelegationPacket:
        """Create a token-contained, desensitized DelegationPacket."""
        files_dict = files or {}
        sanitized_files = self.extractor.extract_and_bound_files(files_dict, max_total_tokens=1500)
        
        # Scrub objective, constraints, and questions
        scrubbed_objective = self.extractor.scrub_sensitive_data(objective)
        scrubbed_constraints = [self.extractor.scrub_sensitive_data(c) for c in (constraints or [])]
        scrubbed_questions = [self.extractor.scrub_sensitive_data(q) for q in (questions or [])]

        total_text = scrubbed_objective + " ".join(scrubbed_constraints) + " ".join(scrubbed_questions) + "".join(sanitized_files.values())
        estimated_tokens = self.extractor.estimate_tokens(total_text)

        return DelegationPacket(
            task_id=task_id,
            task_type=task_type,
            objective=scrubbed_objective,
            mode=mode,
            sanitized_files=sanitized_files,
            constraints=scrubbed_constraints,
            questions_for_advisor=scrubbed_questions,
            token_budget=min(max_tokens, 2000),
            estimated_tokens=estimated_tokens,
        )

    def parse_advisor_response(
        self,
        packet_id: str,
        raw_output: Any,
        advisor_model: str = "advisor",
    ) -> AdvisorResponse:
        """Parse raw output from external Advisor into typed AdvisorResponse."""
        if isinstance(raw_output, dict):
            return AdvisorResponse(
                packet_id=packet_id,
                success=raw_output.get("status", "success") in ("success", "ok", True),
                advisor_model=raw_output.get("model", advisor_model),
                recommendations=raw_output.get("recommendations", []),
                proposed_plan=raw_output.get("proposed_plan"),
                code_patches=raw_output.get("code_patches", []),
                raw_content=json.dumps(raw_output),
                fallback_triggered=raw_output.get("fallback_triggered", False),
            )

        if isinstance(raw_output, str):
            cleaned = raw_output.strip()
            if cleaned.startswith("```json") and cleaned.endswith("```"):
                cleaned = cleaned[7:-3].strip()

            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    return self.parse_advisor_response(packet_id, parsed, advisor_model)
            except Exception:
                pass

            # Structured markdown check
            if any(marker in cleaned.lower() for marker in ("#", "recommend", "plan", "step 1", "architecture")):
                return AdvisorResponse(
                    packet_id=packet_id,
                    success=True,
                    advisor_model=advisor_model,
                    recommendations=[cleaned[:200]],
                    proposed_plan=cleaned,
                    raw_content=cleaned,
                    fallback_triggered=False,
                )

            # Unstructured or corrupted string
            return AdvisorResponse(
                packet_id=packet_id,
                success=False,
                advisor_model=advisor_model,
                error=f"External advisor returned unparseable or unstructured response: {cleaned[:100]}",
                raw_content=cleaned,
            )

        return AdvisorResponse(
            packet_id=packet_id,
            success=False,
            advisor_model=advisor_model,
            error=f"Unsupported advisor response type: {type(raw_output).__name__}",
            raw_content=str(raw_output),
        )

    def execute_delegation(
        self,
        packet: DelegationPacket,
        external_caller: Optional[Callable[[Dict[str, Any]], Any]] = None,
        fallback_caller: Optional[Callable[[str], Any]] = None,
        timeout_seconds: float = 30.0,
    ) -> AdvisorResponse:
        """
        Execute advisor delegation according to the packet mode.
        If external caller times out, raises error, or returns invalid structure,
        automatically falls back to the internal model caller.
        """
        start_time = time.perf_counter()

        # Mode: Zero Risk Manual Mode
        if packet.mode == AdvisorMode.ZERO_RISK_MANUAL:
            clipboard_md = packet.to_clipboard_markdown()
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return AdvisorResponse(
                packet_id=packet.packet_id,
                success=True,
                advisor_model="ZERO_RISK_MANUAL",
                recommendations=["Payload rendered for manual review and clipboard copying."],
                proposed_plan=clipboard_md,
                raw_content=clipboard_md,
                fallback_triggered=False,
                duration_ms=duration_ms,
            )

        # Mode: Automated MCP Call
        if external_caller is not None:
            try:
                raw_res = external_caller(packet.to_mcp_arguments())
                parsed = self.parse_advisor_response(
                    packet_id=packet.packet_id,
                    raw_output=raw_res,
                    advisor_model="external-advisor",
                )
                if parsed.success and (parsed.recommendations or parsed.proposed_plan):
                    parsed.duration_ms = int((time.perf_counter() - start_time) * 1000)
                    return parsed
                else:
                    logger.warning("[DelegationManager] External advisor returned invalid structure; triggering fallback")
            except Exception as exc:
                logger.warning("[DelegationManager] External advisor call failed (%s); triggering fallback", exc)

        # Graceful Fallback to Internal Model
        if fallback_caller is not None:
            logger.info("[DelegationManager] Invoking internal fallback caller for task '%s'", packet.task_id)
            try:
                fallback_prompt = packet.to_clipboard_markdown()
                fallback_output = fallback_caller(fallback_prompt)
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return AdvisorResponse(
                    packet_id=packet.packet_id,
                    success=True,
                    advisor_model="internal-fallback-model",
                    recommendations=["Plan synthesized via internal fallback model."],
                    proposed_plan=str(fallback_output),
                    raw_content=str(fallback_output),
                    fallback_triggered=True,
                    duration_ms=duration_ms,
                )
            except Exception as fb_exc:
                logger.error("[DelegationManager] Internal fallback also failed: %s", fb_exc)
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return AdvisorResponse(
                    packet_id=packet.packet_id,
                    success=False,
                    advisor_model="failed-fallback",
                    error=f"Both external advisor and fallback failed: {fb_exc}",
                    fallback_triggered=True,
                    duration_ms=duration_ms,
                )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return AdvisorResponse(
            packet_id=packet.packet_id,
            success=False,
            advisor_model="unreachable",
            error="No external caller or fallback caller available",
            fallback_triggered=False,
            duration_ms=duration_ms,
        )
