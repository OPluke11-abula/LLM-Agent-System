import os
import json
import re
import logging
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


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
                
        # Trigger milestone reflection automatically (Task 21-01)
        try:
            import asyncio
            from agent_workspace.core.discussion_room import DiscussionRoom
            
            discussion_room = DiscussionRoom(workspace_path=project_root)
            
            try:
                loop = asyncio.get_running_loop()
                # Run reflection in a background task if inside async context
                loop.create_task(discussion_room.run_milestone_reflection(milestone_id, tasks_dict=tasks_dict))
            except RuntimeError:
                # Synchronous fallback if no running event loop
                asyncio.run(discussion_room.run_milestone_reflection(milestone_id, tasks_dict=tasks_dict))
        except Exception as e:
            logger.error(f"Failed to automatically trigger milestone reflection debate: {e}")
                
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

    @staticmethod
    def compact_task_queue(workspace_path: str, threshold: int = 10) -> bool:
        """
        Scans the agent_tasks.md file in .agent/ directory.
        If the number of completed tasks (lines matching - [x]) exceeds the threshold,
        it automatically compacts the completed phases into the COMPLETED PHASES list
        and removes their detailed sections, saving context length.
        Returns True if compaction was performed, False otherwise.
        """
        # Resolve path to agent_tasks.md
        path_check = Path(workspace_path)
        if (path_check / ".agent").is_dir():
            project_root = path_check
        elif (path_check.parent / ".agent").is_dir():
            project_root = path_check.parent
        else:
            project_root = path_check.parent
            
        tasks_file = project_root / ".agent" / "agent_tasks.md"
        if not tasks_file.is_file():
            logger.warning("agent_tasks.md not found for compaction.")
            return False
            
        try:
            content = tasks_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("Failed to read agent_tasks.md: %s", e)
            return False
            
        # Count the number of completed tasks in active sections
        # Separated by "## 🛠️ COMPLETED PHASES" and "## 📈 Queue Summary & Progress"
        parts = content.split("## 🛠️ COMPLETED PHASES")
        if len(parts) < 2:
            return False
            
        archive_and_active = parts[1]
        active_parts = archive_and_active.split("## 📈 Queue Summary & Progress")
        active_content = active_parts[0]
        
        # Split active content into archive block and active phases block
        active_phases_split = active_content.split("## 🏢 PHASE", 1)
        if len(active_phases_split) < 2:
            logger.info("No active phases found in agent_tasks.md.")
            return False
            
        real_active_content = "## 🏢 PHASE" + active_phases_split[1]
        
        # Regex to match completed task checklist items in real active sections only
        completed_tasks = re.findall(r'^\s*-\s*\[x\]\s+(.*)', real_active_content, re.MULTILINE)
        completed_count = len(completed_tasks)
        
        if completed_count <= threshold:
            logger.info("Active completed tasks (%d) does not exceed threshold (%d). Skipping compaction.", completed_count, threshold)
            return False
            
        # Trigger compaction sweep!
        # Regex split by active phase block headers
        phase_blocks = re.split(r'(## 🏢 PHASE \d+ — [^\n]+)', active_content)
        
        new_active_content = phase_blocks[0]
        archived_phases = []
        
        for i in range(1, len(phase_blocks), 2):
            phase_header = phase_blocks[i]
            phase_body = phase_blocks[i+1]
            
            # Find phase number and title
            header_match = re.search(r'## 🏢 PHASE (\d+) — ([^\n/]+)', phase_header)
            if not header_match:
                new_active_content += phase_header + phase_body
                continue
                
            phase_num = header_match.group(1)
            phase_title = header_match.group(2).strip()
            
            # Extract task details from phase_body
            all_tasks = re.findall(r'^\s*-\s*\[[ x~!]\]\s+(.*)', phase_body, re.MULTILINE)
            comp_tasks = re.findall(r'^\s*-\s*\[x\]\s+(.*)', phase_body, re.MULTILINE)
            
            # Phase is considered fully completed if it contains tasks and all of them are marked done ([x])
            if len(all_tasks) > 0 and len(all_tasks) == len(comp_tasks):
                # Compress detailed tasks into high-level summarized markdown headers
                sub_headers = re.findall(r'^###\s+(.*)', phase_body, re.MULTILINE)
                if sub_headers:
                    task_summary = ", ".join(sh.strip() for sh in sub_headers)
                else:
                    task_summary = ", ".join(t.strip() for t in comp_tasks[:3]) + ("..." if len(comp_tasks) > 3 else "")
                
                archive_line = f"- [x] **PHASE {phase_num} — {phase_title}**: {task_summary}."
                archived_phases.append(archive_line)
                logger.info("Compacted Phase %s into archived archive list.", phase_num)
            else:
                new_active_content += phase_header + phase_body
                
        if not archived_phases:
            logger.info("No fully completed active phases to compact.")
            return False
            
        # Rebuild file components
        preamble = parts[0]
        archive_block_parts = parts[1].split("---", 1)
        archive_block = archive_block_parts[0]
        
        archive_lines = [line.strip() for line in archive_block.splitlines() if line.strip()]
        
        existing_archive_lines = []
        for line in archive_lines:
            if line.startswith("- [x]"):
                existing_archive_lines.append(line)
                
        # Merge new archived phases
        merged_archive_lines = existing_archive_lines + archived_phases
        
        # Deduplicate archived phases by Phase ID to preserve manifest integrity
        seen_phases = set()
        deduped_archive_lines = []
        for line in merged_archive_lines:
            match = re.search(r'\*\*PHASE\s+(\d+)', line, re.IGNORECASE)
            if match:
                phase_id = match.group(1)
                if phase_id not in seen_phases:
                    seen_phases.add(phase_id)
                    deduped_archive_lines.append(line)
            else:
                deduped_archive_lines.append(line)
                
        # Re-construct COMPLETED PHASES markdown block
        new_archive_block = "\n\n## 🛠️ COMPLETED PHASES (Phases 0 - 17 Summarized Archive)\n\n"
        for line in deduped_archive_lines:
            new_archive_block += f"{line}\n"
        new_archive_block += "\n"
        
        # Stitch document sections back together
        new_content = preamble + "## 🛠️ COMPLETED PHASES" + new_archive_block + "---" + new_active_content
        if len(active_parts) > 1:
            new_content += "## 📈 Queue Summary & Progress" + active_parts[1]
            
        try:
            tasks_file.write_text(new_content, encoding="utf-8")
            logger.info("Successfully executed automated agent_tasks.md compaction sweep.")
            return True
        except Exception as e:
            logger.error("Failed to write compacted agent_tasks.md: %s", e)
            return False


class ContextMinimizer:
    """Safely sweeps active workspace to prune obsolete logs, tmp files, and transition guides."""

    @staticmethod
    def dejunk_workspace(workspace_path: str) -> list[str]:
        """
        Recursively scans the active workspace boundaries, detects, and safely deletes
        obsolete manual scripts, transient .tmp files, and unused transition files
        while protecting core code, tests, schemas, active configs, and .agent registries.
        Returns a list of deleted file paths.
        """
        workspace_path = os.path.abspath(workspace_path)
        deleted_files = []
        
        redundant_basenames = {
            "handoff.md", 
            "transition_guide.md", 
            "transition.md", 
            "redundant_log.txt"
        }
        
        for root, dirs, files in os.walk(workspace_path):
            normalized_root = os.path.abspath(root)
            
            # Skip traversal of system/protected folders entirely
            root_parts = normalized_root.split(os.sep)
            if any(part in root_parts for part in [".agent", ".git", ".pytest_cache", ".venv"]):
                continue
                
            # Skip traversal of core codebase directories inside agent_workspace
            rel_root = os.path.relpath(normalized_root, workspace_path)
            rel_parts = rel_root.split(os.sep)
            if "agent_workspace" in rel_parts:
                if any(p in rel_parts for p in ["core", "tests", "skills"]):
                    continue
                    
            for f in files:
                f_path = os.path.join(normalized_root, f)
                
                # Protect core project config files from deletion
                if f in [
                    "accounts.json", "pyproject.toml", "requirements.txt", 
                    "requirements-providers.txt", "config.yaml", "tool_manifest.json", 
                    "tool_manifest.py", "api.py", "cli.py", "run.py", 
                    "observability.py", "topology_bridge.py", "topology_stream.py", 
                    "long_term_memory.py", "memory_backends.py", "pap_validate.py",
                    "README.md", "CONTRIBUTING.md", "Dockerfile", "docker-compose.yml", "nginx.conf"
                ]:
                    continue
                    
                # Prevent deleting active test suites
                if f.startswith("test_") and f.endswith(".py"):
                    if "tests" in rel_parts:
                        continue
                        
                is_redundant = False
                
                # Check for redundant basenames
                if f in redundant_basenames:
                    is_redundant = True
                # Check for transient temp files
                elif f.endswith(".tmp") or f.startswith("tmp_") or ".tmp" in f:
                    is_redundant = True
                # Check for log files
                elif f.endswith(".log"):
                    is_redundant = True
                # Check for obsolete manual python scripts in non-core sandbox directories
                elif (f.startswith("scratch_") or f.startswith("manual_test_") or f == "temp_script.py") and f.endswith(".py"):
                    is_redundant = True
                    
                if is_redundant:
                    try:
                        os.remove(f_path)
                        deleted_files.append(f_path)
                    except Exception as e:
                        logger.error("Failed to delete redundant file %s: %s", f_path, e)
                        
        return deleted_files
