from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# We import the long-term memory store from the workspace
import sys
import os
# Add agent_workspace to sys.path so we can import long_term_memory directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from long_term_memory import LongTermMemoryStore

def _get_store(context: Optional[Dict] = None) -> LongTermMemoryStore:
    workspace_path = context.get("workspace_path", ".") if context else "."
    memory_dir = os.path.join(workspace_path, "agent_workspace", "memory")
    return LongTermMemoryStore(memory_dir)

def _get_session_id(context: Optional[Dict] = None) -> str:
    # Use workspace project title as global session id, or fallback to 'global_session'
    if context and "workspace_path" in context:
        return "findai_studio_workspace"
    return "global_session"

# ==========================================
# Query Memory
# ==========================================

class QueryMemoryArgs(BaseModel):
    query_text: str = Field(description="Search keywords or phrase.")
    domain: Optional[str] = Field(default=None, description="Optional domain to restrict search to (e.g. 'semantic', 'episodic', 'preference').")
    limit: int = Field(default=5, description="Maximum number of records to return.")

def memory_query(args: QueryMemoryArgs, context: Optional[Dict] = None) -> str:
    """Search long-term memory for records matching the query."""
    store = _get_store(context)
    session_id = _get_session_id(context)
    
    results = store.query(
        query_text=args.query_text,
        session_id=session_id,
        limit=args.limit,
        domain=args.domain
    )
    
    if not results:
        return "No memory records found."
        
    output = []
    for r in results:
        domain = r.get("domain", "episodic")
        summary = r.get("summary", "")
        record_id = r.get("id", "")
        created = r.get("created_at", "")
        output.append(f"[{domain.upper()}] ID: {record_id} | Created: {created}\n{summary}\n")
        
    return "\n".join(output)

# ==========================================
# Store Knowledge
# ==========================================

class StoreKnowledgeArgs(BaseModel):
    knowledge_text: str = Field(description="The factual knowledge, experience, or solution to store.")
    citations: List[str] = Field(default_factory=list, description="List of task IDs, URLs, or file paths referencing where this knowledge came from.")

def memory_store_knowledge(args: StoreKnowledgeArgs, context: Optional[Dict] = None) -> str:
    """Store valuable experience or facts as semantic knowledge."""
    store = _get_store(context)
    session_id = _get_session_id(context)
    
    record = store.add_semantic_knowledge(
        session_id=session_id,
        knowledge_text=args.knowledge_text,
        citations=args.citations
    )
    
    return f"Successfully stored semantic knowledge. Memory ID: {record.id}"

# ==========================================
# Store Preference
# ==========================================

class StorePreferenceArgs(BaseModel):
    preference_text: str = Field(description="The user preference to store.")

def memory_store_preference(args: StorePreferenceArgs, context: Optional[Dict] = None) -> str:
    """Store a specific user preference."""
    store = _get_store(context)
    session_id = _get_session_id(context)
    
    record = store.add_preference(
        session_id=session_id,
        preference_text=args.preference_text
    )
    
    return f"Successfully stored preference. Memory ID: {record.id}"
