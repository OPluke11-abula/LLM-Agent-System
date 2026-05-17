import os
import yaml
import asyncio
from pydantic import BaseModel, Field

class DelegateTaskArgs(BaseModel):
    worker_name: str = Field(..., description="The name of the specialized worker agent to delegate to (e.g. 'math_expert', 'researcher').")
    task_instructions: str = Field(..., description="Detailed instructions for what the worker needs to accomplish.")

def delegate_task(args: DelegateTaskArgs, context: dict) -> str:
    """
    [Supervisor Tool] Delegate a complex sub-task to a specialized worker agent.
    The worker will run autonomously and return its final response.
    """
    engine = context.get("engine")
    if not engine:
        return "Error: AgentEngine not found in context. Cannot delegate."

    worker_name = args.worker_name
    parent_session = context.get("session_id", "default")
    
    # 1. 讀取 Worker 的設定檔 (取得 allowed_tools 等)
    config_path = os.path.join(engine.workspace_path, "agents", f"{worker_name}.yaml")
    allowed_tools = None
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                worker_config = yaml.safe_load(f)
                allowed_tools = worker_config.get("allowed_tools")
        except Exception as e:
            return f"Error: 讀取 worker 設定失敗 - {e}"
    else:
        # 如果沒有設定檔，我們也可以依賴 Jinja2 判斷，但預設允許所有工具可能會不安全
        # 這裡為了簡單，若沒有 yaml 就不限制，或由系統管理
        pass

    # 2. 建立新的 Router 實例，產生子 session_id 隔離記憶
    from core.router import AgentRouter
    worker_session_id = f"{parent_session}:{worker_name}"
    
    router = AgentRouter(engine, session_id=worker_session_id, agent_name=worker_name)
    
    # 3. 透過 asyncio.run 啟動一個全新的事件迴圈來執行 worker
    try:
        result = asyncio.run(router.run_agent_loop(args.task_instructions, allowed_tools=allowed_tools))
        return f"[Worker '{worker_name}' Result]:\n{result}"
    except Exception as e:
        return f"Error: Worker '{worker_name}' 執行失敗 - {e}"
