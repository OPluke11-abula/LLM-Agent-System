"""Structured log tools for the FindAi Studio workspace.

Provides three Pydantic-based tools:
  - log_append: Add a timestamped log entry to a task.
  - log_compress_done: Compress all Done tasks' logs to ≤3 lines.
  - log_archive_month: Move a month's log entries into workspace/logs/YYYY-MM.md.

These tools reuse WorkspaceManager from tool_workspace.py for state persistence.
"""

import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

# Ensure sibling module is importable
_skills_dir = os.path.dirname(os.path.abspath(__file__))
if _skills_dir not in sys.path:
    sys.path.insert(0, _skills_dir)

from tool_workspace import WorkspaceManager


# ==========================================
# Pydantic Tool Definitions
# ==========================================

class AppendLogArgs(BaseModel):
    task_id: str = Field(description="The task ID to append a log entry to (e.g. TASK-003).")
    message: str = Field(description="The log message content to append.")


def log_append(args: AppendLogArgs, context: Optional[Dict] = None) -> str:
    """Append a timestamped log entry to a specific task.

    [觸發時機] When a user says '記錄進度', '寫日誌', or wants to log progress.
    [限制條件] Task must exist in the workspace.
    """
    workspace_path = context.get("workspace_path", ".") if context else "."
    manager = WorkspaceManager(workspace_path)

    if args.task_id not in manager.tasks:
        return f"Error: Task {args.task_id} not found."

    task = manager.tasks[args.task_id]
    today = datetime.now().strftime("%Y-%m-%d")
    entry = f"- `{today}` {args.message}"
    task.logs.append(entry)
    task.updated = today

    manager.save()
    return f"Log appended to {args.task_id}: {args.message}"


class CompressLogsArgs(BaseModel):
    pass


def log_compress_done(args: CompressLogsArgs, context: Optional[Dict] = None) -> str:
    """Compress all Done tasks' logs to ≤3 lines.

    Keeps the first log entry (task start) and the last 2 entries (final results).
    All intermediate entries are removed and replaced with a compression marker.

    [觸發時機] When a user says '壓縮舊日誌' or the workspace feels bloated.
    [限制條件] Only affects tasks with status 'Done'.
    """
    workspace_path = context.get("workspace_path", ".") if context else "."
    manager = WorkspaceManager(workspace_path)

    compressed_count = 0
    for task in manager.tasks.values():
        if task.status != "Done":
            continue
        if len(task.logs) <= 3:
            continue

        first = task.logs[0]
        last_two = task.logs[-2:]
        task.logs = [first, "- `...` _(Logs compressed)_"] + last_two
        # Still over 3? Force trim to exactly 3
        if len(task.logs) > 3:
            task.logs = task.logs[:1] + task.logs[-2:]
        compressed_count += 1

    if compressed_count > 0:
        manager.save()

    return f"Compressed logs for {compressed_count} Done task(s)."


class ArchiveMonthArgs(BaseModel):
    month: str = Field(description="Month to archive in YYYY-MM format (e.g. 2026-05).")


def log_archive_month(args: ArchiveMonthArgs, context: Optional[Dict] = None) -> str:
    """Archive a specific month's log entries into workspace/logs/YYYY-MM.md.

    Scans all tasks for log entries whose timestamp matches the given month,
    moves them into a dedicated archive file, and removes them from the task nodes.

    [觸發時機] When a user says '歸檔日誌' or at the end of each month.
    [限制條件] Only moves log entries matching the specified month prefix.
    """
    workspace_path = context.get("workspace_path", ".") if context else "."
    manager = WorkspaceManager(workspace_path)

    # Validate month format
    if not re.match(r"^\d{4}-\d{2}$", args.month):
        return f"Error: Invalid month format '{args.month}'. Use YYYY-MM (e.g. 2026-05)."

    # Determine logs directory
    logs_dir = os.path.join(os.path.dirname(manager.md_path), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    archive_path = os.path.join(logs_dir, f"{args.month}.md")

    archived_entries: List[str] = []
    tasks_affected = 0

    for task in manager.tasks.values():
        kept: List[str] = []
        moved: List[str] = []

        for entry in task.logs:
            # Match entries like "- `2026-05-19` ..."
            if f"`{args.month}" in entry:
                moved.append(entry)
            else:
                kept.append(entry)

        if moved:
            archived_entries.append(f"## [{task.task_id}] {task.title}\n")
            archived_entries.extend(moved)
            archived_entries.append("")
            task.logs = kept
            tasks_affected += 1

    if not archived_entries:
        return f"No log entries found for month {args.month}."

    # Write archive file (append if exists)
    header = f"# 📦 Archived Logs — {args.month}\n\n"
    mode = "a" if os.path.exists(archive_path) else "w"
    with open(archive_path, mode, encoding="utf-8") as f:
        if mode == "w":
            f.write(header)
        f.write("\n".join(archived_entries) + "\n")

    manager.save()
    total_entries = sum(1 for e in archived_entries if e.startswith("- "))
    return (
        f"Archived {total_entries} log entries from {tasks_affected} task(s) "
        f"to workspace/logs/{args.month}.md"
    )
