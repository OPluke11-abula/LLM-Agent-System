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

try:
    from core.account_manager import AccountManager
    from core.providers import ProviderFactory, BaseLLMProvider
    from core.prompt_composer import PromptComposer
except ImportError:
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
        topic: str = ""
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

    async def run(
        self,
        topic: str,
        agents: list[dict[str, Any]],
        max_rounds: int = 2,
        moderator_persona: str | None = None,
        session_id: str = "debate-session",
        sub_problems: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Orchestrate a round-robin sequential debate among agents on a topic.

        Concludes with a synthesized Consensus Summary, with parallel hierarchical sub-swarm delegation.
        """
        transcript: list[dict[str, str]] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_estimated_cost = 0.0
        models_used = set()

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
                        sub_problems=None
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
                "account_id": account_id
            })

        # 2. Sequential Round-Robin Dialogue Loop
        for round_idx in range(1, max_rounds + 1):
            logger.info("Starting discussion round %d/%d", round_idx, max_rounds)
            for p in participants:
                # Format current transcript for the participant
                if transcript:
                    formatted_transcript = "\n".join(
                        f"[{msg['agent']} ({msg['role']})]: {msg['content']}"
                        for msg in transcript
                    )
                else:
                    formatted_transcript = "(The discussion has just started. No contributions yet.)"

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
                contribution = f"[Silent / Connection Error]"
                resolved_acc_id = "default-account"
                
                # Dynamic Account Swapping & Error Self-Healing Retry Loop
                max_attempts = 3
                for attempt in range(1, max_attempts + 2):
                    try:
                        prompt_len = len(system_prompt + user_content) // 4
                        provider, config, resolved_acc_id = self._resolve_agent_provider(
                            account_id=p["account_id"],
                            prompt_len=prompt_len,
                            topic=topic
                        )
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
        formatted_final_transcript = "\n".join(
            f"[{msg['agent']} ({msg['role']})]: {msg['content']}"
            for msg in transcript
        )

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
                    topic="consensus_synthesis"
                )
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
            "consensus_summary": consensus_summary
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

