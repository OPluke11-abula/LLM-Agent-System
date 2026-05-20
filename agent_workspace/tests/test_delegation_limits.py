import os
import sys
import asyncio
import pytest
from unittest.mock import MagicMock, patch

# Ensure paths are set up correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_workspace.skills.delegate_task import delegate_task, DelegateTaskArgs
from agent_workspace.core.router import AgentRouter
from agent_workspace.core.providers import ProviderResponse
from agent_workspace.skills.tool_workspace import (
    workspace_add_task, AddTaskArgs,
    workspace_cancel_task, CancelTaskArgs,
    WorkspaceManager
)

def test_delegate_task_timeout():
    # Setup mock engine
    mock_engine = MagicMock()
    mock_engine.workspace_path = "."
    
    context = {"engine": mock_engine, "session_id": "test_session"}
    args = DelegateTaskArgs(worker_name="slow_worker", task_instructions="Do something very slow")
    
    async def mock_run_agent_loop(*args, **kwargs):
        await asyncio.sleep(0.5)
        return "Finished successfully"
        
    mock_provider = MagicMock()
    
    with patch("core.router.ProviderFactory.get_provider", return_value=mock_provider), \
         patch("agent_workspace.core.router.ProviderFactory.get_provider", return_value=mock_provider), \
         patch("core.router.AgentRouter.run_agent_loop", side_effect=mock_run_agent_loop), \
         patch("agent_workspace.core.router.AgentRouter.run_agent_loop", side_effect=mock_run_agent_loop), \
         patch("agent_workspace.skills.delegate_task.load_worker_config") as mock_load_config:
         
        mock_load_config.return_value = {"timeout": 0.05, "allowed_tools": []}
        
        result = delegate_task(args, context)
        assert "Timeout: execution exceeded 0.05 seconds limit." in result

@pytest.mark.asyncio
async def test_router_tool_limit():
    # Setup mock engine
    mock_engine = MagicMock()
    mock_engine.workspace_path = "."
    mock_engine.get_tool_schemas.return_value = [{"name": "mock_tool"}]
    mock_engine.execute_tool.return_value = "Tool run completed"
    
    mock_provider = MagicMock()
    
    with patch("core.router.ProviderFactory.get_provider", return_value=mock_provider), \
         patch("agent_workspace.core.router.ProviderFactory.get_provider", return_value=mock_provider):
         
        # Create router
        router = AgentRouter(mock_engine, session_id="test_session", agent_name="test_agent")
        router.max_tool_calls = 2  # Set a low tool limit
        
        # Provider will keep returning tool calls to simulate an infinite loop
        async def mock_generate_content(*args, **kwargs):
            return ProviderResponse("tool_calls", [{"name": "mock_tool", "arguments": {}}])
            
        mock_provider.generate_content = mock_generate_content
        router._provider = mock_provider
        
        # Mock _classify_intent to return TASK so tool flow is triggered
        async def mock_classify_intent(user_input):
            return "TASK"
        router._classify_intent = mock_classify_intent
        
        # Run the loop
        response = await router.run_agent_loop("Trigger infinite loop")
        
        # Verify the output includes the limit warning
        assert "Maximum tool execution limit (2) exceeded" in response

@pytest.mark.asyncio
async def test_stream_router_tool_limit():
    mock_engine = MagicMock()
    mock_engine.workspace_path = "."
    mock_engine.get_tool_schemas.return_value = [{"name": "mock_tool"}]
    mock_engine.execute_tool.return_value = "Tool run completed"
    
    mock_provider = MagicMock()
    
    with patch("core.router.ProviderFactory.get_provider", return_value=mock_provider), \
         patch("agent_workspace.core.router.ProviderFactory.get_provider", return_value=mock_provider):
         
        router = AgentRouter(mock_engine, session_id="test_session", agent_name="test_agent")
        router.max_tool_calls = 2
        
        async def mock_stream(*args, **kwargs):
            yield ProviderResponse("tool_calls", [{"name": "mock_tool", "arguments": {}}])
            
        mock_provider.generate_content_stream = mock_stream
        router._provider = mock_provider
        
        async def mock_classify_intent(user_input):
            return "TASK"
        router._classify_intent = mock_classify_intent
        
        # Gather streaming events
        events = []
        async for event in router.stream_agent_loop("Trigger stream limit"):
            events.append(event)
            
        # Check that we received the error type event
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) > 0
        assert "Maximum tool execution limit (2) exceeded" in error_events[0]["content"]

def test_workspace_cancel_task():
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create workspace subdir so WorkspaceManager can save
        os.makedirs(os.path.join(temp_dir, "workspace"))
        
        context = {"workspace_path": temp_dir}
        
        # Add tasks: TASK-1 -> TASK-2 -> TASK-3
        workspace_add_task(AddTaskArgs(task_id="TASK-1", title="Task 1", agent="Unassigned", description="", depends_on=[]), context)
        workspace_add_task(AddTaskArgs(task_id="TASK-2", title="Task 2", agent="Unassigned", description="", depends_on=["TASK-1"]), context)
        workspace_add_task(AddTaskArgs(task_id="TASK-3", title="Task 3", agent="Unassigned", description="", depends_on=["TASK-2"]), context)
        
        # Verify initial states (default is Todo)
        mgr = WorkspaceManager(temp_dir)
        assert mgr.tasks["TASK-1"].status == "Todo"
        assert mgr.tasks["TASK-2"].status == "Todo"
        assert mgr.tasks["TASK-3"].status == "Todo"
        
        # Cancel TASK-2, which should cancel TASK-2 and TASK-3 (its recursive descendant)
        # but NOT TASK-1 (its parent dependency)
        res = workspace_cancel_task(CancelTaskArgs(task_id="TASK-2"), context)
        assert "TASK-2" in res
        assert "TASK-3" in res
        assert "TASK-1" not in res
        
        mgr_after = WorkspaceManager(temp_dir)
        assert mgr_after.tasks["TASK-1"].status == "Todo"
        assert mgr_after.tasks["TASK-2"].status == "Cancelled"
        assert mgr_after.tasks["TASK-3"].status == "Cancelled"
