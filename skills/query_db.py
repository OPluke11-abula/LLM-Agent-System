"""Example database query skill.

[觸發時機]
- 當使用者要求從資料庫查詢結構化資訊時。

[限制條件]
- 僅支援唯讀查詢，不應執行寫入或刪除操作。
"""

from pydantic import BaseModel, Field


class QueryDBArgs(BaseModel):
    """Arguments for the query_db skill."""

    query: str = Field(..., description="The SQL query string to execute.")
    limit: int = Field(10, ge=1, description="Maximum number of rows to return.")


def query_db(args: QueryDBArgs) -> str:
    """Execute a database query using validated arguments."""
    raw_query = args.query.strip()
    normalized_query = raw_query.lower()
    if not normalized_query.startswith("select"):
        raise ValueError("Only read-only SELECT queries are allowed.")
    if ";" in raw_query:
        raise ValueError("Multiple statements are not allowed.")
    if " into outfile" in normalized_query or " into dumpfile" in normalized_query:
        raise ValueError("File-writing clauses are not allowed.")
    return f"Query requested: {args.query} (limit={args.limit})"
