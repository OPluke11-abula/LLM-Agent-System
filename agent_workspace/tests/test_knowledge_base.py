import os
import sys
import tempfile
import json
import pytest
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.knowledge import KnowledgeBase


@pytest.fixture
def mock_kb_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 1. Create standard PAP structure for KB
        pap_dir = temp_path / ".agent"
        kb_index_dir = pap_dir / "knowledge_base"
        kb_index_dir.mkdir(parents=True, exist_ok=True)
        
        workspace_path = temp_path / "agent_workspace"
        kb_docs_dir = workspace_path / "knowledge_base"
        kb_docs_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Create standard coding standards document
        standards_md = """---
id: standards
title: "Coding Guidelines"
description: "Guidelines for clean code"
creator: "Lead Developer"
version: "1.0.0"
tags:
  - testing
  - clean
---
# Coding Guidelines
- Write tests first.
"""
        (kb_docs_dir / "standards.md").write_text(standards_md, encoding="utf-8")
        
        # 3. Create index.json catalog
        index_data = {
            "schema_version": "1.0.0",
            "documents": [
                {
                    "id": "standards",
                    "title": "Coding Guidelines",
                    "file_path": "agent_workspace/knowledge_base/standards.md",
                    "description": "Guidelines for clean code",
                    "creator": "Lead Developer",
                    "version": "1.0.0",
                    "tags": ["testing", "clean"]
                }
            ]
        }
        
        with open(kb_index_dir / "index.json", "w", encoding="utf-8") as f:
            json.dump(index_data, f)
            
        yield temp_dir


def test_knowledge_base_happy_path(mock_kb_env):
    workspace_path = os.path.join(mock_kb_env, "agent_workspace")
    
    # Query by tag "testing"
    results = KnowledgeBase.query("testing", workspace_path=workspace_path)
    assert len(results) == 1
    
    doc = results[0]
    assert doc["id"] == "standards"
    assert doc["title"] == "Coding Guidelines"
    assert doc["frontmatter"]["creator"] == "Lead Developer"
    assert "Write tests first." in doc["content"]
    
    # Query by keyword in raw text "Write"
    results_raw = KnowledgeBase.query("Write", workspace_path=workspace_path)
    assert len(results_raw) == 1
    
    # Query non-existent keyword
    results_none = KnowledgeBase.query("non-existent-word", workspace_path=workspace_path)
    assert len(results_none) == 0


def test_knowledge_base_boundary_protection(mock_kb_env):
    temp_path = Path(mock_kb_env)
    workspace_path = temp_path / "agent_workspace"
    
    # Create a secret file OUTSIDE the knowledge base directory (under temp_dir root)
    secret_file = temp_path / "secret.txt"
    secret_file.write_text("SUPER_SECRET_PAYLOAD", encoding="utf-8")
    
    # Register this secret file in index.json trying to bypass boundaries
    index_data = {
        "schema_version": "1.0.0",
        "documents": [
            {
                "id": "exploit",
                "title": "Malicious Bypass",
                "file_path": "secret.txt",  # Resolves outside knowledge_base/
                "description": "Exploit",
                "creator": "Attacker",
                "version": "1.0.0",
                "tags": ["exploit"]
            }
        ]
    }
    
    with open(temp_path / ".agent" / "knowledge_base" / "index.json", "w", encoding="utf-8") as f:
        json.dump(index_data, f)
        
    # Querying should trigger PermissionError due to boundary traversal protection
    with pytest.raises(PermissionError) as excinfo:
        KnowledgeBase.query("exploit", workspace_path=str(workspace_path))
        
    assert "Directory traversal warning" in str(excinfo.value)


def test_knowledge_base_semantic_fallback(mock_kb_env):
    workspace_path = os.path.join(mock_kb_env, "agent_workspace")
    
    # Query "clean first" which does NOT exist as an exact substring anywhere in index.json or documents.
    # Therefore, exact matching fails (returning empty list), triggering the semantic search fallback.
    results = KnowledgeBase.query("clean first", workspace_path=workspace_path)
    assert len(results) == 1
    assert results[0]["id"] == "standards"
    assert "clean" in results[0]["description"]
    assert "first" in results[0]["content"]


def test_knowledge_base_external_slot():
    # Verify the external vector database search API slot signature runs without crashing
    res = KnowledgeBase.external_vector_search("test query")
    assert isinstance(res, list)
    assert len(res) == 0
