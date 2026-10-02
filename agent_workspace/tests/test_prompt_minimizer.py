import os
import sys
import pytest

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.prompt_composer import PromptComposer


def test_prompt_under_threshold_not_compacted():
    """Verify that a compiled system prompt with learning directives under 6,000 tokens remains completely unchanged."""
    composer = PromptComposer()
    
    under_limit_prompt = (
        "You are a helpful agent.\n\n"
        "## 🎓 SYSTEM SELF-LEARNING DIRECTIVES (Auto-Learned Best Practices):\n"
        "- **Best Practice**: Always mock approval checks.\n"
        "- **Best Practice**: Wrap all SQLite write transactions in a dedicated lock guard.\n"
    )
    
    result = composer.prune_compiled_prompt(under_limit_prompt)
    assert result == under_limit_prompt


def test_prompt_over_threshold_cleanly_compacted():
    """Verify that a compiled system prompt exceeding 6,000 tokens is cleanly compacted into dense semantic summaries."""
    composer = PromptComposer()
    
    # 6,000 tokens ≈ 24,000 characters. Let's build a large directive block of 26,000 characters.
    large_directives = []
    # Add a SQLite transaction lock guideline
    large_directives.append("- **Best Practice**: Enforce an async lock guard on concurrent SQLite write transactions to prevent operational lock errors.")
    # Add an approval mocking guideline
    large_directives.append("- **Best Practice**: Always mock interactive approval checks in automated test environments to bypass interactive gateways.")
    # Add a ResizeObserver guideline
    large_directives.append("- **Best Practice**: Throttle all dynamic layout and ResizeObserver calculations with requestAnimationFrame.")
    # Add many dummy guidelines to inflate size
    for i in range(300):
        large_directives.append(f"- **Best Practice Guideline {i}**: Ensure system properties are parsed cleanly and verified according to standard code style guides.")
        
    large_directives_str = "\n".join(large_directives)
    
    over_limit_prompt = (
        "SYSTEM_PERSONA: You are the Lead Architect Swarm Agent.\n\n"
        "## 🎓 SYSTEM SELF-LEARNING DIRECTIVES (Auto-Learned Best Practices):\n"
        f"{large_directives_str}\n\n"
        "## 🎓 SYSTEM SELF-LEARNING DIRECTIVES (Auto-Learned Best Practices):\n"
        "- **Best Practice**: Active high priority recent guideline that must be retained.\n"
    )
    
    # Ensure it's actually over 6,000 tokens (24,000 characters)
    assert len(over_limit_prompt) > 24000
    
    result = composer.prune_compiled_prompt(over_limit_prompt)
    
    # Verify compaction has occurred
    assert len(result) < len(over_limit_prompt)
    assert "### ⚡ COMPACTED SEMANTIC HISTORICAL DIRECTIVES" in result
    assert "### 🎓 ACTIVE HIGH-PRIORITY SYSTEM DIRECTIVES" in result
    
    # Verify critical developer constraints from older items are preserved semantically
    assert "SQLite" in result
    assert "mock" in result or "Mock" in result
    assert "ResizeObserver" in result or "resizing" in result
    
    # Verify the most recent guidelines are preserved in active list
    assert "recent guideline" in result
