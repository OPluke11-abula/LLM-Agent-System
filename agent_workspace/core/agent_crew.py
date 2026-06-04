import threading
import uuid
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AgentCrew")

class CrewRegistry:
    """
    A thread-safe global registry to track crew sessions and their agent nodes
    for visualization on the visual control-plane frontend canvas.
    """
    _lock = threading.Lock()
    # Structure: { session_id: { node_id: dict } }
    _sessions: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._sessions.clear()

    @classmethod
    def register_node(
        cls,
        session_id: str,
        node_id: str,
        role: str,
        parent_node_id: Optional[str] = None,
        status: str = "pending",
        description: str = "",
        input_parameters: Optional[Dict[str, Any]] = None,
        security_restrictions: Optional[Dict[str, Any]] = None,
        mock_directives: Optional[Dict[str, Any]] = None,
        validation_assertions: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        if not tenant_id:
            try:
                from core.account_manager import AccountManager
                tenant_id = AccountManager.get_session_tenant(session_id)
            except Exception:
                pass
            tenant_id = tenant_id or "default_tenant"

        with cls._lock:
            if session_id not in cls._sessions:
                cls._sessions[session_id] = {}
            
            cls._sessions[session_id][node_id] = {
                "id": node_id,
                "parent_id": parent_node_id,
                "role": role,
                "status": status,
                "description": description,
                "input_parameters": input_parameters or {},
                "security_restrictions": security_restrictions or {},
                "mock_directives": mock_directives or {},
                "validation_assertions": validation_assertions or [],
                "tenant_id": tenant_id,
            }
            logger.info(f"Registered crew node '{node_id}' for role '{role}' in session '{session_id}' under tenant '{tenant_id}'")

    @classmethod
    def update_node_status(cls, session_id: str, node_id: str, status: str) -> None:
        with cls._lock:
            if session_id in cls._sessions and node_id in cls._sessions[session_id]:
                cls._sessions[session_id][node_id]["status"] = status
                logger.info(f"Updated crew node '{node_id}' status to '{status}' in session '{session_id}'")

    @classmethod
    def get_topology(cls, session_id: Optional[str] = None, tenant_id: str = "default_tenant") -> Dict[str, Any]:
        """
        Returns nodes and edges matching the node-based visual control-plane standard.
        """
        nodes = []
        edges = []
        
        with cls._lock:
            target_sessions = [session_id] if session_id else list(cls._sessions.keys())
            
            for s_id in target_sessions:
                if s_id not in cls._sessions:
                    continue
                for node_id, node_data in cls._sessions[s_id].items():
                    # Filter by tenant
                    if node_data.get("tenant_id", "default_tenant") != tenant_id:
                        continue
                    # Format node for visual canvas
                    nodes.append({
                        "id": node_id,
                        "type": "agent",
                        "role": node_data["role"],
                        "status": node_data["status"],
                        "data": {
                            "description": node_data["description"],
                            "input_parameters": node_data["input_parameters"],
                            "security_restrictions": node_data["security_restrictions"],
                            "mock_directives": node_data["mock_directives"],
                            "validation_assertions": node_data["validation_assertions"],
                            "session_id": s_id,
                        }
                    })
                    # Format edge for visual canvas
                    if node_data["parent_id"]:
                        edges.append({
                            "id": f"edge-{node_data['parent_id']}-{node_id}",
                            "source": node_data["parent_id"],
                            "target": node_id,
                            "type": "handoff"
                        })
                        
        return {"nodes": nodes, "edges": edges}


class AgentCrew:
    """
    Manages hierarchical multi-agent task dispatches across roles (CEO, Developer, Auditor, CFO).
    Enforces structured delegation protocols and verification assertions.
    """
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"crew-session-{uuid.uuid4()}"
        logger.info(f"Initialized AgentCrew with session_id: {self.session_id}")

    def dispatch_to_role(
        self,
        role: str,
        task_instructions: str,
        parent_node_id: Optional[str] = None,
        input_parameters: Optional[Dict[str, Any]] = None,
        security_restrictions: Optional[Dict[str, Any]] = None,
        mock_directives: Optional[Dict[str, Any]] = None,
        validation_assertions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches a task to a designated persona role. Enforces schema validation.
        """
        # Validate schema presence
        if input_parameters is None:
            raise ValueError("Structured delegation requires 'input_parameters' to be specified.")
        if security_restrictions is None:
            raise ValueError("Structured delegation requires 'security_restrictions' to be specified.")
        if mock_directives is None:
            raise ValueError("Structured delegation requires 'mock_directives' to be specified.")
        if validation_assertions is None:
            raise ValueError("Structured delegation requires 'validation_assertions' to be specified.")

        # Ensure valid roles
        valid_roles = {"CEO", "Developer", "Auditor", "CFO"}
        normalized_role = role.strip().upper()
        # Find if role matches one of the canonical personas
        matched_role = None
        for vr in valid_roles:
            if vr in normalized_role:
                matched_role = vr
                break
        if not matched_role:
            matched_role = role  # Keep original if non-canonical

        node_id = f"node-{matched_role.lower()}-{uuid.uuid4()}"
        
        # 1. Register as pending
        CrewRegistry.register_node(
            session_id=self.session_id,
            node_id=node_id,
            role=matched_role,
            parent_node_id=parent_node_id,
            status="pending",
            description=task_instructions,
            input_parameters=input_parameters,
            security_restrictions=security_restrictions,
            mock_directives=mock_directives,
            validation_assertions=validation_assertions,
        )

        # 2. Transition to running
        CrewRegistry.update_node_status(self.session_id, node_id, "running")

        try:
            # Check security restrictions mock check
            if security_restrictions.get("block_all") or "restrict_execution" in security_restrictions:
                raise PermissionError("Security sandbox interception: Execution blocked by policy rules.")

            # Execute simulation/delegation response logic depending on role
            output = f"Execution result for role [{matched_role}] with instructions: {task_instructions}."
            
            # Apply mock directives
            if mock_directives.get("force_mock_response"):
                output = mock_directives["force_mock_response"]
            
            # Run/validate assertions
            for assertion in validation_assertions:
                if "fail" in assertion.lower() or "error" in assertion.lower():
                    raise AssertionError(f"Validation assertion failed: '{assertion}'")
            
            # Update status to completed
            CrewRegistry.update_node_status(self.session_id, node_id, "completed")
            return {
                "node_id": node_id,
                "status": "completed",
                "output": output
            }
        except Exception as e:
            CrewRegistry.update_node_status(self.session_id, node_id, "error")
            logger.error(f"Role dispatch execution failed: {e}")
            return {
                "node_id": node_id,
                "status": "error",
                "error": str(e)
            }
