"""
test_closed_loop.py - End-to-end closed loop test.

Usage:
  $env:GOOGLE_API_KEY='your-key'
  python agent_workspace/test_closed_loop.py
"""

import sys
import os

# 確保 agent_workspace 在 path 中
workspace = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace)

from core.engine import AgentEngine
from core.router import AgentRouter

def main():
    # 檢查 API Key
    if not os.environ.get("GOOGLE_API_KEY"):
        print("ERROR: 請先設定 GOOGLE_API_KEY 環境變數")
        print("  PowerShell: $env:GOOGLE_API_KEY='your-key-here'")
        return

    # 初始化引擎
    engine = AgentEngine(workspace_path=workspace)
    router = AgentRouter(engine)

    print(engine.summary())
    print()

    # ── 測試 1：純文字對話 (不需要工具) ──
    print("=" * 60)
    print("  測試 1：純文字對話")
    print("=" * 60)
    result = router.run_agent_loop("你好，用一句話介紹你自己。")
    print(f"\n回覆: {result}\n")

    # ── 測試 2：工具調用閉環 (LLM 應該呼叫 calculate) ──
    print("=" * 60)
    print("  測試 2：工具調用閉環")
    print("=" * 60)
    result = router.run_agent_loop("請幫我計算 123 乘以 456 等於多少？請使用 calculate 工具。")
    print(f"\n回覆: {result}\n")

    # ── 測試 3：驗證記憶持久化 ──
    print("=" * 60)
    print("  測試 3：記憶持久化驗證")
    print("=" * 60)
    import json
    recent = router.memory.get_recent_context(n=5)
    print(f"記憶中共有 {len(recent)} 輪對話:")
    for i, conv in enumerate(recent):
        print(f"  [{i+1}] User: {conv['user'][:50]}...")
        print(f"       AI:   {conv['assistant'][:50]}...")

if __name__ == "__main__":
    main()
