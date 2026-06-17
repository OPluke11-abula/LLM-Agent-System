import pytest
from agent_workspace.service import SwarmAgentService

def test_service_compiles():
    """Smoke test to ensure the service module can be imported and instantiated without syntax/indentation errors."""
    service = SwarmAgentService(role="CEO", redis_url="redis://localhost:6379", workspace_path=".")
    assert service.role == "ceo"
