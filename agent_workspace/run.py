"""
run.py - Event-Driven Task Runner for FindAi Studio LLM Agent.

Usage:
  python run.py <event_name> [options]

Examples:
  python run.py summary
  python run.py test --session test-123
  python run.py chat --msg "Hello" --session user-456
"""

import sys
import os
import json
import asyncio
import argparse
import logging

# 確保能 import agent_workspace
workspace = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace)

from core.engine import AgentEngine
from core.router import AgentRouter
from observability import configure_logging

# 設定全域 Logging（CLI 模式使用人類可讀格式，設定 json_output=True 可切換為 JSON）
configure_logging(json_output=False)
logger = logging.getLogger("TaskRunner")


class EventRegistry:
    """事件註冊與分發中心"""

    @staticmethod
    def run_summary(args):
        """顯示引擎狀態 (knowledge + tools)"""
        engine = AgentEngine(workspace_path=workspace)
        print(engine.summary())
        schemas = engine.get_tool_schemas()
        print(f"\nTool Schemas ({len(schemas)}):")
        print(json.dumps(schemas, indent=2, ensure_ascii=False))

    @staticmethod
    async def run_test(args):
        """執行閉環端對端測試"""
        if not os.environ.get("GOOGLE_API_KEY"):
            logger.error("GOOGLE_API_KEY not set. Use: $env:GOOGLE_API_KEY='your-key'")
            return

        session_id = args.session or "test-session"
        engine = AgentEngine(workspace_path=workspace)
        router = AgentRouter(engine, session_id=session_id)

        print(f"\n=== Test 1: Text Response (Session: {session_id}) ===")
        r1 = await router.run_agent_loop("Hello, introduce yourself in one sentence.")
        print(f"\nReply: {r1}\n")

        print("=== Test 2: Tool Call Loop ===")
        r2 = await router.run_agent_loop("Calculate 123 * 456 using the calculate tool.")
        print(f"\nReply: {r2}\n")

        print("=== Test 3: Memory Check ===")
        recent = router.memory.get_recent_context(n=5)
        print(f"Stored conversations: {len(recent)}")
        for i, c in enumerate(recent):
            print(f"  [{i+1}] User: {c['user'][:50]}")
            print(f"       AI:   {c['assistant'][:50]}")

    @staticmethod
    async def run_chat(args):
        """執行單次對話"""
        if not os.environ.get("GOOGLE_API_KEY"):
            logger.error("GOOGLE_API_KEY not set.")
            return

        session_id = args.session or "default-session"
        msg = args.msg or "Hello"
        
        engine = AgentEngine(workspace_path=workspace)
        router = AgentRouter(engine, session_id=session_id)
        
        result = await router.run_agent_loop(msg)
        print(f"\n{result}")

    @staticmethod
    async def run_stream(args):
        """執行單次對話 (Streaming 模式)"""
        if not os.environ.get("GOOGLE_API_KEY"):
            logger.error("GOOGLE_API_KEY not set.")
            return

        session_id = args.session or "stream-session"
        msg = args.msg or "Hello"
        
        engine = AgentEngine(workspace_path=workspace)
        router = AgentRouter(engine, session_id=session_id)
        
        print(f"\nUser: {msg}\nAgent: ", end="", flush=True)
        
        async for event in router.stream_agent_loop(msg):
            event_type = event.get("type")
            if event_type == "status":
                print(f"[{event['content']}]...", end="", flush=True)
            elif event_type == "tool_call":
                print(f"\n[呼叫工具] {event['name']}({json.dumps(event.get('arguments', {}), ensure_ascii=False)})", flush=True)
            elif event_type == "tool_result":
                # 只印出前 50 個字避免洗版
                res_preview = str(event.get('result', ''))[:50].replace('\n', ' ')
                print(f"[工具結果] {res_preview}...\nAgent: ", end="", flush=True)
            elif event_type == "text_chunk":
                print(event["content"], end="", flush=True)
            elif event_type == "done":
                print("\n")
            elif event_type == "error":
                print(f"\n[錯誤] {event['content']}\n")

    @staticmethod
    def run_log(args):
        """管理工作區結構化日誌"""
        try:
            from skills.tool_log import CompressLogsArgs, log_compress_done, ArchiveMonthArgs, log_archive_month
            context = {"workspace_path": workspace}
            if args.compress:
                result = log_compress_done(CompressLogsArgs(), context=context)
                print(result)
            elif args.archive:
                result = log_archive_month(ArchiveMonthArgs(month=args.archive), context=context)
                print(result)
            else:
                print("Usage: python run.py log --compress | --archive YYYY-MM")
        except ImportError as e:
            logger.error(f"Failed to load log tools: {e}")

def main():
    parser = argparse.ArgumentParser(description="FindAi Studio Agent Task Runner")
    subparsers = parser.add_subparsers(dest="event", required=True, help="Event to run")

    # Event: summary
    parser_summary = subparsers.add_parser("summary", help="Show engine status and tool schemas")

    # Event: test
    parser_test = subparsers.add_parser("test", help="Run E2E closed-loop test")
    parser_test.add_argument("--session", type=str, help="Session ID for memory isolation")

    # Event: chat
    parser_chat = subparsers.add_parser("chat", help="Send a message to the agent")
    parser_chat.add_argument("--msg", type=str, required=True, help="Message to send")
    parser_chat.add_argument("--session", type=str, help="Session ID for memory isolation")

    # Event: stream
    parser_stream = subparsers.add_parser("stream", help="Send a message with streaming output")
    parser_stream.add_argument("--msg", type=str, required=True, help="Message to send")
    parser_stream.add_argument("--session", type=str, help="Session ID for memory isolation")

    # Event: log
    parser_log = subparsers.add_parser("log", help="Manage structured logs")
    parser_log.add_argument("--compress", action="store_true", help="Compress logs of done tasks")
    parser_log.add_argument("--archive", type=str, help="Archive logs for a specific month (YYYY-MM)")

    args = parser.parse_args()

    # 事件分發路由
    if args.event == "summary":
        EventRegistry.run_summary(args)
    elif args.event == "test":
        asyncio.run(EventRegistry.run_test(args))
    elif args.event == "chat":
        asyncio.run(EventRegistry.run_chat(args))
    elif args.event == "stream":
        asyncio.run(EventRegistry.run_stream(args))
    elif args.event == "log":
        EventRegistry.run_log(args)
    else:
        logger.error(f"Unknown event: {args.event}")


if __name__ == "__main__":
    main()
