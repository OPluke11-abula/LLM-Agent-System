import os
import sys
import tempfile
import pytest

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine

def test_agent_engine_pap_loading():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a .agent directory
        pap_dir = os.path.join(temp_dir, ".agent")
        os.makedirs(pap_dir)
        
        # Create agent.md
        agent_md = os.path.join(pap_dir, "agent.md")
        with open(agent_md, "w", encoding="utf-8") as f:
            f.write("""---
name: programmer-agent
description: A developer agent.
---
# Programmer Persona Details
- Coding skills: Python, JavaScript.
""")

        # Create agent_tasks.md
        tasks_md = os.path.join(pap_dir, "agent_tasks.md")
        with open(tasks_md, "w", encoding="utf-8") as f:
            f.write("""---
name: test-tasks
description: Tasks queue.
---
# Task Queue
- [ ] Task 1
- [x] Task 2
""")

        # Instantiate engine
        engine = AgentEngine(workspace_path=temp_dir)
        
        # Verify knowledge contexts
        contexts = engine.knowledge_contexts
        
        # Find programmer-agent
        agent_ctx = next((c for c in contexts if c["name"] == "programmer-agent"), None)
        assert agent_ctx is not None
        assert "A developer agent." in agent_ctx["description"]
        assert "Programmer Persona Details" in agent_ctx["content"]
        
        # Find test-tasks
        tasks_ctx = next((c for c in contexts if c["name"] == "test-tasks"), None)
        assert tasks_ctx is not None
        assert "Tasks queue." in tasks_ctx["description"]
        assert "Task Queue" in tasks_ctx["content"]
