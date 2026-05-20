"""Agent routing, memory, and closed-loop execution for LAS."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

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

    async def _classify_intent(self, user_input: str) -> str:
        """Return TASK when tools may be needed, otherwise CHAT."""
        prompt = (
            "You are an intent classifier. Determine if the user's input requires executing any tools/tasks "
            "(like calculating, fetching data, creating files) or if it is just a simple greeting/chat. "
            "Reply EXACTLY with 'TASK' or 'CHAT'.\n\n"
            f"User input: {user_input}"
        )
        try:
            resp = await self._provider.generate_content(
                system_prompt="You are an intent classifier.",
                messages=[{"role": "user", "content": prompt}],
                tool_schemas=[],
                config=self._config.get("llm", {}),
            )
            resp_type, resp_data = resp
            if hasattr(resp, "usage") and resp.usage:
                self.total_prompt_tokens += resp.usage.get("prompt_tokens", 0) or 0
                self.total_completion_tokens += resp.usage.get("completion_tokens", 0) or 0
                self.total_tokens += resp.usage.get("total_tokens", 0) or 0

            if resp_type == "text" and "CHAT" in str(resp_data).upper():
                return "CHAT"
        except Exception:
            logger.debug("Intent classification failed; falling back to TASK.", exc_info=True)
        return "TASK"

    async def run_agent_loop(
        self,
        user_input: str,
        allowed_tools: list[str] | None = None,
        output_schema: Any = None,
    ) -> str:
        """Run the non-streaming closed-loop agent path."""
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
                    if output_schema:
                        llm_config["output_schema"] = output_schema

                    response = await self._provider.generate_content(
                        system_prompt=system_prompt,
                        messages=messages,
                        tool_schemas=tool_schemas,
                        config=llm_config,
                    )

                    if hasattr(response, "usage") and response.usage:
                        self.total_prompt_tokens += response.usage.get("prompt_tokens", 0) or 0
                        self.total_completion_tokens += response.usage.get("completion_tokens", 0) or 0
                        self.total_tokens += response.usage.get("total_tokens", 0) or 0

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
    ):
        """Run the streaming closed-loop agent path."""
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
                            self.total_prompt_tokens += event.usage.get("prompt_tokens", 0) or 0
                            self.total_completion_tokens += event.usage.get("completion_tokens", 0) or 0
                            self.total_tokens += event.usage.get("total_tokens", 0) or 0

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
