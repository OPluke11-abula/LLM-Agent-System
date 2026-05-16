"""
=========================================================================
 core/engine.py — 雙軌解析引擎 (Dual-Parser Engine)
 
 職責：
   軌道 1 (大腦/Persona)：解析 knowledge_base/ 中的 SKILL.md，
       提取 YAML Frontmatter 與 Markdown 內文，作為上下文注入 Jinja2 模板。
   軌道 2 (手腳/Tools)：反射掃描 skills/ 中的 Python 函數，
       萃取 Pydantic BaseModel 的 Type Hints 與 Docstring，轉換為 JSON Schema。
=========================================================================
"""

import os
import sys
import importlib
import inspect
import logging
from typing import Any

logger = logging.getLogger(__name__)

import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, UndefinedError
from pydantic import BaseModel


class AgentEngine:
    """Agent 核心引擎：負責模板渲染、知識載入與工具發現。"""

    def __init__(self, workspace_path: str = "."):
        self.workspace_path = os.path.abspath(workspace_path)

        # Jinja2 環境初始化 (預設 undefined 行為會在缺少變數時拋出 UndefinedError)
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.workspace_path),
        )

        # ── 軌道 1：知識上下文 (Persona / Knowledge) ──
        self.knowledge_contexts: list[dict[str, str]] = []
        self._discover_markdown_contexts()

        # ── 軌道 2：可執行工具 (Tools / Actions) ──
        self.tools_registry: dict[str, dict[str, Any]] = {}
        self._ensure_skills_importable()
        self._discover_tools()

    # =====================================================================
    #  公開介面 (Public API)
    # =====================================================================

    def render_prompt(self, context_vars: dict) -> str:
        """
        渲染 agent.jinja2 模板。
        自動將 knowledge_contexts 注入到上下文中，
        使用者只需傳入額外的動態變數 (如 current_time)。
        """
        # 將知識上下文自動合併進渲染變數
        merged_vars = {
            "knowledge_contexts": self.knowledge_contexts,
            **context_vars,
        }
        try:
            template = self.jinja_env.get_template("agent.jinja2")
            return template.render(**merged_vars)
        except TemplateNotFound:
            raise FileNotFoundError(
                f"找不到 agent.jinja2，請確認它位於 {self.workspace_path}"
            )
        except UndefinedError as e:
            raise ValueError(
                f"模板渲染失敗：變數未定義 — {e}。"
                f"請檢查 agent.jinja2 中的 {{{{ }}}} 佔位符是否都有對應的值。"
            )

    def get_tool_schemas(self) -> list[dict]:
        """
        回傳所有已註冊工具的 JSON Schema 列表，
        格式相容 Anthropic / OpenAI 的 Function Calling API。
        """
        schemas = []
        for name, tool in self.tools_registry.items():
            schema = tool["schema"].copy()
            # 移除 Pydantic 自動產生的 title，LLM API 不需要
            schema.pop("title", None)

            schemas.append({
                "name": name,
                "description": (tool["description"] or "").strip(),
                "input_schema": schema,
            })
        return schemas

    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """
        安全執行指定的工具。
        使用 Pydantic 做二次校驗後才真正呼叫函數。
        """
        if tool_name not in self.tools_registry:
            raise KeyError(f"未知的工具名稱：'{tool_name}'。已註冊：{list(self.tools_registry.keys())}")

        tool = self.tools_registry[tool_name]
        # 用 Pydantic 進行型別校驗 (防止 LLM 傳入錯誤參數)
        validated_args = tool["args_model"](**arguments)
        result = tool["function"](validated_args)
        return str(result)

    def summary(self) -> str:
        """印出引擎當前狀態摘要，方便除錯。"""
        lines = [
            "=" * 60,
            "  AgentEngine 狀態摘要",
            "=" * 60,
            f"  工作目錄：{self.workspace_path}",
            "",
            f"  ── 軌道 1：知識上下文 (共 {len(self.knowledge_contexts)} 個) ──",
        ]
        for ctx in self.knowledge_contexts:
            lines.append(f"    • {ctx['name']}: {ctx['description'][:60]}...")

        lines.append("")
        lines.append(f"  ── 軌道 2：可執行工具 (共 {len(self.tools_registry)} 個) ──")
        for name in self.tools_registry:
            lines.append(f"    • {name}")

        lines.append("=" * 60)
        return "\n".join(lines)

    # =====================================================================
    #  軌道 1：Markdown SKILL.md 解析 (Persona / Knowledge)
    # =====================================================================

    def _discover_markdown_contexts(self):
        """
        掃描 knowledge_base/ 目錄，尋找 SKILL.md 格式的知識檔案。
        支援兩種結構：
          - knowledge_base/SKILL.md           (單一檔案)
          - knowledge_base/skill-name/SKILL.md (子目錄分類)
        """
        kb_dir = os.path.join(self.workspace_path, "knowledge_base")
        if not os.path.isdir(kb_dir):
            return

        # 掃描子目錄中的 SKILL.md
        for entry in sorted(os.listdir(kb_dir)):
            entry_path = os.path.join(kb_dir, entry)

            # 直接放在 knowledge_base/ 下的 .md 檔案
            if os.path.isfile(entry_path) and entry.lower().endswith(".md"):
                self._parse_skill_md(entry_path)

            # 子目錄裡的 SKILL.md
            elif os.path.isdir(entry_path):
                skill_file = os.path.join(entry_path, "SKILL.md")
                if os.path.isfile(skill_file):
                    self._parse_skill_md(skill_file)

    def _parse_skill_md(self, filepath: str):
        """
        解析單一 SKILL.md 檔案。
        格式：YAML Frontmatter (--- ... ---) + Markdown 正文。
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
        except (IOError, OSError) as e:
            logger.warning(f"無法讀取 {filepath}: {e}")
            return

        # 分離 YAML Frontmatter 與 Markdown 正文
        frontmatter, body = self._split_frontmatter(raw)

        name = frontmatter.get("name", os.path.basename(os.path.dirname(filepath)))
        description = frontmatter.get("description", "")

        self.knowledge_contexts.append({
            "name": name,
            "description": description,
            "content": body.strip(),
            "source_file": filepath,
        })

    @staticmethod
    def _split_frontmatter(raw_text: str) -> tuple[dict, str]:
        """
        將 YAML Frontmatter (---...---) 從 Markdown 正文中分離。
        回傳 (frontmatter_dict, markdown_body)。
        """
        if not raw_text.startswith("---"):
            return {}, raw_text

        parts = raw_text.split("---", 2)
        if len(parts) < 3:
            return {}, raw_text

        try:
            frontmatter = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            frontmatter = {}

        body = parts[2]
        return frontmatter, body

    # =====================================================================
    #  軌道 2：Python Pydantic 反射 (Tools / Actions)
    # =====================================================================

    def _ensure_skills_importable(self):
        """確保 agent_workspace 在 sys.path 中，使 importlib 能找到 skills 模組。"""
        if self.workspace_path not in sys.path:
            sys.path.insert(0, self.workspace_path)

    def _discover_tools(self):
        """
        反射掃描 skills/ 目錄下的 .py 檔案，
        尋找參數為 Pydantic BaseModel 的函數並自動註冊。
        忽略 __init__.py 與範本檔案。
        """
        skills_dir = os.path.join(self.workspace_path, "skills")
        if not os.path.isdir(skills_dir):
            return

        skip_files = {"__init__.py"}

        for filename in sorted(os.listdir(skills_dir)):
            if not filename.endswith(".py") or filename in skip_files:
                continue

            module_name = f"skills.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                self._register_functions_from_module(module)
            except Exception as e:
                logger.warning(f"載入技能模組 {module_name} 失敗: {e}")

    def _register_functions_from_module(self, module):
        """從模組中找出有效的工具函數 (吃 Pydantic BaseModel 的函數)。"""
        for name, func in inspect.getmembers(module, inspect.isfunction):
            # 跳過私有函數
            if name.startswith("_"):
                continue

            sig = inspect.signature(func)
            params = list(sig.parameters.values())

            # 有效工具：恰好一個參數，且型別為 Pydantic BaseModel
            if len(params) != 1:
                continue

            annotation = params[0].annotation
            if not (inspect.isclass(annotation) and issubclass(annotation, BaseModel)):
                continue

            self.tools_registry[name] = {
                "function": func,
                "args_model": annotation,
                "description": inspect.getdoc(func),
                "schema": annotation.model_json_schema(),
            }


# =====================================================================
#  本機驗證入口
# =====================================================================
if __name__ == "__main__":
    # 從 agent_workspace/ 目錄直接執行：python core/engine.py
    import json

    engine = AgentEngine(workspace_path=os.path.dirname(os.path.dirname(__file__)))

    # 印出引擎狀態
    print(engine.summary())

    # 測試渲染
    print("\n--- 渲染後的 System Prompt (前 500 字) ---")
    prompt = engine.render_prompt({
        "current_time": "2026-05-16T11:30:00+08:00",
        "context_status": "OK",
        "user_input": "你好，請告訴我你擁有哪些知識？",
    })
    print(prompt[:500])

    # 測試工具 Schema
    print("\n--- Tool Schemas (JSON) ---")
    print(json.dumps(engine.get_tool_schemas(), indent=2, ensure_ascii=False))
