import sys
from pathlib import Path

# Add project root and workspace to sys.path
root_dir = Path(__file__).resolve().parents[2]
workspace_dir = root_dir / "agent_workspace"
for p in (str(root_dir), str(workspace_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
import os
from agent_workspace.skills.tool_log import (
    AppendLogArgs, log_append,
    CompressLogsArgs, log_compress_done,
    ArchiveMonthArgs, log_archive_month
)
from agent_workspace.skills.tool_workspace import WorkspaceManager


def test_log_append_success(tmp_path):
    mgr = WorkspaceManager(str(tmp_path))
    mgr.add_task("TASK-001", "Initial Task", "todo")
    mgr.save()

    res = log_append(AppendLogArgs(task_id="TASK-001", message="Started working on feature"), context={"workspace_path": str(tmp_path)})
    assert "Log appended" in res

    mgr2 = WorkspaceManager(str(tmp_path))
    assert len(mgr2.tasks["TASK-001"].logs) == 1
    assert "Started working on feature" in mgr2.tasks["TASK-001"].logs[0]


def test_log_append_task_not_found(tmp_path):
    res = log_append(AppendLogArgs(task_id="NONEXISTENT", message="test"), context={"workspace_path": str(tmp_path)})
    assert "Error: Task NONEXISTENT not found" in res


def test_log_compress_done(tmp_path):
    mgr = WorkspaceManager(str(tmp_path))
    task = mgr.add_task("TASK-002", "Finished Task", "Done")
    task.logs = [
        "- `2026-05-01` Started",
        "- `2026-05-02` Step 1",
        "- `2026-05-03` Step 2",
        "- `2026-05-04` Step 3",
        "- `2026-05-05` Completed"
    ]
    mgr.save()

    res = log_compress_done(CompressLogsArgs(), context={"workspace_path": str(tmp_path)})
    assert "Compressed logs for 1 Done task" in res

    mgr2 = WorkspaceManager(str(tmp_path))
    assert len(mgr2.tasks["TASK-002"].logs) <= 4
    assert mgr2.tasks["TASK-002"].logs[0] == "- `2026-05-01` Started"


def test_log_archive_month(tmp_path):
    mgr = WorkspaceManager(str(tmp_path))
    task = mgr.add_task("TASK-003", "May Task", "Done")
    task.logs = [
        "- `2026-05-10` Work item 1",
        "- `2026-05-11` Work item 2",
        "- `2026-06-01` Next month item"
    ]
    mgr.save()

    res = log_archive_month(ArchiveMonthArgs(month="2026-05"), context={"workspace_path": str(tmp_path)})
    assert "Archived 2 log entries" in res

    mgr2 = WorkspaceManager(str(tmp_path))
    assert len(mgr2.tasks["TASK-003"].logs) == 1
    assert "2026-06-01" in mgr2.tasks["TASK-003"].logs[0]
