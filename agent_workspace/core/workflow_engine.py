"""Asynchronous n8n-like Workflow Engine for LAS.

Parses DAG steps from .agent/workflows/<id>.md, executes them step-by-step
with dynamic JSON payload passing, conditional branching, and checkpoint state resume.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, Template

try:
    from core.engine import AgentEngine
    from core.account_manager import AccountManager
    from core.providers import ProviderFactory
except ImportError:
    from agent_workspace.core.engine import AgentEngine
    from agent_workspace.core.account_manager import AccountManager
    from agent_workspace.core.providers import ProviderFactory

logger = logging.getLogger(__name__)


@dataclass
class StepState:
    step_id: str
    status: str = "pending"  # "pending", "running", "success", "failed", "skipped"
    output: Any = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


@dataclass
class WorkflowRunState:
    workflow_id: str
    session_id: str
    status: str = "pending"  # "pending", "running", "success", "failed"
    current_step_id: str | None = None
    steps: dict[str, StepState] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkflowEngine:
    """Core Workflow Engine executing n8n-like step workflows."""

    telemetry_callbacks = []

    @classmethod
    def register_callback(cls, callback):
        if callback not in cls.telemetry_callbacks:
            cls.telemetry_callbacks.append(callback)

    def __init__(self, engine: AgentEngine):
        self.engine = engine
        # We determine the project root directory
        self.project_root = Path(engine.workspace_path).parent
        self.workflows_dir = self.project_root / ".agent" / "workflows"
        self.runs_dir = self.workflows_dir / "runs"
        
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _get_workflow_file(self, workflow_id: str) -> Path:
        """Get the absolute path to a workflow markdown definition."""
        resolved = (self.workflows_dir / f"{workflow_id}.md").resolve()
        try:
            resolved.relative_to(self.workflows_dir.resolve())
        except ValueError:
            raise PermissionError("Directory traversal warning: Access denied outside workflow boundaries")
        return resolved

    def _get_run_file(self, session_id: str) -> Path:
        """Get the absolute path to a workflow run state snapshot."""
        resolved = (self.runs_dir / f"{session_id}.json").resolve()
        try:
            resolved.relative_to(self.runs_dir.resolve())
        except ValueError:
            raise PermissionError("Directory traversal warning: Access denied outside workflow run boundaries")
        return resolved

    def load_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Load and parse the declarative workflow from .agent/workflows/<id>.md."""
        workflow_file = self._get_workflow_file(workflow_id)
        if not workflow_file.is_file():
            raise FileNotFoundError(f"Workflow '{workflow_id}' not found at {workflow_file}")

        content = workflow_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            raise ValueError(f"Workflow file '{workflow_id}' is missing frontmatter start delimiter '---'")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Workflow file '{workflow_id}' is missing frontmatter end delimiter '---'")

        try:
            workflow_def = yaml.safe_load(parts[1])
        except yaml.YAMLError as err:
            raise ValueError(f"Failed to parse workflow '{workflow_id}' frontmatter YAML: {err}") from err

        if not isinstance(workflow_def, dict):
            raise ValueError(f"Workflow '{workflow_id}' frontmatter is not a dictionary")

        # Basic validation
        required = ["id", "name", "description", "version", "steps"]
        missing = [k for k in required if k not in workflow_def]
        if missing:
            raise ValueError(f"Workflow '{workflow_id}' is missing required fields: {missing}")

        return workflow_def

    def save_state(self, state: WorkflowRunState) -> None:
        """Serialize and persist the workflow run state to disk."""
        state.updated_at = datetime.now(timezone.utc).isoformat()
        run_file = self._get_run_file(state.session_id)
        
        # Convert objects to serializable dict
        data = {
            "workflow_id": state.workflow_id,
            "session_id": state.session_id,
            "status": state.status,
            "current_step_id": state.current_step_id,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
            "payload": state.payload,
            "steps": {
                step_id: asdict(step) for step_id, step in state.steps.items()
            }
        }
        run_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_state(self, session_id: str) -> WorkflowRunState | None:
        """Load and deserialize a workflow run state if it exists."""
        run_file = self._get_run_file(session_id)
        if not run_file.is_file():
            return None

        try:
            data = json.loads(run_file.read_text(encoding="utf-8"))
            steps = {}
            for step_id, step_data in data.get("steps", {}).items():
                steps[step_id] = StepState(
                    step_id=step_data["step_id"],
                    status=step_data["status"],
                    output=step_data["output"],
                    error=step_data["error"],
                    started_at=step_data["started_at"],
                    completed_at=step_data["completed_at"],
                )
            return WorkflowRunState(
                workflow_id=data["workflow_id"],
                session_id=data["session_id"],
                status=data["status"],
                current_step_id=data["current_step_id"],
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                payload=data.get("payload", {}),
                steps=steps,
            )
        except Exception as e:
            logger.warning("Failed to deserialize workflow run state for session %s: %s", session_id, e)
            return None

    def _resolve_placeholder(self, value: Any, context: dict[str, Any]) -> Any:
        """Evaluate parameter value dynamically using step outputs context."""
        if isinstance(value, str):
            if "{{" in value and "}}" in value:
                # Optimized fast-path: if the string is EXACTLY a single expression, return the raw object
                stripped = value.strip()
                if stripped.startswith("{{") and stripped.endswith("}}") and stripped.count("{{") == 1:
                    expr = stripped[2:-2].strip()
                    try:
                        # Safely resolve nested dictionary properties e.g., steps.step_1.output.result
                        parts = expr.split('.')
                        curr = context
                        for part in parts:
                            if isinstance(curr, dict) and part in curr:
                                curr = curr[part]
                            elif hasattr(curr, part):
                                curr = getattr(curr, part)
                            else:
                                break
                        else:
                            return curr
                    except Exception:
                        pass
                
                # Default Jinja2 interpolation
                template = Template(value)
                return template.render(**context)
            return value
        elif isinstance(value, dict):
            return {k: self._resolve_placeholder(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_placeholder(v, context) for v in value]
        return value

    async def _invoke_llm_healing(self, skill_id: str, params: dict[str, Any], error_msg: str) -> dict[str, Any]:
        """Invoke LLM correction call to auto-diagnose and patch step parameters."""
        lessons_learned_content = ""
        path_check = Path(self.project_root)
        lessons_file = path_check / ".agent" / "knowledge_base" / "lessons_learned.md"
        if lessons_file.is_file():
            try:
                lessons_learned_content = lessons_file.read_text(encoding="utf-8")
            except Exception:
                pass
        
        system_prompt = (
            "You are an expert self-healing engine for the LLM Agent System (LAS).\n"
            "A workflow step failed executing a skill.\n"
            "Your task is to analyze the traceback/error and the original parameters, "
            "cross-reference them with the lessons learned registry, and generate a parameters patch (JSON format).\n"
            f"Lessons Learned Database:\n{lessons_learned_content}\n\n"
            "Respond ONLY with a valid JSON object representing the fully corrected/patched parameters for the skill execution. "
            "Do not include any explanation or markdown formatting (like ```json ... ```) - just return raw JSON."
        )
        
        user_content = (
            f"Skill Failed: {skill_id}\n"
            f"Original Parameters: {json.dumps(params, ensure_ascii=False)}\n"
            f"Traceback/Error: {error_msg}\n\n"
            "Please analyze this failure. If a matching lesson is found, apply its best practice. "
            "Otherwise, correct the parameters to fix the error. Return the corrected parameters as a JSON object."
        )
        
        am = AccountManager(self.engine.workspace_path)
        account = am.get_active_account()
        if not account:
            logger.warning("No active account for self-healing correction.")
            return params
            
        api_key = am.resolve_api_key(account)
        provider = ProviderFactory.get_provider(
            account["provider"],
            api_key=api_key,
            base_url=account.get("base_url")
        )
        config = {
            "model": account["model"],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        
        try:
            response_type, response_data = await provider.complete(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_content}],
                tool_schemas=[],
                config=config
            )
            if response_type == "error":
                logger.error("Self-healing LLM call failed: %s", response_data)
                return params
            
            raw_text = str(response_data).strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()
            
            patched_params = json.loads(raw_text)
            if isinstance(patched_params, dict):
                logger.info("Successfully generated self-healing parameter patch: %s", patched_params)
                return patched_params
        except Exception as e:
            logger.error("Failed to parse self-healing parameters patch: %s", e)
            
        return params

    async def _execute_step_async(self, step_id: str, step_def: dict[str, Any], state: WorkflowRunState, context: dict[str, Any], session_id: str, lock: Any) -> bool:
        """Asynchronously executes a single step, wrapping blocking execute_tool in executor."""
        async with lock:
            step_state = state.steps[step_id]
            step_state.status = "running"
            step_state.started_at = datetime.now(timezone.utc).isoformat()
            state.current_step_id = step_id
            self.save_state(state)

        skill_id = step_def["skill_id"]
        raw_params = step_def.get("params", {})
        on_failure = step_def.get("on_failure", "fail")
        
        # We broadcast the step_started event
        start_event = {
            "session": session_id,
            "type": "step_started",
            "step_id": step_id,
            "skill_id": skill_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        for cb in self.telemetry_callbacks:
            try:
                cb(session_id, start_event)
            except Exception:
                pass

        resolved_params = self._resolve_placeholder(raw_params, context)
        logger.info("Executing step '%s' [Skill: %s] asynchronously", step_id, skill_id)
        
        output = None
        error_msg = None
        success = False
        step_start_time = time.perf_counter()
        
        # Self-healing retry loop: original + 3 healing attempts = 4 total attempts
        healing_attempts = 3
        for attempt in range(1, healing_attempts + 2):
            try:
                if attempt > 1:
                    logger.info("Self-healing: Retrying step '%s' (Attempt %d/%d) with patched parameters", step_id, attempt - 1, healing_attempts)
                    import asyncio
                    await asyncio.sleep(0.5)

                sys_context = {
                    "session_id": session_id,
                    "workspace_path": self.engine.workspace_path
                }
                
                # Execute blocking engine tool in a non-blocking thread executor
                import asyncio
                loop = asyncio.get_running_loop()
                raw_output = await loop.run_in_executor(
                    None,
                    self.engine.execute_tool,
                    skill_id,
                    resolved_params,
                    None,
                    sys_context
                )
                
                if isinstance(raw_output, str) and raw_output.strip().startswith("Error:"):
                    raise RuntimeError(raw_output.strip())

                try:
                    output = json.loads(raw_output)
                except Exception:
                    try:
                        import ast
                        output = ast.literal_eval(raw_output)
                    except Exception:
                        output = raw_output

                success = True
                break
            except Exception as e:
                error_msg = str(e)
                logger.warning("Step '%s' execution failed on attempt %d: %s", step_id, attempt, error_msg)
                
                if attempt <= healing_attempts:
                    logger.info("Attempting self-healing diagnostic for step '%s'...", step_id)
                    resolved_params = await self._invoke_llm_healing(skill_id, resolved_params, error_msg)

        duration_ms = int((time.perf_counter() - step_start_time) * 1000)
        
        # Calculate cost warning telemetry
        cost_alert = False
        am = AccountManager(self.engine.workspace_path)
        active_acc = am.get_active_account()
        if active_acc:
            budget = active_acc.get("token_budget", -1)
            used = active_acc.get("tokens_used", 0)
            if budget > 0 and (used / budget) >= 0.8:
                cost_alert = True

        # Broadcast the step_completed event
        end_event = {
            "session": session_id,
            "type": "step_completed",
            "step_id": step_id,
            "skill_id": skill_id,
            "status": "success" if success else "failed",
            "duration_ms": duration_ms,
            "active_latency_alert": duration_ms > 5000,
            "cost_alert": cost_alert,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        for cb in self.telemetry_callbacks:
            try:
                cb(session_id, end_event)
            except Exception:
                pass

        async with lock:
            if success:
                step_state.status = "success"
                step_state.output = output
                step_state.error = None
                step_state.completed_at = datetime.now(timezone.utc).isoformat()
                context["steps"][step_id] = {
                    "output": output
                }
                self.save_state(state)
                return True
            else:
                step_state.status = "failed"
                step_state.error = error_msg
                step_state.completed_at = datetime.now(timezone.utc).isoformat()
                
                if on_failure == "skip":
                    logger.info("Step '%s' failed but 'on_failure' is set to 'skip'.", step_id)
                    step_state.status = "skipped"
                    self.save_state(state)
                    return True
                elif on_failure == "fallback":
                    fallback_step = step_def.get("fallback_step")
                    if fallback_step:
                        logger.info("Step '%s' failed. Routing to fallback step '%s'.", step_id, fallback_step)
                        step_state.status = "failed"
                        self.save_state(state)
                        return False
                
                state.status = "failed"
                self.save_state(state)
                return False

    async def execute(self, workflow_id: str, session_id: str, payload: dict[str, Any] | None = None, resume: bool = False) -> dict[str, Any]:
        """Execute the workflow from start, or resume if requested and a saved checkpoint exists."""
        workflow_def = self.load_workflow(workflow_id)
        
        # Check if we should resume
        state = self.load_state(session_id)
        is_resume = False

        if resume and state and state.workflow_id == workflow_id and state.status == "failed":
            is_resume = True
            logger.info("Resuming workflow '%s' for session '%s' from checkpoint", workflow_id, session_id)
            state.status = "running"
            state.payload.update(payload or {})
            # Reset any failed steps to pending so they will execute again
            for step_state in state.steps.values():
                if step_state.status == "failed":
                    step_state.status = "pending"
                    step_state.error = None
        else:
            logger.info("Initializing new run for workflow '%s' (session: %s)", workflow_id, session_id)
            if state:
                try:
                    run_file = self._get_run_file(session_id)
                    if run_file.is_file():
                        run_file.unlink()
                except Exception:
                    pass
            state = WorkflowRunState(
                workflow_id=workflow_id,
                session_id=session_id,
                status="running",
                payload=payload or {}
            )
            # Initialize steps
            for step in workflow_def["steps"]:
                state.steps[step["step_id"]] = StepState(step_id=step["step_id"])

        steps_map = {step["step_id"]: step for step in workflow_def["steps"]}
        
        # Build execution context for variable interpolation
        context = {
            "payload": state.payload,
            "steps": {}
        }
        # Populate context with already successful step outputs
        for step_id, step_state in state.steps.items():
            if step_state.status == "success":
                context["steps"][step_id] = {
                    "output": step_state.output
                }

        # Resolve dependencies for each step to support multi-dimensional mind-map edges
        explicit_dependency_steps = set()
        step_dependencies = {}
        for idx, step in enumerate(workflow_def["steps"]):
            step_id = step["step_id"]
            deps = step.get("dependencies") or step.get("depends_on")
            if deps is not None:
                explicit_dependency_steps.add(step_id)
            else:
                if idx == 0:
                    deps = []
                else:
                    deps = [workflow_def["steps"][idx - 1]["step_id"]]
            
            if isinstance(deps, str):
                deps = [deps]
            step_dependencies[step_id] = deps

        import asyncio
        lock = asyncio.Lock()
        
        # Main execution DAG evaluation loop
        while True:
            # 1. Collect all active steps starting from the first step and propagating dynamically
            active_steps = set()
            if workflow_def["steps"]:
                active_steps.add(workflow_def["steps"][0]["step_id"])
            
            for sid, sstate in state.steps.items():
                if sstate.status in ["success", "skipped", "failed"]:
                    active_steps.add(sid)
            
            changed = True
            while changed:
                changed = False
                for sid in list(active_steps):
                    sstate = state.steps.get(sid)
                    if not sstate:
                        continue
                    sdef = steps_map[sid]
                    
                    if sstate.status in ["success", "skipped"]:
                        next_id = self._get_next_step_id(sdef, context)
                        if next_id and next_id not in active_steps:
                            active_steps.add(next_id)
                            changed = True
                        for cid, deps in step_dependencies.items():
                            if cid in explicit_dependency_steps and sid in deps and cid not in active_steps:
                                active_steps.add(cid)
                                changed = True
                    elif sstate.status == "failed":
                        on_failure = sdef.get("on_failure", "fail")
                        if on_failure == "skip":
                            next_id = self._get_next_step_id(sdef, context)
                            if next_id and next_id not in active_steps:
                                active_steps.add(next_id)
                                changed = True
                        elif on_failure == "fallback":
                            fb_id = sdef.get("fallback_step")
                            if fb_id and fb_id not in active_steps:
                                active_steps.add(fb_id)
                                changed = True

            all_steps_in_active = [state.steps[sid] for sid in active_steps]
            all_done = all(s.status in ["success", "failed", "skipped"] for s in all_steps_in_active)
            if all_done:
                break
                
            any_fatal_failure = any(
                s.status == "failed" and steps_map[s.step_id].get("on_failure", "fail") == "fail"
                for s in all_steps_in_active
            )
            if any_fatal_failure:
                state.status = "failed"
                self.save_state(state)
                failed_errors = [
                    f"{s.step_id} failed: {s.error}"
                    for s in all_steps_in_active
                    if s.status == "failed" and s.error
                ]
                err_msg = "; ".join(failed_errors) or "Workflow halted due to step failure."
                raise RuntimeError(f"Workflow step failed: {err_msg}")

            # Find ready steps that can execute in parallel
            ready_step_ids = []
            for step_id in active_steps:
                step_state = state.steps[step_id]
                if step_state.status == "pending":
                    deps = step_dependencies[step_id]
                    all_deps_ok = True
                    for dep in deps:
                        dep_state = state.steps.get(dep)
                        if not dep_state:
                            all_deps_ok = False
                            break
                        if dep_state.status in ["success", "skipped"]:
                            continue
                        if dep_state.status == "failed":
                            dep_def = steps_map.get(dep)
                            if dep_def and dep_def.get("on_failure") == "fallback" and dep_def.get("fallback_step") == step_id:
                                continue
                        all_deps_ok = False
                        break
                        
                    if all_deps_ok:
                        ready_step_ids.append(step_id)

            if not ready_step_ids:
                running_steps = [s for s in all_steps_in_active if s.status == "running"]
                if not running_steps:
                    logger.warning("Deadlock or unreached steps detected in workflow DAG.")
                    break
                else:
                    await asyncio.sleep(0.1)
                    continue

            # Concurrently execute ready steps
            tasks = [
                self._execute_step_async(
                    step_id,
                    steps_map[step_id],
                    state,
                    context,
                    session_id,
                    lock
                )
                for step_id in ready_step_ids
            ]
            
            results = await asyncio.gather(*tasks)
            if not all(results):
                # Check if any failure has 'fail' policy
                failed_any_fatal = False
                for sid in ready_step_ids:
                    sstate = state.steps[sid]
                    if sstate.status == "failed":
                        sdef = steps_map[sid]
                        if sdef.get("on_failure", "fail") == "fail":
                            failed_any_fatal = True
                
                if failed_any_fatal:
                    state.status = "failed"
                    self.save_state(state)
                    failed_errors = [
                        f"{s.step_id} failed: {s.error}"
                        for s in all_steps_in_active
                        if s.status == "failed" and s.error
                    ]
                    err_msg = "; ".join(failed_errors) or "Workflow step execution failed."
                    raise RuntimeError(f"Workflow step failed: {err_msg}")

        state.status = "success"
        state.current_step_id = None
        self.save_state(state)
        logger.info("Workflow '%s' completed successfully (session: %s)", workflow_id, session_id)
        
        # Return summary of final step outputs
        return {
            step_id: step.output for step_id, step in state.steps.items() if step.status == "success"
        }

    def _get_next_step_id(self, step_def: dict[str, Any], context: dict[str, Any]) -> str | None:
        """Resolve next step ID including evaluating conditional templating in 'next_step'."""
        next_step_template = step_def.get("next_step")
        if not next_step_template:
            return None

        # If next_step is templated, evaluate it dynamically (supports outcome-based branching)
        if "{{" in next_step_template and "}}" in next_step_template:
            try:
                template = Template(next_step_template)
                resolved = template.render(**context).strip()
                return resolved if resolved else None
            except Exception as e:
                logger.error("Failed to render dynamic next_step template '%s': %s", next_step_template, e)
                return None
        return next_step_template
