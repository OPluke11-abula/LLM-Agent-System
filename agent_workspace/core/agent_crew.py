import threading
import uuid
import logging
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AgentCrew")
PROJECT_ROOT = Path(__file__).resolve().parents[2]

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
    def __init__(self, session_id: Optional[str] = None, workspace_path: Optional[str] = None):
        self.session_id = session_id or f"crew-session-{uuid.uuid4()}"
        if workspace_path is None:
            workspace_path = str(PROJECT_ROOT / "agent_workspace" / "scratch" / "agent_crew" / self.session_id)
        workspace = Path(workspace_path).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        self.workspace_path = str(workspace)
        logger.info(f"Initialized AgentCrew with session_id: {self.session_id}")

    async def _async_dispatch_to_role(
        self,
        broker,
        node_id: str,
        role: str,
        task_instructions: str,
        parent_node_id: Optional[str],
        input_parameters: Optional[Dict[str, Any]],
        security_restrictions: Optional[Dict[str, Any]],
        mock_directives: Optional[Dict[str, Any]],
        validation_assertions: Optional[List[str]],
        target_node_id: Optional[str] = None,
        checkpoint: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response_channel = f"swarm:task:{node_id}:response"
        
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        
        async def on_response(msg: dict):
            if not future.done():
                future.set_result(msg)
                
        await broker.subscribe(response_channel, on_response)
        
        try:
            # Publish request
            request_msg = {
                "type": "task_request",
                "session_id": self.session_id,
                "node_id": node_id,
                "role": role,
                "task_instructions": task_instructions,
                "parent_node_id": parent_node_id,
                "input_parameters": input_parameters,
                "security_restrictions": security_restrictions,
                "mock_directives": mock_directives,
                "validation_assertions": validation_assertions,
                "target_node_id": target_node_id,
                "checkpoint": checkpoint
            }
            await broker.publish(f"swarm:role:{role.lower()}", request_msg)
            
            # Wait for response with timeout (5.0 seconds)
            response = await asyncio.wait_for(future, timeout=5.0)
            return response
        finally:
            await broker.unsubscribe(response_channel)

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

        # Resolve tenant_id
        tenant_id = None
        try:
            from core.account_manager import AccountManager
            tenant_id = AccountManager.get_session_tenant(self.session_id)
        except Exception:
            pass
        tenant_id = tenant_id or "default_tenant"

        # Verify tenant credits
        workspace_path = getattr(self, "workspace_path", ".")
        from agent_workspace.core.swarm_coordinator import SwarmCoordinator
        SwarmCoordinator.verify_tenant_credit(workspace_path, tenant_id)

        # Enforce model downscaling policy if budget is low
        if SwarmCoordinator.should_downscale_model(workspace_path, tenant_id):
            if mock_directives is None:
                mock_directives = {}
            mock_directives["downscale"] = True
            logger.info(f"Model downscaling policy active for tenant {tenant_id}. Flagging downstream dispatches.")

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

        # Check for distributed broker delegation
        from agent_workspace.core.broker import get_broker, RedisSwarmBroker, InMemorySwarmBroker
        from agent_workspace.core.swarm_coordinator import SwarmCoordinator
        from agent_workspace.core.sandbox import FileSnapshotTransaction
            
        workspace_path = getattr(self, "workspace_path", ".")
        broker = get_broker()
        
        from agent_workspace.core.p2p_router import get_p2p_router
            
        p2p_router = get_p2p_router()
        has_p2p_peer = any(
            peer.get("status") == "connected" and peer.get("role", "").lower() == matched_role.lower()
            for peer in p2p_router.peers.values()
        )
        
        if has_p2p_peer and isinstance(broker, InMemorySwarmBroker):
            logger.info(f"RedisSwarmBroker offline or unreachable. Attempting P2P dispatch to role '{matched_role}'...")
            async def run_p2p_dispatch():
                return await p2p_router.dispatch_task(
                    role=matched_role,
                    task_instructions=task_instructions,
                    input_parameters=input_parameters,
                    security_restrictions=security_restrictions,
                    mock_directives=mock_directives,
                    validation_assertions=validation_assertions
                )
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(lambda: asyncio.run(run_p2p_dispatch()))
                        p2p_res = future.result()
                else:
                    p2p_res = loop.run_until_complete(run_p2p_dispatch())
            except Exception as e:
                try:
                    p2p_res = asyncio.run(run_p2p_dispatch())
                except Exception as ex:
                    p2p_res = {"status": "error", "error": str(ex)}
            if p2p_res and p2p_res.get("status") == "completed":
                CrewRegistry.update_node_status(self.session_id, node_id, "completed")
                return p2p_res
            else:
                logger.warning(f"P2P dispatch failed: {p2p_res.get('error') if p2p_res else 'No response'}")

        if isinstance(broker, (RedisSwarmBroker, InMemorySwarmBroker)):
            best_node_id = SwarmCoordinator.get_best_node(matched_role)
            nodes_tracked = (best_node_id is not None)
            max_attempts = 2 if nodes_tracked else 1
            
            for attempt in range(max_attempts):
                if attempt > 0 and nodes_tracked:
                    best_node_id = SwarmCoordinator.get_best_node(matched_role)
                    if not best_node_id:
                        break
                
                try:
                    async def run_dispatch():
                        checkpoint = await self.get_checkpoint(broker)
                        return await self._async_dispatch_to_role(
                            broker=broker,
                            node_id=node_id,
                            role=matched_role,
                            task_instructions=task_instructions,
                            parent_node_id=parent_node_id,
                            input_parameters=input_parameters,
                            security_restrictions=security_restrictions,
                            mock_directives=mock_directives,
                            validation_assertions=validation_assertions,
                            target_node_id=best_node_id,
                            checkpoint=checkpoint
                        )
                    
                    # Wrap dispatch in transactional workspace snapshot
                    with FileSnapshotTransaction(workspace_path):
                        try:
                            loop = asyncio.get_running_loop()
                            if loop.is_running():
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(lambda: asyncio.run(run_dispatch()))
                                    res = future.result()
                            else:
                                res = loop.run_until_complete(run_dispatch())
                        except RuntimeError:
                            res = asyncio.run(run_dispatch())
                    
                    if res and res.get("status") == "completed":
                        CrewRegistry.update_node_status(self.session_id, node_id, "completed")
                        if best_node_id:
                            SwarmCoordinator.release_node_load(best_node_id)
                        return res
                    elif res and res.get("status") == "error":
                        CrewRegistry.update_node_status(self.session_id, node_id, "error")
                        if best_node_id:
                            SwarmCoordinator.release_node_load(best_node_id)
                        return res
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"Swarm dispatch attempt {attempt + 1} failed for node '{best_node_id}': {e}")
                    if best_node_id:
                        SwarmCoordinator.mark_node_offline(best_node_id, reason="dispatch_timeout")
                    if not nodes_tracked:
                        break
            
            logger.info("All microservice dispatch attempts failed. Attempting P2P routing fallback...")
            has_p2p_peer = any(
                peer.get("status") == "connected" and peer.get("role", "").lower() == matched_role.lower()
                for peer in p2p_router.peers.values()
            )
            if has_p2p_peer:
                async def run_p2p_dispatch():
                    return await p2p_router.dispatch_task(
                        role=matched_role,
                        task_instructions=task_instructions,
                        input_parameters=input_parameters,
                        security_restrictions=security_restrictions,
                        mock_directives=mock_directives,
                        validation_assertions=validation_assertions
                    )
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(lambda: asyncio.run(run_p2p_dispatch()))
                            p2p_res = future.result()
                    else:
                        p2p_res = loop.run_until_complete(run_p2p_dispatch())
                except Exception as e:
                    try:
                        p2p_res = asyncio.run(run_p2p_dispatch())
                    except Exception as ex:
                        p2p_res = {"status": "error", "error": str(ex)}
                if p2p_res and p2p_res.get("status") == "completed":
                    CrewRegistry.update_node_status(self.session_id, node_id, "completed")
                    return p2p_res
                else:
                    logger.warning(f"P2P fallback dispatch failed: {p2p_res.get('error') if p2p_res else 'No response'}")

            logger.info("All microservice dispatch attempts failed. Falling back to local execution.")

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

    @staticmethod
    def generate_checkpoint_signature(checkpoint_data: Dict[str, Any], role: str) -> str:
        import hashlib
        from agent_workspace.core.discussion_room import ProofOfConsensus
            
        data_to_hash = {
            "session_id": checkpoint_data.get("session_id"),
            "node_id": checkpoint_data.get("node_id"),
            "role": checkpoint_data.get("role"),
            "task_instructions": checkpoint_data.get("task_instructions"),
            "input_parameters": checkpoint_data.get("input_parameters"),
            "completed_subtasks": checkpoint_data.get("completed_subtasks", []),
            "intermediate_outputs": checkpoint_data.get("intermediate_outputs", {})
        }
        serialized = json.dumps(data_to_hash, sort_keys=True)
        payload_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return ProofOfConsensus.generate_member_signature(role, payload_hash)

    @staticmethod
    def verify_checkpoint_signature(checkpoint_data: Dict[str, Any]) -> bool:
        import hashlib
        from agent_workspace.core.discussion_room import ProofOfConsensus
            
        signature = checkpoint_data.get("signature")
        signer = checkpoint_data.get("signer", "ceo")
        if not signature:
            return False
            
        data_to_hash = {
            "session_id": checkpoint_data.get("session_id"),
            "node_id": checkpoint_data.get("node_id"),
            "role": checkpoint_data.get("role"),
            "task_instructions": checkpoint_data.get("task_instructions"),
            "input_parameters": checkpoint_data.get("input_parameters"),
            "completed_subtasks": checkpoint_data.get("completed_subtasks", []),
            "intermediate_outputs": checkpoint_data.get("intermediate_outputs", {})
        }
        serialized = json.dumps(data_to_hash, sort_keys=True)
        payload_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        expected = ProofOfConsensus.generate_member_signature(signer, payload_hash)
        return signature == expected

    async def save_checkpoint(
        self,
        broker,
        node_id: str,
        role: str,
        task_instructions: str,
        input_parameters: Dict[str, Any],
        completed_subtasks: Optional[List[str]] = None,
        intermediate_outputs: Optional[Dict[str, Any]] = None,
        signer: str = "ceo"
    ) -> Dict[str, Any]:
        checkpoint_data = {
            "session_id": self.session_id,
            "node_id": node_id,
            "role": role,
            "task_instructions": task_instructions,
            "input_parameters": input_parameters,
            "completed_subtasks": completed_subtasks or [],
            "intermediate_outputs": intermediate_outputs or {}
        }
        sig = self.generate_checkpoint_signature(checkpoint_data, signer)
        checkpoint_data["signature"] = sig
        checkpoint_data["signer"] = signer

        redis_key = f"swarm:session:{self.session_id}:checkpoint"
        from agent_workspace.core.broker import RedisSwarmBroker
            
        if hasattr(broker, "kv_store"):
            broker.kv_store[redis_key] = json.dumps(checkpoint_data)
        elif getattr(broker, "client", None) is not None:
            await broker.client.set(redis_key, json.dumps(checkpoint_data))

        # Expose checkpoint state to the swarm using Redis pub/sub
        sync_msg = {
            "type": "checkpoint_sync",
            "session_id": self.session_id,
            "checkpoint": checkpoint_data
        }
        await broker.publish("swarm:session:checkpoint:sync", sync_msg)
        return checkpoint_data

    async def get_checkpoint(self, broker) -> Optional[Dict[str, Any]]:
        redis_key = f"swarm:session:{self.session_id}:checkpoint"
        data_str = None
        from agent_workspace.core.broker import RedisSwarmBroker
            
        if hasattr(broker, "kv_store"):
            data_str = broker.kv_store.get(redis_key)
        elif getattr(broker, "client", None) is not None:
            data_str = await broker.client.get(redis_key)
            
        if data_str:
            return json.loads(data_str)
        return None
