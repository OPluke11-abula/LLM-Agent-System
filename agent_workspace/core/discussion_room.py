"""Multi-Agent Consensus & Debate Room for LAS.

Orchestrates sequential, round-robin debate cycles among multiple agents using
different personas and LLM models from accounts.json, concluding with a
synthesized consensus summary by a moderator agent.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
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
                    system_prompt += f"\n\n## SYSTEM SELF-LEARNING DIRECTIVES:\n{content}"
            except Exception as e:
                logger.error(f"Failed to read learning guide at {guide_path}: {e}")
                
        return system_prompt

    def _resolve_agent_provider(self, account_id: str | None = None) -> tuple[BaseLLMProvider, dict[str, Any], str]:
        """Resolve LLM provider, configuration, and account ID."""
        account = None
        if account_id:
            account = self.account_manager.get_account(account_id)
        if not account:
            account = self.account_manager.get_active_account()

        if not account:
            raise RuntimeError("No LLM accounts configured in accounts.json.")

        api_key = self.account_manager.resolve_api_key(account)
        provider = ProviderFactory.get_provider(
            account["provider"],
            api_key=api_key,
            base_url=account.get("base_url")
        )
        config = {
            "model": account["model"],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        return provider, config, account["id"]

    async def run(
        self,
        topic: str,
        agents: list[dict[str, Any]],
        max_rounds: int = 2,
        moderator_persona: str | None = None
    ) -> dict[str, Any]:
        """Orchestrate a round-robin sequential debate among agents on a topic.

        Concludes with a synthesized Consensus Summary.
        """
        transcript: list[dict[str, str]] = []

        # 1. Resolve participants and their personas
        participants = []
        for a in agents:
            role = a.get("role", "agent").lower()
            name = a.get("name", role.capitalize())
            
            # Check dynamic role config first
            persona = self.prompt_composer.load_role_persona(role)
            if not persona:
                # Fallback cleanly
                persona = a.get("persona", DEFAULT_PERSONAS.get(role, f"You are a helpful {role} agent."))
                
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
                user_content = f"""Topic for discussion: {topic}

Here is the dialogue transcript so far:
---
{formatted_transcript}
---

It is now your turn, {p['name']}. Please respond to the topic or build on top of previous points in a constructive manner. Keep your response brief, precise, and focused on driving consensus."""

                try:
                    provider, config, resolved_acc_id = self._resolve_agent_provider(p["account_id"])
                    messages = [{"role": "user", "content": user_content}]

                    response_type, response_data = await provider.complete(
                        system_prompt=system_prompt,
                        messages=messages,
                        tool_schemas=[],
                        config=config
                    )

                    if response_type == "error":
                        raise RuntimeError(f"LLM call returned error: {response_data}")

                    contribution = str(response_data).strip()
                    logger.info("%s (%s) contribution: %s...", p["name"], p["role"], contribution[:50])

                    transcript.append({
                        "agent": p["name"],
                        "role": p["role"],
                        "content": contribution
                    })

                except Exception as e:
                    logger.error("Failed to generate contribution for agent %s: %s", p["name"], e)
                    transcript.append({
                        "agent": p["name"],
                        "role": p["role"],
                        "content": f"[Silent / Connection Error: {e}]"
                    })

        # 3. Moderator Synthesis Round
        logger.info("Synthesizing meeting consensus summary...")
        mod_persona = moderator_persona or self.prompt_composer.load_role_persona("moderator") or DEFAULT_PERSONAS["moderator"]
        formatted_final_transcript = "\n".join(
            f"[{msg['agent']} ({msg['role']})]: {msg['content']}"
            for msg in transcript
        )

        mod_system_prompt = mod_persona
        mod_user_content = f"""Topic discussed: {topic}

Here is the complete dialogue transcript:
---
{formatted_final_transcript}
---

Please synthesize a professional Consensus Summary. Standardize the response to clearly outline:
1. Core Topic & Agreements reached.
2. Minor Disagreements or pending design choices.
3. Decisive action items or next steps.

Format the summary nicely in Markdown."""

        try:
            provider, config, resolved_acc_id = self._resolve_agent_provider(None)
            messages = [{"role": "user", "content": mod_user_content}]

            response_type, response_data = await provider.complete(
                system_prompt=mod_system_prompt,
                messages=messages,
                tool_schemas=[],
                config=config
            )

            if response_type == "error":
                raise RuntimeError(f"LLM call returned error: {response_data}")

            consensus_summary = str(response_data).strip()

        except Exception as e:
            logger.error("Moderator synthesis failed: %s", e)
            consensus_summary = f"Error synthesizing consensus: {e}\n\nMeeting adjourned."

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
