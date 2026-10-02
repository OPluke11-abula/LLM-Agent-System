"""
tests/test_federated_sync.py - Unit tests for the FederatedSyncEngine class.
"""

import os
import sys
import json
import shutil
import pytest
from pathlib import Path

# Add project root parent to sys.path
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(test_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
workspace_dir = os.path.dirname(test_dir)
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from agent_workspace.core.federated_sync import FederatedSyncEngine


@pytest.fixture
def temp_project(tmp_path):
    project_dir = tmp_path / "federated_project"
    project_dir.mkdir()
    (project_dir / ".agent").mkdir()
    (project_dir / ".agent" / "knowledge_base").mkdir()
    (project_dir / "workspace").mkdir()
    return project_dir


def test_federated_sync_no_failures(temp_project):
    """Verify that sync runs cleanly when there are no failed records."""
    # Write a happy-path topology json
    happy_json = {
        "nodes": [
            {
                "id": "node-1",
                "title": "Good Node",
                "status": "done",
                "result_summary": "Success"
            }
        ]
    }
    workspace_dir = temp_project / "workspace"
    (workspace_dir / "t1.json").write_text(json.dumps(happy_json), encoding="utf-8")
    
    engine = FederatedSyncEngine(str(workspace_dir))
    res = engine.sync()
    
    assert res["new_lessons_added"] == 0
    assert not engine.lessons_file.exists()


def test_federated_sync_discover_and_merge(temp_project):
    """Verify that syncer aggregates a failed node, writes a lesson, and prevents duplication on second run."""
    failed_json = {
        "nodes": [
            {
                "id": "node-failed",
                "title": "Broken Swarm Node",
                "status": "error",
                "description": "Failed to compile main.rs",
                "result_summary": "Error: compilation failed due to missing dependency"
            }
        ]
    }
    workspace_dir = temp_project / "workspace"
    (workspace_dir / "t2.json").write_text(json.dumps(failed_json), encoding="utf-8")
    
    engine = FederatedSyncEngine(str(workspace_dir))
    
    # 1. First Run: Discover mistake
    res_1 = engine.sync()
    assert res_1["new_lessons_added"] == 1
    assert engine.lessons_file.is_file()
    
    md_content = engine.lessons_file.read_text(encoding="utf-8")
    assert "Broken Swarm Node" in md_content
    assert "compilation failed due to missing dependency" in md_content
    assert "Lesson ID: L-" in md_content
    
    # 2. Second Run: Assert duplicate prevention
    res_2 = engine.sync()
    assert res_2["new_lessons_added"] == 0
