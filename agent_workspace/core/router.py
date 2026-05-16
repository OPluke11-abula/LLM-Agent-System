"""
core/router.py - Agent Loop, LLM Communication, Memory, and Hot-Reload.

Responsibilities:
  - LLM API communication (currently supports Google Genai)
  - Message history management
  - Cross-turn memory persistence (memory/short_term_cache.json)
  - Closed-loop state machine execution
  - Hot-reload of agent.jinja2 via watchdog
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

from .engine import AgentEngine


class MemoryManager:
    """管理 memory/short_term_cache.json 的讀寫。"""

    def __init__(self, memory_path: str):
        self.memory_path = memory_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """確保記憶檔案存在。"""
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        if not os.path.isfile(self.memory_path):
            self._write({})

    def load(self) -> dict:
        """讀取記憶。"""
        try:
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save(self, data: dict):
        """寫入記憶。"""
        self._write(data)

    def append_conversation(self, user_input: str, assistant_response: str):
        """將一輪對話附加到記憶中。"""
        memory = self.load()
        if "conversations" not in memory:
            memory["conversations"] = []

        memory["conversations"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user_input,
            "assistant": assistant_response,
        })

        # 保留最近 20 輪對話，避免記憶檔案無限增長
        memory["conversations"] = memory["conversations"][-20:]
        self.save(memory)

    def get_recent_context(self, n: int = 5) -> list[dict]:
        """取得最近 n 輪對話作為上下文。"""
        memory = self.load()
        conversations = memory.get("conversations", [])
        return conversations[-n:]

    def _write(self, data: dict):
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class TemplateWatcher:
    """監視 agent.jinja2 檔案變更，存檔即自動重新編譯模板 (Hot-Reload)。"""

    def __init__(self, engine: AgentEngine):
        self.engine = engine
        self._observer = None
        self._watch_path = engine.workspace_path

    def start(self):
        """啟動檔案監視。"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            print("Warning: watchdog 未安裝，跳過 hot-reload。pip install watchdog")
            return

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith("agent.jinja2"):
                    # 清除 Jinja2 快取，下次 render_prompt 會自動重新讀取
                    watcher.engine.jinja_env.cache.clear()
                    print("[Hot-Reload] agent.jinja2 已重新載入。")

        self._observer = Observer()
        self._observer.schedule(_Handler(), self._watch_path, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        print(f"[Hot-Reload] 正在監視 {self._watch_path}/agent.jinja2")

    def stop(self):
        """停止檔案監視。"""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None


class AgentRouter:
    """Agent 執行路由器：負責 LLM 通訊、狀態機迴圈與模板熱重載。"""

    def __init__(self, engine: AgentEngine):
        self.engine = engine

        # LLM 客戶端 (延遲初始化)
        self._llm_client = None
        self._config = self._load_config()

        # 從 config.yaml 讀取 max_iterations (防禦無限迴圈)
        self.max_iterations = self._config.get("agent", {}).get("max_iterations", 5)

        # 記憶管理
        memory_path = os.path.join(engine.workspace_path, "memory", "short_term_cache.json")
        self.memory = MemoryManager(memory_path)

        # 熱重載 (Hot-Reload)
        self._watcher = TemplateWatcher(engine)

    def _load_config(self) -> dict:
        """從 config.yaml 載入 LLM 設定。"""
        import yaml
        config_path = os.path.join(self.engine.workspace_path, "config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (IOError, yaml.YAMLError) as e:
            print(f"Warning: 無法載入 config.yaml: {e}")
            return {}

    def _get_llm_client(self):
        """延遲初始化 LLM 客戶端。"""
        if self._llm_client is not None:
            return self._llm_client

        provider = self._config.get("llm", {}).get("provider", "google-genai")

        if provider == "google-genai":
            try:
                from google import genai
                # google-genai SDK 會自動讀取 GOOGLE_API_KEY 環境變數
                self._llm_client = genai.Client()
            except ImportError:
                raise ImportError(
                    "google-genai SDK 未安裝。請執行: pip install google-genai"
                )
        else:
            raise ValueError(
                f"不支援的 LLM provider: '{provider}'。"
                f"目前支援: 'google-genai'。"
                f"未來可擴充 'anthropic' / 'openai'。"
            )

        return self._llm_client

    def run_agent_loop(self, user_input: str) -> str:
        """
        主執行迴圈。
        1. 渲染 System Prompt
        2. 組裝對話歷史
        3. 發送給 LLM
        4. 若 LLM 要求工具調用 → 執行 → 回傳結果 → 繼續迴圈
        5. 若 LLM 回傳文字 → 結束迴圈
        """
        # 1. 收集動態上下文並渲染 System Prompt
        context_vars = {
            "current_time": datetime.now(timezone.utc).isoformat(),
            "context_status": "OK",
            "user_input": user_input,
        }
        system_prompt = self.engine.render_prompt(context_vars)

        # 2. 組裝工具 Schema
        tool_schemas = self.engine.get_tool_schemas()

        # 3. 組裝對話歷史 (從記憶中載入最近的上下文)
        messages = self._build_message_history(user_input)

        print(f"--- Agent Loop 啟動 ---")
        print(f"  System Prompt 長度: {len(system_prompt)} chars")
        print(f"  可用工具: {[t['name'] for t in tool_schemas]}")
        print(f"  對話歷史: {len(messages)} 則訊息")

        # 4. 狀態機迴圈
        final_response = ""
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n[迭代 {iteration}/{self.max_iterations}]")

            # 呼叫 LLM
            response = self._call_llm(system_prompt, messages, tool_schemas)

            if response is None:
                final_response = "Error: LLM 呼叫失敗。"
                break

            # 解析回應
            response_type, response_data = self._parse_response(response)

            if response_type == "text":
                # LLM 回傳了最終文字回覆
                final_response = response_data
                print(f"  → 最終回覆 ({len(final_response)} chars)")
                break

            elif response_type == "tool_call":
                # LLM 要求工具調用
                tool_name = response_data.get("name", "")
                tool_args = response_data.get("arguments", {})
                print(f"  → 工具調用: {tool_name}({json.dumps(tool_args, ensure_ascii=False)})")

                # 執行工具
                try:
                    tool_result = self.engine.execute_tool(tool_name, tool_args)
                except Exception as e:
                    tool_result = f"Error: 工具執行失敗 — {e}"

                # 將工具結果附加到訊息歷史，讓 LLM 看到結果
                messages.append({"role": "assistant", "tool_call": response_data})
                messages.append({"role": "tool", "name": tool_name, "content": tool_result})
                print(f"  → 工具結果: {tool_result[:200]}")
                # 繼續迴圈，讓 LLM 根據工具結果決定下一步

            else:
                final_response = "Error: 無法解析 LLM 回應。"
                break

        if iteration >= self.max_iterations:
            final_response = (
                f"Error: 已達最大迭代次數 ({self.max_iterations})。"
                f"可能存在無限迴圈，已強制中止。"
            )
            print(f"  ⚠ {final_response}")

        # 5. 將這輪對話寫入記憶
        self.memory.append_conversation(user_input, final_response)
        print(f"\n--- Agent Loop 結束 (共 {iteration} 次迭代) ---")

        return final_response

    def _build_message_history(self, current_input: str) -> list[dict]:
        """從記憶中載入最近的對話，加上當前用戶輸入。"""
        messages = []

        # 載入最近的歷史對話作為上下文
        recent = self.memory.get_recent_context(n=5)
        for conv in recent:
            messages.append({"role": "user", "content": conv["user"]})
            messages.append({"role": "assistant", "content": conv["assistant"]})

        # 加入當前用戶輸入
        messages.append({"role": "user", "content": current_input})
        return messages

    def _call_llm(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_schemas: list[dict],
    ) -> Any | None:
        """
        呼叫 LLM API。
        目前實作 google-genai，未來可擴充其他 provider。
        """
        provider = self._config.get("llm", {}).get("provider", "google-genai")

        if provider == "google-genai":
            return self._call_google_genai(system_prompt, messages, tool_schemas)
        else:
            print(f"Error: 不支援的 provider '{provider}'")
            return None

    def _call_google_genai(
        self,
        system_prompt: str,
        messages: list[dict],
        tool_schemas: list[dict],
    ) -> Any | None:
        """使用 google-genai SDK 呼叫 Gemini。"""
        try:
            from google import genai
            from google.genai import types

            client = self._get_llm_client()
            model = self._config.get("llm", {}).get("model", "gemini-2.5-flash")

            # 組裝 google-genai 格式的 contents
            contents = []
            for msg in messages:
                if msg["role"] == "user":
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=msg["content"])],
                    ))
                elif msg["role"] == "assistant" and "content" in msg:
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=msg["content"])],
                    ))
                elif msg["role"] == "assistant" and "tool_call" in msg:
                    # LLM 先前要求的工具調用 → 轉為 FunctionCall Part
                    tc = msg["tool_call"]
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_function_call(
                            name=tc["name"],
                            args=tc.get("arguments", {}),
                        )],
                    ))
                elif msg["role"] == "tool":
                    # 工具執行結果 → 轉為 FunctionResponse Part
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(
                            name=msg["name"],
                            response={"result": msg["content"]},
                        )],
                    ))

            # 組裝工具定義 (如果有的話)
            tools = None
            if tool_schemas:
                function_declarations = []
                for ts in tool_schemas:
                    # 將我們的 schema 轉換為 google-genai 格式
                    params = ts.get("input_schema", {})
                    function_declarations.append(types.FunctionDeclaration(
                        name=ts["name"],
                        description=ts["description"],
                        parameters=params,
                    ))
                tools = [types.Tool(function_declarations=function_declarations)]

            # 發送請求
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self._config.get("llm", {}).get("temperature", 0.0),
                max_output_tokens=self._config.get("llm", {}).get("max_tokens", 4096),
                tools=tools,
            )

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response

        except Exception as e:
            print(f"Error: Google Genai API 呼叫失敗 — {e}")
            return None

    def _parse_response(self, response: Any) -> tuple[str, Any]:
        """
        解析 LLM 回應，回傳 (type, data)。
        type: "text" | "tool_call"
        """
        try:
            # google-genai 回應格式
            candidate = response.candidates[0]
            parts = candidate.content.parts

            for part in parts:
                # 檢查是否為 function call
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    return "tool_call", {
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {},
                    }

            # 如果沒有 function call，就是純文字
            text = response.text if hasattr(response, "text") else ""
            return "text", text

        except (AttributeError, IndexError, TypeError) as e:
            print(f"Warning: 解析 LLM 回應時發生錯誤: {e}")
            # 嘗試取得純文字
            try:
                return "text", str(response.text)
            except Exception:
                return "error", str(e)


    def start_watching(self):
        """啟動 agent.jinja2 熱重載監視。"""
        self._watcher.start()

    def stop_watching(self):
        """停止熱重載監視。"""
        self._watcher.stop()


# =====================================================================
#  本機驗證入口
# =====================================================================
if __name__ == "__main__":
    import sys
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, workspace)

    engine = AgentEngine(workspace_path=workspace)
    router = AgentRouter(engine)

    print(engine.summary())
    print(f"max_iterations (from config.yaml): {router.max_iterations}")
    print()

    # 測試熱重載
    print("--- Hot-Reload 測試 ---")
    router.start_watching()
    print("  (修改 agent.jinja2 並存檔，應看到 [Hot-Reload] 訊息)")
    print("  (按 Ctrl+C 結束)")
    print()

    # 測試 LLM 呼叫 (需要設定 GOOGLE_API_KEY 環境變數)
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if api_key:
        print("--- LLM 通訊測試 ---")
        result = router.run_agent_loop("Hello")
        print(f"Reply: {result}")
    else:
        print("--- Skip LLM test (GOOGLE_API_KEY not set) ---")

    router.stop_watching()
