from pydantic import BaseModel, Field

class TransferToAgentArgs(BaseModel):
    target_agent: str = Field(..., description="The name of the agent to transfer to. For example: 'CodeEngineer', 'DatabaseAdmin'.")
    reason: str = Field(..., description="The reason for the handoff, summarizing what needs to be done next.")
    
def transfer_agent(args: TransferToAgentArgs) -> str:
    """
    [System Tool] Transfer the current session to a different Agent.
    Call this tool ONLY when you realize the user's request requires the expertise of a different specialized agent.
    """
    # 回傳特殊保留字串讓 router.py 攔截
    return f"HANDOFF_TO: {args.target_agent}"
