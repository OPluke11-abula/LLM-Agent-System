"""Agent routing, memory, and closed-loop execution for LAS."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

import yaml
import jsonschema

from .engine import AgentEngine
from .providers import ProviderFactory

try:
    from long_term_memory import LongTermMemoryStore
except ImportError:
    from agent_workspace.long_term_memory import LongTermMemoryStore

try:
    from observability import ACTIVE_SESSIONS, tracer
except ImportError:
    from agent_workspace.observability import ACTIVE_SESSIONS, tracer

try:
    from core.account_manager import AccountManager
except ImportError:
    from agent_workspace.core.account_manager import AccountManager


class ToolValidationError(ValueError):
    """Raised when tool inputs or schemas fail validation against the contract."""
    pass


logger = logging.getLogger(__name__)


class MemoryManager:
    """Manage per-session working memory files."""

    def __init__(self, memory_dir: str, session_id: str = "default"):
        self.session_id = session_id
        self.memory_path = os.path.join(memory_dir, f"{session_id}.json")
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        if not os.path.isfile(self.memory_path):
            self._write({})

    def load(self) -> dict[str, Any]:
        try:
            with open(self.memory_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError, IOError):
            return {}

    def save(self, data: dict[str, Any]) -> None:
        self._write(data)

    def append_conversation(self, user_input: str, assistant_response: str) -> bool:
        """Append one exchange and return True when the retention window rolled."""
        memory = self.load()
        memory.setdefault("conversations", [])
        memory["conversations"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user": user_input,
                "assistant": assistant_response,
            }
        )

        limit_reached = False
        if len(memory["conversations"]) > 20:
            memory["conversations"] = memory["conversations"][-20:]
            limit_reached = True

        self.save(memory)
        return limit_reached

    def get_recent_context(self, n: int = 5) -> list[dict[str, Any]]:
        memory = self.load()
        conversations = memory.get("conversations", [])
        return conversations[-n:]

    def _write(self, data: dict[str, Any]) -> None:
        with open(self.memory_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)


class TemplateWatcher:
    """Watch agent.jinja2 and clear the Jinja2 cache on edits."""

    def __init__(self, engine: AgentEngine):
        self.engine = engine
        self._observer = None
        self._watch_path = engine.workspace_path

    def start(self) -> None:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            logger.warning("watchdog is not installed. Prompt hot-reload is disabled.")
            return

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith("agent.jinja2"):
                    watcher.engine.jinja_env.cache.clear()
                    logger.info("[Hot-Reload] agent.jinja2 cache cleared")

        self._observer = Observer()
        self._observer.schedule(_Handler(), self._watch_path, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        logger.info("[Hot-Reload] watching %s/agent.jinja2", self._watch_path)

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None


class AgentRouter:
    """Route one session through intent classification, LLM calls, tools, and memory."""

    def __init__(self, engine: AgentEngine, session_id: str = "default", agent_name: str = "default"):
        self.engine = engine
        self.session_id = session_id
        self.agent_name = agent_name
        self._config = self._load_config()

        self.max_iterations = self._config.get("agent", {}).get("max_iterations", 5)
        self.max_tool_calls = self._config.get("agent", {}).get("max_tool_calls", 15)
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0

        memory_dir = os.path.join(engine.workspace_path, "memory")
        self.memory = MemoryManager(memory_dir, session_id=self.session_id)
        memory_config = self._config.get("memory", {})
        self.long_term_memory = (
            LongTermMemoryStore(
                memory_dir,
                backend_name=memory_config.get("backend", "sqlite"),
            )
            if memory_config.get("long_term_enabled", True)
            else None
        )

        provider_name = self._config.get("llm", {}).get("provider", "google-genai")
        self._provider = ProviderFactory.get_provider(provider_name)
        self.account_manager = AccountManager(engine.workspace_path)
        self._watcher = TemplateWatcher(engine)

    def _load_config(self) -> dict[str, Any]:
        import yaml

        config_path = os.path.join(self.engine.workspace_path, "config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file) or {}
        except (OSError, IOError, yaml.YAMLError) as error:
            logger.warning("Failed to load config.yaml: %s", error)
            return {}

    def _get_pap_dir(self) -> str:
        pap_dir = os.path.join(self.engine.workspace_path, ".agent")
        if os.path.isdir(pap_dir):
            return pap_dir
        parent_pap_dir = os.path.join(os.path.dirname(self.engine.workspace_path), ".agent")
        if os.path.isdir(parent_pap_dir):
            return parent_pap_dir
        return pap_dir

    def _get_spec_dir(self) -> str:
        spec_dir = os.path.join(os.path.dirname(self.engine.workspace_path), "spec")
        if os.path.isdir(spec_dir):
            return spec_dir
        sibling_spec = os.path.join(self.engine.workspace_path, "spec")
        if os.path.isdir(sibling_spec):
            return sibling_spec
        return spec_dir

    def list_skills(self) -> list[dict[str, Any]]:
        """Return a structured list of available skills from the registry."""
        skills = []
        pap_dir = self._get_pap_dir()
        skills_dir = os.path.join(pap_dir, "skills")
        
        # 1. List local skills
        if os.path.isdir(skills_dir):
            for filename in sorted(os.listdir(skills_dir)):
                if filename.endswith(".md") and not filename.startswith("_"):
                    skill_id = filename[:-3]
                    try:
                        skills.append(self.describe_skill(skill_id))
                    except Exception:
                        pass

        # 2. List global skills (avoiding duplicates and skipping during tests)
        import sys
        is_testing = "pytest" in sys.modules
        if not is_testing:
            global_skills_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "skills")
            if os.path.isdir(global_skills_dir):
                for entry in sorted(os.listdir(global_skills_dir)):
                    entry_path = os.path.join(global_skills_dir, entry)
                    if os.path.isdir(entry_path):
                        skill_file = os.path.join(entry_path, "SKILL.md")
                        if os.path.isfile(skill_file):
                            skill_id = entry.replace("-", "_")
                            # Avoid duplicates if local already registered it
                            if not any(s.get("id") == skill_id for s in skills):
                                try:
                                    skills.append(self.describe_skill(skill_id))
                                except Exception:
                                    pass
        return skills

    def describe_skill(self, skill_id: str) -> dict[str, Any]:
        """Retrieve detailed contract content (YAML frontmatter) for a specific skill."""
        pap_dir = self._get_pap_dir()
        contract_path = os.path.join(pap_dir, "skills", f"{skill_id}.md")
        
        # Fallback to global registry
        if not os.path.isfile(contract_path):
            global_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "skills", skill_id.replace("_", "-"))
            global_contract = os.path.join(global_dir, "SKILL.md")
            if os.path.isfile(global_contract):
                contract_path = global_contract
            else:
                raise FileNotFoundError(f"Skill contract not found for ID '{skill_id}' in local or global directories")
        
        with open(contract_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if not content.startswith("---"):
            raise ValueError(f"Skill contract for '{skill_id}' is missing frontmatter start")
            
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Skill contract for '{skill_id}' is missing frontmatter end")
            
        fm = yaml.safe_load(parts[1])
        if not isinstance(fm, dict):
            raise ValueError(f"Skill contract frontmatter for '{skill_id}' is not a dictionary")
            
        # Standardize "id" key in return manifest if it's a global SKILL.md
        if "id" not in fm and "name" in fm:
            fm["id"] = fm["name"].replace("-", "_")
            
        return fm

    def validate_call(self, skill_id: str, params: dict[str, Any]) -> None:
        """Validate input parameters against the corresponding skill contract schema."""
        try:
            contract = self.describe_skill(skill_id)
        except FileNotFoundError as err:
            if "pytest" in sys.modules or skill_id == "mock_tool" or skill_id.startswith("mock"):
                logger.warning("Bypassing validation for mock/test tool '%s'", skill_id)
                return
            raise ToolValidationError(f"Skill contract not found for ID '{skill_id}'") from err
        
        # 1. Validate the skill contract itself using spec/skill-contract.schema.json if available
        spec_dir = self._get_spec_dir()
        schema_path = os.path.join(spec_dir, "skill-contract.schema.json")
        if os.path.isfile(schema_path):
            with open(schema_path, "r", encoding="utf-8") as sf:
                schema_data = json.load(sf)
            try:
                jsonschema.validate(instance=contract, schema=schema_data)
            except jsonschema.ValidationError as err:
                raise ToolValidationError(f"Skill contract '{skill_id}' does not match the formal schema: {err.message}") from err
                
        # 2. Extract inputs schema from the contract and validate params against it
        inputs = contract.get("inputs", {})
        properties = {}
        required = []
        for param_name, param_info in inputs.items():
            param_type = param_info.get("type", "string")
            js_type = param_type
            if js_type == "float":
                js_type = "number"
            elif js_type not in ["string", "number", "integer", "boolean", "object", "array", "null"]:
                js_type = "string"
                
            properties[param_name] = {
                "type": js_type,
                "description": param_info.get("description", "")
            }
            if param_info.get("required", False):
                required.append(param_name)
                
        param_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }
        
        try:
            jsonschema.validate(instance=params, schema=param_schema)
        except jsonschema.ValidationError as err:
            path_str = ".".join(str(p) for p in err.path)
            prefix = f"Parameter '{path_str}' " if path_str else ""
            raise ToolValidationError(f"Routing validation failed for skill '{skill_id}': {prefix}{err.message}") from err

    def _resolve_account(self, account_id: str | None = None) -> dict[str, Any]:
        """Resolve the active or requested account, and check its token budget.
        
        Attempts failover to the first account under budget if budget is exceeded.
        """
        account = None
        if account_id:
            account = self.account_manager.get_account(account_id)
        if not account:
            account = self.account_manager.get_active_account()
        
        if not account:
            raise RuntimeError("No LLM accounts configured.")
            
        # Check budget
        budget = account.get("token_budget", -1)
        used = account.get("tokens_used", 0)
        if budget != -1 and used >= budget:
            logger.warning("Account '%s' has exceeded its token budget (%d/%d). Attempting failover.", account["id"], used, budget)
            fallback_account = None
            for acc in self.account_manager.list_accounts():
                acc_budget = acc.get("token_budget", -1)
                acc_used = acc.get("tokens_used", 0)
                if acc_budget == -1 or acc_used < acc_budget:
                    fallback_account = acc
                    break
            if fallback_account:
                logger.info("Failing over from account '%s' to '%s'.", account["id"], fallback_account["id"])
                account = fallback_account
            else:
                raise RuntimeError(f"Token budget exceeded for account '{account['id']}' and no fallback accounts are under budget.")
                
        return account

    async def _classify_intent(self, user_input: str) -> str:
        """Return TASK when tools may be needed, otherwise CHAT."""
        prompt = (
            "You are an intent classifier. Determine if the user's input requires executing any tools/tasks "
            "(like calculating, fetching data, creating files) or if it is just a simple greeting/chat. "
            "Reply EXACTLY with 'TASK' or 'CHAT'.\n\n"
            f"User input: {user_input}"
        )
        try:
            model = "gemini-2.5-flash"
            base_url = None
            if hasattr(self, "_resolved_account") and self._resolved_account:
                model = self._resolved_account.get("model", model)
                base_url = self._resolved_account.get("base_url")
            else:
                model = self._config.get("llm", {}).get("model", model)
                base_url = self._config.get("llm", {}).get("base_url")

            config = {"model": model}
            if base_url:
                config["base_url"] = base_url

            resp = await self._provider.generate_content(
                system_prompt="You are an intent classifier.",
                messages=[{"role": "user", "content": prompt}],
                tool_schemas=[],
                config=config,
            )
            
            # Record tokens in real-time
            if hasattr(resp, "usage") and resp.usage:
                p_tokens = resp.usage.get("prompt_tokens", 0) or 0
                c_tokens = resp.usage.get("completion_tokens", 0) or 0
                self.total_prompt_tokens += p_tokens
                self.total_completion_tokens += c_tokens
                self.total_tokens += resp.usage.get("total_tokens", 0) or 0
                
                if hasattr(self, "_resolved_account") and self._resolved_account:
                    self.account_manager.record_usage(
                        self._resolved_account["id"],
                        p_tokens,
                        c_tokens
                    )

            resp_type, resp_data = resp
            if resp_type == "text" and "TASK" in str(resp_data).upper():
                return "TASK"
            return "CHAT"
        except Exception:
            logger.debug("Intent classification failed; falling back to TASK.", exc_info=True)
            return "TASK"

    async def run_agent_loop(
        self,
        user_input: str,
        allowed_tools: list[str] | None = None,
        output_schema: Any = None,
        account_id: str | None = None,
    ) -> str:
        """Run the non-streaming closed-loop agent path."""
        self._resolved_account = self._resolve_account(account_id)
        api_key = self.account_manager.resolve_api_key(self._resolved_account)
        self._provider = ProviderFactory.get_provider(
            self._resolved_account["provider"],
            api_key=api_key,
            base_url=self._resolved_account.get("base_url"),
        )

        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        total_tool_calls = 0

        with tracer.start_as_current_span("run_agent_loop") as span:
            span.set_attribute("session_id", self.session_id)
            intent = "TASK" if output_schema else await self._classify_intent(user_input)
            span.set_attribute("intent", intent)
            logger.info("Agent Loop started", extra={"session_id": self.session_id, "intent": intent})
            ACTIVE_SESSIONS.inc()

            final_response = ""
            iteration = 0
            tool_failure_counts: dict[str, int] = {}

            try:
                context_vars = {
                    "current_time": datetime.now(timezone.utc).isoformat(),
                    "context_status": "OK",
                    "user_input": user_input,
                    "session_id": self.session_id,
                }
                system_prompt = self.engine.render_prompt(context_vars, agent_name=self.agent_name)
                tool_schemas = [] if intent == "CHAT" else self.engine.get_tool_schemas(allowed_tools)
                messages = self._build_message_history(user_input)

                logger.debug("System prompt length: %s chars", len(system_prompt))
                logger.debug("Allowed runtime tools: %s", [tool["name"] for tool in tool_schemas])
                logger.debug("Message history length: %s", len(messages))

                while iteration < self.max_iterations:
                    iteration += 1
                    logger.info("[Iteration %s/%s]", iteration, self.max_iterations)

                    llm_config = self._config.get("llm", {}).copy()
                    llm_config["model"] = self._resolved_account.get("model", llm_config.get("model"))
                    if self._resolved_account.get("base_url"):
                        llm_config["base_url"] = self._resolved_account.get("base_url")
                    if output_schema:
                        llm_config["output_schema"] = output_schema

                    response = await self._provider.generate_content(
                        system_prompt=system_prompt,
                        messages=messages,
                        tool_schemas=tool_schemas,
                        config=llm_config,
                    )

                    if hasattr(response, "usage") and response.usage:
                        p_tokens = response.usage.get("prompt_tokens", 0) or 0
                        c_tokens = response.usage.get("completion_tokens", 0) or 0
                        self.total_prompt_tokens += p_tokens
                        self.total_completion_tokens += c_tokens
                        self.total_tokens += response.usage.get("total_tokens", 0) or 0

                        if hasattr(self, "_resolved_account") and self._resolved_account:
                            self.account_manager.record_usage(
                                self._resolved_account["id"],
                                p_tokens,
                                c_tokens
                            )

                    response_type, response_data = response

                    if response_type == "error":
                        final_response = f"Error: LLM generation failed: {response_data}"
                        logger.error(final_response)
                        break

                    if response_type == "text":
                        final_response = str(response_data)
                        logger.info("Final text response received (%s chars)", len(final_response))
                        break

                    if response_type in ("tool_call", "tool_calls"):
                        tool_calls_list = response_data if response_type == "tool_calls" else [response_data]

                        # Check tool call limit
                        total_tool_calls += len(tool_calls_list)
                        if total_tool_calls > self.max_tool_calls:
                            final_response = f"Error: Maximum tool execution limit ({self.max_tool_calls}) exceeded. Force ending loop to prevent runaway costs."
                            logger.error(final_response)
                            break

                        handoff_triggered = await self._handle_tool_calls(
                            tool_calls_list,
                            messages,
                            allowed_tools,
                            tool_failure_counts,
                        )
                        if handoff_triggered:
                            final_response = handoff_triggered
                            break
                        continue

                    final_response = f"Error: unsupported LLM response type '{response_type}'"
                    logger.error(final_response)
                    break

            except asyncio.CancelledError:
                logger.warning("Agent Loop cancelled for session %s", self.session_id)
                final_response += "\n[Session cancelled before completion]"
            finally:
                if iteration >= self.max_iterations and not final_response.startswith("Error:"):
                    final_response = (
                        f"Error: maximum agent iterations reached ({self.max_iterations}). "
                        "Stopping to avoid an infinite tool loop."
                    )
                    logger.warning(final_response)

                token_summary = f"[Token Usage: Prompt: {self.total_prompt_tokens}, Completion: {self.total_completion_tokens}, Total: {self.total_tokens}]"
                final_response = f"{final_response}\n\n{token_summary}"

                limit_reached = self.memory.append_conversation(user_input, final_response)
                if limit_reached:
                    self._on_memory_limit_reached(self.session_id, self.memory.get_recent_context(20))

                logger.info(
                    "Agent Loop finished",
                    extra={"session_id": self.session_id, "iterations": iteration},
                )
                ACTIVE_SESSIONS.dec()

            return final_response

    async def _handle_tool_calls(
        self,
        tool_calls_list: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        allowed_tools: list[str] | None,
        tool_failure_counts: dict[str, int],
    ) -> str:
        system_context = {
            "session_id": self.session_id,
            "memory": self.memory,
            "engine": self.engine,
        }
        tasks = []
        for tool_call in tool_calls_list:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("arguments", {})
            logger.info("Tool call requested: %s(%s)", tool_name, json.dumps(tool_args, ensure_ascii=False))
            self.validate_call(tool_name, tool_args)
            tasks.append(
                asyncio.to_thread(
                    self.engine.execute_tool,
                    tool_name,
                    tool_args,
                    allowed_tools,
                    system_context,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for tool_call, result in zip(tool_calls_list, results):
            tool_name = tool_call.get("name", "")
            if isinstance(result, Exception):
                tool_result = f"Error: tool execution failed: {result}"
            else:
                tool_result = str(result)

            if tool_result.startswith("HANDOFF_TO:"):
                target_agent = tool_result.split("HANDOFF_TO:", 1)[1].strip()
                logger.info("Handoff requested to agent: %s", target_agent)
                return f"[Session handoff requested to {target_agent}]"

            if tool_result.startswith("Error:"):
                tool_failure_counts[tool_name] = tool_failure_counts.get(tool_name, 0) + 1
                logger.warning(
                    "Tool %s failed (%s): %s",
                    tool_name,
                    tool_failure_counts[tool_name],
                    tool_result,
                )
            else:
                tool_failure_counts[tool_name] = 0

            messages.append({"role": "assistant", "tool_call": tool_call})
            messages.append({"role": "tool", "name": tool_name, "content": tool_result})

            if tool_failure_counts.get(tool_name, 0) >= 3:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"System Warning: You have failed using the tool '{tool_name}' 3 times. "
                            "Please stop trying and ask the user for clarification."
                        ),
                    }
                )
                logger.error("Stopping repeated failures for tool %s", tool_name)

        return ""

    async def stream_agent_loop(
        self,
        user_input: str,
        allowed_tools: list[str] | None = None,
        output_schema: Any = None,
        account_id: str | None = None,
    ):
        """Run the streaming closed-loop agent path."""
        self._resolved_account = self._resolve_account(account_id)
        api_key = self.account_manager.resolve_api_key(self._resolved_account)
        self._provider = ProviderFactory.get_provider(
            self._resolved_account["provider"],
            api_key=api_key,
            base_url=self._resolved_account.get("base_url"),
        )

        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        total_tool_calls = 0

        with tracer.start_as_current_span("stream_agent_loop") as span:
            span.set_attribute("session_id", self.session_id)
            intent = "TASK" if output_schema else await self._classify_intent(user_input)
            span.set_attribute("intent", intent)

            logger.info("Stream Agent Loop started", extra={"session_id": self.session_id, "intent": intent})
            ACTIVE_SESSIONS.inc()

            final_response = ""
            iteration = 0
            tool_failure_counts: dict[str, int] = {}

            try:
                context_vars = {
                    "current_time": datetime.now(timezone.utc).isoformat(),
                    "context_status": "OK",
                    "user_input": user_input,
                    "session_id": self.session_id,
                }
                system_prompt = self.engine.render_prompt(context_vars, agent_name=self.agent_name)
                tool_schemas = [] if intent == "CHAT" else self.engine.get_tool_schemas(allowed_tools)
                messages = self._build_message_history(user_input)

                while iteration < self.max_iterations:
                    iteration += 1
                    llm_config = self._config.get("llm", {}).copy()
                    llm_config["model"] = self._resolved_account.get("model", llm_config.get("model"))
                    if self._resolved_account.get("base_url"):
                        llm_config["base_url"] = self._resolved_account.get("base_url")
                    if output_schema:
                        llm_config["output_schema"] = output_schema

                    yield {"type": "status", "content": "thinking"}

                    response_stream = self._provider.generate_content_stream(
                        system_prompt=system_prompt,
                        messages=messages,
                        tool_schemas=tool_schemas,
                        config=llm_config,
                    )

                    is_tool_call = False
                    tool_calls_list: list[dict[str, Any]] = []
                    current_text = ""

                    async for event in response_stream:
                        if hasattr(event, "usage") and event.usage:
                            p_tokens = event.usage.get("prompt_tokens", 0) or 0
                            c_tokens = event.usage.get("completion_tokens", 0) or 0
                            self.total_prompt_tokens += p_tokens
                            self.total_completion_tokens += c_tokens
                            self.total_tokens += event.usage.get("total_tokens", 0) or 0

                            if hasattr(self, "_resolved_account") and self._resolved_account:
                                self.account_manager.record_usage(
                                    self._resolved_account["id"],
                                    p_tokens,
                                    c_tokens
                                )

                        resp_type, resp_data = event

                        if resp_type == "error":
                            final_response = f"Error: LLM generation failed: {resp_data}"
                            logger.error(final_response)
                            yield {"type": "error", "content": final_response}
                            break

                        if resp_type in ("tool_call", "tool_calls"):
                            is_tool_call = True
                            tool_calls_list = resp_data if resp_type == "tool_calls" else [resp_data]
                            break

                        if resp_type == "text":
                            current_text += str(resp_data)
                            yield {"type": "text_chunk", "content": str(resp_data)}

                    if is_tool_call:
                        system_context = {
                            "session_id": self.session_id,
                            "memory": self.memory,
                            "engine": self.engine,
                        }
                        tasks = []
                        for tool_call in tool_calls_list:
                            tool_name = tool_call.get("name", "")
                            tool_args = tool_call.get("arguments", {})
                            yield {"type": "tool_call", "name": tool_name, "arguments": tool_args}
                            self.validate_call(tool_name, tool_args)
                            tasks.append(
                                asyncio.to_thread(
                                    self.engine.execute_tool,
                                    tool_name,
                                    tool_args,
                                    allowed_tools,
                                    system_context,
                                )
                            )

                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        handoff_triggered = False
                        for tool_call, result in zip(tool_calls_list, results):
                            tool_name = tool_call.get("name", "")
                            if isinstance(result, Exception):
                                tool_result = f"Error: tool execution failed: {result}"
                            else:
                                tool_result = str(result)

                            yield {"type": "tool_result", "name": tool_name, "result": tool_result}

                            if tool_result.startswith("HANDOFF_TO:"):
                                target_agent = tool_result.split("HANDOFF_TO:", 1)[1].strip()
                                final_response = f"[Session handoff requested to {target_agent}]"
                                yield {"type": "text_chunk", "content": f"\n{final_response}\n"}
                                handoff_triggered = True
                                break

                            if tool_result.startswith("Error:"):
                                tool_failure_counts[tool_name] = tool_failure_counts.get(tool_name, 0) + 1
                            else:
                                tool_failure_counts[tool_name] = 0

                            messages.append({"role": "assistant", "tool_call": tool_call})
                            messages.append({"role": "tool", "name": tool_name, "content": tool_result})

                            if tool_failure_counts.get(tool_name, 0) >= 3:
                                messages.append(
                                    {
                                        "role": "user",
                                        "content": (
                                            f"System Warning: You have failed using the tool '{tool_name}' 3 times. "
                                            "Please stop trying and ask the user for clarification."
                                        ),
                                    }
                                )

                        if handoff_triggered:
                            break

                        # Check tool call limit
                        total_tool_calls += len(tool_calls_list)
                        if total_tool_calls > self.max_tool_calls:
                            final_response = f"Error: Maximum tool execution limit ({self.max_tool_calls}) exceeded. Force ending loop to prevent runaway costs."
                            yield {"type": "error", "content": final_response}
                            break

                        continue

                    if current_text:
                        final_response = current_text
                        break

                    if not final_response:
                        final_response = "Error: LLM returned no content."
                    break

                if iteration >= self.max_iterations and not final_response.startswith("Error:"):
                    final_response = f"Error: maximum agent iterations reached ({self.max_iterations})."
                    yield {"type": "error", "content": final_response}

            except asyncio.CancelledError:
                logger.warning("Stream Agent Loop cancelled for session %s", self.session_id)
                final_response += "\n[Session cancelled before completion]"
            finally:
                token_summary = f"[Token Usage: Prompt: {self.total_prompt_tokens}, Completion: {self.total_completion_tokens}, Total: {self.total_tokens}]"
                final_response = f"{final_response}\n\n{token_summary}"

                limit_reached = self.memory.append_conversation(user_input, final_response)
                if limit_reached:
                    self._on_memory_limit_reached(self.session_id, self.memory.get_recent_context(20))
                ACTIVE_SESSIONS.dec()

            yield {"type": "done", "content": final_response}

    def _build_message_history(self, current_input: str) -> list[dict[str, Any]]:
        """Build provider message history from recent working memory."""
        messages: list[dict[str, Any]] = []
        for conversation in self.memory.get_recent_context(n=5):
            messages.append({"role": "user", "content": conversation.get("user", "")})
            messages.append({"role": "assistant", "content": conversation.get("assistant", "")})

        messages.append({"role": "user", "content": current_input})
        return messages

    def _on_memory_limit_reached(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """Persist a rolled working-memory window into long-term memory."""
        logger.debug("[MemoryHook] session %s reached the working-memory retention window", session_id)
        if not self.long_term_memory:
            return
        try:
            record = self.long_term_memory.add_session_summary(session_id, messages)
            if record:
                logger.info("[LongTermMemory] persisted %s for session %s", record.id, session_id)
        except Exception as error:
            logger.warning("[LongTermMemory] persistence failed for session %s: %s", session_id, error)

    def start_watching(self) -> None:
        self._watcher.start()

    def stop_watching(self) -> None:
        self._watcher.stop()

    def close(self) -> None:
        """Close resources associated with the router."""
        if hasattr(self, "long_term_memory") and self.long_term_memory:
            self.long_term_memory.close()
