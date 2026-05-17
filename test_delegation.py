import asyncio
from agent_workspace.core.engine import AgentEngine
from agent_workspace.core.router import AgentRouter

async def main():
    engine = AgentEngine(workspace_path="agent_workspace")
    # Supervisor has all tools except we want to see it delegate to math_expert
    # Let's see if the delegate tool is available
    supervisor = AgentRouter(engine, session_id="test_supervisor")
    
    # User asks a complex math question
    print("User: Please calculate 13 * 17 and then tell me if the result is even or odd. Please delegate this to the math_expert.")
    
    # Run the loop
    response = await supervisor.run_agent_loop(
        "Please calculate 13 * 17 and then tell me if the result is even or odd. Please delegate this to the math_expert.",
        allowed_tools=["delegate_task"] # Force supervisor to only use delegate_task
    )
    print("\nSupervisor Final Response:")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
