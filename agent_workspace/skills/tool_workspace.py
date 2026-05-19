import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

WORKSPACE_MD = os.path.join("workspace", "workspace.md")
WORKSPACE_JSON = os.path.join("workspace", "workspace.json")

class TaskNode:
    def __init__(self, task_id: str, title: str):
        self.task_id = task_id
        self.title = title
        self.agent = "Unassigned"
        self.status = "Todo"
        self.priority = "Medium"
        self.created = datetime.now().strftime("%Y-%m-%d")
        self.updated = self.created
        self.description = ""
        self.done_criteria: List[Dict[str, Any]] = [] # {"done": bool, "text": str}
        self.logs: List[str] = []
        self.depends_on: List[str] = []
        self.depended_by: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.task_id,
            "title": self.title,
            "agent": self.agent,
            "status": self.status,
            "priority": self.priority,
            "created": self.created,
            "updated": self.updated,
            "description": self.description,
            "done_criteria": self.done_criteria,
            "logs": self.logs,
            "depends_on": self.depends_on,
            "depended_by": self.depended_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        task = cls(data["id"], data["title"])
        task.agent = data.get("agent", "Unassigned")
        task.status = data.get("status", "Todo")
        task.priority = data.get("priority", "Medium")
        task.created = data.get("created", datetime.now().strftime("%Y-%m-%d"))
        task.updated = data.get("updated", task.created)
        task.description = data.get("description", "")
        task.done_criteria = data.get("done_criteria", [])
        task.logs = data.get("logs", [])
        task.depends_on = data.get("depends_on", [])
        task.depended_by = data.get("depended_by", [])
        return task

class WorkspaceManager:
    def __init__(self, workspace_path: str):
        self.base_dir = os.path.abspath(workspace_path)
        # If base_dir is 'agent_workspace', project root is its dirname.
        # Otherwise, assume base_dir is the project root.
        if os.path.basename(self.base_dir) == "agent_workspace":
            project_root = os.path.dirname(self.base_dir)
        else:
            project_root = self.base_dir
            
        self.md_path = os.path.join(project_root, "workspace", "workspace.md")
        self.json_path = os.path.join(project_root, "workspace", "workspace.json")
        self.tasks: Dict[str, TaskNode] = {}
        self.project_title = "FindAi Studio Workspace"
        self.project_desc = "Topological Workspace for Multi-Agent Systems"
        self._ensure_workspace()
        self.load()

    def _ensure_workspace(self):
        ws_dir = os.path.dirname(self.md_path)
        os.makedirs(ws_dir, exist_ok=True)
        if not os.path.exists(self.md_path):
            self.save()

    def load(self):
        """Load tasks from workspace.json if available, fallback to basic parsing of workspace.md"""
        if os.path.exists(self.json_path):
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.project_title = data.get("project_title", self.project_title)
                self.project_desc = data.get("project_desc", self.project_desc)
                self.tasks = {t["id"]: TaskNode.from_dict(t) for t in data.get("tasks", [])}
        elif os.path.exists(self.md_path):
            self._parse_markdown()
            self.save() # generate json

    def _parse_markdown(self):
        """Fallback markdown parser."""
        with open(self.md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extremely basic parser for first load, robust json will be used subsequently
        task_blocks = re.split(r'\n---+\n', content)
        for block in task_blocks:
            match = re.search(r'## \[([^\]]+)\] (.+)', block)
            if match:
                task_id = match.group(1).strip()
                title = match.group(2).strip()
                task = TaskNode(task_id, title)
                
                agent_match = re.search(r'\*\*負責 Agent：\*\*\s*(.+)', block)
                if agent_match: task.agent = agent_match.group(1).strip()
                
                status_match = re.search(r'\*\*狀態：\*\*\s*`([^`]+)`', block)
                if status_match: task.status = status_match.group(1).strip()
                
                desc_match = re.search(r'### 說明\n(.*?)(?=\n###|\Z)', block, re.DOTALL)
                if desc_match: task.description = desc_match.group(1).strip()
                
                self.tasks[task_id] = task

    def save(self):
        """Save state to both JSON and Markdown."""
        # Update json
        data = {
            "project_title": self.project_title,
            "project_desc": self.project_desc,
            "tasks": [t.to_dict() for t in self.tasks.values()]
        }
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Update markdown
        md_content = self._generate_markdown()
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    def _generate_markdown(self) -> str:
        agents = set(t.agent for t in self.tasks.values() if t.agent and t.agent != "Unassigned")
        active_agents = ", ".join(agents) if agents else "None"
        
        counts = {"Todo": 0, "InProgress": 0, "Review": 0, "Done": 0}
        for t in self.tasks.values():
            if t.status in counts: counts[t.status] += 1
            
        today = datetime.now().strftime("%Y-%m-%d")

        lines = [
            f"# 🗂️ {self.project_title}",
            "",
            f"> {self.project_desc}",
            "",
            f"**最後更新：** {today} | **活躍 Agents：** {active_agents}",
            f"**進度：** Todo({counts['Todo']}) / InProgress({counts['InProgress']}) / Review({counts['Review']}) / Done({counts['Done']})",
            "",
            "---",
            "",
            "## 🗺️ 任務拓撲圖"
        ]

        # Generate simple ASCII DAG
        # Finding root tasks (no dependencies)
        roots = [t for t in self.tasks.values() if not t.depends_on]
        if not roots and self.tasks:
            roots = list(self.tasks.values())[:1] # handle cycles gracefully

        visited = set()
        def render_graph(task_id, prefix=""):
            if task_id in visited:
                return
            visited.add(task_id)
            t = self.tasks[task_id]
            lines.append(f"{prefix}[{t.task_id}: {t.title}] {t.status}")
            for i, child_id in enumerate(t.depended_by):
                if child_id in self.tasks:
                    is_last = (i == len(t.depended_by) - 1)
                    conn = "└──→ " if is_last else "├──→ "
                    child_prefix = prefix + ("    " if is_last else "│   ")
                    lines.append(f"{prefix}{conn}[{child_id}] {self.tasks[child_id].status}")
                    # don't recurse deeply to avoid complex ascii mess, just show 1 level for now
                    # or use a simplified linear representation as per spec: A -> B
        
        # Spec format: [TASK-001] InProgress ──→ [TASK-002] Todo
        lines.append(self._render_ascii_dag())

        # Render Task Blocks
        for task in self.tasks.values():
            lines.extend(["", "---", ""])
            lines.append(f"## [{task.task_id}] {task.title}")
            lines.append("")
            lines.append(f"**負責 Agent：** {task.agent}  ")
            lines.append(f"**狀態：** `{task.status}`  ")
            lines.append(f"**優先級：** {task.priority}  ")
            lines.append(f"**建立：** {task.created} | **更新：** {task.updated}")
            lines.append("")
            lines.append("### 說明")
            lines.append(task.description if task.description else "(無)")
            lines.append("")
            
            lines.append("### 完成條件 (Done When)")
            if task.done_criteria:
                for c in task.done_criteria:
                    check = "x" if c.get("done") else " "
                    lines.append(f"- [{check}] {c.get('text', '')}")
            else:
                lines.append("(無)")
            lines.append("")
            
            lines.append("### 日誌")
            if task.logs:
                lines.extend(task.logs)
            else:
                lines.append("(尚未開始)")
            lines.append("")
            
            lines.append("### 連結節點")
            deps = ", ".join(f"[{d}]" for d in task.depends_on) if task.depends_on else "無"
            lines.append(f"→ 依賴：{deps}  ")
            depby = ", ".join(f"[{d}]" for d in task.depended_by) if task.depended_by else "無"
            lines.append(f"→ 被依賴：{depby}")

        return "\n".join(lines)

    def _render_ascii_dag(self) -> str:
        """Render DAG matching the spec: [TASK-001: Name] Status ──→ [TASK-002: Name] Status"""
        lines = []
        visited = set()
        
        for task in self.tasks.values():
            if task.task_id in visited:
                continue
                
            # If it has dependencies, it will be rendered from parent, skip for root level unless it's a root
            if task.depends_on:
                continue
                
            # Simple DFS path rendering
            path = []
            curr = task
            while curr:
                visited.add(curr.task_id)
                path.append(f"[{curr.task_id}: {curr.title}] {curr.status}")
                if curr.depended_by and curr.depended_by[0] in self.tasks:
                    curr = self.tasks[curr.depended_by[0]]
                else:
                    curr = None
            lines.append(" ──→ ".join(path))
            
        if not lines:
            # Fallback
            for task in self.tasks.values():
                lines.append(f"[{task.task_id}: {task.title}] {task.status}")
                
        return "\n↓\n".join(lines)


# ==========================================
# Pydantic Tool Definitions
# ==========================================

class AddTaskArgs(BaseModel):
    task_id: str = Field(description="Unique Task ID (e.g. TASK-005).")
    title: str = Field(description="Task title.")
    agent: str = Field(default="Unassigned", description="Assigned Agent.")
    description: str = Field(default="", description="Task description.")
    depends_on: List[str] = Field(default_factory=list, description="List of task IDs this task depends on.")

def workspace_add_task(args: AddTaskArgs, context: Optional[Dict] = None) -> str:
    """Add a new task node to the topological workspace."""
    workspace_path = context.get("workspace_path", ".") if context else "."
    manager = WorkspaceManager(workspace_path)
    
    if args.task_id in manager.tasks:
        return f"Error: Task {args.task_id} already exists."
        
    task = TaskNode(args.task_id, args.title)
    task.agent = args.agent
    task.description = args.description
    
    manager.tasks[args.task_id] = task
    
    for dep_id in args.depends_on:
        if dep_id in manager.tasks:
            task.depends_on.append(dep_id)
            manager.tasks[dep_id].depended_by.append(task.task_id)
            
    manager.save()
    return f"Successfully added {args.task_id}: {args.title}"


class UpdateStatusArgs(BaseModel):
    task_id: str = Field(description="Task ID to update.")
    status: str = Field(description="New status: Todo, InProgress, Review, or Done.")
    log_message: str = Field(default="", description="Optional log message to append.")

def workspace_update_status(args: UpdateStatusArgs, context: Optional[Dict] = None) -> str:
    """Update task status and append to log."""
    workspace_path = context.get("workspace_path", ".") if context else "."
    manager = WorkspaceManager(workspace_path)
    
    if args.task_id not in manager.tasks:
        return f"Error: Task {args.task_id} not found."
        
    task = manager.tasks[args.task_id]
    task.status = args.status
    task.updated = datetime.now().strftime("%Y-%m-%d")
    
    if args.log_message:
        today = datetime.now().strftime("%Y-%m-%d")
        task.logs.append(f"- `{today}` {args.log_message}")
        
    # Compress logs if Done
    if task.status == "Done" and len(task.logs) > 3:
        task.logs = [f"- `{today}` Task completed. (Logs compressed)"] + task.logs[-2:]
        
    manager.save()
    return f"Successfully updated {args.task_id} to {args.status}."


class LinkTasksArgs(BaseModel):
    from_task_id: str = Field(description="The task that needs to be done first (dependency).")
    to_task_id: str = Field(description="The task that waits for from_task_id (dependent).")

def workspace_link_tasks(args: LinkTasksArgs, context: Optional[Dict] = None) -> str:
    """Link two tasks, establishing a dependency relationship in the DAG."""
    workspace_path = context.get("workspace_path", ".") if context else "."
    manager = WorkspaceManager(workspace_path)
    
    if args.from_task_id not in manager.tasks or args.to_task_id not in manager.tasks:
        return "Error: One or both tasks not found."
        
    parent = manager.tasks[args.from_task_id]
    child = manager.tasks[args.to_task_id]
    
    if args.from_task_id not in child.depends_on:
        child.depends_on.append(args.from_task_id)
        
    if args.to_task_id not in parent.depended_by:
        parent.depended_by.append(args.to_task_id)
        
    manager.save()
    return f"Linked {args.from_task_id} ──→ {args.to_task_id}"

class RenderTopologyArgs(BaseModel):
    pass

def workspace_render_topology(args: RenderTopologyArgs, context: Optional[Dict] = None) -> str:
    """Render and return the current topological ASCII graph."""
    workspace_path = context.get("workspace_path", ".") if context else "."
    manager = WorkspaceManager(workspace_path)
    return manager._render_ascii_dag()
