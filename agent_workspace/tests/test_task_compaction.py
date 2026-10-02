import os
import sys
import tempfile
import pytest
import re
from pathlib import Path

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.log_compactor import LogCompactor


@pytest.fixture
def temp_tasks_env():
    """Scaffolds a mock .agent/agent_tasks.md file structure inside a temp directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        agent_dir = temp_path / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        tasks_content = """# PAP Agent Task Queue (English Master Edition)
> **Protocol**: Portable Agent Protocol (PAP) v0.1.0  
> **Format**: PAP Task Contract v1  
> **Status legend**: `[ ]` pending · `[~]` in-progress · `[x]` done · `[!]` blocked

---

## 🛠️ COMPLETED PHASES (Phases 0 - 15 Summarized Archive)

- [x] **PHASE 0 — Foundation & Local Tooling**: Schemas, memory backend, skill contracts.
- [x] **PHASE 1 — Protocol Completeness**: n8n-like Workflow Engine.

---

## 🏢 PHASE 16 — Swarm Debate Consensus Engine / 舊群落引擎

### 16-01 Multi-Agent Debate
- [x] Subtask 16-01-A / 共識測試子任務A
- [x] Subtask 16-01-B / 共識測試子任務B

---

### 16-02 Token Telemetry
- [x] Subtask 16-02-A / 子任務A
- [x] Subtask 16-02-B / 子任務B

---

## 🏢 PHASE 17 — Advanced Swarm Minimizer / 新群落優化

### 17-01 Auto-Pruning
- [ ] Subtask 17-01-A / 去雜質子任務A
- [ ] Subtask 17-01-B / 去雜質子任務B

---

## 📈 Queue Summary & Progress

| Phase | Total Tasks | Completed Tasks | Status |
|---|---|---|---|
| **Phase 0 - 15** | 10 tasks | 10 tasks | 100% Done |
| **Phase 16** | 4 tasks | 4 tasks | 100% Done |
| **Phase 17** | 2 tasks | 0 tasks | 0% Pending |
"""
        tasks_file = agent_dir / "agent_tasks.md"
        tasks_file.write_text(tasks_content, encoding="utf-8")
        
        yield temp_dir


def test_task_compaction_below_threshold(temp_tasks_env):
    """Verify that compaction is skipped if the completed task count in active sections is below threshold."""
    # Active section has 4 completed tasks (Phase 16 has 4 [x]).
    # Set threshold to 5 (4 <= 5), so it should skip.
    temp_path = Path(temp_tasks_env)
    tasks_file = temp_path / ".agent" / "agent_tasks.md"
    original_content = tasks_file.read_text(encoding="utf-8")
    
    compacted = LogCompactor.compact_task_queue(temp_tasks_env, threshold=5)
    
    assert compacted is False
    # File content must remain unchanged
    assert tasks_file.read_text(encoding="utf-8") == original_content


def test_task_compaction_above_threshold_triggers_sweep(temp_tasks_env):
    """Verify that compaction sweep archives fully completed active phases, deduplicates, and preserves incomplete ones."""
    # Active section has 4 completed tasks (Phase 16).
    # Set threshold to 2 (4 > 2), so it should trigger.
    temp_path = Path(temp_tasks_env)
    tasks_file = temp_path / ".agent" / "agent_tasks.md"
    
    compacted = LogCompactor.compact_task_queue(temp_tasks_env, threshold=2)
    
    assert compacted is True
    
    new_content = tasks_file.read_text(encoding="utf-8")
    
    # 1. Assert that Phase 16 detailed sections are deleted from active content
    assert "## 🏢 PHASE 16 — Swarm Debate Consensus Engine" not in new_content
    assert "### 16-01 Multi-Agent Debate" not in new_content
    assert "- [x] Subtask 16-01-A" not in new_content
    
    # 2. Assert that Phase 16 was successfully summarized and moved to COMPLETED PHASES archive
    assert "## 🛠️ COMPLETED PHASES" in new_content
    assert "- [x] **PHASE 16 — Swarm Debate Consensus Engine**: 16-01 Multi-Agent Debate, 16-02 Token Telemetry." in new_content
    
    # 3. Assert that incomplete Phase 17 detailed checklist remains fully intact in the active section
    assert "## 🏢 PHASE 17 — Advanced Swarm Minimizer" in new_content
    assert "### 17-01 Auto-Pruning" in new_content
    assert "- [ ] Subtask 17-01-A" in new_content
    
    # 4. Assert that markdown layout, queue summary, and file syntax are completely preserved
    assert "## 📈 Queue Summary & Progress" in new_content
    assert "| **Phase 17** | 2 tasks | 0 tasks | 0% Pending |" in new_content
