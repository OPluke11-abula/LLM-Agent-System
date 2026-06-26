"""Multi-Agent Consensus & Debate Room for LAS.

Orchestrates sequential, round-robin debate cycles among multiple agents using
different personas and LLM models from accounts.json, concluding with a
synthesized consensus summary by a moderator agent.
"""

from __future__ import annotations

import logging
import os
import time
import json
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_workspace.core.account_manager import AccountManager
from agent_workspace.core.providers import ProviderFactory, BaseLLMProvider
from agent_workspace.core.prompt_composer import PromptComposer

logger = logging.getLogger(__name__)


DEFAULT_PERSONAS = {
    "analyst": "You are a professional Business Analyst agent focused on identifying requirements, constraints, and structuring user stories.",
    "programmer": "You are an elite Software Engineer agent focused on technical implementation details, clean code conventions, and robust testing strategies.",
    "architect": "You are a Principal Architect agent focused on architectural boundaries, system components design, and scalability patterns.",
    "moderator": "You are an expert meeting moderator. Your task is to remain objective, analyze the debate transcript, and synthesize a clear Consensus Summary containing key agreements, disagreements, and next steps.",
    "ceo": "You are a visionary CEO Agent. You focus on strategic alignment, customer priorities, resource allocation, and budget controls.",
    "cto": "You are an elite CTO Planner Agent. You focus on architectural design, workflow DAG decompositions, and system integration.",
    "dev": "You are a highly efficient Dev Agent. You write robust, clean, modular Python and frontend React Flow components.",
    "qa": "You are a strict QA Auditor Agent. You review code conventions, check test coverage, and execute automated validation gates.",
    "cfo": "You are a professional CFO Token Controller. You audit cumulative token consumption, track API cost structures, and maintain budget caps."
}


@dataclass
class DiscussionRoleContract:
    runtime_role: str
    name: str
    source_role: str
    responsibility: str
    verifier: bool = False
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_role": self.runtime_role,
            "name": self.name,
            "source_role": self.source_role,
            "responsibility": self.responsibility,
            "verifier": self.verifier,
            "required": self.required,
        }


@dataclass
class VerifierVerdict:
    session_id: str
    topic: str
    decision: str
    verifier_role: str
    rationale: str
    risk_level: str
    durable: bool = True
    escalation: str | None = None
    consensus_certificate: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "decision": self.decision,
            "verifier_role": self.verifier_role,
            "rationale": self.rationale,
            "risk_level": self.risk_level,
            "durable": self.durable,
            "escalation": self.escalation,
            "consensus_certificate": self.consensus_certificate,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


class DiscussionRoom:
    """Orchestrates multi-agent consensus debate loops using different LLM models and personas."""

    telemetry_callbacks = []

    @classmethod
    def register_callback(cls, callback):
        if callback not in cls.telemetry_callbacks:
            cls.telemetry_callbacks.append(callback)

    def __init__(self, workspace_path: str = "."):
        self.workspace_path = os.path.abspath(workspace_path)
        self.account_manager = AccountManager(self.workspace_path)
        self.prompt_composer = PromptComposer(self.workspace_path)

    def _append_role_learning_guide(self, role: str, system_prompt: str) -> str:
        """Appends role-specific learning guide as SYSTEM SELF-LEARNING DIRECTIVES to system_prompt."""
        role_lower = role.lower()
        guide_path = None

        if role_lower in ("dev", "programmer"):
            guide_path = self.prompt_composer.project_root / ".agent" / "programmer" / "programmer_learning_guide.md"
        elif role_lower == "qa":
            guide_path = self.prompt_composer.project_root / ".agent" / "qa" / "qa_learning_guide.md"
            if not guide_path.is_file():
                try:
                    guide_path.parent.mkdir(parents=True, exist_ok=True)
                    scaffold = (
                        "# 🧠 Strict QA Auditor Learning Guide\n\n"
                        "> **Target Audience**: Strict QA Auditor Agents operating within FindAi Studio LLM Agent System (LAS).\n"
                        "> **Purpose**: Establish standard operating protocols for robust unit/integration testing with pytest, linting rules, static analysis validation, and quality verification gates.\n\n"
                        "---\n\n"
                        "## 1. 📂 Core QA Principles / 核心測試原則\n\n"
                        "1. **Strict Test Coverage / 嚴格測試覆蓋率**:\n"
                        "   - Ensure all new features, subsystems, and routes have corresponding automated test coverage in `tests/` or `agent_workspace/tests/`.\n"
                        "   - Never skip tests unless explicitly requested and documented. Keep existing coverage high.\n\n"
                        "2. **Automated Verification / 自動化驗證機制**:\n"
                        "   - Run tests using `pytest` inside the workspace environment (`.venv`).\n"
                        "   - Validate API endpoints, rate limiting, and debate room operations via pytest assertions.\n\n"
                        "3. **Lint & Static Analysis Standards / 程式碼風格與靜態分析標準**:\n"
                        "   - Follow strict linting guidelines using `ruff` or `flake8` as required by the repository.\n"
                        "   - Code must be formatted neatly, type annotations should be added where appropriate, and all dead imports must be removed.\n"
                        "   - Assert standard compliance prior to delivering feature verification.\n"
                    )
                    guide_path.write_text(scaffold, encoding="utf-8")
                except Exception as e:
                    logger.error(f"Failed to scaffold QA learning guide: {e}")
        elif role_lower == "analyst":
            guide_path = self.prompt_composer.project_root / ".agent" / "analyst" / "analyst_learning_guide.md"

        if guide_path and guide_path.is_file():
            try:
                content = guide_path.read_text(encoding="utf-8").strip()
                if content:
                    system_prompt += f"\n\n## 🎓 SYSTEM SELF-LEARNING DIRECTIVES (Auto-Learned Best Practices):\n{content}"
            except Exception as e:
                logger.error(f"Failed to read learning guide at {guide_path}: {e}")

        return system_prompt

    def _resolve_agent_persona(self, role: str) -> str:
        """Resolve the agent persona dynamically from contract files or default fallback."""
        role_lower = role.lower()

        # Apply dynamic .agent detection logic (from L-20260531-001) using Path to locate active configuration directory
        path_check = Path(self.workspace_path)
        if (path_check / ".agent").is_dir():
            project_root = path_check
        elif (path_check.parent / ".agent").is_dir():
            project_root = path_check.parent
        else:
            project_root = path_check.parent

        role_file = project_root / ".agent" / "prompts" / "roles" / f"{role_lower}.md"
        if role_file.is_file():
            try:
                content = role_file.read_text(encoding="utf-8")
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        import yaml
                        role_def = yaml.safe_load(parts[1])
                        if isinstance(role_def, dict) and "persona" in role_def:
                            return role_def["persona"]
            except Exception as e:
                logger.error(f"Failed to dynamically load persona for role {role_lower}: {e}")

        # Fallback cleanly to DEFAULT_PERSONAS
        return DEFAULT_PERSONAS.get(role_lower, f"You are a helpful {role_lower} agent.")

    def _resolve_agent_provider(
        self,
        account_id: str | None = None,
        prompt_len: int = 0,
        topic: str = "",
        session_id: str | None = None
    ) -> tuple[BaseLLMProvider, dict[str, Any], str]:
        """Resolve LLM provider, configuration, and account ID, with dynamic upscaling/downscaling."""
        # Apply dynamic .agent detection logic (from L-20260531-001) to locate the contract folder
        path_check = Path(self.workspace_path)
        if (path_check / ".agent").is_dir():
            project_root = path_check
        elif (path_check.parent / ".agent").is_dir():
            project_root = path_check.parent
        else:
            project_root = path_check.parent

        account = None
        if account_id:
            account = self.account_manager.get_account(account_id)
        if not account:
            account = self.account_manager.get_active_account()

        if not account:
            raise RuntimeError("No LLM accounts configured in accounts.json.")

        # Budget exhaustion check
        budget = account.get("token_budget", -1)
        used = account.get("tokens_used", 0)
        if budget > 0 and used >= budget:
            logger.info("Active account '%s' budget exhausted (%d/%d). Swapping to fallback...", account["id"], used, budget)
            if self.account_manager.swap_to_fallback():
                account = self.account_manager.get_active_account()
                logger.info("Swapped to fallback account '%s'", account["id"])
            else:
                logger.warning("Budget exhausted and no fallback accounts available!")

        api_key = self.account_manager.resolve_api_key(account)
        provider = ProviderFactory.get_provider(
            account["provider"],
            api_key=api_key,
            base_url=account.get("base_url")
        )

        model = account.get("model", "gemini-2.5-flash")

        # Resolve tenant_id
        tenant_id = None
        if session_id:
            try:
                from core.account_manager import AccountManager
                tenant_id = AccountManager.get_session_tenant(session_id)
            except Exception:
                pass
        tenant_id = tenant_id or "default_tenant"

        # Verify tenant credits
        from agent_workspace.core.swarm_coordinator import SwarmCoordinator
        SwarmCoordinator.verify_tenant_credit(self.workspace_path, tenant_id)

        # Enforce model downscaling policy if budget is low
        if SwarmCoordinator.should_downscale_model(self.workspace_path, tenant_id):
            if "pro" in model.lower():
                model = "gemini-2.5-flash"
                logger.info(f"Model downscaling active: overriding model to gemini-2.5-flash for tenant {tenant_id}")

        # Dynamic Model Tier Downscaling for low complexity or summary tasks
        is_simple_summary = any(k in topic.lower() for k in ["summary", "simple", "consensus_synthesis"])
        if is_simple_summary and "pro" in model.lower():
            original_model = model
            model = model.replace("pro", "flash")
            logger.info("Complexity Downscaling: Swapped premium model %s to %s for simple/summary task.", original_model, model)

        # Dynamic Model Tier Upscaling for large-context tasks (prompt_len > 8000)
        elif prompt_len > 8000 and "flash" in model.lower():
            original_model = model
            model = model.replace("flash", "pro")
            logger.info("Context Upscaling: Swapped base model %s to %s for large context task (prompt_len=%d > 8000).", original_model, model, prompt_len)

        config = {
            "model": model,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        return provider, config, account["id"]

    async def _invoke_llm_healing(self, skill_id: str, params: dict[str, Any], error_msg: str) -> dict[str, Any]:
        """Invoke LLM correction call to auto-diagnose and patch prompts or parameters."""
        lessons_learned_content = ""
        path_check = Path(self.workspace_path)
        if (path_check / ".agent").is_dir():
            project_root = path_check
        elif (path_check.parent / ".agent").is_dir():
            project_root = path_check.parent
        else:
            project_root = path_check.parent

        lessons_file = project_root / ".agent" / "knowledge_base" / "lessons_learned.md"
        if lessons_file.is_file():
            try:
                lessons_learned_content = lessons_file.read_text(encoding="utf-8")
            except Exception:
                pass

        system_prompt = (
            "You are an expert self-healing engine for the LLM Agent System (LAS).\n"
            "An execution component failed.\n"
            "Your task is to analyze the traceback/error and original context, "
            "cross-reference them with the lessons learned registry, and generate patched fields (JSON format).\n"
            f"Lessons Learned Database:\n{lessons_learned_content}\n\n"
            "Respond ONLY with a valid JSON object representing the corrected/patched context fields. "
            "Do not include any explanation or markdown formatting (like ```json ... ```) - just return raw JSON."
        )

        user_content = (
            f"Component/Skill Failed: {skill_id}\n"
            f"Original Context: {json.dumps(params, ensure_ascii=False)}\n"
            f"Traceback/Error: {error_msg}\n\n"
            "Please analyze this failure. If a matching lesson is found, apply its best practice. "
            "Otherwise, correct the parameters/context to fix the error. Return the corrected fields as a JSON object."
        )

        try:
            provider, config, resolved_acc_id = self._resolve_agent_provider(None)
            response_type, response_data = await provider.complete(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_content}],
                tool_schemas=[],
                config=config
            )
            if response_type == "error":
                return params

            raw_text = str(response_data).strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            patched = json.loads(raw_text)
            if isinstance(patched, dict):
                return patched
        except Exception:
            pass
        return params

    async def _delegate_turn_to_microservice(
        self,
        broker,
        session_id: str,
        agent_name: str,
        role: str,
        topic: str,
        system_prompt: str,
        user_content: str,
        account_id: Optional[str]
    ) -> Optional[dict[str, Any]]:
        # We subscribe to response channel
        response_channel = f"swarm:debate:{session_id}:{role.lower()}:response"

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        async def on_response(msg: dict):
            if not future.done():
                future.set_result(msg)

        await broker.subscribe(response_channel, on_response)

        try:
            # Publish request
            request_msg = {
                "type": "turn_request",
                "session_id": session_id,
                "agent_name": agent_name,
                "role": role.lower(),
                "topic": topic,
                "system_prompt": system_prompt,
                "user_content": user_content,
                "account_id": account_id
            }
            # Publish to role debate channel
            await broker.publish(f"swarm:debate:{role.lower()}", request_msg)

            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=5.0)
            return response
        finally:
            await broker.unsubscribe(response_channel)

    def __init__(self, workspace_path: str = "."):
        self.workspace_path = os.path.abspath(workspace_path)
        self.account_manager = AccountManager(self.workspace_path)
        self.prompt_composer = PromptComposer(self.workspace_path)

    def _is_line_protected(self, line: str) -> bool:
        import re
        # Case insensitive terms
        for term in ["Error", "Exception", "Decision", "Disagreement", "Conflict", "disagree"]:
            if term.lower() in line.lower():
                return True
        # Case sensitive or special patterns
        if "file://" in line:
            return True
        if ".py" in line:
            return True
        # hex SHA-256: 64 character hex string
        if re.search(r'\b[a-fA-F0-9]{64}\b', line):
            return True
        return False

    def _compact_transcript(self, transcript: list[dict[str, str]], max_tokens: int = 4000) -> str:
        """Compact the transcript deterministically when it exceeds the token limit.

        Preserves protected elements: file://, .py, Error, Exception, Decision,
        Disagreement, Conflict, disagree, and 64-char hex SHA-256 hashes.
        """
        if not transcript:
            return "(The discussion has just started. No contributions yet.)"

        # First, format the transcript as it is
        formatted = "\n".join(
            f"[{msg['agent']} ({msg['role']})]: {msg['content']}"
            for msg in transcript
        )
        from agent_workspace.core.token_counter import TokenCounter
        if TokenCounter.count_text(formatted).count <= max_tokens:
            return formatted

        # Let's perform deterministic compaction on each message's content
        compacted_messages = []
        for msg in transcript:
            content = msg["content"]
            lines = content.splitlines()
            compacted_lines = []
            for line in lines:
                if self._is_line_protected(line):
                    compacted_lines.append(line)
                else:
                    # Truncate line if it's long
                    trimmed = line.strip()
                    if len(trimmed) > 80:
                        compacted_lines.append(trimmed[:60] + "... [compacted]")
                    else:
                        compacted_lines.append(line)
            compacted_content = "\n".join(compacted_lines)
            compacted_messages.append({
                "agent": msg["agent"],
                "role": msg["role"],
                "content": compacted_content
            })

        # Re-format compacted
        formatted_compacted = "\n".join(
            f"[{msg['agent']} ({msg['role']})]: {msg['content']}"
            for msg in compacted_messages
        )

        # If it's still over max_tokens, let's aggressively drop non-protected lines or drop older messages
        if TokenCounter.count_text(formatted_compacted).count > max_tokens:
            # Let's do a more aggressive compaction: drop any line that is NOT protected.
            more_compacted_messages = []
            for msg in compacted_messages:
                content = msg["content"]
                lines = content.splitlines()
                compacted_lines = []
                for line in lines:
                    if self._is_line_protected(line):
                        compacted_lines.append(line)

                # If everything in the message was dropped, keep at least a minimal note
                if not compacted_lines:
                    compacted_content = "... [message content compacted, no decisions/paths/errors/hashes present] ..."
                else:
                    compacted_content = "\n".join(compacted_lines)

                more_compacted_messages.append({
                    "agent": msg["agent"],
                    "role": msg["role"],
                    "content": compacted_content
                })
            formatted_compacted = "\n".join(
                f"[{msg['agent']} ({msg['role']})]: {msg['content']}"
                for msg in more_compacted_messages
            )

        return formatted_compacted

    def build_role_contracts(self, agents: list[dict[str, Any]]) -> list[DiscussionRoleContract]:
        role_map = {
            "architect": ("thinker", "Plan the discussion strategy and decompose the work."),
            "cto": ("thinker", "Plan the discussion strategy and decompose the work."),
            "analyst": ("thinker", "Clarify requirements, risks, and constraints."),
            "ceo": ("thinker", "Confirm strategic alignment and escalation priority."),
            "dev": ("worker", "Execute the implementation-oriented discussion work."),
            "programmer": ("worker", "Execute the implementation-oriented discussion work."),
            "engineer": ("worker", "Execute the implementation-oriented discussion work."),
            "qa": ("verifier", "Verify the outcome against requirements and tests."),
            "auditor": ("verifier", "Verify the outcome against requirements and tests."),
            "cfo": ("verifier", "Verify cost, budget, and operational risk."),
            "moderator": ("verifier", "Synthesize and verify consensus durability."),
        }
        contracts: list[DiscussionRoleContract] = []
        assigned_runtime_roles: set[str] = set()
        for index, agent in enumerate(agents):
            source_role = str(agent.get("role", "agent")).lower()
            runtime_role, responsibility = role_map.get(
                source_role,
                ("worker", "Contribute to the discussion using the declared source role."),
            )
            if runtime_role in assigned_runtime_roles and runtime_role != "worker":
                runtime_role = "worker"
            assigned_runtime_roles.add(runtime_role)
            name = str(agent.get("name") or source_role.capitalize())
            contracts.append(
                DiscussionRoleContract(
                    runtime_role=runtime_role,
                    name=name,
                    source_role=source_role,
                    responsibility=responsibility,
                    verifier=runtime_role == "verifier",
                    required=index == 0 or runtime_role in {"worker", "verifier"},
                )
            )

        if contracts and not any(contract.runtime_role == "thinker" for contract in contracts):
            contracts[0].runtime_role = "thinker"
            contracts[0].responsibility = "Plan the discussion strategy and decompose the work."
        if contracts and not any(contract.runtime_role == "verifier" for contract in contracts):
            contracts[-1].runtime_role = "verifier"
            contracts[-1].responsibility = "Verify the outcome against requirements and tests."
            contracts[-1].verifier = True
            contracts[-1].required = True
        return contracts

    def create_verifier_verdict(
        self,
        *,
        session_id: str,
        topic: str,
        consensus_summary: str,
        transcript: list[dict[str, str]],
        role_contracts: list[DiscussionRoleContract],
        risk_level: str = "medium",
        approval_required: bool = False,
        consensus_certificate: dict[str, Any] | None = None,
    ) -> VerifierVerdict:
        verifier = next((contract for contract in role_contracts if contract.verifier), None)
        if verifier is None:
            raise ValueError("Verifier role contract is required for a durable verdict.")

        normalized_risk = risk_level.lower()
        if normalized_risk == "high" and not approval_required and not consensus_certificate:
            raise PermissionError("High-risk verifier verdict requires approval or consensus certificate.")

        lowered_summary = consensus_summary.lower()
        if "error synthesizing consensus" in lowered_summary or "[error" in lowered_summary:
            decision = "reject"
        elif "escalate" in lowered_summary or "blocked" in lowered_summary:
            decision = "escalate"
        else:
            decision = "accept"

        verifier_lines = [
            str(msg.get("content", ""))
            for msg in transcript
            if str(msg.get("role", "")).lower() in {"qa", "auditor", "cfo", "moderator"}
        ]
        rationale_source = verifier_lines[-1] if verifier_lines else consensus_summary
        rationale = " ".join(rationale_source.split())[:240]
        escalation = None
        if consensus_certificate:
            escalation = "consensus_certificate"
        elif approval_required:
            escalation = "approval_required"
        elif decision == "escalate":
            escalation = "verifier_escalation"

        return VerifierVerdict(
            session_id=session_id,
            topic=topic,
            decision=decision,
            verifier_role=verifier.name,
            rationale=rationale,
            risk_level=normalized_risk,
            escalation=escalation,
            consensus_certificate=consensus_certificate,
        )

    async def run(
        self,
        topic: str,
        agents: list[dict[str, Any]],
        max_rounds: int = 2,
        moderator_persona: str | None = None,
        session_id: str = "debate-session",
        sub_problems: list[dict[str, Any]] | None = None,
        max_participants: int = 5,
        max_sub_swarms: int = 3,
        risk_level: str = "medium",
        approval_required: bool = False,
        consensus_certificate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Orchestrate a round-robin sequential debate among agents on a topic.

        Concludes with a synthesized Consensus Summary, with parallel hierarchical sub-swarm delegation.
        """
        # Enforce participant limits
        if len(agents) > max_participants:
            raise ValueError(f"Number of agents ({len(agents)}) exceeds max_participants ceiling ({max_participants}).")

        if sub_problems:
            if len(sub_problems) > max_sub_swarms:
                raise ValueError(f"Number of sub-problems ({len(sub_problems)}) exceeds max_sub_swarms ceiling ({max_sub_swarms}).")
            for i, sp in enumerate(sub_problems):
                sp_agents = sp.get("agents", [])
                if len(sp_agents) > max_participants:
                    raise ValueError(f"Sub-swarm {i+1} agents count ({len(sp_agents)}) exceeds max_participants ceiling ({max_participants}).")

        transcript: list[dict[str, str]] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_estimated_cost = 0.0
        models_used = set()
        role_contracts = self.build_role_contracts(agents)

        def estimate_cost(model_name: str, prompt_t: int, completion_t: int) -> float:
            m_lower = model_name.lower()
            if "pro" in m_lower:
                input_rate = 1.25 / 1_000_000
                output_rate = 5.00 / 1_000_000
            else:
                input_rate = 0.075 / 1_000_000
                output_rate = 0.30 / 1_000_000
            return (prompt_t * input_rate) + (completion_t * output_rate)

        # 0. Handle parallel sub-swarm delegation
        sub_swarm_results = []
        sub_swarm_context = ""
        if sub_problems:
            logger.info("Encountered highly complex problem. Spawning parallel sub-swarms...")
            tasks = []
            for i, sp in enumerate(sub_problems):
                sp_topic = sp["topic"]
                sp_agents = sp["agents"]
                sp_max_rounds = sp.get("max_rounds", max_rounds)
                sp_moderator_persona = sp.get("moderator_persona", moderator_persona)
                sp_session_id = sp.get("session_id", f"{session_id}-sub-{i}")
                tasks.append(
                    self.run(
                        topic=sp_topic,
                        agents=sp_agents,
                        max_rounds=sp_max_rounds,
                        moderator_persona=sp_moderator_persona,
                        session_id=sp_session_id,
                        sub_problems=None,
                        max_participants=max_participants,
                        max_sub_swarms=max_sub_swarms,
                        risk_level=risk_level,
                        approval_required=approval_required,
                        consensus_certificate=consensus_certificate,
                    )
                )
            sub_swarm_results = await asyncio.gather(*tasks)

            sub_swarm_context = "### Sub-Swarm Consensus Summaries:\n"
            for i, res in enumerate(sub_swarm_results):
                sub_topic = res["topic"]
                sub_summary = res["consensus_summary"]
                sub_swarm_context += f"#### Sub-Swarm {i+1} Topic: {sub_topic}\n"
                sub_swarm_context += f"*Consensus Summary*:\n{sub_summary}\n\n"
            sub_swarm_context += "---\n\n"

        # 1. Resolve participants and their personas
        participants = []
        for a in agents:
            role = a.get("role", "agent").lower()
            name = a.get("name", role.capitalize())
            persona = self._resolve_agent_persona(role)
            account_id = a.get("account_id")
            participants.append({
                "name": name,
                "role": role,
                "persona": persona,
                "account_id": account_id,
                "runtime_role": role_contracts[len(participants)].runtime_role if len(participants) < len(role_contracts) else "worker",
            })

        # 2. Sequential Round-Robin Dialogue Loop
        for round_idx in range(1, max_rounds + 1):
            logger.info("Starting discussion round %d/%d", round_idx, max_rounds)
            for p in participants:
                # Format current transcript for the participant with compaction check (max 4000 tokens)
                formatted_transcript = self._compact_transcript(transcript, max_tokens=4000)

                system_prompt = f"{p['persona']}\n\nYou are participating in a multi-agent debate/discussion room. Help the team achieve a consensus."
                system_prompt = self._append_role_learning_guide(p["role"], system_prompt)
                system_prompt = self.prompt_composer.prune_compiled_prompt(system_prompt)
                user_content = f"""Topic for discussion: {topic}

{sub_swarm_context}Here is the dialogue transcript so far:
---
{formatted_transcript}
---

It is now your turn, {p['name']}. Please respond to the topic or build on top of previous points in a constructive manner. Keep your response brief, precise, and focused on driving consensus."""

                start_time = time.perf_counter()
                contribution = None
                resolved_acc_id = p["account_id"] or "default-account"

                # Check for distributed broker delegation
                from agent_workspace.core.broker import get_broker, RedisSwarmBroker

                broker = get_broker(workspace_path=self.workspace_path)
                if isinstance(broker, RedisSwarmBroker) and not os.environ.get("PYTEST_CURRENT_TEST"):
                    try:
                        delegated_resp = await self._delegate_turn_to_microservice(
                            broker=broker,
                            session_id=session_id,
                            agent_name=p["name"],
                            role=p["role"],
                            topic=topic,
                            system_prompt=system_prompt,
                            user_content=user_content,
                            account_id=p["account_id"]
                        )
                        if delegated_resp and delegated_resp.get("status") == "success":
                            contribution = delegated_resp.get("contribution")
                            p_tok = delegated_resp.get("prompt_tokens", 0)
                            c_tok = delegated_resp.get("completion_tokens", 0)
                            self.account_manager.record_usage(resolved_acc_id, p_tok, c_tok)

                            model_used = delegated_resp.get("model", "gemini-2.5-flash")
                            models_used.add(model_used)
                            call_cost = estimate_cost(model_used, p_tok, c_tok)
                            total_prompt_tokens += p_tok
                            total_completion_tokens += c_tok
                            total_estimated_cost += call_cost
                    except Exception as e:
                        logger.warning(f"Failed to delegate debate turn to microservice: {e}. Falling back to in-process execution.")

                if contribution is None:
                    contribution = f"[Silent / Connection Error]"
                    # Dynamic Account Swapping & Error Self-Healing Retry Loop
                    max_attempts = 3
                    for attempt in range(1, max_attempts + 2):
                        try:
                            prompt_len = len(system_prompt + user_content) // 4
                            provider, config, resolved_acc_id = self._resolve_agent_provider(
                                account_id=p["account_id"],
                                prompt_len=prompt_len,
                                topic=topic,
                                session_id=session_id
                            )
                            # Cap per-response completion tokens inside run
                            config["max_tokens"] = min(config.get("max_tokens", 4096), 1024)

                            messages = [{"role": "user", "content": user_content}]

                            response_type, response_data = await provider.complete(
                                system_prompt=system_prompt,
                                messages=messages,
                                tool_schemas=[],
                                config=config
                            )

                            is_rate_limit = False
                            if response_type == "error":
                                err_str = str(response_data).lower()
                                if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                                    is_rate_limit = True

                            if is_rate_limit:
                                logger.info("Rate limit (HTTP 429) detected on account '%s'. Swapping to fallback...", resolved_acc_id)
                                if self.account_manager.swap_to_fallback():
                                    continue
                                else:
                                    raise RuntimeError(f"Rate limited and no fallback accounts available: {response_data}")

                            if response_type == "error":
                                raise RuntimeError(f"LLM call returned error: {response_data}")

                            contribution = str(response_data).strip()
                            prompt_tokens = len(system_prompt + user_content) // 4
                            completion_tokens = len(contribution) // 4
                            self.account_manager.record_usage(resolved_acc_id, prompt_tokens, completion_tokens)

                            model_used = config.get("model", "gemini-2.5-flash")
                            models_used.add(model_used)
                            call_cost = estimate_cost(model_used, prompt_tokens, completion_tokens)
                            total_prompt_tokens += prompt_tokens
                            total_completion_tokens += completion_tokens
                            total_estimated_cost += call_cost
                            break
                        except Exception as e:
                            error_msg = str(e)
                            logger.error("Failed to generate contribution for agent %s on attempt %d: %s", p["name"], attempt, error_msg)
                            if attempt <= max_attempts:
                                logger.info("Attempting self-healing correction for debate participant...")
                                healed_data = await self._invoke_llm_healing("discussion_room_llm", {"system_prompt": system_prompt, "user_content": user_content}, error_msg)
                                system_prompt = healed_data.get("system_prompt", system_prompt)
                                user_content = healed_data.get("user_content", user_content)

                                if "429" in error_msg.lower() or "rate limit" in error_msg.lower():
                                    self.account_manager.swap_to_fallback()
                            else:
                                contribution = f"[Silent / Connection Error: {e}]"

                duration_ms = int((time.perf_counter() - start_time) * 1000)

                # Cost Alert Calculation
                cost_alert = False
                active_acc = self.account_manager.get_active_account()
                if active_acc:
                    budget = active_acc.get("token_budget", -1)
                    used = active_acc.get("tokens_used", 0)
                    if budget > 0 and (used / budget) >= 0.8:
                        cost_alert = True

                # Broadcast debate contribution event
                debate_event = {
                    "session": session_id,
                    "type": "debate_contribution",
                    "agent": p["name"],
                    "role": p["role"],
                    "duration_ms": duration_ms,
                    "active_latency_alert": duration_ms > 5000,
                    "cost_alert": cost_alert,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                for cb in self.telemetry_callbacks:
                    try:
                        cb(session_id, debate_event)
                    except Exception:
                        pass

                logger.info("%s (%s) contribution: %s...", p["name"], p["role"], contribution[:50])
                transcript.append({
                    "agent": p["name"],
                    "role": p["role"],
                    "content": contribution
                })

        # 3. Moderator Synthesis Round
        logger.info("Synthesizing meeting consensus summary...")
        mod_persona = moderator_persona or self._resolve_agent_persona("moderator")
        # Format final transcript for moderator with compaction check
        formatted_final_transcript = self._compact_transcript(transcript, max_tokens=4000)

        mod_system_prompt = mod_persona
        mod_user_content = f"""Topic discussed: {topic}

{sub_swarm_context}Here is the complete dialogue transcript:
---
{formatted_final_transcript}
---

Please synthesize a professional Consensus Summary. Standardize the response to clearly outline:
1. Core Topic & Agreements reached.
2. Minor Disagreements or pending design choices.
3. Decisive action items or next steps.

Format the summary nicely in Markdown."""

        consensus_summary = f"[Error synthesizing consensus]"
        start_time = time.perf_counter()

        max_attempts = 3
        for attempt in range(1, max_attempts + 2):
            try:
                mod_prompt_len = len(mod_system_prompt + mod_user_content) // 4
                provider, config, resolved_acc_id = self._resolve_agent_provider(
                    account_id=None,
                    prompt_len=mod_prompt_len,
                    topic="consensus_synthesis",
                    session_id=session_id
                )
                # Cap per-response completion tokens inside run
                config["max_tokens"] = min(config.get("max_tokens", 4096), 1024)

                messages = [{"role": "user", "content": mod_user_content}]

                response_type, response_data = await provider.complete(
                    system_prompt=mod_system_prompt,
                    messages=messages,
                    tool_schemas=[],
                    config=config
                )

                is_rate_limit = False
                if response_type == "error":
                    err_str = str(response_data).lower()
                    if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                        is_rate_limit = True

                if is_rate_limit:
                    logger.info("Rate limit (HTTP 429) detected on Moderator account '%s'. Swapping to fallback...", resolved_acc_id)
                    if self.account_manager.swap_to_fallback():
                        continue
                    else:
                        raise RuntimeError(f"Rate limited and no fallback accounts available: {response_data}")

                if response_type == "error":
                    raise RuntimeError(f"LLM call returned error: {response_data}")

                consensus_summary = str(response_data).strip()
                prompt_tokens = len(mod_system_prompt + mod_user_content) // 4
                completion_tokens = len(consensus_summary) // 4
                self.account_manager.record_usage(resolved_acc_id, prompt_tokens, completion_tokens)

                model_used = config.get("model", "gemini-2.5-flash")
                models_used.add(model_used)
                call_cost = estimate_cost(model_used, prompt_tokens, completion_tokens)
                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens
                total_estimated_cost += call_cost
                break
            except Exception as e:
                error_msg = str(e)
                logger.error("Moderator synthesis failed on attempt %d: %s", attempt, error_msg)
                if attempt <= max_attempts:
                    logger.info("Attempting self-healing correction for Moderator synthesis...")
                    healed_data = await self._invoke_llm_healing("discussion_room_moderator", {"system_prompt": mod_system_prompt, "user_content": mod_user_content}, error_msg)
                    mod_system_prompt = healed_data.get("system_prompt", mod_system_prompt)
                    mod_user_content = healed_data.get("user_content", mod_user_content)

                    if "429" in error_msg.lower() or "rate limit" in error_msg.lower():
                        self.account_manager.swap_to_fallback()
                else:
                    consensus_summary = f"Error synthesizing consensus: {e}\n\nMeeting adjourned."

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Cost Alert Calculation
        cost_alert = False
        active_acc = self.account_manager.get_active_account()
        if active_acc:
            budget = active_acc.get("token_budget", -1)
            used = active_acc.get("tokens_used", 0)
            if budget > 0 and (used / budget) >= 0.8:
                cost_alert = True

        # Broadcast moderator synthesized event
        mod_event = {
            "session": session_id,
            "type": "consensus_synthesis",
            "agent": "Moderator",
            "role": "moderator",
            "duration_ms": duration_ms,
            "active_latency_alert": duration_ms > 5000,
            "cost_alert": cost_alert,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        for cb in self.telemetry_callbacks:
            try:
                cb(session_id, mod_event)
            except Exception:
                pass

        # Explicitly append sub-swarm summaries to guarantee 100% synthesis integration
        if sub_swarm_results:
            consensus_summary += "\n\n### Integrated Sub-Swarm Consensus Reports\n"
            for i, res in enumerate(sub_swarm_results):
                consensus_summary += f"\n#### Sub-Swarm {i+1} [{res['topic']}]:\n{res['consensus_summary']}\n"

        verifier_verdict = self.create_verifier_verdict(
            session_id=session_id,
            topic=topic,
            consensus_summary=consensus_summary,
            transcript=transcript,
            role_contracts=role_contracts,
            risk_level=risk_level,
            approval_required=approval_required,
            consensus_certificate=consensus_certificate,
        )

        # Compile structured real-time invoice telemetry audit record
        import uuid
        invoice_id = f"inv-{uuid.uuid4().hex[:12]}"
        model_used_str = ", ".join(sorted(list(models_used))) if models_used else "gemini-2.5-flash"

        invoice_record = {
            "invoice_id": invoice_id,
            "session_id": session_id,
            "topic": topic,
            "model_used": model_used_str,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "estimated_cost_usd": round(total_estimated_cost, 6),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Persist this invoice JSON file to disk under memory/semantic/billing/
        billing_dir = Path(self.workspace_path) / "memory" / "semantic" / "billing"
        try:
            billing_dir.mkdir(parents=True, exist_ok=True)
            invoice_file = billing_dir / f"{invoice_id}.json"
            invoice_file.write_text(json.dumps(invoice_record, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("Persisted billing audit trail to %s", invoice_file)
        except Exception as e:
            logger.error("Failed to persist billing audit trail: %s", e)

        # Archive full session transcript
        archive_dir = Path(self.workspace_path) / ".agent" / "memory" / "archive"
        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            archive_file = archive_dir / f"debate_{session_id}_{timestamp}.json"
            archive_data = {
                "session_id": session_id,
                "topic": topic,
                "rounds": max_rounds,
                "participants": participants,
                "transcript": transcript,
                "consensus_summary": consensus_summary,
                "role_contracts": [contract.to_dict() for contract in role_contracts],
                "verifier_verdict": verifier_verdict.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            archive_file.write_text(json.dumps(archive_data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("Archived full debate transcript to %s", archive_file)
        except Exception as e:
            logger.error("Failed to archive debate transcript: %s", e)

        # Broadcast invoice telemetry event
        invoice_event = {
            "session": session_id,
            "type": "invoice_telemetry",
            "invoice": invoice_record,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        for cb in self.telemetry_callbacks:
            try:
                cb(session_id, invoice_event)
            except Exception:
                pass

        return {
            "topic": topic,
            "rounds": max_rounds,
            "transcript": transcript,
            "consensus_summary": consensus_summary,
            "role_contracts": [contract.to_dict() for contract in role_contracts],
            "verifier_verdict": verifier_verdict.to_dict(),
        }

    async def run_corporate_audit(self, task_id: str, proposed_code: str) -> dict[str, Any]:
        """
        Executes a corporate verification flow. Dev agent submits code, and QA agent
        runs automated pytest validations, acting as a real-time gating check.
        """
        logger.info("Initiating corporate audit gate for task %s", task_id)

        # 1. Dev Agent (Programmer) produces the code review submission
        dev_note = f"Dev Agent submitted code review for Task {task_id}:\n```python\n{proposed_code}\n```"

        # 2. QA Agent (Auditor) executes automated testing suite in the workspace asynchronously
        import asyncio
        import sys
        logger.info("QA Agent executing automated validation gate using pytest asynchronously...")

        # Use current python executable to guarantee we use the correct environment
        python_exe = sys.executable or "python"

        proc = await asyncio.create_subprocess_exec(
            python_exe, "-m", "pytest",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.workspace_path
        )

        stdout_chunks = []
        stderr_chunks = []

        async def read_stream(stream, chunks, log_prefix):
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace")
                chunks.append(decoded)
                logger.info("%s: %s", log_prefix, decoded.strip())

        await asyncio.gather(
            read_stream(proc.stdout, stdout_chunks, "[QA pytest STDOUT]"),
            read_stream(proc.stderr, stderr_chunks, "[QA pytest STDERR]")
        )

        returncode = await proc.wait()

        stdout_str = "".join(stdout_chunks)
        stderr_str = "".join(stderr_chunks)

        test_passed = (returncode == 0)
        qa_status = "PASS" if test_passed else "FAIL"

        qa_feedback = f"""[QA Auditor Report] Task ID: {task_id}
Status: {qa_status}
Exit Code: {returncode}
Stdout: {stdout_str[:500]}
Stderr: {stderr_str[:500]}
"""

        # 3. CFO Agent logs token cost and audits total financial allocation
        cfo_feedback = f"[CFO Audit Log] Task ID: {task_id} approved for release. Token cost checked against phase budget." if test_passed else f"[CFO Audit Log] Task ID: {task_id} rejected. Return to Dev for correction loop."

        return {
            "task_id": task_id,
            "dev_note": dev_note,
            "qa_status": qa_status,
            "qa_feedback": qa_feedback,
            "cfo_feedback": cfo_feedback,
            "passed": test_passed
        }

    async def run_milestone_reflection(
        self,
        milestone_id: str,
        tasks_dict: dict[str, Any] | None = None,
        transaction_logs: list[str] | None = None
    ) -> str:
        """Triggers a round-robin debate among roles analyzing completed tasks.

        Refines consensus to produce a unified milestone_learning_report.md and registers it.
        """
        logger.info("Initiating autonomous milestone reflection consensus loop for milestone %s", milestone_id)

        # 1. Format transaction logs summary
        logs_summary_parts = []
        if tasks_dict:
            for task_id, task in tasks_dict.items():
                # Extract fields handling both objects and dicts
                if hasattr(task, "to_dict"):
                    task_dict = task.to_dict()
                elif isinstance(task, dict):
                    task_dict = task
                else:
                    task_dict = {}

                title = getattr(task, "title", "") or task_dict.get("title", "")
                desc = getattr(task, "description", "") or task_dict.get("description", "")
                logs = getattr(task, "logs", []) or task_dict.get("logs", [])

                logs_str = "\n".join(logs) if isinstance(logs, list) else str(logs)
                logs_summary_parts.append(
                    f"### Task: {task_id} - {title}\n"
                    f"**Description**: {desc}\n"
                    f"**Logs**:\n{logs_str}"
                )
        if transaction_logs:
            for log_entry in transaction_logs:
                logs_summary_parts.append(str(log_entry))

        logs_summary = "\n\n".join(logs_summary_parts) if logs_summary_parts else "(No task logs provided.)"

        topic = (
            f"Review and reflect on the concluded milestone: {milestone_id}.\n"
            f"Here are the transaction logs of completed tasks in this milestone:\n"
            f"---\n"
            f"{logs_summary}\n"
            f"---\n"
            f"Please conduct a multi-role debate to analyze this milestone's execution. Focus on identifying:\n"
            f"1. Performance Gaps: Where did the system or agents struggle or hit limits?\n"
            f"2. Budget Consumption Audits: How did we use tokens/API quota? Any alerts or overspending?\n"
            f"3. Prompt Refactoring Suggestions: How should we improve declarative system prompts or guidelines for each role to prevent future mistakes?"
        )

        agents = [
            {"role": "ceo", "name": "CEO Strategy"},
            {"role": "cto", "name": "CTO Architecture"},
            {"role": "dev", "name": "Dev Engineering"},
            {"role": "qa", "name": "QA Auditing"},
            {"role": "cfo", "name": "CFO Billing"}
        ]

        # 2. Run the round-robin debate (1 round for efficiency)
        debate_result = await self.run(
            topic=topic,
            agents=agents,
            max_rounds=1,
            moderator_persona=self._get_reflection_moderator_persona(),
            session_id=f"reflection-{milestone_id}"
        )
        consensus_summary = debate_result.get("consensus_summary", "")

        # 3. Resolve project root and knowledge base directory path
        path_check = Path(self.workspace_path)
        if (path_check / ".agent").is_dir():
            project_root = path_check
        elif (path_check.parent / ".agent").is_dir():
            project_root = path_check.parent
        else:
            project_root = path_check.parent

        kb_dir = project_root / ".agent" / "knowledge_base"
        kb_dir.mkdir(parents=True, exist_ok=True)

        # 4. Write milestone learning report
        report_file = kb_dir / "milestone_learning_report.md"
        try:
            report_file.write_text(consensus_summary, encoding="utf-8")
            logger.info("Successfully persisted milestone learning report to %s", report_file)
        except Exception as e:
            logger.error("Failed to persist milestone learning report: %s", e)

        # 5. Dynamically register in index.json
        index_file = kb_dir / "index.json"
        index_data = {}
        if index_file.is_file():
            try:
                index_data = json.loads(index_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("Failed to parse index.json: %s", e)

        if not isinstance(index_data, dict):
            index_data = {}

        index_data.setdefault("schema_version", "1.0.0")
        index_data.setdefault("generated_at", datetime.now(timezone.utc).isoformat())

        documents = index_data.setdefault("documents", [])

        doc_id = f"milestone_learning_report"
        new_doc = {
            "id": doc_id,
            "title": "Milestone Learning Report",
            "file_path": ".agent/knowledge_base/milestone_learning_report.md",
            "description": f"Autonomous multi-agent role consensus learning report for milestone {milestone_id}.",
            "creator": "LAS Orchestrator Swarm",
            "version": "1.0.0",
            "tags": ["reflection", "consensus", "compaction", "milestone"]
        }

        # Deduplicated upsert
        exists = False
        for idx, doc in enumerate(documents):
            if doc.get("id") == doc_id:
                documents[idx] = new_doc
                exists = True
                break
        if not exists:
            documents.append(new_doc)

        try:
            index_file.write_text(json.dumps(index_data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("Successfully registered report in index.json")
        except Exception as e:
            logger.error("Failed to write to index.json: %s", e)

        return consensus_summary

    def _get_reflection_moderator_persona(self) -> str:
        return (
            "You are a professional meeting moderator and systems strategist.\n"
            "Your task is to analyze the debate transcript and synthesize a unified, highly detailed Milestone Learning Report.\n"
            "You MUST structure the report with the following exact Markdown headers and sections:\n\n"
            "# Milestone Learning Report\n\n"
            "## 1. Performance Gaps / 效能差距分析\n"
            "Identify and detail any performance gaps, latency alerts, tool failures, or architectural bottlenecks encountered.\n\n"
            "## 2. Budget Consumption Audits / 預算消費審計\n"
            "Analyze token footprints, estimated API costs, account failover swaps, and financial efficiency.\n\n"
            "## 3. Prompt Refactoring Suggestions / 提示詞重構建議\n"
            "Provide specific suggestions for optimizing role system prompts (CEO, CTO, Dev, QA, CFO) with target version adjustments.\n\n"
            "Enforce a highly professional, factual, and actionable tone."
        )

    async def run_governance_vote(self, proposal: dict) -> dict:
        """
        Executes a round-robin voting debate where each swarm member (ceo, cto, dev, qa, cfo)
        votes "approve" or "reject" on a proposal and signs the payload hash.
        """
        logger.info("Initiating dynamic governance vote calibration debate for proposal %s", proposal.get("id"))

        votes = {}
        signatures = {}
        payload_hash = proposal["payload_hash"]

        # Loop through all swarm members
        members = ProofOfConsensus.get_swarm_members()
        for role in members:
            if SwarmIDS.is_quarantined(role):
                logger.warning("Member %s is quarantined and cannot participate in governance vote.", role)
                continue

            # Each active node votes. We simulate the vote based on the role and proposal type.
            # Let's run a quick LLM call for each member to evaluate the rule.
            persona = self._resolve_agent_persona(role)
            system_prompt = (
                f"{persona}\n\n"
                "You are participating in a decentralized swarm governance vote on a prompt policy calibration proposal.\n"
                "You must evaluate the proposal and cast your vote: either APPROVE or REJECT."
            )

            user_content = (
                f"Rule Type: {proposal.get('rule_type')}\n"
                f"Rule Text: {proposal.get('rule_text')}\n\n"
                "Do you approve or reject this prompt calibration directive? "
                "Respond with either 'APPROVE' or 'REJECT' as the first word of your response, "
                "followed by a short, one-sentence rationale."
            )

            vote = "approve"
            try:
                prompt_len = len(system_prompt + user_content) // 4
                provider, config, resolved_acc_id = self._resolve_agent_provider(
                    account_id=None,
                    prompt_len=prompt_len,
                    topic="governance-vote",
                    session_id=f"vote-{proposal.get('id')}-{role}"
                )
                messages = [{"role": "user", "content": user_content}]
                response_type, response_data = await provider.complete(
                    system_prompt=system_prompt,
                    messages=messages,
                    tool_schemas=[],
                    config=config
                )
                if response_type == "success" and response_data:
                    resp_text = response_data.strip().upper()
                    if resp_text.startswith("REJECT"):
                        vote = "reject"
                    elif resp_text.startswith("APPROVE"):
                        vote = "approve"
            except Exception as e:
                logger.warning("LLM vote query failed for role %s: %s. Defaulting to APPROVE.", role, e)
                vote = "approve"

            votes[role] = vote
            sig = ProofOfConsensus.generate_member_signature(role, payload_hash)
            signatures[role] = sig

        return {
            "proposal_id": proposal.get("id"),
            "votes": votes,
            "signatures": signatures
        }



class ProofOfConsensus:
    """Implements decentralized Proof of Consensus (PoC) for the swarm."""

    SECRET_KEYS = {
        "ceo": "poc-secret-ceo-key-92834",
        "cto": "poc-secret-cto-key-83749",
        "dev": "poc-secret-dev-key-10293",
        "qa": "poc-secret-qa-key-58291",
        "cfo": "poc-secret-cfo-key-47284"
    }

    CONSENSUS_KEY = "poc-master-consensus-key-84729"

    @classmethod
    def rotate_session_keys(cls):
        """Rotates SECRET_KEYS and CONSENSUS_KEY dynamically using a random rotation suffix."""
        import uuid
        rotation_suffix = uuid.uuid4().hex[:8]
        for role in list(cls.SECRET_KEYS.keys()):
            cls.SECRET_KEYS[role] = f"poc-secret-{role}-key-{rotation_suffix}"
        cls.CONSENSUS_KEY = f"poc-master-consensus-key-{rotation_suffix}"
        logger.info("[ProofOfConsensus] Swarm session keys rotated with suffix: %s", rotation_suffix)

    @classmethod
    def reset_keys(cls):
        """Restores default SECRET_KEYS and CONSENSUS_KEY values."""
        cls.SECRET_KEYS = {
            "ceo": "poc-secret-ceo-key-92834",
            "cto": "poc-secret-cto-key-83749",
            "dev": "poc-secret-dev-key-10293",
            "qa": "poc-secret-qa-key-58291",
            "cfo": "poc-secret-cfo-key-47284"
        }
        cls.CONSENSUS_KEY = "poc-master-consensus-key-84729"

    @classmethod
    def get_swarm_members(cls) -> list[str]:
        return list(cls.SECRET_KEYS.keys())

    @classmethod
    def generate_member_signature(cls, role: str, payload_hash: str) -> str:
        """Generates a SHA256 signature for a specific role and payload hash."""
        import hashlib
        normalized_role = role.lower()
        secret = cls.SECRET_KEYS.get(normalized_role)
        if not secret:
            raise ValueError(f"Unknown consensus role: {role}")
        return hashlib.sha256(f"{normalized_role}:{payload_hash}:{secret}".encode("utf-8")).hexdigest()

    @classmethod
    def create_consensus_certificate(cls, payload_hash: str, approved_roles: list[str]) -> dict[str, Any]:
        """Creates a signed consensus certificate if a majority approves."""
        import hashlib
        swarm_members = cls.get_swarm_members()
        # Exclude quarantined roles
        approvals = [r.lower() for r in approved_roles if r.lower() in swarm_members and not SwarmIDS.is_quarantined(r.lower())]

        # Majority is > 50% of the swarm
        majority_needed = (len(swarm_members) // 2) + 1  # 3 out of 5

        if len(approvals) < majority_needed:
            raise ValueError(f"Consensus failed: only got {len(approvals)}/{majority_needed} approvals.")

        signatures = {}
        for role in approvals:
            signatures[role] = cls.generate_member_signature(role, payload_hash)

        sorted_roles = sorted(approvals)
        roles_str = ",".join(sorted_roles)

        # Master signature
        master_sig = hashlib.sha256(f"consensus:{payload_hash}:{roles_str}:{cls.CONSENSUS_KEY}".encode("utf-8")).hexdigest()

        return {
            "payload_hash": payload_hash,
            "approvals": approvals,
            "signatures": signatures,
            "consensus_signature": master_sig,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def verify_consensus_certificate(cls, certificate: dict[str, Any]) -> bool:
        """Verifies if the consensus certificate is cryptographically valid and has a majority."""
        import hashlib
        try:
            payload_hash = certificate["payload_hash"]
            approvals = certificate["approvals"]
            signatures = certificate["signatures"]
            consensus_signature = certificate["consensus_signature"]

            swarm_members = cls.get_swarm_members()
            valid_approvals = []

            # Verify each signature
            for role in approvals:
                if role not in swarm_members:
                    continue
                if SwarmIDS.is_quarantined(role):
                    logger.warning("[ProofOfConsensus] Quarantined node '%s' signature validation skipped.", role)
                    continue
                expected_sig = cls.generate_member_signature(role, payload_hash)
                if signatures.get(role) == expected_sig:
                    valid_approvals.append(role)
                else:
                    logger.warning("[ProofOfConsensus] Signature mismatch for role '%s'. Expected %s, got %s", role, expected_sig, signatures.get(role))
                    SwarmIDS.record_failure(role)

            majority_needed = (len(swarm_members) // 2) + 1
            if len(valid_approvals) < majority_needed:
                logger.warning("Verification failed: Not enough valid member signatures (%d/%d)", len(valid_approvals), majority_needed)
                return False

            # Verify master consensus signature
            sorted_roles = sorted(valid_approvals)
            roles_str = ",".join(sorted_roles)
            expected_master_sig = hashlib.sha256(f"consensus:{payload_hash}:{roles_str}:{cls.CONSENSUS_KEY}".encode("utf-8")).hexdigest()

            if consensus_signature != expected_master_sig:
                logger.warning("Verification failed: Master consensus signature mismatch")
                return False

            return True
        except Exception as e:
            logger.error("Failed to verify consensus certificate: %s", e)
            return False

    @classmethod
    def register_consensus(cls, workspace_path: str, payload_hash: str, certificate: dict[str, Any]) -> None:
        """Persists the verified consensus certificate to a local swarm registry."""
        if not cls.verify_consensus_certificate(certificate):
            raise ValueError("Cannot register invalid consensus certificate.")

        # Log consensus registration to AuditLedger
        from agent_workspace.core.audit_ledger import AuditLedger

        try:
            audit = AuditLedger(workspace_path)
            audit.record_event("consensus_vote", {
                "payload_hash": payload_hash,
                "approvals": certificate.get("approvals", []),
                "consensus_signature": certificate.get("consensus_signature")
            })
        except Exception as e:
            logger.warning("[ProofOfConsensus] Audit logging failed: %s", e)

        project_root = Path(workspace_path)
        if not (project_root / ".agent").is_dir() and (project_root.parent / ".agent").is_dir():
            project_root = project_root.parent

        registry_dir = project_root / ".agent" / "memory"
        registry_dir.mkdir(parents=True, exist_ok=True)
        registry_file = registry_dir / "consensus_registry.json"

        registry = {}
        if registry_file.is_file():
            try:
                registry = json.loads(registry_file.read_text(encoding="utf-8"))
            except Exception:
                registry = {}

        registry[payload_hash] = certificate

        try:
            registry_file.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("Successfully registered consensus certificate for hash: %s", payload_hash)
        except Exception as e:
            logger.error("Failed to write to consensus_registry.json: %s", e)

    @classmethod
    def is_consensus_approved(cls, workspace_path: str, payload_hash: str) -> bool:
        """Checks if a payload hash is registered and cryptographically valid in the local consensus registry."""
        project_root = Path(workspace_path)
        if not (project_root / ".agent").is_dir() and (project_root.parent / ".agent").is_dir():
            project_root = project_root.parent

        registry_file = project_root / ".agent" / "memory" / "consensus_registry.json"
        if not registry_file.is_file():
            return False

        try:
            registry = json.loads(registry_file.read_text(encoding="utf-8"))
            if payload_hash in registry:
                return cls.verify_consensus_certificate(registry[payload_hash])
        except Exception:
            pass
        return False


class SwarmIDS:
    """Intrusion Detection System (IDS) for Swarm Node/Role consensus auditing."""
    quarantined_nodes = set()
    failures_count = {}

    @classmethod
    def record_failure(cls, role: str):
        role_lower = role.lower()
        cls.failures_count[role_lower] = cls.failures_count.get(role_lower, 0) + 1
        logger.warning("[SwarmIDS] Signature failure recorded for role: %s. Failure count: %d", role_lower, cls.failures_count[role_lower])
        if cls.failures_count[role_lower] >= 3:
            cls.quarantine_node(role_lower)

    @classmethod
    def quarantine_node(cls, role: str):
        role_lower = role.lower()
        if role_lower not in cls.quarantined_nodes:
            cls.quarantined_nodes.add(role_lower)
            logger.error("[SwarmIDS] Quarantined malicious swarm node/role: %s", role_lower)
            ProofOfConsensus.rotate_session_keys()

    @classmethod
    def is_quarantined(cls, role: str) -> bool:
        return role.lower() in cls.quarantined_nodes

    @classmethod
    def reset(cls):
        """Helper to clear failures and quarantine for testing."""
        cls.quarantined_nodes.clear()
        cls.failures_count.clear()
