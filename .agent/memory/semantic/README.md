# Semantic Memory Storage

Semantic memory stores long-term factual knowledge, user preferences, and generalized solutions learned across multiple agent sessions.

## File Specification

*   **Format**: JSON files (`.json`), representing individual records or a dictionary of keys to values.
*   **Path**: `.agent/memory/semantic/<key>.json`
*   **Retention**: Indefinite or long-term (manually curated or governed).

## Fields Captured

Every semantic memory record contains:
1.  `id`: Unique semantic key (e.g. `sem-<hash>` or `pref-<hash>`).
2.  `session_id`: Session ID where the fact/preference was extracted.
3.  `summary`: The factual text or preference text description.
4.  `keywords`: Extracted searchable keywords.
5.  `citations`: Task IDs, file paths, or links where this knowledge originated.
6.  `confidence`: Float score (0.0 to 1.0) indicating factual reliability.
7.  `domain`: Either `"semantic"` or `"preference"`.
8.  `privacy_level`: `"user"`, `"project"`, or `"deployment"`.
