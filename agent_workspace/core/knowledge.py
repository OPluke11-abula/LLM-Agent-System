"""Knowledge Base Query Engine for LAS.

Maintains strict read-only boundary checks to prevent directory traversal
and searches/indexes structured YAML knowledge documents.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Secure, read-only manager for domain knowledge base documents."""

    @staticmethod
    def query(keyword: str, workspace_path: str = ".") -> list[dict[str, Any]]:
        """Query indexed static knowledge base documents by a keyword.

        Checks for matches in tags, title, description, ID, or raw text.
        Maintains robust read-only boundary check to prevent traversal out of
        the active knowledge_base directory.
        """
        resolved_workspace = Path(os.path.abspath(workspace_path))
        project_root = resolved_workspace.parent
        
        index_file = project_root / ".agent" / "knowledge_base" / "index.json"
        kb_dir = resolved_workspace / "knowledge_base"
        kb_dir_resolved = kb_dir.resolve()

        if not index_file.is_file():
            logger.warning("Knowledge index file not found at %s", index_file)
            return []

        try:
            index_data = json.loads(index_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to parse knowledge base index: %s", e)
            return []

        documents = index_data.get("documents", [])
        matched_docs = []

        keyword_lower = keyword.lower().strip()

        for doc in documents:
            doc_id = doc.get("id", "")
            title = doc.get("title", "")
            desc = doc.get("description", "")
            tags = doc.get("tags", [])
            doc_path = doc.get("file_path", "")

            # Boundary resolution & protection check
            # Combine paths and resolve completely to absolute forms
            target_file = (project_root / doc_path).resolve()

            try:
                # relative_to will throw ValueError if target_file is not under kb_dir_resolved
                target_file.relative_to(kb_dir_resolved)
            except ValueError:
                raise PermissionError(
                    f"Directory traversal warning: Access denied to outside boundary path '{target_file}'"
                )

            if not target_file.is_file():
                logger.warning("Indexed file '%s' does not exist at resolved path '%s'", doc_id, target_file)
                continue

            try:
                content = target_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error("Failed to read knowledge document '%s': %s", doc_id, e)
                continue

            # Check if keyword matches title, desc, ID, tags, or raw content
            match_found = (
                keyword_lower in doc_id.lower()
                or keyword_lower in title.lower()
                or keyword_lower in desc.lower()
                or any(keyword_lower in t.lower() for t in tags)
                or keyword_lower in content.lower()
            )

            if match_found:
                # Parse frontmatter and body
                frontmatter = {}
                body = content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        try:
                            frontmatter = yaml.safe_load(parts[1]) or {}
                        except yaml.YAMLError:
                            pass
                        body = parts[2].strip()

                matched_docs.append({
                    "id": doc_id,
                    "title": title,
                    "description": desc,
                    "creator": doc.get("creator", ""),
                    "version": doc.get("version", ""),
                    "tags": tags,
                    "frontmatter": frontmatter,
                    "content": body
                })

        return matched_docs
