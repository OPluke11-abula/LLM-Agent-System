import os
import sys
import json
import uuid
import time
import asyncio
import logging
import hashlib
from typing import Any, Dict, List, Optional
import websockets

logger = logging.getLogger("P2PSwarmRouter")

class SwarmP2PCrypto:
    """Provides ECDH key exchange and AES-GCM-256 messaging utilities."""
    def __init__(self):
        from cryptography.hazmat.primitives.asymmetric import ec
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self.private_key.public_key()
        
    def get_public_bytes(self) -> str:
        from cryptography.hazmat.primitives import serialization
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode("utf-8")

    @classmethod
    def load_public_key(cls, pem_str: str):
        from cryptography.hazmat.primitives import serialization
        return serialization.load_pem_public_key(pem_str.encode("utf-8"))

    def compute_shared_key(self, peer_public_key_pem: str) -> bytes:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        peer_public_key = self.load_public_key(peer_public_key_pem)
        shared_secret = self.private_key.exchange(ec.ECDH(), peer_public_key)
        
        # Derive key using HKDF
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"swarm-session-key",
        ).derive(shared_secret)
        
        return derived_key

    @classmethod
    def encrypt_message(cls, key: bytes, plaintext: str) -> dict[str, str]:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import os
        import base64
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return {
            "encrypted": "true",
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8")
        }

    @classmethod
    def decrypt_message(cls, key: bytes, encrypted_payload: dict[str, str]) -> str:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        aesgcm = AESGCM(key)
        ciphertext = base64.b64decode(encrypted_payload["ciphertext"])
        nonce = base64.b64decode(encrypted_payload["nonce"])
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")


class P2PSwarmRouter:
    """Manages secure decentralized gossip-based routing and P2P handoffs over direct WebSockets."""
    def __init__(self, node_id: str, role: str, host: str, port: int):
        self.node_id = node_id
        self.role = role
        self.host = host
        self.port = port
        
        # Localized node discovery map: node_id -> peer_info
        self.peers: Dict[str, Dict[str, Any]] = {}
        
        # Futures for pending task requests: task_id -> Future
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        self._gossip_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self):
        self._is_running = True
        self._gossip_task = asyncio.create_task(self._gossip_loop())
        logger.info(f"P2PSwarmRouter started as node {self.node_id} ({self.role}) on {self.host}:{self.port}")

    async def stop(self):
        self._is_running = False
        if self._gossip_task:
            self._gossip_task.cancel()
            try:
                await self._gossip_task
            except asyncio.CancelledError:
                pass
        
        # Close all active connections
        for peer in list(self.peers.values()):
            ws = peer.get("ws")
            if ws:
                try:
                    if hasattr(ws, "close") and asyncio.iscoroutinefunction(ws.close):
                        await ws.close()
                    elif hasattr(ws, "close"):
                        await ws.close()
                except Exception:
                    pass
        self.peers.clear()

    def add_peer(self, node_id: str, role: str, host: str, port: int, status: str = "disconnected", ws: Any = None, shared_key: bytes = None) -> Dict[str, Any]:
        if node_id not in self.peers:
            self.peers[node_id] = {
                "node_id": node_id,
                "role": role,
                "host": host,
                "port": port,
                "status": status,
                "latency": 0.0,
                "last_seen": time.monotonic(),
                "ws": ws,
                "key": shared_key
            }
        else:
            self.peers[node_id].update({
                "role": role,
                "host": host,
                "port": port,
                "status": status,
                "last_seen": time.monotonic()
            })
            if ws is not None:
                self.peers[node_id]["ws"] = ws
            if shared_key is not None:
                self.peers[node_id]["key"] = shared_key
        return self.peers[node_id]

    def get_known_peers_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "node_id": p["node_id"],
                "role": p["role"],
                "host": p["host"],
                "port": p["port"]
            }
            for p in self.peers.values()
        ]

    def is_already_connected(self, host: str, port: int) -> bool:
        for p in self.peers.values():
            if p.get("status") == "connected" and p.get("host") == host and p.get("port") == port:
                return True
        return False

    async def discover_peers(self, host_ports: List[str]):
        """Register initial seed nodes to initiate mesh discovery."""
        for hp in host_ports:
            if ":" in hp:
                host, port_str = hp.split(":", 1)
                try:
                    port = int(port_str)
                    if host == self.host and port == self.port:
                        continue
                    peer_id = f"seed-{host}-{port}"
                    self.add_peer(peer_id, "unknown", host, port, status="disconnected")
                except ValueError:
                    pass

    async def connect_to_peer(self, host: str, port: int) -> bool:
        if self.is_already_connected(host, port):
            return True
            
        url = f"ws://{host}:{port}/v1/swarm/p2p/tunnel"
        try:
            ws = await websockets.connect(url)
            
            # 1. Handshake server_hello
            server_hello = json.loads(await ws.recv())
            if server_hello.get("handshake") != "server_hello":
                await ws.close()
                return False
                
            server_pub = server_hello["public_key"]
            
            # 2. Handshake client_hello
            client_crypto = SwarmP2PCrypto()
            await ws.send(json.dumps({
                "handshake": "client_hello",
                "public_key": client_crypto.get_public_bytes()
            }))
            
            # 3. Derive symmetric session key
            shared_key = client_crypto.compute_shared_key(server_pub)
            
            # 4. Generate Proof-of-Consensus verification signature
            payload_hash = hashlib.sha256(f"{client_crypto.get_public_bytes()}:{server_pub}".encode("utf-8")).hexdigest()
            
            try:
                from core.discussion_room import ProofOfConsensus
            except ImportError:
                from agent_workspace.core.discussion_room import ProofOfConsensus
                
            sig = ProofOfConsensus.generate_member_signature(self.role, payload_hash)
            
            await ws.send(json.dumps({
                "handshake": "verify",
                "role": self.role,
                "node_id": self.node_id,
                "host": self.host,
                "port": self.port,
                "payload_hash": payload_hash,
                "signature": sig
            }))
            
            # 5. Handshake verification response
            resp = json.loads(await ws.recv())
            if resp.get("handshake") == "verified" and resp.get("status") == "success":
                peer_node_id = resp["node_id"]
                peer_role = resp["role"]
                
                self.add_peer(peer_node_id, peer_role, host, port, status="connected", ws=ws, shared_key=shared_key)
                
                # Start websocket listening loop as client
                asyncio.create_task(self._listen_to_ws(ws, peer_node_id, shared_key))
                logger.info(f"Successfully connected P2P tunnel to {peer_node_id} ({peer_role})")
                return True
            else:
                await ws.close()
                return False
        except Exception as e:
            logger.debug(f"P2P connection attempt to {host}:{port} failed: {e}")
            return False

    async def _listen_to_ws(self, ws: Any, peer_node_id: str, shared_key: bytes):
        try:
            while self._is_running:
                if hasattr(ws, "recv"):
                    data_str = await ws.recv()
                else:
                    data_str = await ws.receive_text()
                
                encrypted = json.loads(data_str)
                decrypted = SwarmP2PCrypto.decrypt_message(shared_key, encrypted)
                msg = json.loads(decrypted)
                
                await self._process_ws_message(msg, peer_node_id, ws, shared_key)
        except Exception as e:
            logger.debug(f"P2P WS tunnel disconnect for {peer_node_id}: {e}")
        finally:
            if peer_node_id in self.peers:
                self.peers[peer_node_id]["status"] = "disconnected"
                self.peers[peer_node_id]["ws"] = None

    async def _send_msg(self, ws: Any, msg_dict: dict, shared_key: bytes):
        plaintext = json.dumps(msg_dict)
        encrypted = SwarmP2PCrypto.encrypt_message(shared_key, plaintext)
        payload_str = json.dumps(encrypted)
        if hasattr(ws, "send"):
            await ws.send(payload_str)
        else:
            await ws.send_text(payload_str)

    async def _process_ws_message(self, msg: dict, peer_node_id: str, ws: Any, shared_key: bytes):
        msg_type = msg.get("type")
        
        if msg_type == "ping":
            sender_id = msg["sender_id"]
            role = msg["role"]
            host = msg["host"]
            port = msg["port"]
            known_peers = msg.get("known_peers", [])
            
            self.add_peer(sender_id, role, host, port, status="connected", ws=ws, shared_key=shared_key)
            
            # Gossip integration: learn other peers
            for p in known_peers:
                p_id = p.get("node_id")
                if p_id and p_id != self.node_id:
                    self.add_peer(p_id, p.get("role"), p.get("host"), p.get("port"), status="disconnected")
            
            # Send gossip pong back
            pong_msg = {
                "type": "pong",
                "sender_id": self.node_id,
                "role": self.role,
                "host": self.host,
                "port": self.port,
                "known_peers": self.get_known_peers_list()
            }
            await self._send_msg(ws, pong_msg, shared_key)
            
        elif msg_type == "pong":
            sender_id = msg["sender_id"]
            known_peers = msg.get("known_peers", [])
            
            if sender_id in self.peers:
                peer = self.peers[sender_id]
                peer["status"] = "connected"
                peer["last_seen"] = time.monotonic()
                if "ping_start_time" in peer:
                    peer["latency"] = (time.monotonic() - peer["ping_start_time"]) * 1000.0
            
            # Gossip integration
            for p in known_peers:
                p_id = p.get("node_id")
                if p_id and p_id != self.node_id:
                    self.add_peer(p_id, p.get("role"), p.get("host"), p.get("port"), status="disconnected")

        elif msg_type == "task_request":
            task_id = msg["task_id"]
            role = msg["role"]
            task_instructions = msg["task_instructions"]
            input_parameters = msg.get("input_parameters", {})
            security_restrictions = msg.get("security_restrictions", {})
            mock_directives = msg.get("mock_directives", {})
            validation_assertions = msg.get("validation_assertions", [])
            
            asyncio.create_task(self._run_task_locally(
                task_id, role, task_instructions, input_parameters,
                security_restrictions, mock_directives, validation_assertions,
                ws, shared_key
            ))

        elif msg_type == "task_response":
            task_id = msg["task_id"]
            if task_id in self.pending_requests:
                fut = self.pending_requests.pop(task_id)
                if not fut.done():
                    fut.set_result(msg)

    async def _run_task_locally(
        self,
        task_id: str,
        role: str,
        task_instructions: str,
        input_parameters: dict,
        security_restrictions: dict,
        mock_directives: dict,
        validation_assertions: list,
        ws: Any,
        shared_key: bytes
    ):
        try:
            if security_restrictions.get("block_all") or "restrict_execution" in security_restrictions:
                raise PermissionError("Security sandbox interception: Execution blocked by policy rules.")

            output = f"P2P direct execution result for role [{role}] with instructions: {task_instructions}."
            if mock_directives.get("force_mock_response"):
                output = mock_directives["force_mock_response"]
            
            for assertion in validation_assertions:
                if "fail" in assertion.lower() or "error" in assertion.lower():
                    raise AssertionError(f"Validation assertion failed: '{assertion}'")
            
            res = {
                "type": "task_response",
                "task_id": task_id,
                "status": "completed",
                "output": output,
                "error": None
            }
        except Exception as e:
            res = {
                "type": "task_response",
                "task_id": task_id,
                "status": "error",
                "output": None,
                "error": str(e)
            }
            
        await self._send_msg(ws, res, shared_key)

    async def ping_peer(self, peer: dict):
        ws = peer.get("ws")
        shared_key = peer.get("key")
        if not ws or not shared_key:
            return
            
        ping_msg = {
            "type": "ping",
            "sender_id": self.node_id,
            "role": self.role,
            "host": self.host,
            "port": self.port,
            "known_peers": self.get_known_peers_list()
        }
        peer["ping_start_time"] = time.monotonic()
        try:
            await self._send_msg(ws, ping_msg, shared_key)
        except Exception:
            pass

    async def _gossip_loop(self):
        while self._is_running:
            try:
                # 1. Connect to disconnected peers
                disconnected = [p for p in self.peers.values() if p["status"] == "disconnected"]
                for p in disconnected:
                    asyncio.create_task(self.connect_to_peer(p["host"], p["port"]))
                    
                # 2. Gossip ping connected peers
                connected = [p for p in self.peers.values() if p["status"] == "connected"]
                for p in connected:
                    asyncio.create_task(self.ping_peer(p))
            except Exception as e:
                logger.error(f"Error in P2P gossip loop: {e}")
            await asyncio.sleep(5.0)

    async def dispatch_task(
        self,
        role: str,
        task_instructions: str,
        input_parameters: dict,
        security_restrictions: dict,
        mock_directives: dict,
        validation_assertions: list
    ) -> Optional[dict]:
        target_peer = None
        for peer in self.peers.values():
            if peer.get("status") == "connected" and peer.get("role", "").lower() == role.lower():
                target_peer = peer
                break
                
        if not target_peer:
            logger.warning(f"No connected peer found for role {role}")
            return None
            
        ws = target_peer["ws"]
        shared_key = target_peer["key"]
        
        task_id = f"p2p-task-{uuid.uuid4().hex[:8]}"
        req_msg = {
            "type": "task_request",
            "task_id": task_id,
            "role": role,
            "task_instructions": task_instructions,
            "input_parameters": input_parameters,
            "security_restrictions": security_restrictions,
            "mock_directives": mock_directives,
            "validation_assertions": validation_assertions
        }
        
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending_requests[task_id] = fut
        
        try:
            await self._send_msg(ws, req_msg, shared_key)
            response = await asyncio.wait_for(fut, timeout=5.0)
            return response
        except Exception as e:
            logger.error(f"P2P dispatch failed for task {task_id}: {e}")
            self.pending_requests.pop(task_id, None)
            return {"status": "error", "error": f"P2P dispatch failed: {e}"}


P2P_ROUTER = None

def get_p2p_router(node_id: Optional[str] = None, role: Optional[str] = None, host: Optional[str] = None, port: Optional[int] = None) -> P2PSwarmRouter:
    global P2P_ROUTER
    if P2P_ROUTER is None:
        nid = node_id or f"node-{uuid.uuid4().hex[:8]}"
        r = role or "dev"
        h = host or "127.0.0.1"
        p = port or 8000
        P2P_ROUTER = P2PSwarmRouter(nid, r, h, p)
    return P2P_ROUTER
