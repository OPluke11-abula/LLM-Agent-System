import threading
import jinja2
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

class AgentBuilderRegistry:
    """
    Thread-safe registry for custom agent personas and skill bindings
    configured via the No-Code SaaS builder.
    """
    _lock = threading.Lock()
    _agents: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register_agent(cls, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        with cls._lock:
            # Ensure name is in the configuration
            config_copy = dict(config)
            config_copy["name"] = name
            cls._agents[name] = config_copy
            return config_copy

    @classmethod
    def get_agent(cls, name: str) -> Optional[Dict[str, Any]]:
        with cls._lock:
            return cls._agents.get(name)

    @classmethod
    def get_all_agents(cls) -> List[Dict[str, Any]]:
        with cls._lock:
            return list(cls._agents.values())

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._agents.clear()


PRESET_TEMPLATES = [
    {
        "name": "default_assistant",
        "description": "Standard helpful assistant with dynamic guidelines.",
        "template": (
            "You are {{ name }}, a helpful AI assistant in the role of: {{ role }}.\n"
            "Your description is: {{ description }}\n"
            "Current guidelines:\n"
            "{% for g in guidelines %}\n"
            "- {{ g }}\n"
            "{% endfor %}"
        )
    },
    {
        "name": "executive_coach",
        "description": "Concise CEO Executive Coach focusing on business strategy.",
        "template": (
            "You are {{ name }}, the Executive Coach. "
            "Focus strictly on high-level strategy: {{ strategy_focus }}.\n"
            "Keep feedback short and actionable."
        )
    }
]


def render_system_prompt(template_str: str, variables: Dict[str, Any]) -> str:
    """Renders dynamic Jinja2 prompts based on variables context."""
    template = jinja2.Template(template_str)
    return template.render(**variables)


def emit_mock_webhook_telemetry(gateways: List[Dict[str, Any]], message: str) -> List[Dict[str, Any]]:
    """Generates mock webhook telemetry records for third-party systems like Slack or LINE."""
    logs = []
    for g in gateways:
        g_type = g.get("type", "unknown").lower()
        webhook_url = g.get("webhook_url", "http://mock-endpoint")
        
        # Build mock payload structure based on service type
        if g_type == "slack":
            payload = {"text": message}
        elif g_type == "line":
            payload = {"messages": [{"type": "text", "text": message}]}
        else:
            payload = {"message": message}

        logs.append({
            "gateway": g_type,
            "webhook_url": webhook_url,
            "payload_sent": payload,
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    return logs
