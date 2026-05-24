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
except ImportError:
    from agent_workspace.core.engine import AgentEngine

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

        # Determine where to start/resume execution
        current_step_id = None
        if is_resume:
            # Find the first step that is not successful
            for step in workflow_def["steps"]:
                step_id = step["step_id"]
                if state.steps[step_id].status != "success":
                    current_step_id = step_id
                    break
        
        if not current_step_id:
            # Start from the first step in the list
            if workflow_def["steps"]:
                current_step_id = workflow_def["steps"][0]["step_id"]

        while current_step_id:
            step_def = steps_map.get(current_step_id)
            if not step_def:
                raise ValueError(f"Step ID '{current_step_id}' referenced but not defined in steps list")

            step_state = state.steps[current_step_id]
            state.current_step_id = current_step_id
            self.save_state(state)

            if step_state.status == "success":
                # Already succeeded step, skip it (useful in resume scenarios)
                current_step_id = self._get_next_step_id(step_def, context)
                continue

            step_state.status = "running"
            step_state.started_at = datetime.now(timezone.utc).isoformat()
            self.save_state(state)

            skill_id = step_def["skill_id"]
            raw_params = step_def.get("params", {})
            on_failure = step_def.get("on_failure", "fail")
            max_retries = 3 if on_failure == "retry" else 1

            # Resolve parameters using current context
            resolved_params = self._resolve_placeholder(raw_params, context)

            logger.info("Executing step '%s' [Skill: %s]", current_step_id, skill_id)
            
            output = None
            error_msg = None
            success = False

            for attempt in range(1, max_retries + 1):
                try:
                    if attempt > 1:
                        logger.info("Retrying step '%s' (Attempt %d/%d)", current_step_id, attempt, max_retries)
                        # Sleep briefly between retries
                        time.sleep(0.5)

                    # Execute the tool via the engine
                    # Construct system context for the skill execution
                    sys_context = {
                        "session_id": session_id,
                        "workspace_path": self.engine.workspace_path
                    }
                    
                    # Run the tool synchronously or asynchronously (engine.execute_tool is synchronous)
                    raw_output = self.engine.execute_tool(
                        skill_id,
                        resolved_params,
                        context=sys_context
                    )
                    
                    # Handle tool errors returned as strings starting with Error:
                    if isinstance(raw_output, str) and raw_output.strip().startswith("Error:"):
                        raise RuntimeError(raw_output.strip())

                    # Attempt to parse output string as json/python payload for convenience
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
                    logger.warning("Step '%s' execution failed on attempt %d: %s", current_step_id, attempt, error_msg)

            if success:
                step_state.status = "success"
                step_state.output = output
                step_state.error = None
                step_state.completed_at = datetime.now(timezone.utc).isoformat()
                
                # Add to context
                context["steps"][current_step_id] = {
                    "output": output
                }
                
                current_step_id = self._get_next_step_id(step_def, context)
            else:
                step_state.status = "failed"
                step_state.error = error_msg
                step_state.completed_at = datetime.now(timezone.utc).isoformat()
                
                if on_failure == "skip":
                    logger.info("Step '%s' failed but 'on_failure' is set to 'skip'. Continuing.", current_step_id)
                    step_state.status = "skipped"
                    current_step_id = self._get_next_step_id(step_def, context)
                elif on_failure == "fallback":
                    fallback_step = step_def.get("fallback_step")
                    if fallback_step:
                        logger.info("Step '%s' failed. Routing to fallback step '%s'.", current_step_id, fallback_step)
                        current_step_id = fallback_step
                    else:
                        logger.error("Step '%s' failed with fallback strategy but no 'fallback_step' defined.", current_step_id)
                        state.status = "failed"
                        self.save_state(state)
                        raise RuntimeError(f"Workflow step failed: {error_msg}")
                else:
                    logger.error("Step '%s' failed with 'fail' policy. Stopping workflow.", current_step_id)
                    state.status = "failed"
                    self.save_state(state)
                    raise RuntimeError(f"Workflow step failed: {error_msg}")

            self.save_state(state)

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
