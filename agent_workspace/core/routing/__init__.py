"""Routing package for agent swarm dispatch, memory, and template monitoring."""

from __future__ import annotations

from .registry import SwarmRouteRegistry, ROUTE_REGISTRY
from .memory import MemoryManager
from .template_watcher import TemplateWatcher

__all__ = [
    "SwarmRouteRegistry",
    "ROUTE_REGISTRY",
    "MemoryManager",
    "TemplateWatcher",
]
