"""Routing skeleton for directing requests to skills/tools."""


class SkillRouter:
    """Routes incoming tasks to registered skills."""

    def route(self, task_name: str) -> str:
        """Return the skill identifier for a given task."""
        raise NotImplementedError("Routing logic is not implemented yet.")
