"""Multi-Agent Committee Coordinator for LAS Autonomous Coding Pipeline.

Dynamically selects and orchestrates specialist committee personas based on
the coding task's blast radius, target files, and security sensitivity.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from .models import CodingTaskRequest

logger = logging.getLogger("CodingPipeline.CommitteeCoordinator")

# Sensitivity keywords that trigger strict security audit inclusion
SECURITY_TRIGGERS = {
    "auth", "security", "token", "secret", "credential", "crypto",
    "password", "sandbox", "policy_gate", "mtls", "cert", "audit_ledger",
    "vulnerability", "sanitize", "permission", "rbac", "signature"
}

# Architectural impact triggers
ARCHITECT_TRIGGERS = {
    "core", "models", "contracts", "interface", "protocol", "pipeline",
    "api.py", "database", "mesh", "p2p", "federation", "workflow"
}

# Frontend impact triggers
FRONTEND_EXTENSIONS = {".tsx", ".jsx", ".css", ".html"}
FRONTEND_PATHS = {"viewer/", "frontend/", "ui/", "components/"}


class CommitteeMemberSelection(BaseModel):
    """Selection record for an individual committee persona."""
    model_config = ConfigDict(extra="forbid")

    role: str
    display_name: str
    mandatory: bool
    selection_reason: str
    model_tier: str = "STANDARD_CODING"
    thinking_budget: int = 0


class CommitteeFormation(BaseModel):
    """Result of committee dynamic auto-selection."""
    model_config = ConfigDict(extra="forbid")

    task_id: str
    members: list[CommitteeMemberSelection] = Field(default_factory=list)
    risk_level: str = "NORMAL"  # "LOW", "NORMAL", "HIGH", "CRITICAL"
    enforced_security_audit: bool = False
    enforced_architect_review: bool = False
    max_tokens_per_member: int = 1500


class CommitteeCoordinator:
    """
    Evaluates task requirements and automatically assembles the optimal
    cross-functional review committee according to Protocol v3.8.0.
    """

    ROLE_DISPLAY_NAMES = {
        "architect": "Principal System Architect",
        "securityauditor": "Zero-Trust Security Auditor",
        "qaengineer": "Strict QA & Test Engineer",
        "backenddev": "Backend Infrastructure Engineer",
        "frontenddev": "Frontend UI/UX Engineer",
        "devopsengineer": "DevOps & CI/CD Engineer",
        "refactoringspecialist": "Refactoring & SLOC Specialist",
    }

    def evaluate_committee(self, request: CodingTaskRequest) -> CommitteeFormation:
        """
        Analyzes target files, requirement prompt, and repository context
        to dynamically assemble the reviewing committee.
        """
        members: list[CommitteeMemberSelection] = []
        selected_roles: set[str] = set()

        # Check explicit roles from request if specified
        explicit_roles = [r.lower() for r in getattr(request, "committee_roles", []) if r]

        # 1. Evaluate Security Sensitivity
        is_security_critical = self._is_security_critical(request)
        if is_security_critical:
            selected_roles.add("securityauditor")
            sec_budget = getattr(request, "thinking_budget", None) or 4096
            members.append(
                CommitteeMemberSelection(
                    role="securityauditor",
                    display_name=self.ROLE_DISPLAY_NAMES.get("securityauditor", "Security Auditor"),
                    mandatory=True,
                    selection_reason="Target files or prompt touch security, auth, crypto, or sandbox boundaries.",
                    model_tier="REASONING",
                    thinking_budget=sec_budget,
                )
            )

        # 2. Evaluate Architecture Impact
        is_architect_critical = self._is_architecture_critical(request)
        if is_architect_critical:
            selected_roles.add("architect")
            arch_budget = getattr(request, "thinking_budget", None) or 8192
            members.append(
                CommitteeMemberSelection(
                    role="architect",
                    display_name=self.ROLE_DISPLAY_NAMES.get("architect", "Principal System Architect"),
                    mandatory=True,
                    selection_reason="Cross-cutting architectural modifications, core models, or new subsystems detected.",
                    model_tier="REASONING",
                    thinking_budget=arch_budget,
                )
            )

        # 3. Evaluate Frontend Impact
        is_frontend_critical = self._is_frontend_critical(request)
        if is_frontend_critical and "frontenddev" not in selected_roles:
            selected_roles.add("frontenddev")
            members.append(
                CommitteeMemberSelection(
                    role="frontenddev",
                    display_name=self.ROLE_DISPLAY_NAMES.get("frontenddev", "Frontend UI/UX Engineer"),
                    mandatory=False,
                    selection_reason="UI components, TSX views, or styling assets in target scope.",
                )
            )

        # 4. Strictly enforce QA Engineer for all actionable code modifications
        if "qaengineer" not in selected_roles:
            selected_roles.add("qaengineer")
            members.append(
                CommitteeMemberSelection(
                    role="qaengineer",
                    display_name=self.ROLE_DISPLAY_NAMES.get("qaengineer", "Strict QA Engineer"),
                    mandatory=True,
                    selection_reason="Mandatory verification ladder design and edge case coverage analysis.",
                )
            )

        # 5. Merge any additional explicit roles requested by the caller
        for role in explicit_roles:
            if role not in selected_roles:
                selected_roles.add(role)
                members.append(
                    CommitteeMemberSelection(
                        role=role,
                        display_name=self.ROLE_DISPLAY_NAMES.get(role, role.capitalize()),
                        mandatory=False,
                        selection_reason="Explicitly requested by task specification.",
                    )
                )

        # Determine risk level
        risk_level = "NORMAL"
        if is_security_critical and is_architect_critical:
            risk_level = "CRITICAL"
        elif is_security_critical or is_architect_critical:
            risk_level = "HIGH"

        logger.info(
            "[Committee %s] Formed committee of %d members (Risk: %s, Roles: %s)",
            request.task_id,
            len(members),
            risk_level,
            [m.role for m in members],
        )

        return CommitteeFormation(
            task_id=request.task_id,
            members=members,
            risk_level=risk_level,
            enforced_security_audit=is_security_critical,
            enforced_architect_review=is_architect_critical,
            max_tokens_per_member=2000 if risk_level in ("HIGH", "CRITICAL") else 1200,
        )

    def _is_security_critical(self, request: CodingTaskRequest) -> bool:
        """Determines if the task touches sensitive security or sandbox domains."""
        prompt_lower = request.requirement_prompt.lower()
        for kw in SECURITY_TRIGGERS:
            if re.search(r"\b" + re.escape(kw) + r"\b", prompt_lower):
                return True

        for path in request.target_files + request.inspected_files:
            clean = path.replace("\\", "/").lower()
            for kw in SECURITY_TRIGGERS:
                if kw in clean:
                    return True

        return False

    def _is_architecture_critical(self, request: CodingTaskRequest) -> bool:
        """Determines if the task impacts core architectural contracts or boundaries."""
        if len(request.target_files) >= 3:
            return True

        prompt_lower = request.requirement_prompt.lower()
        for kw in ARCHITECT_TRIGGERS:
            if re.search(r"\b" + re.escape(kw) + r"\b", prompt_lower):
                return True

        for path in request.target_files:
            clean = path.replace("\\", "/").lower()
            for kw in ARCHITECT_TRIGGERS:
                if kw in clean:
                    return True

        return False

    def _is_frontend_critical(self, request: CodingTaskRequest) -> bool:
        """Determines if UI components or styling are touched."""
        for path in request.target_files:
            clean = path.replace("\\", "/").lower()
            if any(clean.endswith(ext) for ext in FRONTEND_EXTENSIONS):
                return True
            if any(p in clean for p in FRONTEND_PATHS):
                return True

        prompt_lower = request.requirement_prompt.lower()
        return any(w in prompt_lower for w in ("react", "ui", "viewer", "tailwind", "component", "button", "modal"))
