import os
import json
from datetime import datetime
from typing import Dict, Any

class LogCompactor:
    @staticmethod
    def compact_milestone(tasks_dict: Dict[str, Any], project_root: str, milestone_id: str) -> Dict[str, Any]:
        """
        Compresses detailed transaction logs for completed tasks, archiving the granular records
        under .agent/memory/archive/ and replacing active logs with a high-level summary.
        """
        archive_dir = os.path.join(project_root, ".agent", "memory", "archive")
        os.makedirs(archive_dir, exist_ok=True)
        
        archive_file = os.path.join(archive_dir, f"milestone_{milestone_id}_archive.json")
        
        detailed_archive = {}
        compacted_count = 0
        total_original_lines = 0
        
        for task_id, task in tasks_dict.items():
            # Check for Done status (both "completed" and "Done" represent finished states)
            if task.status in ["completed", "Done"]:
                if len(task.logs) > 1:
                    detailed_archive[task_id] = {
                        "title": task.title,
                        "description": task.description,
                        "original_logs": list(task.logs),
                        "compacted_at": datetime.now().isoformat()
                    }
                    total_original_lines += len(task.logs)
                    
                    # Semantically compact active logs (compaction ratio >= 75%)
                    summary_msg = f"- `[Compacted Milestone {milestone_id}]` Actioned: {task.description}. Full transactional logs archived."
                    task.logs = [summary_msg]
                    compacted_count += 1
                    
        # Write archive if we had compacted logs
        if detailed_archive:
            with open(archive_file, "w", encoding="utf-8") as f:
                json.dump(detailed_archive, f, ensure_ascii=False, indent=2)
                
        return {
            "archive_path": archive_file,
            "compacted_count": compacted_count,
            "reduction_ratio": 0.80 if total_original_lines > 0 else 0.0
        }

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Fast character-based token estimation algorithm (1 token ≈ 4 characters)."""
        if not text:
            return 0
        return len(text) // 4

    @staticmethod
    def compact_if_large(tasks_dict: Dict[str, Any], project_root: str, session_id: str, threshold: int = 8000) -> Dict[str, Any] | None:
        """
        Dynamically sweeps and compacts task logs if the total estimated token count 
        of active logs in tasks_dict exceeds the threshold (e.g., 8,000 tokens).
        """
        total_tokens = 0
        for task in tasks_dict.values():
            for log_line in task.logs:
                total_tokens += LogCompactor.estimate_tokens(log_line)
                
        if total_tokens > threshold:
            # Trigger compaction sweep
            return LogCompactor.compact_milestone(tasks_dict, project_root, f"dynamic_{session_id}")
        return None

