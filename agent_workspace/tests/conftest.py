import os
import sys
import pkgutil
import importlib

# Dynamically add project root directory to sys.path during pytest startup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Ensure the agent_workspace directory itself is also in sys.path for top-level modules like api.py
workspace_dir = os.path.join(project_root, "agent_workspace")
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

# To ensure that mock patches and imports of "core.xyz", "observability", etc.,
# map to "agent_workspace.core.xyz" and "agent_workspace.observability",
# we dynamically alias all modules and packages under agent_workspace in sys.modules.
try:
    import agent_workspace
    
    # 1. Alias all top-level modules and packages directly under agent_workspace
    for _, name, is_pkg in pkgutil.iter_modules(agent_workspace.__path__):
        try:
            mod = importlib.import_module(f"agent_workspace.{name}")
            sys.modules[name] = mod
            
            # 2. If it is a package, recursively walk and alias its submodules
            if is_pkg and hasattr(mod, "__path__"):
                for _, sub_name, _ in pkgutil.walk_packages(mod.__path__, f"agent_workspace.{name}."):
                    try:
                        sub_mod = importlib.import_module(sub_name)
                        alias_name = sub_name.replace("agent_workspace.", "", 1)
                        sys.modules[alias_name] = sub_mod
                    except Exception:
                        pass
        except Exception:
            pass
except Exception:
    pass


import pytest

@pytest.fixture(scope="session", autouse=True)
def shutdown_otel_tracing():
    yield
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        provider = trace.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            provider.shutdown()
    except Exception:
        pass

