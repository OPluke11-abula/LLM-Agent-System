# Episodic Memory Storage

Episodic memory captures historical snapshots of conversation sessions within the LLM Agent System (LAS).

## File Specification

*   **Format**: JSON Lines (`.jsonl`), where each line is a valid JSON object matching the memory schema.
*   **Path**: `.agent/memory/episodic/<session_id>.jsonl`
*   **Retention**: Configurable per session or until size limit is reached.

## Fields Captured

Every episodic memory record contains:
1.  `id`: A unique content-hash-based ID (e.g. `ltm-<hash>`).
2.  `session_id`: The ID of the session that generated the memory.
3.  `summary`: High-level summarization of the conversation window.
4.  `keywords`: Key tokens extracted from the discussion.
5.  `payload`: The raw or formatted messages involved in the session.
6.  `created_at`: ISO 8601 UTC timestamp.
