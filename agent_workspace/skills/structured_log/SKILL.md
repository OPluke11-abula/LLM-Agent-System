---
name: structured-log
description: >
  以最小空間記錄任務歷史。已完成任務只保留摘要（≤3行），
  進行中任務記錄完整 context。自動壓縮超過 30 天的舊日誌。
  當使用者要求「記錄進度」、「寫日誌」、「更新狀態」時觸發。
triggers:
  - 記錄進度
  - 寫日誌
  - 更新狀態
  - 壓縮舊日誌
---

# Structured Log Skill

This skill manages task logging with automatic space optimization.

## Workflow
1. **Append**: Use `log_append` to add a timestamped log entry to any task.
2. **Compress**: Use `log_compress_done` to shrink all completed tasks' logs to ≤3 lines.
3. **Archive**: Use `log_archive_month` to move a specific month's log entries into `workspace/logs/YYYY-MM.md`, keeping the main workspace lean.

## Rules
- InProgress tasks always retain full context logs.
- Done tasks are compressed: keep first entry + last 2 entries, remove the rest.
- Archived logs are moved, not copied — the original entries are deleted from the task node.
