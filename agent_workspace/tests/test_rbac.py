import os
import sys
import tempfile
import json
import pytest

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.engine import AgentEngine
from core.router import AgentRouter


def test_rbac_authorization():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set AGENT_WORKSPACE_DIR to point to temp_dir so topology state file is generated there
        old_env = os.environ.get("AGENT_WORKSPACE_DIR")
        os.environ["AGENT_WORKSPACE_DIR"] = temp_dir
        
        try:
            # Create a mock .agent directory structure
            pap_dir = os.path.join(temp_dir, ".agent")
            skills_dir = os.path.join(pap_dir, "skills")
            os.makedirs(skills_dir)
            
            # Create config.yaml
            with open(os.path.join(temp_dir, "config.yaml"), "w", encoding="utf-8") as f:
                f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")
                
            # Create mock skill contracts with required_role
            with open(os.path.join(skills_dir, "admin_skill.md"), "w", encoding="utf-8") as f:
                f.write("""---
id: admin_skill
description: Admin-only skill.
version: 1.0.0
required_role: admin
inputs:
  expr:
    type: string
    required: true
    description: Dummy input
outputs:
  result: A string.
---
# admin_skill
""")

            with open(os.path.join(skills_dir, "dev_skill.md"), "w", encoding="utf-8") as f:
                f.write("""---
id: dev_skill
description: Developer skill.
version: 1.0.0
required_role: developer
inputs:
  expr:
    type: string
    required: true
    description: Dummy input
outputs:
  result: A string.
---
# dev_skill
""")

            with open(os.path.join(skills_dir, "standard_skill.md"), "w", encoding="utf-8") as f:
                f.write("""---
id: standard_skill
description: Standard skill.
version: 1.0.0
inputs:
  expr:
    type: string
    required: true
    description: Dummy input
outputs:
  result: A string.
---
# standard_skill
""")

            # Create account JSON files to mock active account roles
            accounts_file = os.path.join(temp_dir, "accounts.json")
            
            # Helper to set accounts file
            def set_accounts(role):
                data = {
                    "accounts": [
                        {
                            "id": "default-account",
                            "provider": "google-genai",
                            "model": "gemini-2.5-flash",
                            "api_key": "env:GOOGLE_API_KEY",
                            "base_url": "",
                            "token_budget": -1,
                            "tokens_used": 0,
                            "is_active": True,
                            "role": role
                        }
                    ],
                    "active_account_id": "default-account"
                }
                with open(accounts_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)

            engine = AgentEngine(workspace_path=temp_dir)
            router = AgentRouter(engine=engine, session_id="test-session")
            
            try:
                # 1. Admin Role test
                set_accounts("admin")
                router.validate_call("admin_skill", {"expr": "test"})
                router.validate_call("dev_skill", {"expr": "test"})
                router.validate_call("standard_skill", {"expr": "test"})
                
                # 2. Developer Role test
                set_accounts("developer")
                router.validate_call("dev_skill", {"expr": "test"})
                router.validate_call("standard_skill", {"expr": "test"})
                with pytest.raises(PermissionError) as excinfo:
                    router.validate_call("admin_skill", {"expr": "test"})
                assert "insufficient" in str(excinfo.value)
                
                # 3. Standard Role test
                set_accounts("standard")
                router.validate_call("standard_skill", {"expr": "test"})
                with pytest.raises(PermissionError):
                    router.validate_call("dev_skill", {"expr": "test"})
                with pytest.raises(PermissionError):
                    router.validate_call("admin_skill", {"expr": "test"})
                    
                # 4. Default role (when not specified in account, defaults to standard)
                data_no_role = {
                    "accounts": [
                        {
                            "id": "default-account",
                            "provider": "google-genai",
                            "model": "gemini-2.5-flash",
                            "api_key": "env:GOOGLE_API_KEY",
                            "base_url": "",
                            "token_budget": -1,
                            "tokens_used": 0,
                            "is_active": True
                        }
                    ],
                    "active_account_id": "default-account"
                }
                with open(accounts_file, "w", encoding="utf-8") as f:
                    json.dump(data_no_role, f)
                    
                router.validate_call("standard_skill", {"expr": "test"})
                with pytest.raises(PermissionError):
                    router.validate_call("dev_skill", {"expr": "test"})
                    
                # Check topology error state generation
                topology_path = os.path.join(temp_dir, "topology_state.json")
                assert os.path.isfile(topology_path)
                with open(topology_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                assert len(state["nodes"]) > 0
                err_node = [n for n in state["nodes"] if n["node_type"] == "error"][0]
                assert "RBAC" in err_node["title"]
                assert "insufficient" in err_node["description"]
                
            finally:
                router.close()
        finally:
            if old_env is None:
                os.environ.pop("AGENT_WORKSPACE_DIR", None)
            else:
                os.environ["AGENT_WORKSPACE_DIR"] = old_env
