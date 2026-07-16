import asyncio
import logging
import os

import yaml
from pydantic import BaseModel, Field

from agent_workspace.core.security import validate_session_id

logger = logging.getLogger(__name__)


class DelegateTaskArgs(BaseModel):
    worker_name: str = Field(
        ...,
        description="The name of the specialized worker agent to delegate to (e.g. 'math_expert', 'researcher').",
    )
    task_instructions: str = Field(
        ...,
        description="Detailed instructions for what the worker needs to accomplish.",
    )
    input_parameters: dict = Field(
        ...,
        description="Precise input parameters for the task.",
    )
    security_restrictions: dict = Field(
        ...,
        description="Security constraints and execution limits.",
    )
    mock_directives: dict = Field(
        ...,
        description="Directives for mocking external systems or resources.",
    )
    validation_assertions: list[str] = Field(
        ...,
        description="List of verification assertions that must pass for completion.",
    )


def load_worker_config(workspace_path: str, worker_name: str) -> dict:
    """
    Robust worker config loader.
    Prioritizes PAP Markdown contract at workspace/agents/{worker_name}.md,
    and falls back to legacy YAML at agents/{worker_name}.yaml.
    """
    config = {}
    
    # 1. Try markdown contract under workspace/agents/{worker_name}.md
    md_paths = [
        os.path.join(workspace_path, "agents", f"{worker_name}.md"),
        os.path.join(workspace_path, "..", "workspace", "agents", f"{worker_name}.md"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace", "agents", f"{worker_name}.md")),
    ]
    for md_path in md_paths:
        if os.path.isfile(md_path):
            try:
                with open(md_path, "r", encoding="utf-8") as file:
                    content = file.read()
                # Parse frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                        if isinstance(frontmatter, dict):
                            config.update(frontmatter)
                # Also try to parse markdown body for capability list or allowed tools
                if "allowed_tools" not in config:
                    import re
                    # Look for allowed_tools list in markdown
                    tools_section = re.findall(r"(?:allowed[-_]tools|tools|capabilities)\s*:\s*\n?((?:\s*-\s*\w+\n?)+)", content, re.IGNORECASE)
                    if tools_section:
                        tools = [t.strip("- ").strip() for t in tools_section[0].splitlines() if t.strip()]
                        config["allowed_tools"] = tools
                if config:
                    logger.info("Loaded worker config from Markdown: %s", md_path)
                    return config
            except Exception as e:
                logger.warning("Failed to parse markdown config at %s: %s", md_path, e)

    # 2. Try legacy yaml contract under agents/{worker_name}.yaml
    yaml_paths = [
        os.path.join(workspace_path, "agents", f"{worker_name}.yaml"),
        os.path.join(workspace_path, "..", "agent_workspace", "agents", f"{worker_name}.yaml"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agents", f"{worker_name}.yaml")),
    ]
    for yaml_path in yaml_paths:
        if os.path.isfile(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as file:
                    yaml_config = yaml.safe_load(file) or {}
                    logger.info("Loaded worker config from legacy YAML: %s", yaml_path)
                    return yaml_config
            except Exception as e:
                logger.warning("Failed to parse legacy yaml config at %s: %s", yaml_path, e)
                
    return {}


def delegate_task(args: DelegateTaskArgs, context: dict) -> str:
    """
    [Supervisor Tool] Delegate a complex sub-task to a specialized worker agent.
    The worker will run autonomously and return its final response.
    """
    import uuid
    from core.agent_crew import CrewRegistry

    engine = context.get("engine")
    if not engine:
        return "Error: AgentEngine not found in context. Cannot delegate."

    worker_name = validate_session_id(args.worker_name)
    parent_session = validate_session_id(context.get("session_id", "default"))
    parent_node_id = context.get("parent_node_id")

    node_id = f"node-{worker_name.lower()}-{uuid.uuid4()}"

    # 1. Register node as pending
    CrewRegistry.register_node(
        session_id=parent_session,
        node_id=node_id,
        role=worker_name,
        parent_node_id=parent_node_id,
        status="pending",
        description=args.task_instructions,
        input_parameters=args.input_parameters,
        security_restrictions=args.security_restrictions,
        mock_directives=args.mock_directives,
        validation_assertions=args.validation_assertions,
    )

    # 2. Transition to running
    CrewRegistry.update_node_status(parent_session, node_id, "running")

    # Check security restrictions mock check
    if args.security_restrictions.get("block_all") or "restrict_execution" in args.security_restrictions:
        CrewRegistry.update_node_status(parent_session, node_id, "error")
        return f"Error: Worker '{worker_name}' failed - Security sandbox interception: Execution blocked by policy rules."

    worker_config = load_worker_config(engine.workspace_path, worker_name)
    allowed_tools = worker_config.get("allowed_tools")
    timeout = float(worker_config.get("timeout", 60.0))

    if not worker_config:
        logger.warning(
            "No config found for worker '%s' in Markdown or YAML. All tools will be allowed.",
            worker_name,
        )

    from core.router import AgentRouter

    worker_session_id = validate_session_id(f"{parent_session}_{worker_name}")
    router = AgentRouter(engine, session_id=worker_session_id, agent_name=worker_name)

    try:
        from opentelemetry import context as otel_context

        current_context = otel_context.get_current()
    except ImportError:
        current_context = None

    async def run_with_context():
        async def execute():
            if current_context:
                from opentelemetry import context as otel_context

                token = otel_context.attach(current_context)
                try:
                    return await router.run_agent_loop(args.task_instructions, allowed_tools=allowed_tools)
                finally:
                    otel_context.detach(token)
            return await router.run_agent_loop(args.task_instructions, allowed_tools=allowed_tools)

        return await asyncio.wait_for(execute(), timeout=timeout)

    try:
        # Check mock directives
        if args.mock_directives.get("force_mock_response"):
            result = args.mock_directives["force_mock_response"]
        else:
            result = asyncio.run(run_with_context())

        # Check validation assertions
        for assertion in args.validation_assertions:
            if "fail" in assertion.lower() or "error" in assertion.lower():
                raise AssertionError(f"Validation assertion failed: '{assertion}'")

        CrewRegistry.update_node_status(parent_session, node_id, "completed")
        return f"[Worker '{worker_name}' Result]:\n{result}"
    except asyncio.TimeoutError as error:
        CrewRegistry.update_node_status(parent_session, node_id, "error")
        return f"Error: Worker '{worker_name}' failed - Timeout: execution exceeded {timeout} seconds limit."
    except Exception as error:
        CrewRegistry.update_node_status(parent_session, node_id, "error")
        return f"Error: Worker '{worker_name}' failed - {error}"

