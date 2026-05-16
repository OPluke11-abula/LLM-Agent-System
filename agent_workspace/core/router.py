"""
core/router.py - Agent Loop, LLM Communication, Memory, and Hot-Reload.

Responsibilities:
  - LLM API communication via Custom Provider abstraction
  - Message history management with session_id support
  - Cross-turn memory persistence
  - Closed-loop state machine execution (Partial Async)
  - Hot-reload of agent.jinja2 via watchdog
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Any, List, Dict

from .engine import AgentEngine
from .providers import ProviderFactory

logger = logging.getLogger(__name__)


class MemoryManager:
    """管理 memory/{session_id}.json 的讀寫。"""

    def __init__(self, memory_dir: str, session_id: str = "default"):
        self.session_id = session_id
        self.memory_path = os.path.join(memory_dir, f"{session_id}.json")
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

    def append_conversation(self, user_input: str, assistant_response: str) -> bool:
        """
        將一輪對話附加到記憶中。
        回傳 bool 表示是否達到上限並觸發了 hook。
        """
        memory = self.load()
        if "conversations" not in memory:
            memory["conversations"] = []

        memory["conversations"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user_input,
            "assistant": assistant_response,
        })

        limit_reached = False
        # 保留最近 20 輪對話，避免記憶檔案無限增長
        if len(memory["conversations"]) > 20:
            memory["conversations"] = memory["conversations"][-20:]
            limit_reached = True
            
        self.save(memory)
        return limit_reached

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
            logger.warning("watchdog 未安裝，跳過 hot-reload。pip install watchdog")
            return

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith("agent.jinja2"):
                    # 清除 Jinja2 快取，下次 render_prompt 會自動重新讀取
                    watcher.engine.jinja_env.cache.clear()
                    logger.info("[Hot-Reload] agent.jinja2 已重新載入。")

        self._observer = Observer()
        self._observer.schedule(_Handler(), self._watch_path, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        logger.info(f"[Hot-Reload] 正在監視 {self._watch_path}/agent.jinja2")

    def stop(self):
        """停止檔案監視。"""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None


class AgentRouter:
    """Agent 執行路由器：負責 LLM 通訊、狀態機迴圈與模板熱重載。"""

    def __init__(self, engine: AgentEngine, session_id: str = "default"):
        self.engine = engine
        self.session_id = session_id
        self._config = self._load_config()

        # 從 config.yaml 讀取 max_iterations (防禦無限迴圈)
        self.max_iterations = self._config.get("agent", {}).get("max_iterations", 5)

        # 記憶管理 (傳入 session_id)
        memory_dir = os.path.join(engine.workspace_path, "memory")
        self.memory = MemoryManager(memory_dir, session_id=self.session_id)

        # 實例化 LLM Provider (工廠模式)
        provider_name = self._config.get("llm", {}).get("provider", "google-genai")
        self._provider = ProviderFactory.get_provider(provider_name)

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
            logger.warning(f"無法載入 config.yaml: {e}")
            return {}

    async def run_agent_loop(self, user_input: str) -> str:
        """
        主執行迴圈 (異步)。
        1. 渲染 System Prompt
        2. 組裝對話歷史
        3. 發送給 LLM (使用 await)
        4. 若 LLM 要求工具調用 → 執行(同步) → 回傳結果 → 繼續迴圈
        5. 若 LLM 回傳文字 → 結束迴圈
        """
        # 1. 收集動態上下文並渲染 System Prompt
        context_vars = {
            "current_time": datetime.now(timezone.utc).isoformat(),
            "context_status": "OK",
            "user_input": user_input,
            "session_id": self.session_id,
        }
        system_prompt = self.engine.render_prompt(context_vars)

        # 2. 組裝工具 Schema
        tool_schemas = self.engine.get_tool_schemas()

        # 3. 組裝對話歷史 (從記憶中載入最近的上下文)
        messages = self._build_message_history(user_input)

        logger.info(f"--- Agent Loop 啟動 (Session: {self.session_id}) ---")
        logger.debug(f"  System Prompt 長度: {len(system_prompt)} chars")
        logger.debug(f"  可用工具: {[t['name'] for t in tool_schemas]}")
        logger.debug(f"  對話歷史: {len(messages)} 則訊息")

        # 4. 狀態機迴圈
        final_response = ""
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"[迭代 {iteration}/{self.max_iterations}]")

            # 呼叫 LLM (異步)
            llm_config = self._config.get("llm", {})
            response_type, response_data = await self._provider.generate_content(
                system_prompt=system_prompt,
                messages=messages,
                tool_schemas=tool_schemas,
                config=llm_config
            )

            if response_type == "error":
                final_response = f"Error: LLM 呼叫失敗 — {response_data}"
                logger.error(final_response)
                break

            if response_type == "text":
                # LLM 回傳了最終文字回覆
                final_response = response_data
                logger.info(f"  → 最終回覆 ({len(final_response)} chars)")
                break

            elif response_type == "tool_call":
                # LLM 要求工具調用
                tool_name = response_data.get("name", "")
                tool_args = response_data.get("arguments", {})
                logger.info(f"  → 工具調用: {tool_name}({json.dumps(tool_args, ensure_ascii=False)})")

                # 執行工具 (同步)
                try:
                    tool_result = self.engine.execute_tool(tool_name, tool_args)
                except Exception as e:
                    tool_result = f"Error: 工具執行失敗 — {e}"

                # 將工具結果附加到訊息歷史，讓 LLM 看到結果
                messages.append({"role": "assistant", "tool_call": response_data})
                messages.append({"role": "tool", "name": tool_name, "content": tool_result})
                logger.debug(f"  → 工具結果: {tool_result[:200]}")
                # 繼續迴圈，讓 LLM 根據工具結果決定下一步

            else:
                final_response = f"Error: 無法解析 LLM 回應類型 '{response_type}'。"
                logger.error(final_response)
                break

        if iteration >= self.max_iterations:
            final_response = (
                f"Error: 已達最大迭代次數 ({self.max_iterations})。"
                f"可能存在無限迴圈，已強制中止。"
            )
            logger.warning(final_response)

        # 5. 將這輪對話寫入記憶
        limit_reached = self.memory.append_conversation(user_input, final_response)
        
        # 觸發記憶掛鉤 (如果需要)
        if limit_reached:
            self._on_memory_limit_reached(self.session_id, self.memory.get_recent_context(20))
            
        logger.info(f"--- Agent Loop 結束 (共 {iteration} 次迭代) ---")

        return final_response

    async def stream_agent_loop(self, user_input: str):
        """
        串流執行迴圈 (AsyncGenerator)。
        主動向外部廣播當前狀態（thinking, tool_call, tool_result）與逐字串流 (text_chunk)。
        """
        context_vars = {
            "current_time": datetime.now(timezone.utc).isoformat(),
            "context_status": "OK",
            "user_input": user_input,
            "session_id": self.session_id,
        }
        system_prompt = self.engine.render_prompt(context_vars)
        tool_schemas = self.engine.get_tool_schemas()
        messages = self._build_message_history(user_input)

        logger.info(f"--- Stream Agent Loop 啟動 (Session: {self.session_id}) ---")
        
        final_response = ""
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            llm_config = self._config.get("llm", {})
            
            yield {"type": "status", "content": "thinking"}

            response_stream = self._provider.generate_content_stream(
                system_prompt=system_prompt,
                messages=messages,
                tool_schemas=tool_schemas,
                config=llm_config
            )

            is_tool_call = False
            tool_call_data = {}
            current_text = ""

            async for resp_type, resp_data in response_stream:
                if resp_type == "error":
                    final_response = f"Error: LLM 呼叫失敗 — {resp_data}"
                    logger.error(final_response)
                    yield {"type": "error", "content": final_response}
                    break
                    
                elif resp_type == "tool_call":
                    is_tool_call = True
                    tool_call_data = resp_data
                    break  # tool call chunk is usually singular or we just break on first one
                    
                elif resp_type == "text":
                    current_text += resp_data
                    yield {"type": "text_chunk", "content": resp_data}

            if is_tool_call:
                tool_name = tool_call_data.get("name", "")
                tool_args = tool_call_data.get("arguments", {})
                yield {"type": "tool_call", "name": tool_name, "arguments": tool_args}
                
                try:
                    tool_result = self.engine.execute_tool(tool_name, tool_args)
                except Exception as e:
                    tool_result = f"Error: 工具執行失敗 — {e}"
                
                yield {"type": "tool_result", "name": tool_name, "result": tool_result}

                messages.append({"role": "assistant", "tool_call": tool_call_data})
                messages.append({"role": "tool", "name": tool_name, "content": tool_result})
                continue
            
            if current_text:
                final_response = current_text
                break
                
            if not is_tool_call and not current_text:
                # LLM returned nothing?
                final_response = "Error: LLM 未回傳任何有效內容。"
                break

        if iteration >= self.max_iterations:
            final_response = f"Error: 已達最大迭代次數 ({self.max_iterations})。"
            yield {"type": "error", "content": final_response}

        limit_reached = self.memory.append_conversation(user_input, final_response)
        if limit_reached:
            self._on_memory_limit_reached(self.session_id, self.memory.get_recent_context(20))
            
        yield {"type": "done", "content": final_response}

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

    def _on_memory_limit_reached(self, session_id: str, messages: list):
        """
        [Memory Hook] 記憶擴充預留掛鉤
        當 short_term_cache 達到限制 (如 20 輪) 時觸發。
        未來子專案可覆寫此方法，實作背景呼叫 LLM 進行自動摘要。
        """
        logger.debug(f"[Hook] Session {session_id} 記憶已達上限，可於此處實作記憶摘要邏輯。")
        pass


    def start_watching(self):
        """啟動 agent.jinja2 熱重載監視。"""
        self._watcher.start()

    def stop_watching(self):
        """停止熱重載監視。"""
        self._watcher.stop()
