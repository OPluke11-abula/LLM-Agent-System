import sys
import os

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from agent_workspace.skills.tool_memory import (
    memory_store_knowledge, StoreKnowledgeArgs,
    memory_query, QueryMemoryArgs,
    memory_store_preference, StorePreferenceArgs
)

def test_memory_skills():
    context = {"workspace_path": "."}
    
    # 1. Store knowledge
    args = StoreKnowledgeArgs(
        knowledge_text="When parsing workspace.json, always provide fallback defaults for project_title.",
        citations=["TASK-004"]
    )
    res = memory_store_knowledge(args, context)
    print("Store Knowledge Result:", res)
    assert "Successfully stored" in res

    # 2. Store preference
    args2 = StorePreferenceArgs(
        preference_text="Use snake_case for all Python variables."
    )
    res2 = memory_store_preference(args2, context)
    print("Store Preference Result:", res2)
    assert "Successfully stored" in res2

    # 3. Query memory (semantic)
    q_args = QueryMemoryArgs(
        query_text="workspace.json fallback",
        domain="semantic",
        limit=5
    )
    res3 = memory_query(q_args, context)
    print("\nQuery Semantic Result:\n", res3)
    assert "workspace.json" in res3

    # 4. Query memory (preference)
    q_args2 = QueryMemoryArgs(
        query_text="snake_case variables",
        domain="preference",
        limit=5
    )
    res4 = memory_query(q_args2, context)
    print("\nQuery Preference Result:\n", res4)
    assert "snake_case" in res4

if __name__ == "__main__":
    test_memory_skills()
    print("All tests passed!")
