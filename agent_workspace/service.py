import os
import sys
import json
import uuid
import argparse
import asyncio
import logging
import signal

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.abspath(__file__))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.account_manager import AccountManager
from core.providers import ProviderFactory
from core.prompt_composer import PromptComposer
from core.agent_crew import CrewRegistry, AgentCrew

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SwarmService")


class SwarmAgentService:
    def __init__(self, role: str, redis_url: str, workspace_path: str = "."):
        self.role = role.lower()
        self.redis_url = redis_url
        self.workspace_path = os.path.abspath(workspace_path)
        self.node_id = f"service-{self.role}-{uuid.uuid4().hex[:8]}"
        self.status = "idle"
        self.client = None
        self.pubsub = None
        self._is_running = False
        self._heartbeat_task = None
        self._listener_task = None
        
        self.account_manager = AccountManager(self.workspace_path)
        self.prompt_composer = PromptComposer(self.workspace_path)

    async def start(self):
        import redis.asyncio as aioredis
        self.client = aioredis.from_url(self.redis_url, decode_responses=True)
        await self.client.ping()
        
        self.pubsub = self.client.pubsub()
        self._is_running = True
        
        # Subscribe to channels
        await self.pubsub.subscribe(
            "swarm:discovery",
            f"swarm:role:{self.role}",
            f"swarm:debate:{self.role}"
        )
        
        # Publish join event
        join_payload = {
            "type": "join",
            "role": self.role,
            "node_id": self.node_id,
            "status": self.status
        }
        await self.client.publish("swarm:discovery", json.dumps(join_payload))
        
        # Start background loops
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._listener_task = asyncio.create_task(self._listen_loop())
        
        logger.info(f"SwarmAgentService started for role '{self.role}' (node: {self.node_id})")

    async def stop(self):
        self._is_running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._listener_task:
            self._listener_task.cancel()
            
        # Publish leave event
        if self.client:
            try:
                leave_payload = {
                    "type": "leave",
                    "role": self.role,
                    "node_id": self.node_id
                }
                await self.client.publish("swarm:discovery", json.dumps(leave_payload))
                await self.client.delete(f"swarm:peer:{self.role}:{self.node_id}")
            except Exception as e:
                logger.error(f"Error sending leave signal: {e}")
                
            await self.client.close()
        logger.info(f"SwarmAgentService for role '{self.role}' stopped.")

    async def _heartbeat_loop(self):
        while self._is_running:
            try:
                peer_key = f"swarm:peer:{self.role}:{self.node_id}"
                peer_val = {
                    "role": self.role,
                    "node_id": self.node_id,
                    "status": self.status
                }
                await self.client.set(peer_key, json.dumps(peer_val), ex=10)
                
                # Publish heartbeat to swarm:discovery for active coordination tracking
                hb_payload = {
                    "type": "heartbeat",
                    "role": self.role,
                    "node_id": self.node_id,
                    "status": self.status
                }
                await self.client.publish("swarm:discovery", json.dumps(hb_payload))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
            await asyncio.sleep(5.0)

    async def _listen_loop(self):
        while self._is_running:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    channel = message.get("channel")
                    data_str = message.get("data")
                    if channel and data_str:
                        data = json.loads(data_str)
                        asyncio.create_task(self._process_message(channel, data))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listener loop error: {e}")
                await asyncio.sleep(1.0)

    async def _process_message(self, channel: str, msg: dict):
        logger.info(f"Processing message on channel '{channel}': {msg.get('type')}")
        
        # 1. Peer Discovery Ping
        if channel == "swarm:discovery" and msg.get("type") == "ping":
            pong = {
                "type": "pong",
                "role": self.role,
                "node_id": self.node_id,
                "status": self.status
            }
            await self.client.publish("swarm:discovery:response", json.dumps(pong))
            
        # 2. Debate Turn Request
        elif channel == f"swarm:debate:{self.role}" and msg.get("type") == "turn_request":
            session_id = msg["session_id"]
            agent_name = msg["agent_name"]
            topic = msg["topic"]
            system_prompt = msg["system_prompt"]
            user_content = msg["user_content"]
            account_id = msg.get("account_id")
            
            self.status = "busy"
            response_channel = f"swarm:debate:{session_id}:{self.role}:response"
            
            try:
                # Perform LLM Complete call
                # Resolve account
                account = None
                if account_id:
                    account = self.account_manager.get_account(account_id)
                if not account:
                    account = self.account_manager.get_active_account()
                
                if not account:
                    raise RuntimeError("No LLM accounts configured.")
                
                # Check token budget
                budget = account.get("token_budget", -1)
                used = account.get("tokens_used", 0)
                if budget > 0 and used >= budget:
                    self.account_manager.swap_to_fallback()
                    account = self.account_manager.get_active_account()

                api_key = self.account_manager.resolve_api_key(account)
                provider = ProviderFactory.get_provider(
                    account["provider"],
                    api_key=api_key,
                    base_url=account.get("base_url")
                )
                
                model_used = account.get("model", "gemini-2.5-flash")
                config = {
                    "model": model_used,
                    "temperature": 0.7,
                    "max_tokens": 1024
                }
                
                logger.info(f"Invoking LLM for debate turn {agent_name}...")
                response_type, response_data = await provider.complete(
                    system_prompt=system_prompt,
                    messages=[{"role": "user", "content": user_content}],
                    tool_schemas=[],
                    config=config
                )
                
                if response_type == "error":
                    raise RuntimeError(f"LLM complete error: {response_data}")
                    
                contribution = str(response_data).strip()
                p_tok = len(system_prompt + user_content) // 4
                c_tok = len(contribution) // 4
                
                # Update account usage locally in the microservice's context
                self.account_manager.record_usage(account["id"], p_tok, c_tok)
                
                resp = {
                    "status": "success",
                    "contribution": contribution,
                    "prompt_tokens": p_tok,
                    "completion_tokens": c_tok,
                    "model": model_used
                }
            except Exception as e:
                logger.error(f"Error executing LLM turn for {agent_name}: {e}")
                resp = {
                    "status": "error",
                    "error": str(e)
                }
                
            await self.client.publish(response_channel, json.dumps(resp))
            self.status = "idle"

        # 3. Agent Crew Task Request
        elif channel == f"swarm:role:{self.role}" and msg.get("type") == "task_request":
            target_node_id = msg.get("target_node_id")
            if target_node_id and target_node_id != self.node_id:
                return  # Skip, this task is meant for another node

            session_id = msg["session_id"]
            node_id = msg["node_id"]
            task_instructions = msg["task_instructions"]
            parent_node_id = msg.get("parent_node_id")
            input_parameters = msg["input_parameters"]
            security_restrictions = msg["security_restrictions"]
            mock_directives = msg["mock_directives"]
            validation_assertions = msg["validation_assertions"]
            
            self.status = "busy"
            response_channel = f"swarm:task:{node_id}:response"
            
            try:
                # Execute simulation/delegation response logic
                # Ensure valid roles
                valid_roles = {"CEO", "Developer", "Auditor", "CFO"}
                normalized_role = self.role.strip().upper()
                matched_role = self.role.capitalize()
                for vr in valid_roles:
                    if vr.lower() == self.role:
                        matched_role = vr
                        break
                
                # Check security sandbox
                if security_restrictions.get("block_all") or "restrict_execution" in security_restrictions:
                    raise PermissionError("Security sandbox interception: Execution blocked by policy rules.")
                
                output = f"Execution result for role [{matched_role}] with instructions: {task_instructions}."
                if mock_directives.get("force_mock_response"):
                    output = mock_directives["force_mock_response"]
                
                # Check assertions
                for assertion in validation_assertions:
                    if "fail" in assertion.lower() or "error" in assertion.lower():
                        raise AssertionError(f"Validation assertion failed: '{assertion}'")
                        
                resp = {
                    "status": "completed",
                    "output": output,
                    "node_id": node_id,
                    "error": None
                }
            except Exception as e:
                logger.error(f"Error executing task {node_id}: {e}")
                resp = {
                    "status": "error",
                    "output": None,
                    "node_id": node_id,
                    "error": str(e)
                }
                
            await self.client.publish(response_channel, json.dumps(resp))
            self.status = "idle"


async def main():
    parser = argparse.ArgumentParser(description="LAS Swarm Microservice Agent Daemon")
    parser.add_argument("--role", required=True, help="Agent role name (e.g. ceo, dev, qa, cfo)")
    parser.add_argument("--redis-url", default=None, help="Redis URL connection string")
    parser.add_argument("--workspace", default=".", help="Workspace root directory path")
    args = parser.parse_args()
    
    redis_url = args.redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")
    
    service = SwarmAgentService(args.role, redis_url, args.workspace)
    
    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(service.stop()))
        except NotImplementedError:
            # Signal handling not supported on Windows inside standard loops sometimes, handled via try/except
            pass
            
    try:
        await service.start()
        # Keep running
        while service._is_running:
            await asyncio.sleep(1.0)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
