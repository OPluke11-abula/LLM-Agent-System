import os
import logging
import yaml
import asyncio
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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
        logger.warning(f"No config found for worker '{worker_name}' at {config_path}. All tools will be allowed.")

    # 2. 建立新的 Router 實例，產生子 session_id 隔離記憶
    from core.router import AgentRouter
    worker_session_id = f"{parent_session}:{worker_name}"
    
    router = AgentRouter(engine, session_id=worker_session_id, agent_name=worker_name)
    
    # 3. 透過 asyncio.run 啟動一個全新的事件迴圈來執行 worker
    # 為了確保 OTel Trace Context 能夠跨越 asyncio.run，我們手動提取並附加 Context
    try:
        from opentelemetry import context as otel_context
        current_context = otel_context.get_current()
    except ImportError:
        current_context = None

    async def run_with_context():
        if current_context:
            from opentelemetry import context as otel_context
            token = otel_context.attach(current_context)
            try:
                return await router.run_agent_loop(args.task_instructions, allowed_tools=allowed_tools)
            finally:
                otel_context.detach(token)
        else:
            return await router.run_agent_loop(args.task_instructions, allowed_tools=allowed_tools)

    try:
        result = asyncio.run(run_with_context())
        return f"[Worker '{worker_name}' Result]:\n{result}"
    except Exception as e:
        return f"Error: Worker '{worker_name}' 執行失敗 - {e}"
