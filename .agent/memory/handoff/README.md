# Handoff Memory Storage

Handoff memory packages the entire execution state, pending tasks, session history summary, and key memory snapshots to transfer context to another agent seamlessly.

## File Specification

*   **Format**: JSON files (`.json`).
*   **Path**: `.agent/memory/handoff/<handoff_id>.json`
*   **Retention**: Temporary (safe to delete after successful import).

## Structure of a Handoff Packet

Handoff packets include:
1.  `id`: A unique handoff packet ID (e.g. `handoff-<hash>`).
2.  `domain`: Set to `"handoff"`.
3.  `created_at`: ISO 8601 UTC timestamp.
4.  `payload`: A dictionary containing:
    *   `task_state`: The current visual DAG status of tasks.
    *   `pending_steps`: The remaining steps/checklists for active tasks.
    *   `context_summary`: Summarized conversational history for context.
    *   `memory_snapshot`: Key long-term memory records relevant to the task.
