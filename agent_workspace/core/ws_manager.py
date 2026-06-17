import os
import json
import logging
import threading
from fastapi import WebSocket
from agent_workspace.core.p2p_router import SwarmP2PCrypto

logger = logging.getLogger("ws_manager")
workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class CrewSyncManager:
    """Manages secure multi-agent state, log, and file checkpoint synchronization over WebSockets."""
    def __init__(self):
        self.sessions: dict[str, list[tuple[WebSocket, bytes]]] = {}
        self.lock = threading.Lock()

    def connect(self, session_id: str, websocket: WebSocket, session_key: bytes):
        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = []
            self.sessions[session_id].append((websocket, session_key))
            logger.info(f"Worker WebSocket connected to crew sync session '{session_id}'")

    def disconnect(self, session_id: str, websocket: WebSocket):
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id] = [
                    (ws, key) for ws, key in self.sessions[session_id] if ws != websocket
                ]
                if not self.sessions[session_id]:
                    del self.sessions[session_id]
            logger.info(f"Worker WebSocket disconnected from crew sync session '{session_id}'")

    async def broadcast(self, session_id: str, sender_ws: WebSocket, decrypted_message: str):
        # Record replay event
        try:
            from agent_workspace.core.replay_logger import ReplayLogger
            try:
                msg_data = json.loads(decrypted_message)
            except Exception:
                msg_data = {"raw_message": decrypted_message}
            ReplayLogger.log_event(workspace, session_id, "crew_sync", msg_data)
        except Exception as e:
            logger.error(f"Error logging crew sync event: {e}")

        targets = []
        with self.lock:
            if session_id in self.sessions:
                for ws, key in self.sessions[session_id]:
                    if ws != sender_ws:
                        targets.append((ws, key))

        for ws, key in targets:
            try:
                enc_msg = SwarmP2PCrypto.encrypt_message(key, decrypted_message)
                await ws.send_json(enc_msg)
            except Exception as e:
                logger.error(f"Error broadcasting crew sync event: {e}")

crew_sync_manager = CrewSyncManager()
