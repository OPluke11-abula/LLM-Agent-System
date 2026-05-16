"""
core/providers.py - LLM Provider Abstraction Layer

This module provides a lightweight abstraction for LLM APIs,
allowing the framework to decouple from specific vendor SDKs
without relying on heavy third-party packages.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Tuple, List, Dict

logger = logging.getLogger(__name__)

class BaseLLMProvider(ABC):
    """抽象的 LLM 服務提供者介面。"""
    
    @abstractmethod
    async def generate_content(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tool_schemas: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Tuple[str, Any]:
        """
        呼叫 LLM 並回傳解析後的結果。
        
        回傳值格式:
          (response_type, response_data)
          - response_type: "text" | "tool_call" | "error"
          - response_data: text string 或者 dict (包含 name 與 arguments)
        """
        pass


class GoogleGenAIProvider(BaseLLMProvider):
    """Google Gemini 的實作。"""
    
    def __init__(self):
        try:
            from google import genai
            self.client = genai.Client()
            logger.debug("GoogleGenAIProvider initialized.")
        except ImportError:
            logger.error("google-genai SDK 未安裝。請執行: pip install google-genai")
            raise ImportError("google-genai SDK is required for GoogleGenAIProvider.")

    async def generate_content(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tool_schemas: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Tuple[str, Any]:
        try:
            from google.genai import types
            
            model = config.get("model", "gemini-2.5-flash")
            
            # 組裝 contents
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
                    tc = msg["tool_call"]
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part.from_function_call(
                            name=tc["name"],
                            args=tc.get("arguments", {}),
                        )],
                    ))
                elif msg["role"] == "tool":
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(
                            name=msg["name"],
                            response={"result": msg["content"]},
                        )],
                    ))

            # 組裝 tools
            tools = None
            if tool_schemas:
                function_declarations = []
                for ts in tool_schemas:
                    params = ts.get("input_schema", {})
                    function_declarations.append(types.FunctionDeclaration(
                        name=ts["name"],
                        description=ts["description"],
                        parameters=params,
                    ))
                tools = [types.Tool(function_declarations=function_declarations)]

            req_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=config.get("temperature", 0.0),
                max_output_tokens=config.get("max_tokens", 4096),
                tools=tools,
            )

            logger.debug(f"Calling Google GenAI API (model: {model})")
            
            # 使用 asyncio.to_thread 將同步 API 呼叫包裝為異步
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=model,
                contents=contents,
                config=req_config,
            )

            return self._parse_response(response)

        except Exception as e:
            logger.error(f"Google GenAI API call failed: {e}")
            return "error", str(e)

    def _parse_response(self, response: Any) -> Tuple[str, Any]:
        """解析 LLM 原生回應。"""
        try:
            candidate = response.candidates[0]
            parts = candidate.content.parts

            for part in parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    return "tool_call", {
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {},
                    }

            text = response.text if hasattr(response, "text") else ""
            return "text", text

        except (AttributeError, IndexError, TypeError) as e:
            logger.warning(f"Error parsing LLM response: {e}")
            try:
                return "text", str(response.text)
            except Exception:
                return "error", str(e)

class ProviderFactory:
    """Provider 實例化工廠。"""
    
    @staticmethod
    def get_provider(provider_name: str) -> BaseLLMProvider:
        if provider_name == "google-genai":
            return GoogleGenAIProvider()
        # 未來可以輕鬆擴充 openai 或 anthropic
        else:
            raise ValueError(f"不支援的 LLM provider: '{provider_name}'")
