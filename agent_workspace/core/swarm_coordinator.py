import logging
import time
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SwarmCoordinator")

class SwarmCoordinator:
    """
    Central swarm manager tracking active agent worker nodes, heartbeats, 
    load balancing routing, and elastic auto-scaling simulations.
    """
    _lock = threading.Lock()
    # Structure: { node_id: { role: str, status: str, last_seen: float, load: int } }
    _nodes: Dict[str, Dict[str, Any]] = {}
    _failure_logs: List[Dict[str, Any]] = []

    def __init__(self, heartbeat_timeout: float = 15.0):
        self.heartbeat_timeout = heartbeat_timeout

    @classmethod
    def register_or_update_node(cls, role: str, node_id: str, status: str) -> None:
        """Announces or refreshes a worker node's presence."""
        with cls._lock:
            now = time.time()
            cls._nodes[node_id] = {
                "role": role.lower(),
                "node_id": node_id,
                "status": status.lower(),
                "last_seen": now,
                "load": 1 if status.lower() == "busy" else 0
            }
            logger.info(f"[SwarmCoordinator] Registered/Updated node '{node_id}' for role '{role}' (status: {status})")

    @classmethod
    def mark_node_offline(cls, node_id: str, reason: str = "stale") -> None:
        """Manually or automatically marks a node as offline."""
        with cls._lock:
            if node_id in cls._nodes:
                node = cls._nodes.pop(node_id)
                failure_event = {
                    "timestamp": time.time(),
                    "node_id": node_id,
                    "role": node["role"],
                    "reason": reason
                }
                cls._failure_logs.append(failure_event)
                logger.warning(f"[SwarmCoordinator] Node '{node_id}' marked OFFLINE. Reason: {reason}")

    @classmethod
    def check_heartbeats(cls, timeout: float = 15.0) -> None:
        """Scans the registry and removes nodes that haven't reported heartbeats within timeout."""
        now = time.time()
        stale_nodes = []
        with cls._lock:
            for node_id, node_data in cls._nodes.items():
                if now - node_data["last_seen"] > timeout:
                    stale_nodes.append(node_id)
        
        for node_id in stale_nodes:
            cls.mark_node_offline(node_id, reason="heartbeat_timeout")

    @classmethod
    def get_best_node(cls, role: str) -> Optional[str]:
        """
        Implements load balancing. Returns the best active node_id for the given role.
        Prefers idle nodes.
        """
        cls.check_heartbeats()  # Flush stale nodes first
        
        target_role = role.lower()
        best_node_id = None
        best_load = float("inf")

        with cls._lock:
            for node_id, data in cls._nodes.items():
                if data["role"] == target_role:
                    # Load criteria: idle (0) is preferred over busy (1)
                    if data["load"] < best_load:
                        best_load = data["load"]
                        best_node_id = node_id
                        
            # Increment load on the selected node to simulate immediate task reservation
            if best_node_id:
                cls._nodes[best_node_id]["status"] = "busy"
                cls._nodes[best_node_id]["load"] += 1
                cls._nodes[best_node_id]["last_seen"] = time.time()

        return best_node_id

    @classmethod
    def release_node_load(cls, node_id: str) -> None:
        """Decrements node load after task completion or failure."""
        with cls._lock:
            if node_id in cls._nodes:
                cls._nodes[node_id]["load"] = max(0, cls._nodes[node_id]["load"] - 1)
                if cls._nodes[node_id]["load"] == 0:
                    cls._nodes[node_id]["status"] = "idle"

    @classmethod
    def get_active_nodes(cls) -> List[Dict[str, Any]]:
        """Returns all currently registered active nodes."""
        cls.check_heartbeats()
        with cls._lock:
            return list(cls._nodes.values())

    @classmethod
    def get_failure_logs(cls) -> List[Dict[str, Any]]:
        """Returns the failure and failover logs history."""
        with cls._lock:
            return list(cls._failure_logs)

    @classmethod
    def simulate_scaling(cls, role: str, direction: str) -> Dict[str, Any]:
        """
        Triggers container scaling. Under local simulation, it spawns/stops mock nodes.
        Under Docker, it simulates API invocations.
        """
        role_normalized = role.lower()
        direction_normalized = direction.lower()
        
        import uuid
        result = {
            "role": role_normalized,
            "direction": direction_normalized,
            "timestamp": time.time(),
            "status": "success"
        }

        if direction_normalized == "up":
            # Simulate spawning a new container
            new_node_id = f"service-{role_normalized}-{uuid.uuid4().hex[:8]}"
            cls.register_or_update_node(role_normalized, new_node_id, "idle")
            result["node_id"] = new_node_id
            result["message"] = f"Scaled UP: Spawned container node '{new_node_id}'"
        elif direction_normalized == "down":
            # Simulate stopping the oldest node for this role
            stopped_node_id = None
            with cls._lock:
                for node_id, data in cls._nodes.items():
                    if data["role"] == role_normalized:
                        stopped_node_id = node_id
                        break
            if stopped_node_id:
                cls.mark_node_offline(stopped_node_id, reason="scale_down")
                result["node_id"] = stopped_node_id
                result["message"] = f"Scaled DOWN: Terminated container node '{stopped_node_id}'"
            else:
                result["status"] = "failed"
                result["message"] = f"No active nodes found for role '{role_normalized}' to scale down."
                
        return result
