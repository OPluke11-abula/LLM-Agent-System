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

    @classmethod
    def verify_tenant_credit(cls, workspace_path: str, tenant_id: str) -> None:
        """
        Validates active Stripe subscription status and checks local credit balance.
        Raises TenantSubscriptionInactiveError if status is 'frozen' or 'canceled'.
        Raises QuotaExceededError if credits <= 0.0.
        """
        from agent_workspace.core.ledger import FinancialLedger
        from agent_workspace.core.billing import (
            TenantStatusManager,
            TenantSubscriptionInactiveError,
            QuotaExceededError,
            TenantQuotaStateUnavailable,
        )
            
        import sqlite3

        ledger = FinancialLedger(workspace_path)
        status_mgr = TenantStatusManager(ledger)
        status = status_mgr.get_tenant_status(tenant_id)
        if status in ("frozen", "canceled"):
            raise TenantSubscriptionInactiveError(f"Subscription is {status}. Access restricted.")

        conn = sqlite3.connect(str(ledger.db_path))
        try:
            cursor = conn.execute("SELECT credits FROM tenant_credit_budget WHERE tenant_id = ?", (tenant_id,))
            row = cursor.fetchone()
            if row:
                credits = row[0]
            else:
                credits = 100.0  # default
        except sqlite3.Error as e:
            logger.error(f"Error checking credits for tenant {tenant_id}: {e}")
            raise TenantQuotaStateUnavailable("tenant credit state is unavailable") from e
        finally:
            conn.close()

        if credits <= 0.0:
            raise QuotaExceededError(f"Tenant '{tenant_id}' has run out of credit budget (remaining: {credits}).")

    @classmethod
    def should_downscale_model(cls, workspace_path: str, tenant_id: str) -> bool:
        """
        Returns True if credits / max_budget < 0.20 and routing_policy == 'downscale'.
        """
        from agent_workspace.core.ledger import FinancialLedger
            
        import sqlite3

        ledger = FinancialLedger(workspace_path)
        conn = sqlite3.connect(str(ledger.db_path))
        try:
            cursor = conn.execute("SELECT credits, max_budget, routing_policy FROM tenant_credit_budget WHERE tenant_id = ?", (tenant_id,))
            row = cursor.fetchone()
            if row:
                credits, max_budget, routing_policy = row[0], row[1], row[2]
            else:
                credits, max_budget, routing_policy = 100.0, 100.0, "downscale"
        except Exception as e:
            logger.error(f"Error checking credits for tenant {tenant_id}: {e}")
            return False
        finally:
            conn.close()

        if max_budget > 0.0 and (credits / max_budget) < 0.20:
            return str(routing_policy).lower() == "downscale"
        return False

