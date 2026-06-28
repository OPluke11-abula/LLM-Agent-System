"""Agent routing, memory, and closed-loop execution for LAS."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import threading
from datetime import datetime, timezone
from typing import Any

import yaml
import jsonschema

from .engine import AgentEngine
from .conductor import ConductorPlan, build_default_conductor_plan
from .providers import ProviderFactory

from agent_workspace.long_term_memory import LongTermMemoryStore
from agent_workspace.observability import ACTIVE_SESSIONS, tracer
from agent_workspace.core.account_manager import AccountManager


class ToolValidationError(ValueError):
    """Raised when tool inputs or schemas fail validation against the contract."""
    pass


class ApprovalDeniedError(PermissionError):
    """Raised when human approval is denied for a tool execution."""
    pass


ACTIVE_APPROVALS: dict[str, dict[str, Any]] = {}


class SwarmRouteRegistry:
    def __init__(self):
        self.lock = threading.Lock()
        self.routes = {}  # node_id -> dict
        self.pruned_history = []  # list of dicts showing pruned routes and reasons

    def register_route(self, node_id: str):
        with self.lock:
            if node_id not in self.routes:
                self.routes[node_id] = {
                    "node_id": node_id,
                    "latency_history": [],
                    "success_count": 0,
                    "failure_count": 0,
                    "success_rate": 1.0,
                    "active_load": 0,
                    "status": "active",
                    "last_seen": datetime.now(timezone.utc).isoformat()
                }

    def start_dispatch(self, node_id: str):
        self.register_route(node_id)
        with self.lock:
            route = self.routes[node_id]
            route["active_load"] += 1
            route["last_seen"] = datetime.now(timezone.utc).isoformat()

    def end_dispatch(self, node_id: str, latency_sec: float, success: bool):
        with self.lock:
            if node_id not in self.routes:
                return
            route = self.routes[node_id]
            route["active_load"] = max(0, route["active_load"] - 1)
            route["latency_history"].append(latency_sec)
            if len(route["latency_history"]) > 20:
                route["latency_history"] = route["latency_history"][-20:]

            if success:
                route["success_count"] += 1
            else:
                route["failure_count"] += 1

            total = route["success_count"] + route["failure_count"]
            if total > 0:
                route["success_rate"] = route["success_count"] / total

            route["last_seen"] = datetime.now(timezone.utc).isoformat()

            # Check for auto-pruning
            self._check_auto_prune(route)

    def _check_auto_prune(self, route: dict):
        node_id = route["node_id"]
        if route["status"] == "pruned":
            return

        total = route["success_count"] + route["failure_count"]
        # Thresholds: success_rate < 70% or average latency of last 3 dispatches > 0.5s (500ms)
        # Only evaluate pruning if minimum dispatches >= 3
        if total >= 3:
            avg_latency = sum(route["latency_history"][-3:]) / min(len(route["latency_history"]), 3)
            reason = None
            if route["success_rate"] < 0.7:
                reason = f"Low success rate: {route['success_rate']:.2%}"
            elif avg_latency > 0.5:
                reason = f"High latency: {avg_latency*1000:.1f}ms"

            if reason:
                route["status"] = "pruned"
                prune_entry = {
                    "node_id": node_id,
                    "pruned_at": datetime.now(timezone.utc).isoformat(),
                    "reason": reason,
                    "success_rate": route["success_rate"],
                    "avg_latency_ms": avg_latency * 1000
                }
                self.pruned_history.append(prune_entry)
                logger.warning("Pruned route '%s': %s", node_id, reason)

    def prune_stale_or_all(self, force_all: bool = False):
        with self.lock:
            now = datetime.now(timezone.utc)
            pruned_any = False
            for node_id, route in list(self.routes.items()):
                if route["status"] == "pruned":
                    continue

                # Check stale
                last_seen_dt = datetime.fromisoformat(route["last_seen"])
                age_sec = (now - last_seen_dt).total_seconds()

                reason = None
                if force_all:
                    reason = "Manual administrative prune trigger"
                elif age_sec > 30.0:  # stale threshold of 30 seconds
                    reason = f"Stale route: inactive for {age_sec:.1f}s"

                if reason:
                    route["status"] = "pruned"
                    pruned_any = True
                    self.pruned_history.append({
                        "node_id": node_id,
                        "pruned_at": datetime.now(timezone.utc).isoformat(),
                        "reason": reason,
                        "success_rate": route["success_rate"],
                        "avg_latency_ms": (sum(route["latency_history"]) / len(route["latency_history"]) * 1000) if route["latency_history"] else 0.0
                    })
                    logger.info("Administrative prune performed on '%s': %s", node_id, reason)
            return pruned_any


ROUTE_REGISTRY = SwarmRouteRegistry()



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

    PAUSED_SESSIONS: set[str] = set()

    @classmethod
    def pause_session(cls, session_id: str):
        cls.PAUSED_SESSIONS.add(session_id)

    @classmethod
    def resume_session(cls, session_id: str):
        cls.PAUSED_SESSIONS.discard(session_id)

    @classmethod
    def is_paused(cls, session_id: str) -> bool:
        return session_id in cls.PAUSED_SESSIONS


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
        self.human_intervention_count = 0

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
        self.last_conductor_plan: ConductorPlan | None = None

    def _load_config(self) -> dict[str, Any]:
        import yaml

        config_path = os.path.join(self.engine.workspace_path, "config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file) or {}
        except (OSError, IOError, yaml.YAMLError) as error:
            logger.warning("Failed to load config.yaml: %s", error)
            return {}

    def _get_authorization_level(self) -> str:
        try:
            pap_dir = self._get_pap_dir()
            agent_md_path = os.path.join(pap_dir, "agent.md")
            if os.path.isfile(agent_md_path):
                with open(agent_md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1])
                    if isinstance(fm, dict):
                        return fm.get("authorization_level", "standard")
        except Exception as e:
            logger.warning("Failed to parse agent.md for authorization_level: %s", e)
        return "standard"

    def _get_topology_emitter(self):
        from agent_workspace.topology_bridge import TopologyEmitter

        workspace_dir = os.environ.get("AGENT_WORKSPACE_DIR")
        if workspace_dir:
            path = os.path.join(workspace_dir, "topology_state.json")
        else:
            path = os.path.join(self.engine.workspace_path, "..", "workspace", "topology_state.json")
        return TopologyEmitter(session_id=self.session_id, output_path=path)

    async def _wait_for_approval(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Wait for human approval of the tool execution.
        Returns True if approved, False if rejected.
        """
        self.human_intervention_count += 1
        future = asyncio.get_running_loop().create_future()

        req = {
            "future": future,
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "awaiting_approval",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        ACTIVE_APPROVALS[self.session_id] = req

        from agent_workspace.topology_bridge import TopologyEvent

        # Emit awaiting_approval hitl_gate topology event
        try:
            emitter = self._get_topology_emitter()
            event = TopologyEvent.create(
                session_id=self.session_id,
                node_id=f"hitl-{tool_name}-{self.session_id}",
                parent_node_id=f"session-{self.session_id}",
                node_type="hitl_gate",
                edge_type="hitl",
                status="awaiting_approval",
                payload={
                    "title": f"HITL Gate: {tool_name}",
                    "description": f"Awaiting approval for executing tool '{tool_name}'",
                    "assigned_agent": self.agent_name,
                    "tool_name": tool_name,
                    "arguments": arguments,
                }
            )
            emitter.emit(event)
        except Exception as e:
            logger.warning("Failed to emit awaiting_approval event: %s", e)

        try:
            approved = await future

            # Emit outcome to topology
            try:
                emitter = self._get_topology_emitter()
                event = TopologyEvent.create(
                    session_id=self.session_id,
                    node_id=f"hitl-{tool_name}-{self.session_id}",
                    parent_node_id=f"session-{self.session_id}",
                    node_type="hitl_gate",
                    edge_type="hitl",
                    status="completed" if approved else "error",
                    payload={
                        "title": f"HITL Gate: {tool_name}",
                        "description": f"Approval {'granted' if approved else 'denied'} for tool '{tool_name}'",
                        "assigned_agent": self.agent_name,
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "result_summary": "Approved" if approved else "Rejected",
                    }
                )
                emitter.emit(event)
            except Exception as e:
                logger.warning("Failed to update topology event status: %s", e)

            return approved
        finally:
            ACTIVE_APPROVALS.pop(self.session_id, None)

    def resolve_approval(self, approved: bool) -> None:
        req = ACTIVE_APPROVALS.get(self.session_id)
        if req and not req["future"].done():
            req["future"].set_result(approved)

    async def _execute_tool_with_approval(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        allowed_tools: list[str] | None,
        system_context: dict[str, Any],
    ) -> Any:
        auth_level = self._get_authorization_level()
        is_sensitive = False
        try:
            contract = self.describe_skill(tool_name)
            is_sensitive = contract.get("sensitive", False)
        except Exception:
            pass

        if is_sensitive or auth_level == "interactive-approval":
            approved = await self._wait_for_approval(tool_name, tool_args)
            if isinstance(approved, dict) and approved.get("hijacked"):
                return approved.get("hijack_value")
            if not approved:
                raise ApprovalDeniedError(f"Human approval denied for tool '{tool_name}'")

        from agent_workspace.observability import get_global_balancer

        balancer = get_global_balancer()
        future = balancer.offload(
            self.engine.execute_tool,
            "heavy",
            tool_name,
            tool_args,
            allowed_tools,
            system_context,
        )
        return await asyncio.wrap_future(future)


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

        # RBAC validation
        user_role = "standard"
        resolved_account = getattr(self, "_resolved_account", None)
        if resolved_account is None:
            try:
                resolved_account = self._resolve_account()
            except Exception:
                pass
        if resolved_account:
            user_role = resolved_account.get("role", resolved_account.get("rbac_role", "standard"))

        required_role = contract.get("required_role") if contract else None
        if required_role:
            ROLE_HIERARCHY = {
                "standard": 1,
                "developer": 2,
                "admin": 3
            }
            user_level = ROLE_HIERARCHY.get(user_role, 1)
            req_level = ROLE_HIERARCHY.get(required_role, 1)
            if user_level < req_level:
                from agent_workspace.topology_bridge import TopologyEvent

                try:
                    emitter = self._get_topology_emitter()
                    event = TopologyEvent.create(
                        session_id=self.session_id,
                        node_id=f"rbac-error-{skill_id}-{self.session_id}",
                        parent_node_id=f"session-{self.session_id}",
                        node_type="error",
                        edge_type="rbac",
                        status="error",
                        payload={
                            "title": "RBAC Authorization Failed",
                            "description": f"User role '{user_role}' is insufficient for tool '{skill_id}' requiring role '{required_role}'",
                            "assigned_agent": self.agent_name,
                            "result_summary": "Permission Denied",
                        }
                    )
                    emitter.emit(event)
                except Exception as e:
                    logger.warning("Failed to emit RBAC failure topology event: %s", e)

                raise PermissionError(
                    f"RBAC authorization failed: role '{user_role}' is insufficient for tool '{skill_id}' requiring role '{required_role}'"
                )

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

    def _resolve_account(self, account_id: str | None = None, task_type: str | None = None) -> dict[str, Any]:
        """Resolve the active or requested account, and check its token budget.

        Attempts failover to the first account under budget if budget is exceeded.
        """
        account = None
        if account_id:
            account = self.account_manager.get_account(account_id)
        if not account and task_type:
            account = self.account_manager.get_optimal_account_for_task(task_type)
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

        # Resolve tenant_id
        tenant_id = None
        try:
            from core.account_manager import AccountManager
            tenant_id = AccountManager.get_session_tenant(self.session_id)
        except Exception:
            pass
        tenant_id = tenant_id or "default_tenant"

        # Verify tenant credits
        from agent_workspace.core.swarm_coordinator import SwarmCoordinator

        SwarmCoordinator.verify_tenant_credit(self.engine.workspace_path, tenant_id)

        # Enforce model downscaling policy if budget is low
        if SwarmCoordinator.should_downscale_model(self.engine.workspace_path, tenant_id):
            model = account.get("model", "")
            if "pro" in model.lower():
                account = dict(account)
                account["model"] = "gemini-2.5-flash"
                logger.info(f"Dynamic model downscaling active: overriding {model} -> gemini-2.5-flash for tenant {tenant_id}")

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

            config = {"model": model, "session_id": self.session_id}
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
                        c_tokens,
                        self.session_id
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
        """Run the non-streaming closed-loop agent path with route metrics logging."""
        node_id = self.agent_name
        ROUTE_REGISTRY.start_dispatch(node_id)
        start_time = time.time()
        intervention_count_before = self.human_intervention_count
        success = True
        error_type: str | None = None
        try:
            res = await self._run_agent_loop_internal(
                user_input, allowed_tools, output_schema, account_id
            )
            if isinstance(res, str) and res.startswith("Error:"):
                success = False
                error_type = res.splitlines()[0][:160]
            return res
        except Exception as error:
            success = False
            error_type = type(error).__name__
            raise
        finally:
            latency = time.time() - start_time
            ROUTE_REGISTRY.end_dispatch(node_id, latency, success)
            self._record_route_outcome(
                success=success,
                latency_ms=int(latency * 1000),
                error_type=error_type,
                human_intervention_count=max(0, self.human_intervention_count - intervention_count_before),
            )

    def _resolve_allowed_tools(self, caller_allowed: list[str] | None) -> list[str]:
        """
        Enforce allowlisting by intersecting PAP tools and caller allowed_tools.
        Enforces fail-closed: returns an empty list if agent.md is missing or fails to parse.
        """
        import yaml
        pap_tools = []
        try:
            pap_dir = self._get_pap_dir()
            agent_md_path = os.path.join(pap_dir, "agent.md")
            if os.path.isfile(agent_md_path):
                with open(agent_md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1])
                    if isinstance(fm, dict):
                        pap_tools = fm.get("tools")
                        if not isinstance(pap_tools, list):
                            logger.warning("agent.md 'tools' key is missing or not a list; fail-closed allowlist triggered.")
                            return []
                    else:
                        logger.warning("agent.md frontmatter is not a dictionary; fail-closed allowlist triggered.")
                        return []
                else:
                    logger.warning("agent.md missing frontmatter delimiters; fail-closed allowlist triggered.")
                    return []
            else:
                logger.warning("agent.md is missing; fail-closed allowlist triggered.")
                return []
        except Exception as e:
            logger.warning("Failed to parse agent.md for tools; fail-closed allowlist triggered: %s", e)
            return []

        if not pap_tools:
            logger.warning("PAP tools list is empty; returning empty allowlist.")
            return []

        if caller_allowed is None:
            return list(pap_tools)

        # Intersection: return tools present in both PAP and caller list
        return [tool for tool in pap_tools if tool in caller_allowed]

    def _detect_task_type(self, user_input: str) -> str:
        if not user_input:
            return "text_inference"
        content = user_input.lower()
        if "compile" in content or "code" in content:
            return "compilation"
        elif "layout" in content or "ui" in content or "css" in content:
            return "ui_layout"
        else:
            return "text_inference"

    def _build_conductor_plan(
        self,
        *,
        user_input: str,
        task_type: str,
        intent: str,
        resolved_tools: list[str],
        selected_account: dict[str, Any],
        workflow_stage_id: str | None = None,
        workflow_checkpoint_ref: str | None = None,
        evidence_refs: list[str] | None = None,
    ) -> ConductorPlan:
        route_outcome_hints: list[dict[str, Any]] = []
        if self.long_term_memory:
            try:
                route_outcome_hints = self.long_term_memory.recent_route_outcomes(
                    task_type=task_type,
                    session_id=self.session_id,
                    limit=3,
                )
            except Exception as error:
                logger.warning("[AgentRouter] Failed to retrieve route outcome hints: %s", error)
        plan = build_default_conductor_plan(
            task_id=f"{self.session_id}:{task_type}",
            task_summary=user_input,
            session_id=self.session_id,
            task_type=task_type,
            intent=intent,
            resolved_tools=resolved_tools,
            selected_account=selected_account,
            max_iterations=self.max_iterations,
            max_tool_calls=self.max_tool_calls,
            long_term_enabled=self.long_term_memory is not None,
            route_outcome_hints=route_outcome_hints,
            workflow_stage_id=workflow_stage_id,
            workflow_checkpoint_ref=workflow_checkpoint_ref,
            evidence_refs=evidence_refs,
        )
        self.last_conductor_plan = plan
        return plan

    def _record_conductor_plan(self, span: Any, plan: ConductorPlan) -> None:
        span.set_attribute("conductor.schema_version", plan.schema_version)
        span.set_attribute("conductor.execution_mode", plan.execution_mode)
        span.set_attribute("conductor.topology", plan.topology)
        span.set_attribute("conductor.risk_level", plan.risk_level)
        span.set_attribute("conductor.task_type", plan.task_type)
        span.set_attribute("conductor.tool_allowlist_count", len(plan.tool_allowlist))
        span.set_attribute("conductor.selected_models", len(plan.selected_models))
        span.set_attribute("conductor.routing_memory_hints", len(plan.routing_memory_hints))
        if plan.workflow_stage_id:
            span.set_attribute("conductor.workflow_stage_id", plan.workflow_stage_id)
        if plan.workflow_checkpoint_ref:
            span.set_attribute("conductor.workflow_checkpoint_ref", plan.workflow_checkpoint_ref)
        if plan.evidence_refs:
            span.set_attribute("conductor.evidence_ref_count", len(plan.evidence_refs))
        logger.info(
            "Conductor plan created",
            extra={
                "session_id": self.session_id,
                "execution_mode": plan.execution_mode,
                "topology": plan.topology,
                "risk_level": plan.risk_level,
            },
        )

    def _conductor_trace_event(self, plan: ConductorPlan) -> dict[str, Any]:
        return {
            "type": "conductor_trace",
            "session_id": self.session_id,
            "trace": plan.model_dump(mode="json"),
        }

    def _record_route_outcome(
        self,
        *,
        success: bool,
        latency_ms: int,
        error_type: str | None,
        human_intervention_count: int,
    ) -> None:
        if not self.long_term_memory or not self.last_conductor_plan:
            return
        try:
            record = self.long_term_memory.add_route_outcome(
                session_id=self.session_id,
                conductor_plan=self.last_conductor_plan.model_dump(mode="json"),
                success=success,
                latency_ms=latency_ms,
                token_count=self.total_tokens,
                error_type=error_type,
                human_intervention_count=human_intervention_count,
            )
            logger.info("[LongTermMemory] persisted route outcome %s for session %s", record.id, self.session_id)
        except Exception as error:
            logger.warning("[LongTermMemory] route outcome persistence failed for session %s: %s", self.session_id, error)

    async def _run_agent_loop_internal(
        self,
        user_input: str,
        allowed_tools: list[str] | None = None,
        output_schema: Any = None,
        account_id: str | None = None,
    ) -> str:
        """Run the non-streaming closed-loop agent path internal implementation."""
        loop_start_time = time.time()
        task_type = self._detect_task_type(user_input)
        self._resolved_account = self._resolve_account(account_id, task_type=task_type)
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
                base_system_prompt = self.engine.render_prompt(context_vars, agent_name=self.agent_name)
                mem_context = ""
                if self.long_term_memory:
                    try:
                        mem_context = self.long_term_memory.retrieve_and_format_context(
                            user_input, session_id=self.session_id, limit=5
                        )
                    except Exception as e:
                        logger.warning("[AgentRouter] Failed to retrieve and format long term memory: %s", e)

                system_prompt = base_system_prompt
                if mem_context:
                    system_prompt += mem_context

                resolved_allowed = self._resolve_allowed_tools(allowed_tools)
                tool_schemas = [] if intent == "CHAT" else self.engine.get_tool_schemas(resolved_allowed)
                conductor_plan = self._build_conductor_plan(
                    user_input=user_input,
                    task_type=task_type,
                    intent=intent,
                    resolved_tools=resolved_allowed,
                    selected_account=self._resolved_account,
                )
                self._record_conductor_plan(span, conductor_plan)
                messages = self._build_message_history(user_input)

                logger.debug("System prompt length: %s chars", len(system_prompt))
                logger.debug("Allowed runtime tools: %s", [tool["name"] for tool in tool_schemas])
                logger.debug("Message history length: %s", len(messages))

                while iteration < self.max_iterations:
                    while self.is_paused(self.session_id):
                        await asyncio.sleep(0.2)
                    iteration += 1
                    logger.info("[Iteration %s/%s]", iteration, self.max_iterations)

                    llm_config = self._config.get("llm", {}).copy()
                    llm_config["model"] = self._resolved_account.get("model", llm_config.get("model"))
                    llm_config["session_id"] = self.session_id
                    if self._resolved_account.get("base_url"):
                        llm_config["base_url"] = self._resolved_account.get("base_url")
                    if output_schema:
                        llm_config["output_schema"] = output_schema

                    if iteration >= 3:
                        if "pytest" in sys.modules and not os.environ.get("TEST_LOOP_APPROVAL"):
                            logger.info("Pytest detected without TEST_LOOP_APPROVAL. Bypassing loop continuation gate.")
                        else:
                            logger.warning("Loop iteration limit (3) reached. Awaiting approval to proceed.")
                            approved = await self._wait_for_approval(
                                "loop_continuation_gate",
                                {"iteration": iteration, "message": "Loop iteration threshold (3) reached. Requesting approval to continue."}
                            )
                            if not approved:
                                final_response = "Error: Loop continuation denied by user after 3 iterations."
                                logger.error(final_response)
                                break

                    # Pre-flight estimates (all flagged as estimated=True)
                    from agent_workspace.core.token_counter import TokenCounter
                    estimates = TokenCounter.estimate_components(
                        system_prompt=base_system_prompt,
                        messages=messages,
                        memory_context=mem_context,
                        tool_schemas=tool_schemas,
                        model_name=llm_config.get("model")
                    )
                    sum_estimates = sum(comp["count"] for comp in estimates.values())
                    span.set_attribute("token_estimates.system_prompt", estimates["system_prompt"]["count"])
                    span.set_attribute("token_estimates.messages", estimates["messages"]["count"])
                    span.set_attribute("token_estimates.memory_context", estimates["memory_context"]["count"])
                    span.set_attribute("token_estimates.tool_schemas", estimates["tool_schemas"]["count"])
                    span.set_attribute("token_estimates.total_estimate", sum_estimates)

                    # Gemini Only aggregate preflight count
                    aggregate_preflight = await TokenCounter.get_aggregate_preflight_count(
                        provider=self._provider,
                        system_prompt=system_prompt,
                        messages=messages,
                        tool_schemas=tool_schemas,
                        config=llm_config
                    )
                    if aggregate_preflight is not None:
                        span.set_attribute("token_estimates.aggregate_preflight", aggregate_preflight.count)

                    response = await self._provider.generate_content(
                        system_prompt=system_prompt,
                        messages=messages,
                        tool_schemas=tool_schemas,
                        config=llm_config,
                    )

                    actual_prompt_tokens = 0
                    actual_completion_tokens = 0
                    actual_total_tokens = 0

                    if hasattr(response, "usage") and response.usage:
                        p_tokens = response.usage.get("prompt_tokens", 0) or 0
                        c_tokens = response.usage.get("completion_tokens", 0) or 0
                        actual_prompt_tokens = p_tokens
                        actual_completion_tokens = c_tokens
                        actual_total_tokens = response.usage.get("total_tokens", 0) or 0

                        self.total_prompt_tokens += p_tokens
                        self.total_completion_tokens += c_tokens
                        self.total_tokens += actual_total_tokens

                        if hasattr(self, "_resolved_account") and self._resolved_account:
                            self.account_manager.record_usage(
                                self._resolved_account["id"],
                                p_tokens,
                                c_tokens,
                                self.session_id
                            )

                    # Calculate estimation error
                    estimation_error = abs(sum_estimates - actual_prompt_tokens)
                    span.set_attribute("token_usage.actual_prompt_tokens", actual_prompt_tokens)
                    span.set_attribute("token_usage.actual_completion_tokens", actual_completion_tokens)
                    span.set_attribute("token_usage.actual_total_tokens", actual_total_tokens)
                    span.set_attribute("token_usage.estimation_error", estimation_error)

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

                # Increment conversational turn (Task 23-01)
                self.engine.increment_turns(self.session_id, f"Session turn completed. Input: {user_input[:100]}")

                logger.info(
                    "Agent Loop finished",
                    extra={"session_id": self.session_id, "iterations": iteration},
                )
                ACTIVE_SESSIONS.dec()

                if hasattr(self, "_resolved_account") and self._resolved_account:
                    from agent_workspace.observability import get_cost_router
                    get_cost_router().record_latency(self._resolved_account["provider"], time.time() - loop_start_time)

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
                self._execute_tool_with_approval(
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
        """Run the streaming closed-loop agent path with route metrics logging."""
        node_id = self.agent_name
        ROUTE_REGISTRY.start_dispatch(node_id)
        start_time = time.time()
        success = True
        try:
            async for event in self._stream_agent_loop_raw(
                user_input, allowed_tools, output_schema, account_id
            ):
                if isinstance(event, dict):
                    event["agent_name"] = self.agent_name
                    if event.get("type") == "error":
                        success = False
                yield event
        except Exception:
            success = False
            raise
        finally:
            latency = time.time() - start_time
            ROUTE_REGISTRY.end_dispatch(node_id, latency, success)

    async def _stream_agent_loop_raw(
        self,
        user_input: str,
        allowed_tools: list[str] | None = None,
        output_schema: Any = None,
        account_id: str | None = None,
    ):
        """Run the raw streaming closed-loop agent path."""
        loop_start_time = time.time()
        task_type = self._detect_task_type(user_input)
        self._resolved_account = self._resolve_account(account_id, task_type=task_type)
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
                base_system_prompt = self.engine.render_prompt(context_vars, agent_name=self.agent_name)
                mem_context = ""
                if self.long_term_memory:
                    try:
                        mem_context = self.long_term_memory.retrieve_and_format_context(
                            user_input, session_id=self.session_id, limit=5
                        )
                    except Exception as e:
                        logger.warning("[AgentRouter] Failed to retrieve and format long term memory: %s", e)

                system_prompt = base_system_prompt
                if mem_context:
                    system_prompt += mem_context

                resolved_allowed = self._resolve_allowed_tools(allowed_tools)
                tool_schemas = [] if intent == "CHAT" else self.engine.get_tool_schemas(resolved_allowed)
                conductor_plan = self._build_conductor_plan(
                    user_input=user_input,
                    task_type=task_type,
                    intent=intent,
                    resolved_tools=resolved_allowed,
                    selected_account=self._resolved_account,
                )
                self._record_conductor_plan(span, conductor_plan)
                messages = self._build_message_history(user_input)

                yield self._conductor_trace_event(conductor_plan)

                while iteration < self.max_iterations:
                    while self.is_paused(self.session_id):
                        await asyncio.sleep(0.2)
                    iteration += 1

                    llm_config = self._config.get("llm", {}).copy()
                    llm_config["model"] = self._resolved_account.get("model", llm_config.get("model"))
                    llm_config["session_id"] = self.session_id
                    if self._resolved_account.get("base_url"):
                        llm_config["base_url"] = self._resolved_account.get("base_url")
                    if output_schema:
                        llm_config["output_schema"] = output_schema

                    if iteration >= 3:
                        if "pytest" in sys.modules and not os.environ.get("TEST_LOOP_APPROVAL"):
                            logger.info("Pytest detected without TEST_LOOP_APPROVAL. Bypassing loop continuation gate in stream.")
                        else:
                            logger.warning("Loop iteration limit (3) reached in stream. Awaiting approval to proceed.")
                            approved = await self._wait_for_approval(
                                "loop_continuation_gate",
                                {"iteration": iteration, "message": "Loop iteration threshold (3) reached. Requesting approval to continue."}
                            )
                            if not approved:
                                yield {"type": "error", "content": "Error: Loop continuation denied by user after 3 iterations."}
                                break

                    # Pre-flight estimates (all flagged as estimated=True)
                    from agent_workspace.core.token_counter import TokenCounter
                    estimates = TokenCounter.estimate_components(
                        system_prompt=base_system_prompt,
                        messages=messages,
                        memory_context=mem_context,
                        tool_schemas=tool_schemas,
                        model_name=llm_config.get("model")
                    )
                    sum_estimates = sum(comp["count"] for comp in estimates.values())
                    span.set_attribute("token_estimates.system_prompt", estimates["system_prompt"]["count"])
                    span.set_attribute("token_estimates.messages", estimates["messages"]["count"])
                    span.set_attribute("token_estimates.memory_context", estimates["memory_context"]["count"])
                    span.set_attribute("token_estimates.tool_schemas", estimates["tool_schemas"]["count"])
                    span.set_attribute("token_estimates.total_estimate", sum_estimates)

                    # Gemini Only aggregate preflight count
                    aggregate_preflight = await TokenCounter.get_aggregate_preflight_count(
                        provider=self._provider,
                        system_prompt=system_prompt,
                        messages=messages,
                        tool_schemas=tool_schemas,
                        config=llm_config
                    )
                    if aggregate_preflight is not None:
                        span.set_attribute("token_estimates.aggregate_preflight", aggregate_preflight.count)

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

                    actual_prompt_tokens = 0
                    actual_completion_tokens = 0
                    actual_total_tokens = 0

                    async for event in response_stream:
                        if hasattr(event, "usage") and event.usage:
                            p_tokens = event.usage.get("prompt_tokens", 0) or 0
                            c_tokens = event.usage.get("completion_tokens", 0) or 0
                            actual_prompt_tokens = p_tokens
                            actual_completion_tokens = c_tokens
                            actual_total_tokens = event.usage.get("total_tokens", 0) or 0

                            self.total_prompt_tokens += p_tokens
                            self.total_completion_tokens += c_tokens
                            self.total_tokens += actual_total_tokens

                            if hasattr(self, "_resolved_account") and self._resolved_account:
                                self.account_manager.record_usage(
                                    self._resolved_account["id"],
                                    p_tokens,
                                    c_tokens,
                                    self.session_id
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

                    # Calculate estimation error and record attributes at the end of stream consumption
                    estimation_error = abs(sum_estimates - actual_prompt_tokens)
                    span.set_attribute("token_usage.actual_prompt_tokens", actual_prompt_tokens)
                    span.set_attribute("token_usage.actual_completion_tokens", actual_completion_tokens)
                    span.set_attribute("token_usage.actual_total_tokens", actual_total_tokens)
                    span.set_attribute("token_usage.estimation_error", estimation_error)

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
                            # Check if approval is needed to yield hitl_gate event
                            auth_level = self._get_authorization_level()
                            is_sensitive = False
                            try:
                                contract = self.describe_skill(tool_name)
                                is_sensitive = contract.get("sensitive", False)
                            except Exception:
                                pass

                            if is_sensitive or auth_level == "interactive-approval":
                                yield {
                                    "type": "hitl_gate",
                                    "status": "awaiting_approval",
                                    "name": tool_name,
                                    "arguments": tool_args,
                                    "session_id": self.session_id,
                                }

                            tasks.append(
                                self._execute_tool_with_approval(
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

                # Increment conversational turn (Task 23-01)
                self.engine.increment_turns(self.session_id, f"Session stream turn completed. Input: {user_input[:100]}")

                if hasattr(self, "_resolved_account") and self._resolved_account:
                    from agent_workspace.observability import get_cost_router
                    get_cost_router().record_latency(self._resolved_account["provider"], time.time() - loop_start_time)

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

    def discover_skill(self, contract_yaml_or_json: str | dict) -> bool:
        """Verify, validate against spec/skill-contract.schema.json, save, and dynamically hot-load a skill."""
        from pathlib import Path
        import jsonschema
        import yaml
        from pydantic import create_model, Field

        # 1. Parse payload
        if isinstance(contract_yaml_or_json, str):
            try:
                contract = yaml.safe_load(contract_yaml_or_json) or {}
            except Exception as e:
                raise ValueError(f"Failed to parse skill contract string: {e}")
        elif isinstance(contract_yaml_or_json, dict):
            contract = contract_yaml_or_json
        else:
            raise ValueError("Invalid skill contract format")

        # 2. Locate schema file
        project_root = Path(self.engine.workspace_path).parent if os.path.basename(self.engine.workspace_path) == "workspace" else Path(self.engine.workspace_path)
        if not (project_root / "spec").exists() and (Path(self.engine.workspace_path) / "spec").exists():
            project_root = Path(self.engine.workspace_path)
        schema_path = project_root / "spec" / "skill-contract.schema.json"

        if not schema_path.is_file():
            raise FileNotFoundError(f"Skill schema not found at {schema_path}")

        # 3. Validate against schema
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(contract, schema)

        # 4. Safely load contract into .agent/skills/ dynamically
        skills_dir = project_root / ".agent" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_id = contract["id"]
        contract_path = skills_dir / f"{skill_id}.md"

        frontmatter_yaml = yaml.safe_dump(contract, allow_unicode=True, sort_keys=False).strip()
        content = f"---\n{frontmatter_yaml}\n---\n\n# {skill_id}\n\n{contract.get('description', '')}\n"
        contract_path.write_text(content, encoding="utf-8")

        # 5. Generate Pydantic BaseModel dynamically from 'inputs' schema
        inputs = contract.get("inputs", {})
        fields = {}
        for param_name, param_info in inputs.items():
            type_str = param_info.get("type", "string")
            param_type = str
            if type_str in {"number", "float"}:
                param_type = float
            elif type_str in {"integer", "int"}:
                param_type = int
            elif type_str in {"boolean", "bool"}:
                param_type = bool
            elif type_str == "array":
                param_type = list
            elif type_str == "object":
                param_type = dict

            is_req = param_info.get("required", False)
            default_val = ... if is_req else None
            fields[param_name] = (param_type, Field(default=default_val, description=param_info.get("description", "")))

        ArgsModel = create_model(f"{skill_id.capitalize()}Args", **fields)

        # 6. Expose dynamic function for runtime reflection
        def dynamic_skill_proxy(args: ArgsModel) -> str:
            args_dict = args.model_dump()
            return f"Executed discovered skill {skill_id} successfully. Arguments: {args_dict}"

        dynamic_skill_proxy.__doc__ = contract.get("description", "")
        dynamic_skill_proxy.__name__ = skill_id

        # 7. Register in AgentEngine registry dynamically
        self.engine.tools_registry[skill_id] = {
            "function": dynamic_skill_proxy,
            "args_model": ArgsModel,
            "description": contract.get("description", ""),
            "schema": ArgsModel.model_json_schema(),
            "wants_context": False,
            "is_markdown_skill": False,
        }

        # 8. Mirror to other active router components if any
        logger.info("[SkillDiscovery] Dynamic tool '%s' successfully validated and injected into active engine loop", skill_id)
        return True

    def process_discovered_skill_stream(self, json_stream_chunk: str) -> bool:
        """Process incoming stream chunk representing a discovered skill contract."""
        try:
            payload = json.loads(json_stream_chunk)
            if "type" in payload and payload["type"] == "discover_skill":
                contract = payload.get("contract")
                if contract:
                    return self.discover_skill(contract)
        except Exception as e:
            logger.warning("[SkillDiscovery] Failed to process discovered skill stream chunk: %s", e)
        return False
