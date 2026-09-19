"""Template file watcher for hot-reloading prompt templates."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_workspace.core.engine import AgentEngine

logger = logging.getLogger(__name__)


class TemplateWatcher:
    """Watch agent.jinja2 and clear the Jinja2 cache on edits."""

    def __init__(self, engine: AgentEngine) -> None:
        self.engine = engine
        self._observer = None
        self._watch_path = engine.workspace_path

    def start(self) -> None:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            logger.warning("watchdog is not installed. Prompt hot-reload is disabled.")
            return

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event) -> None:
                if event.src_path.endswith("agent.jinja2"):
                    watcher.engine.jinja_env.cache.clear()
                    logger.info("[Hot-Reload] agent.jinja2 cache cleared")

        self._observer = Observer()
        self._observer.schedule(_Handler(), self._watch_path, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        logger.info("[Hot-Reload] watching %s/agent.jinja2", self._watch_path)

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None
