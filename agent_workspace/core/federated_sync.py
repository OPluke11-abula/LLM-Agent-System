"""
agent_workspace/core/federated_sync.py - Federated Lessons Learned Sync Engine.
"""

from __future__ import annotations

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime


class FederatedSyncEngine:
    """Scans decentralized memory storage or runs logs, aggregating error records to lessons_learned.md."""

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.project_root = Path(self.workspace_path).parent if os.path.basename(self.workspace_path) == "workspace" else Path(self.workspace_path)
        
        # Defense in depth: locate proper .agent folder location
        if not (self.project_root / ".agent").exists() and (Path(self.workspace_path) / ".agent").exists():
            self.project_root = Path(self.workspace_path)

        self.lessons_file = self.project_root / ".agent" / "knowledge_base" / "lessons_learned.md"
        self.lessons_file.parent.mkdir(parents=True, exist_ok=True)

    def _get_existing_lesson_ids(self) -> set[str]:
        """Parse lessons_learned.md and extract all existing Lesson IDs."""
        if not self.lessons_file.is_file():
            return set()
        
        try:
            content = self.lessons_file.read_text(encoding="utf-8")
            # Pattern matches Lesson ID: L-[ID] or Lesson ID: L-[ID] (Title)
            matches = re.findall(r"Lesson ID:\s*(L-[A-Za-z0-9_-]+)", content)
            return {m.strip() for m in matches}
        except Exception:
            return set()

    def _generate_lesson_id(self, mistake: str) -> str:
        """Generate a Lesson ID based on mistake hash signature."""
        hasher = hashlib.sha256(mistake.encode("utf-8"))
        hash_sig = hasher.hexdigest()[:8].upper()
        # Standard format: L-YYYYMMDD-[hash]
        date_str = datetime.now().strftime("%Y%m%d")
        return f"L-{date_str}-{hash_sig}"

    def sync(self) -> dict:
        """Scan decentralized memory storage and aggregate episodic error records, merging into lessons_learned.md."""
        existing_ids = self._get_existing_lesson_ids()
        new_lessons = []
        
        # Scan directories
        scan_dirs = [
            self.project_root / "workspace",
            self.project_root / "agent_workspace" / "memory",
            self.project_root / ".agent" / "workflows" / "runs",
            self.project_root / "memory"
        ]
        
        for s_dir in scan_dirs:
            if not s_dir.is_dir():
                continue
            
            for file_path in s_dir.glob("*.json"):
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    
                    # 1. Standard Topology JSON format
                    if isinstance(data, dict):
                        # check nodes list
                        nodes = data.get("nodes", [])
                        if isinstance(nodes, list):
                            for node in nodes:
                                if not isinstance(node, dict):
                                    continue
                                status = str(node.get("status", "")).lower()
                                title = node.get("title", "")
                                desc = node.get("description", "")
                                result = str(node.get("result_summary", ""))
                                
                                if status in {"error", "failed"} or "error" in result.lower() or "failed" in result.lower():
                                    mistake = result or f"Task '{title}' failed with status '{status}'"
                                    self._add_discovered_lesson(mistake, f"Task details: {title} - {desc}", new_lessons, existing_ids)
                        
                        # 2. Workflow runs JSON format
                        steps = data.get("steps", {})
                        if isinstance(steps, dict):
                            for step_id, step in steps.items():
                                if not isinstance(step, dict):
                                    continue
                                status = str(step.get("status", "")).lower()
                                if status in {"error", "failed"}:
                                    mistake = str(step.get("error", "")) or f"Workflow step '{step_id}' failed"
                                    self._add_discovered_lesson(mistake, f"Workflow step '{step_id}' failed with error", new_lessons, existing_ids)
                                    
                except Exception:
                    # Ignore unparseable or irrelevant JSONs
                    continue
        
        if new_lessons:
            self._write_lessons_to_md(new_lessons)
            
        return {
            "scanned_directories": [str(d) for d in scan_dirs if d.is_dir()],
            "new_lessons_added": len(new_lessons),
            "total_existing_lessons": len(existing_ids) + len(new_lessons)
        }

    def _add_discovered_lesson(self, mistake: str, context: str, new_lessons: list, existing_ids: set):
        mistake = mistake.strip()
        if not mistake:
            return
        
        lesson_id = self._generate_lesson_id(mistake)
        # Avoid duplicate signature conflict
        if lesson_id in existing_ids or any(l["id"] == lesson_id for l in new_lessons):
            return
            
        lesson_entry = {
            "id": lesson_id,
            "mistake": mistake,
            "root_cause": f"System encountered dynamic operational failure during task execution. Context: {context}",
            "resolution": "Implement explicit validations, proper error trapping and recovery loops.",
            "policy": f"Prevent failures related to: {mistake[:60]}"
        }
        new_lessons.append(lesson_entry)

    def _write_lessons_to_md(self, new_lessons: list):
        if not self.lessons_file.is_file():
            # Create standard header
            content = "# 🎓 FindAi Studio LAS Self-Learning Experience & Lessons Learned Registry\n\n"
            content += "This database catalogs engineering resolutions, compile-time errors, and dynamic swarms refactoring choices.\n\n"
            content += "---\n\n## ⚡ 1. Active Resolution Directory (Lessons Database)\n"
        else:
            content = self.lessons_file.read_text(encoding="utf-8")
            
        # Append each new lesson at the bottom under standard format
        for lesson in new_lessons:
            entry = f"\n---\n\n### Lesson ID: {lesson['id']}\n"
            entry += f"- **Mistake Encountered**: {lesson['mistake']}\n"
            entry += f"- **Root Cause**: {lesson['root_cause']}\n"
            entry += f"- **Resolution Code**:\n```python\n# Resolution implemented at runtime\n```\n"
            entry += f"- **Best Practice Policy**: {lesson['policy']}\n"
            content += entry
            
        self.lessons_file.write_text(content, encoding="utf-8")
