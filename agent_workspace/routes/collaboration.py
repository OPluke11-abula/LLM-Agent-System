import os
import sys
import json
import uuid
import logging
import asyncio
import hmac
import hashlib
import time
import base64
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request

from agent_workspace.routes.dependencies import (
    get_tenant_context,
    verify_websocket_tenant,
    build_router,
    get_workspace
)
from agent_workspace.core.ws_manager import crew_sync_manager
from agent_workspace.core.p2p_router import SwarmP2PCrypto, get_p2p_router
from agent_workspace.core.account_manager import AccountManager
from agent_workspace.routes.schemas import CrewRegisterRequest

logger = logging.getLogger(__name__)
MAX_LOCAL_FANOUT_CONCURRENCY = 64

router = APIRouter()

# ----------------- PubSub managers from api.py -----------------

class MultiChannelPubSubManager:
    """Manages multi-channel WebSocket subscription routing for logs, telemetry, ledger, topology, stdout, and state_sync."""
    def __init__(self):
        # Maps channel -> set of (WebSocket, session_id)
        self.channels: dict[str, set[tuple[WebSocket, str]]] = {
            "logs": set(),
            "telemetry": set(),
            "ledger": set(),
            "topology": set(),
            "stdout": set(),
            "state_sync": set()
        }
        self.active_sockets: set[WebSocket] = set()
        self.session_keys: dict[WebSocket, bytes] = {}
        self.websocket_tenants: dict[WebSocket, str] = {}

    async def start_redis_listener(self):
        from agent_workspace.core.broker import get_broker, RedisSwarmBroker
            
        broker = get_broker(workspace_path=get_workspace())
        if isinstance(broker, RedisSwarmBroker):
            logger.info("Starting MultiChannelPubSubManager Redis subscription listener...")
            for ch in list(self.channels.keys()):
                redis_ch = f"swarm:pubsub:{ch}"
                await broker.subscribe(redis_ch, self._make_redis_callback(ch))

    def _make_redis_callback(self, channel: str):
        async def callback(msg: dict):
            session_id = msg.get("session_id")
            data = msg.get("data")
            publisher_tenant = msg.get("publisher_tenant", "default_tenant")
            await self._local_publish(channel, session_id, data, publisher_tenant)
        return callback

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_sockets.add(websocket)

    def register_key(self, websocket: WebSocket, session_key: bytes):
        self.session_keys[websocket] = session_key

    def disconnect(self, websocket: WebSocket):
        self.active_sockets.discard(websocket)
        self.session_keys.pop(websocket, None)
        self.websocket_tenants.pop(websocket, None)
        for channel in self.channels.values():
            to_remove = [item for item in channel if item[0] == websocket]
            for item in to_remove:
                channel.remove(item)

    async def subscribe(self, websocket: WebSocket, session_id: str, channel: str):
        if channel in self.channels:
            self.channels[channel].add((websocket, session_id))
            logger.info(f"WebSocket subscribed to channel '{channel}' for session '{session_id}'")

    async def unsubscribe(self, websocket: WebSocket, session_id: str, channel: str):
        if channel in self.channels:
            self.channels[channel].discard((websocket, session_id))
            logger.info(f"WebSocket unsubscribed from channel '{channel}' for session '{session_id}'")

    async def publish(self, channel: str, session_id: str, data: dict[str, Any], publisher_tenant: str = "default_tenant", from_redis: bool = False):
        if channel not in self.channels:
            return
            
        # Record replay event
        try:
            from core.replay_logger import ReplayLogger
            ReplayLogger.log_event(get_workspace(), session_id, channel, data)
        except Exception as e:
            logger.error(f"Error logging publish event: {e}")
        
        # Propagate to Redis pubsub if published locally
        if not from_redis:
            from agent_workspace.core.broker import get_broker, RedisSwarmBroker
            
            broker = get_broker(workspace_path=get_workspace())
            if isinstance(broker, RedisSwarmBroker):
                redis_msg = {
                    "session_id": session_id,
                    "data": data,
                    "publisher_tenant": publisher_tenant
                }
                asyncio.create_task(broker.publish(f"swarm:pubsub:{channel}", redis_msg))

        await self._local_publish(channel, session_id, data, publisher_tenant)

    async def _local_publish(self, channel: str, session_id: str, data: dict[str, Any], publisher_tenant: str = "default_tenant"):
        # Broadcast to all connections subscribed to this channel for this session or "global"
        send_operations = []
        for ws, s_id in list(self.channels[channel]):
            ws_tenant = self.websocket_tenants.get(ws, "default_tenant")
            if ws_tenant != publisher_tenant:
                continue
            if session_id == "global" or s_id == "global" or s_id == session_id:
                try:
                    payload_dict = {
                        "channel": channel,
                        "session_id": session_id,
                        "payload": data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    key = self.session_keys.get(ws)
                    if key:
                        # Encrypt broadcast message
                        plaintext = json.dumps(payload_dict, ensure_ascii=False)
                        encrypted_msg = SwarmP2PCrypto.encrypt_message(key, plaintext)
                        send_operations.append((ws, encrypted_msg))
                    else:
                        # Fallback for backward compatibility/unencrypted clients if any
                        send_operations.append((ws, payload_dict))
                except Exception:
                    # Stale connection, will be handled during disconnect
                    pass

        if send_operations:
            async def send_one(ws: WebSocket, message: Any) -> None:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

            for start in range(0, len(send_operations), MAX_LOCAL_FANOUT_CONCURRENCY):
                batch = send_operations[start:start + MAX_LOCAL_FANOUT_CONCURRENCY]
                await asyncio.gather(*(send_one(ws, message) for ws, message in batch))


collab_manager = MultiChannelPubSubManager()


class DashboardConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[tuple[WebSocket, str, str]]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, role: str, tenant_id: str):
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append((websocket, role, tenant_id))


    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id] = [
                conn for conn in self.active_connections[session_id] if conn[0] != websocket
            ]
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, event: dict[str, Any], sender_tenant: str = "default_tenant"):
        # Record replay event
        try:
            from core.replay_logger import ReplayLogger
            ReplayLogger.log_event(get_workspace(), session_id, "dashboard", event)
        except Exception as e:
            logger.error(f"Error logging dashboard event: {e}")

        if session_id not in self.active_connections:
            return
            
        event_type = event.get("type")
        
        for websocket, role, tenant_id in self.active_connections[session_id]:
            if tenant_id != sender_tenant:
                continue
            filtered_event = dict(event)
            
            # Apply CEO Strategy filters
            if role == "ceo":
                if event_type == "tool_result" and len(str(event.get("result", ""))) > 200:
                    filtered_event["result"] = str(event.get("result", ""))[:200] + "... (truncated for CEO strategy)"
            
            # Apply Auditor Billing filters and token metrics
            elif role == "auditor":
                # Preserve pre-injected event telemetry alerts
                existing_telemetry = event.get("telemetry") or {}
                if not isinstance(existing_telemetry, dict):
                    existing_telemetry = {}
                
                # Check for active warning telemetry flags in either root or nested dict
                duration = event.get("duration_ms") or existing_telemetry.get("duration_ms", 250)
                
                latency_alert = (
                    event.get("active_latency_alert")
                    or existing_telemetry.get("active_latency_alert")
                    or (duration > 2000)
                )
                cost_alert = (
                    event.get("cost_alert")
                    or existing_telemetry.get("cost_alert")
                    or False
                )
                
                # Coalesce into final structure
                filtered_event["telemetry"] = {
                    "token_used": event.get("token_used") or existing_telemetry.get("token_used", 150),
                    "duration_ms": duration,
                    "active_latency_alert": latency_alert,
                    **existing_telemetry
                }
                if cost_alert:
                    filtered_event["telemetry"]["cost_alert"] = cost_alert
            
            try:
                await websocket.send_json(filtered_event)
            except Exception:
                pass


dashboard_manager = DashboardConnectionManager()


async def run_dashboard_chat(session_id: str, msg: str, tenant_id: str):
    router = build_router(session_id)
    # Register session tenant
    from agent_workspace.core.account_manager import AccountManager
    AccountManager.register_session_tenant(session_id, tenant_id)
    
    # Broadcast user message locally first
    event_user = {
        "type": "chat_message",
        "sender": "user",
        "msg": msg,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await dashboard_manager.broadcast(session_id, event_user, sender_tenant=tenant_id)
    
    try:
        async for event in router.stream_agent_loop(msg):
            # Propagate events to dashboard subscribers
            await dashboard_manager.broadcast(session_id, event, sender_tenant=tenant_id)
            
            # Unify publish channel logging
            event_type = event.get("type", "")
            if event_type in {"agent_response", "tool_result", "thought"}:
                channel = "logs"
                if event_type == "tool_result":
                    channel = "stdout"
                await collab_manager.publish(channel, session_id, event, publisher_tenant=tenant_id)
    except Exception as e:
        logger.error(f"Error in run_dashboard_chat: {e}")
        error_event = {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await dashboard_manager.broadcast(session_id, error_event, sender_tenant=tenant_id)


# ----------------- Endpoints -----------------

@router.post("/v1/crew/register")
async def register_crew_node(req: CrewRegisterRequest, tenant_id: str = Depends(get_tenant_context)):
    try:
        from core.agent_crew import CrewRegistry
    except ImportError:
        from agent_workspace.core.agent_crew import CrewRegistry

    AccountManager.register_session_tenant(req.session_id, tenant_id)

    node_id = req.node_id or f"node-{req.role.lower()}-{uuid.uuid4()}"
    CrewRegistry.register_node(
        session_id=req.session_id,
        node_id=node_id,
        role=req.role,
        parent_node_id=req.parent_node_id,
        status=req.status,
        description=req.description,
        input_parameters=req.input_parameters,
        security_restrictions=req.security_restrictions,
        mock_directives=req.mock_directives,
        validation_assertions=req.validation_assertions,
        tenant_id=tenant_id,
    )
    return {
        "status": "success",
        "session_id": req.session_id,
        "node_id": node_id,
    }


@router.get("/v1/crew/topology")
async def get_crew_topology(session_id: str | None = None, tenant_id: str = Depends(get_tenant_context)):
    try:
        from core.agent_crew import CrewRegistry
    except ImportError:
        from agent_workspace.core.agent_crew import CrewRegistry

    return CrewRegistry.get_topology(session_id, tenant_id=tenant_id)

@router.websocket("/v1/collaboration/{session_id}")
async def collaboration_endpoint(websocket: WebSocket, session_id: str):
    params = websocket.query_params
    from agent_workspace.routes.dependencies import verify_websocket_tenant
    tenant_id = await verify_websocket_tenant(websocket, session_id)
    if not tenant_id:
        return

    # 1. Connection Guard: Validate connection against swarm consensus registry (bypassed for admin)
    is_admin = (tenant_id == "admin_tenant")
    if not is_admin:
        role = params.get("role")
        payload_hash = params.get("payload_hash")
        signature = params.get("signature")

        from core.discussion_room import ProofOfConsensus
        if not (role and payload_hash and signature and 
                ProofOfConsensus.is_consensus_approved(get_workspace(), payload_hash) and
                signature == ProofOfConsensus.generate_member_signature(role, payload_hash)):
            await websocket.close(code=4003, reason="Unauthorized Swarm Handshake")
            return

    # 2. Accept and execute ECDH session key exchange or bypass for admin
    collab_manager.active_sockets.add(websocket)
    collab_manager.websocket_tenants[websocket] = tenant_id
    
    server_crypto = SwarmP2PCrypto()
    try:
        # Send Server Hello with server public key
        await websocket.send_json({
            "handshake": "server_hello",
            "public_key": server_crypto.get_public_bytes()
        })
        # Receive Client Hello
        client_hello = await websocket.receive_json()
        if client_hello.get("handshake") == "bypass" and is_admin:
            logger.info("Admin bypassed ECDH key exchange")
        elif client_hello.get("handshake") != "client_hello" or "public_key" not in client_hello:
            await websocket.close(code=4002, reason="Invalid Handshake Protocol")
            collab_manager.disconnect(websocket)
            return
        else:
            session_key = server_crypto.compute_shared_key(client_hello["public_key"])
            collab_manager.register_key(websocket, session_key)
    except Exception as e:
        logger.error(f"P2P Key Exchange failed: {e}")
        await websocket.close(code=4002, reason="Key Exchange Failure")
        collab_manager.disconnect(websocket)
        return

    try:
        while True:
            # 3. Encrypted P2P Communications
            encrypted_data = await websocket.receive_json()
            if "ciphertext" in encrypted_data and "nonce" in encrypted_data:
                try:
                    decrypted_str = SwarmP2PCrypto.decrypt_message(session_key, encrypted_data)
                    data = json.loads(decrypted_str)
                except Exception as e:
                    logger.error(f"Failed to decrypt client frame: {e}")
                    err_msg = json.dumps({"error": "Decryption failure"})
                    enc_err = SwarmP2PCrypto.encrypt_message(session_key, err_msg)
                    await websocket.send_json(enc_err)
                    continue
            else:
                data = encrypted_data

            msg_type = data.get("type") or data.get("action")
            channel = data.get("channel", "logs")

            if msg_type == "subscribe":
                sub_ch = data.get("channel")
                if sub_ch:
                    await collab_manager.subscribe(websocket, session_id, sub_ch)
                    resp = {"status": "subscribed", "channel": sub_ch}
                    if session_key:
                        enc_resp = SwarmP2PCrypto.encrypt_message(session_key, json.dumps(resp))
                        await websocket.send_json(enc_resp)
                    else:
                        await websocket.send_json(resp)

            elif msg_type == "unsubscribe":
                unsub_ch = data.get("channel")
                if unsub_ch:
                    await collab_manager.unsubscribe(websocket, session_id, unsub_ch)
                    resp = {"status": "unsubscribed", "channel": unsub_ch}
                    if session_key:
                        enc_resp = SwarmP2PCrypto.encrypt_message(session_key, json.dumps(resp))
                        await websocket.send_json(enc_resp)
                    else:
                        await websocket.send_json(resp)

            elif msg_type == "publish":
                pub_payload = data.get("payload", {})
                await collab_manager.publish(channel, session_id, pub_payload, publisher_tenant=tenant_id)
                resp = {"status": "published", "channel": channel}
                if session_key:
                    enc_resp = SwarmP2PCrypto.encrypt_message(session_key, json.dumps(resp))
                    await websocket.send_json(enc_resp)
                else:
                    await websocket.send_json(resp)

    except WebSocketDisconnect:
        logger.info(f"Collaboration WebSocket disconnected for session '{session_id}'")
        collab_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in collaboration endpoint: {e}")
        collab_manager.disconnect(websocket)


@router.websocket("/v1/dashboard/{session_id}/{role}")
async def dashboard_stream(websocket: WebSocket, session_id: str, role: str):
    role = role.lower()
    if role not in {"ceo", "developer", "auditor"}:
        await websocket.accept()
        await websocket.send_json({"error": f"Invalid role: {role}. Supported: ceo, developer, auditor"})
        await websocket.close()
        return

    # Dynamic tenant verification
    from agent_workspace.routes.dependencies import verify_websocket_tenant
    tenant_id = await verify_websocket_tenant(websocket, session_id)
    if not tenant_id:
        return

    # Check session tenancy context
    from agent_workspace.core.account_manager import AccountManager
    existing_tenant = AccountManager.get_session_tenant(session_id)
    if existing_tenant and existing_tenant != tenant_id:
        await websocket.send_json({"error": "Access denied to session of another tenant"})
        await websocket.close()
        return
    AccountManager.register_session_tenant(session_id, tenant_id)

    await dashboard_manager.connect(websocket, session_id, role, tenant_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                msg = payload.get("msg")
                if msg:
                    asyncio.create_task(run_dashboard_chat(session_id, msg, tenant_id))
            except Exception as e:
                logger.error(f"Failed to process dashboard message: {e}")
    except WebSocketDisconnect:
        logger.info(f"Dashboard WebSocket disconnected for session '{session_id}'")
        dashboard_manager.disconnect(websocket, session_id)


@router.websocket("/v1/crew/sync/{session_id}")
async def crew_sync_endpoint(websocket: WebSocket, session_id: str):
    from agent_workspace.routes.dependencies import verify_websocket_tenant
    tenant_id = await verify_websocket_tenant(websocket, session_id)
    if not tenant_id:
        return

    server_crypto = SwarmP2PCrypto()
    try:
        # 1. Send Server Hello
        await websocket.send_json({
            "handshake": "server_hello",
            "public_key": server_crypto.get_public_bytes()
        })
        
        # 2. Recv Client Hello
        client_hello = await websocket.receive_json()
        if client_hello.get("handshake") != "client_hello":
            await websocket.close(code=4002, reason="Handshake Protocol Error")
            return
            
        client_pub = client_hello["public_key"]
        shared_key = server_crypto.compute_shared_key(client_pub)
        
        # 3. Recv verify
        verify_msg = await websocket.receive_json()
        if verify_msg.get("handshake") != "verify":
            await websocket.close(code=4002, reason="Handshake Protocol Error")
            return
            
        role = verify_msg["role"]
        payload_hash = verify_msg["payload_hash"]
        signature = verify_msg["signature"]
        
        # Verify consensus signature
        from agent_workspace.core.discussion_room import ProofOfConsensus
        expected_sig = ProofOfConsensus.generate_member_signature(role, payload_hash)
        if signature != expected_sig:
            await websocket.close(code=4003, reason="Unauthorized Crew Member Handshake")
            return
            
        # Send verified confirmation
        await websocket.send_json({
            "handshake": "verified",
            "status": "success"
        })
        
        # Register and listen
        crew_sync_manager.connect(session_id, websocket, shared_key)
        
        while True:
            # 4. Read P2P messages
            encrypted_data = await websocket.receive_json()
            decrypted_str = SwarmP2PCrypto.decrypt_message(shared_key, encrypted_data)
            await crew_sync_manager.broadcast(session_id, websocket, decrypted_str)
            
    except WebSocketDisconnect:
        crew_sync_manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.error(f"Error in crew sync WebSocket: {e}")
        try:
            await websocket.close(code=4000)
        except Exception:
            pass
        crew_sync_manager.disconnect(session_id, websocket)


TRUSTED_TENANTS_KEYS: dict[str, str] = {}

def parse_all_lessons_from_md(filepath: Path) -> list[dict]:
    """Helper to parse lessons_learned.md into structured dicts."""
    import re
    if not filepath.is_file():
        return []
    content = filepath.read_text(encoding="utf-8")
    blocks = content.split("---")
    lessons = []
    for block in blocks:
        if "Lesson ID:" not in block:
            continue
        lines = block.splitlines()
        lesson = {}
        for line in lines:
            line = line.strip()
            if line.startswith("### Lesson ID:"):
                raw_id = line.replace("### Lesson ID:", "").strip()
                if "(" in raw_id:
                    raw_id = raw_id.split("(")[0].strip()
                lesson["lesson_id"] = raw_id
                lesson["id"] = raw_id
            elif line.startswith("- **Mistake Encountered**:"):
                lesson["mistake"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Root Cause**:"):
                lesson["root_cause"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Best Practice Policy**:"):
                lesson["best_practice"] = line.split(":", 1)[1].strip()

        code_match = re.search(r"```python\n(.*?)```", block, re.DOTALL)
        if code_match:
            lesson["resolution_code"] = code_match.group(1).strip()
            lesson["resolution"] = lesson["resolution_code"]

        if "lesson_id" in lesson:
            lessons.append(lesson)
    return lessons


@router.websocket("/v1/federated/sync")
async def federated_sync_ws(websocket: WebSocket):
    """Secure WebSocket endpoint allowing cross-tenant pushed/pulled signed lessons."""
    await websocket.accept()
    try:
        from core.federated_sync import FederatedKnowledgeExchange
        exchange = FederatedKnowledgeExchange(get_workspace())
        priv_key, pub_key = exchange.load_local_keys()
        if not priv_key or not pub_key:
            priv_key, pub_key = exchange.generate_key_pair()
            exchange.save_local_keys(priv_key, pub_key)

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "push_lesson":
                payload = data.get("payload")
                if not payload:
                    await websocket.send_json({"status": "error", "message": "Missing payload"})
                    continue
                try:
                    verified_lesson = exchange.decrypt_and_verify_lesson(
                        payload, priv_key, TRUSTED_TENANTS_KEYS
                    )
                    if verified_lesson:
                        merged = exchange.merge_lesson(verified_lesson)
                        await websocket.send_json({
                            "status": "success",
                            "message": "Lesson successfully merged",
                            "merged": merged
                        })
                    else:
                        await websocket.send_json({"status": "error", "message": "Verification failed"})
                except Exception as e:
                    await websocket.send_json({"status": "error", "message": str(e)})

            elif msg_type == "pull_lessons":
                receiver_pub_key = data.get("receiver_public_key")
                if not receiver_pub_key:
                    await websocket.send_json({"status": "error", "message": "Missing receiver_public_key"})
                    continue
                try:
                    lessons = parse_all_lessons_from_md(exchange.lessons_file)
                    encrypted_lessons = []
                    sender_id = "server-tenant"
                    for lesson in lessons:
                        enc = exchange.sign_and_encrypt_lesson(
                            lesson, receiver_pub_key, priv_key, sender_id
                        )
                        encrypted_lessons.append(enc)
                    await websocket.send_json({
                        "status": "success",
                        "type": "pull_response",
                        "lessons": encrypted_lessons
                    })
                except Exception as e:
                    await websocket.send_json({"status": "error", "message": str(e)})
            else:
                await websocket.send_json({"status": "error", "message": f"Unsupported message type: {msg_type}"})

    except WebSocketDisconnect:
        logger.info("Federated sync WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in federated sync endpoint: {e}")


@router.websocket("/v1/swarm/p2p/tunnel")
async def swarm_p2p_tunnel_endpoint(websocket: WebSocket):
    await websocket.accept()
    from agent_workspace.core.p2p_router import SwarmP2PCrypto, get_p2p_router
    from agent_workspace.core.discussion_room import ProofOfConsensus
        
    server_crypto = SwarmP2PCrypto()
    router_p2p = get_p2p_router()
    
    try:
        # 1. Send server_hello
        await websocket.send_json({
            "handshake": "server_hello",
            "public_key": server_crypto.get_public_bytes()
        })
        
        # 2. Recv client_hello
        client_hello = await websocket.receive_json()
        if client_hello.get("handshake") != "client_hello":
            await websocket.close(code=4002, reason="Handshake Error")
            return
            
        client_pub = client_hello["public_key"]
        shared_key = server_crypto.compute_shared_key(client_pub)
        
        # 3. Recv verify
        verify_msg = await websocket.receive_json()
        if verify_msg.get("handshake") != "verify":
            await websocket.close(code=4002, reason="Handshake Error")
            return
            
        role = verify_msg["role"]
        client_node_id = verify_msg["node_id"]
        client_host = verify_msg["host"]
        client_port = verify_msg["port"]
        payload_hash = verify_msg["payload_hash"]
        signature = verify_msg["signature"]
        
        # Compute expected hash and verify signature
        expected_hash = hashlib.sha256(f"{client_pub}:{server_crypto.get_public_bytes()}".encode("utf-8")).hexdigest()
        if payload_hash != expected_hash:
            await websocket.close(code=4003, reason="Tampered Handshake")
            return
            
        expected_sig = ProofOfConsensus.generate_member_signature(role, payload_hash)
        if signature != expected_sig:
            await websocket.close(code=4003, reason="Invalid Signature")
            return
            
        # Send confirmation
        await websocket.send_json({
            "handshake": "verified",
            "status": "success",
            "node_id": router_p2p.node_id,
            "role": router_p2p.role
        })
        
        # Register client peer
        router_p2p.add_peer(client_node_id, role, client_host, client_port, status="connected", ws=websocket, shared_key=shared_key)
        
        # Listen for P2P messages on this connection
        await router_p2p._listen_to_ws(websocket, client_node_id, shared_key)
        
    except Exception as e:
        logger.error(f"Error in P2P WebSocket endpoint: {e}")
        try:
            await websocket.close(code=4000)
        except Exception:
            pass


# ----------------- Slack & LINE production webhook adapters -----------------

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "mock_slack_secret_12345")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "mock_slack_bot_token")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "mock_line_secret_12345")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "mock_line_access_token")

def verify_slack_signature(timestamp: str, body: bytes, signature: str) -> bool:
    try:
        now = time.time()
        if abs(now - float(timestamp)) > 300:
            logger.warning("[Slack Auth] Request timestamp is too old or in the future.")
            return False
        sig_basestring = f"v0:{timestamp}:".encode('utf-8') + body
        computed_sig = "v0=" + hmac.new(
            SLACK_SIGNING_SECRET.encode('utf-8'),
            sig_basestring,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed_sig, signature)
    except Exception as e:
        logger.error(f"[Slack Auth] Error verifying signature: {e}")
        return False

def verify_line_signature(body: bytes, signature: str) -> bool:
    try:
        hash_val = hmac.new(
            LINE_CHANNEL_SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).digest()
        computed_sig = base64.b64encode(hash_val).decode('utf-8')
        return hmac.compare_digest(computed_sig, signature)
    except Exception as e:
        logger.error(f"[LINE Auth] Error verifying signature: {e}")
        return False

async def post_to_slack(channel: str, text: str):
    if SLACK_BOT_TOKEN.startswith("mock"):
        logger.info(f"[Mock Slack POST] Channel: {channel}, Msg: {text}")
        return
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"channel": channel, "text": text}
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            logger.info(f"Successfully posted message to Slack: {resp.json()}")
    except Exception as e:
        logger.error(f"Failed to post response to Slack: {e}")

async def post_to_line(reply_token: str, text: str):
    if LINE_CHANNEL_ACCESS_TOKEN.startswith("mock"):
        logger.info(f"[Mock LINE POST] ReplyToken: {reply_token}, Msg: {text}")
        return
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            logger.info(f"Successfully replied to LINE: {resp.json()}")
    except Exception as e:
        logger.error(f"Failed to post reply to LINE: {e}")

async def process_slack_message(session_id: str, channel: str, text: str):
    try:
        router = build_router(session_id)
        response_text = ""
        async for event in router.stream_agent_loop(text):
            if event.get("type") == "agent_response":
                response_text = event.get("content", "")
        if response_text:
            await post_to_slack(channel, response_text)
    except Exception as e:
        logger.error(f"Error processing Slack message: {e}")

async def process_line_message(session_id: str, reply_token: str, text: str):
    try:
        router = build_router(session_id)
        response_text = ""
        async for event in router.stream_agent_loop(text):
            if event.get("type") == "agent_response":
                response_text = event.get("content", "")
        if response_text:
            await post_to_line(reply_token, response_text)
    except Exception as e:
        logger.error(f"Error processing LINE message: {e}")

@router.post("/v1/channels/slack/webhook")
async def slack_webhook(request: Request):
    body_bytes = await request.body()
    headers = request.headers
    timestamp = headers.get("x-slack-request-timestamp")
    signature = headers.get("x-slack-signature")
    if not timestamp or not signature:
        raise HTTPException(status_code=401, detail="Missing Slack headers")
    if not verify_slack_signature(timestamp, body_bytes, signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")
    try:
        payload = json.loads(body_bytes.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    if "event" in payload:
        event = payload["event"]
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return {"status": "ignored"}
        event_type = event.get("type")
        if event_type == "message":
            user = event.get("user")
            channel = event.get("channel")
            text = event.get("text")
            if user and channel and text:
                session_id = f"slack-{channel}-{user}"
                asyncio.create_task(process_slack_message(session_id, channel, text))
    return {"status": "accepted"}

@router.post("/v1/channels/line/webhook")
async def line_webhook(request: Request):
    body_bytes = await request.body()
    headers = request.headers
    signature = headers.get("x-line-signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing x-line-signature header")
    if not verify_line_signature(body_bytes, signature):
        raise HTTPException(status_code=403, detail="Invalid LINE signature")
    try:
        payload = json.loads(body_bytes.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    events = payload.get("events", [])
    for event in events:
        if event.get("type") == "message":
            reply_token = event.get("replyToken")
            message = event.get("message", {})
            text = message.get("text")
            source = event.get("source", {})
            user_id = source.get("userId")
            if reply_token and text and user_id:
                session_id = f"line-{user_id}"
                asyncio.create_task(process_line_message(session_id, reply_token, text))
    return {"status": "accepted"}
