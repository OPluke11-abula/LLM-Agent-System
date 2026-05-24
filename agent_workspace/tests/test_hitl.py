import os
import sys
import tempfile
import json
import asyncio
import pytest

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine
from core.router import AgentRouter, ACTIVE_APPROVALS, ApprovalDeniedError


@pytest.mark.asyncio
async def test_hitl_approval_success():
    with tempfile.TemporaryDirectory() as temp_dir:
        pap_dir = os.path.join(temp_dir, ".agent")
        skills_dir = os.path.join(pap_dir, "skills")
        os.makedirs(skills_dir)
        
        # Create config.yaml
        with open(os.path.join(temp_dir, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            
        # Create agent.md with interactive-approval
        with open(os.path.join(pap_dir, "agent.md"), "w", encoding="utf-8") as f:
            f.write("""---
protocol_version: "1.0.0"
min_runtime_version: "0.1.0"
name: test-agent
version: "1.0.0"
authorization_level: interactive-approval
---
""")
            
        # Create a mock skill contract that does not need parameter inputs
        with open(os.path.join(skills_dir, "mock_sensitive_skill.md"), "w", encoding="utf-8") as f:
            f.write("""---
id: mock_sensitive_skill
description: A sensitive skill.
version: 1.0.0
sensitive: true
inputs:
  param:
    type: string
    required: true
    description: Dummy param
outputs:
  result: A string.
---
# mock_sensitive_skill
""")

        # Set AGENT_WORKSPACE_DIR to point to temp_dir so topology state file is generated there
        old_env = os.environ.get("AGENT_WORKSPACE_DIR")
        os.environ["AGENT_WORKSPACE_DIR"] = temp_dir
        
        try:
            engine = AgentEngine(workspace_path=temp_dir)
            
            # Mock actual execution since we are doing unit tests without full LLM interaction
            # We will directly run _execute_tool_with_approval to test the HITL wait loop.
            router = AgentRouter(engine=engine, session_id="test-session-hitl")
            
            try:
                # Mock engine.execute_tool using a proper Pydantic model
                from pydantic import BaseModel, Field
                class MockArgs(BaseModel):
                    param: str = Field(description="Dummy param")

                engine.tools_registry["mock_sensitive_skill"] = {
                    "function": lambda args: "Success!",
                    "args_model": MockArgs,
                    "description": "Mock description",
                    "schema": {"properties": {"param": {"type": "string"}}},
                    "wants_context": False,
                }

                # Resolve accounts config
                accounts_file = os.path.join(temp_dir, "accounts.json")
                with open(accounts_file, "w", encoding="utf-8") as f:
                    f.write('{"accounts": [{"id": "default-account", "provider": "google-genai", "model": "gemini-2.5-flash", "is_active": true}], "active_account_id": "default-account"}')

                # We will schedule the approval in the background
                async def mock_approver():
                    await asyncio.sleep(0.1)
                    assert "test-session-hitl" in ACTIVE_APPROVALS
                    router.resolve_approval(approved=True)

                asyncio.create_task(mock_approver())
                
                res = await router._execute_tool_with_approval(
                    "mock_sensitive_skill",
                    {"param": "data"},
                    allowed_tools=None,
                    system_context={}
                )
                assert res == "Success!"

                # Check topology node status
                topology_path = os.path.join(temp_dir, "topology_state.json")
                assert os.path.isfile(topology_path)
                with open(topology_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                hitl_node = [n for n in state["nodes"] if n["node_type"] == "hitl_gate"][0]
                assert hitl_node["status"] == "done"  # status mapped completed to done in TopologyEmitter
            finally:
                router.close()
        finally:
            if old_env is None:
                os.environ.pop("AGENT_WORKSPACE_DIR", None)
            else:
                os.environ["AGENT_WORKSPACE_DIR"] = old_env


@pytest.mark.asyncio
async def test_hitl_approval_rejection():
    with tempfile.TemporaryDirectory() as temp_dir:
        pap_dir = os.path.join(temp_dir, ".agent")
        skills_dir = os.path.join(pap_dir, "skills")
        os.makedirs(skills_dir)
        
        with open(os.path.join(temp_dir, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
            
        with open(os.path.join(skills_dir, "mock_sensitive_skill.md"), "w", encoding="utf-8") as f:
            f.write("""---
id: mock_sensitive_skill
description: A sensitive skill.
version: 1.0.0
sensitive: true
inputs:
  param:
    type: string
    required: true
    description: Dummy param
outputs:
  result: A string.
---
""")

        # Set AGENT_WORKSPACE_DIR to point to temp_dir so topology state file is generated there
        old_env = os.environ.get("AGENT_WORKSPACE_DIR")
        os.environ["AGENT_WORKSPACE_DIR"] = temp_dir

        try:
            engine = AgentEngine(workspace_path=temp_dir)
            router = AgentRouter(engine=engine, session_id="test-session-hitl-rej")
            
            try:
                # Mock tool registry using a proper Pydantic model
                from pydantic import BaseModel, Field
                class MockArgs(BaseModel):
                    param: str = Field(description="Dummy param")

                engine.tools_registry["mock_sensitive_skill"] = {
                    "function": lambda args: "Success!",
                    "args_model": MockArgs,
                    "description": "Mock description",
                    "schema": {"properties": {"param": {"type": "string"}}},
                    "wants_context": False,
                }

                # Background task to reject
                async def mock_rejector():
                    await asyncio.sleep(0.1)
                    assert "test-session-hitl-rej" in ACTIVE_APPROVALS
                    router.resolve_approval(approved=False)

                asyncio.create_task(mock_rejector())
                
                with pytest.raises(ApprovalDeniedError):
                    await router._execute_tool_with_approval(
                        "mock_sensitive_skill",
                        {"param": "data"},
                        allowed_tools=None,
                        system_context={}
                    )

                # Check topology node status
                topology_path = os.path.join(temp_dir, "topology_state.json")
                assert os.path.isfile(topology_path)
                with open(topology_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                hitl_node = [n for n in state["nodes"] if n["node_type"] == "hitl_gate"][0]
                assert hitl_node["status"] == "error"
            finally:
                router.close()
        finally:
            if old_env is None:
                os.environ.pop("AGENT_WORKSPACE_DIR", None)
            else:
                os.environ["AGENT_WORKSPACE_DIR"] = old_env
