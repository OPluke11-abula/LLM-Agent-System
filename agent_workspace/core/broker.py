import os
import json
import logging
import asyncio
import inspect
from typing import Callable, Any, Optional


logger = logging.getLogger(__name__)

class BaseSwarmBroker:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        pass

    async def subscribe(self, channel: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        pass

    async def unsubscribe(self, channel: str) -> None:
        pass


class InMemorySwarmBroker(BaseSwarmBroker):
    """Local, in-memory implementation of the broker using asyncio.Queue."""
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._listeners: dict[str, list[asyncio.Task]] = {}
        self.kv_store: dict[str, str] = {}

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        logger.debug(f"[InMemoryBroker] Publish to {channel}: {message}")
        if channel in self._queues:
            for q in self._queues[channel]:
                await q.put(message)

    async def subscribe(self, channel: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        if channel not in self._queues:
            self._queues[channel] = []
            self._listeners[channel] = []
        
        q = asyncio.Queue()
        self._queues[channel].append(q)

        async def worker() -> None:
            while True:
                try:
                    msg = await q.get()
                    if inspect.iscoroutinefunction(callback):
                        await callback(msg)
                    else:
                        callback(msg)
                    q.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in InMemorySwarmBroker callback: {e}")

        task = asyncio.create_task(worker())
        self._listeners[channel].append(task)

    async def unsubscribe(self, channel: str) -> None:
        if channel in self._listeners:
            for t in self._listeners[channel]:
                t.cancel()
            self._listeners.pop(channel)
        self._queues.pop(channel, None)


try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisSwarmBroker(BaseSwarmBroker):
    """Redis-backed message broker using async pub/sub."""
    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        self.redis_url = redis_url
        self.client: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}
        self._listener_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self) -> None:
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis package is missing")
        self.client = aioredis.from_url(self.redis_url, decode_responses=True)
        # Ping to verify connection
        await self.client.ping()
        self.pubsub = self.client.pubsub()
        self._is_running = True
        self._listener_task = asyncio.create_task(self._listen_loop())
        logger.info(f"RedisSwarmBroker connected to {self.redis_url}")

    async def stop(self) -> None:
        self._is_running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self.pubsub:
            await self.pubsub.close()
        if self.client:
            await self.client.close()
        logger.info("RedisSwarmBroker stopped.")

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        if not self.client:
            raise RuntimeError("Broker not started")
        payload = json.dumps(message)
        await self.client.publish(channel, payload)

    async def subscribe(self, channel: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        if not self.client or not self.pubsub:
            raise RuntimeError("Broker not started")
        if channel not in self._subscribers:
            self._subscribers[channel] = []
            await self.pubsub.subscribe(channel)
        self._subscribers[channel].append(callback)

    async def unsubscribe(self, channel: str) -> None:
        if not self.client or not self.pubsub:
            return
        if channel in self._subscribers:
            self._subscribers.pop(channel)
            await self.pubsub.unsubscribe(channel)

    async def _listen_loop(self) -> None:
        while self._is_running:
            try:
                if self.pubsub:
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        channel = message.get("channel")
                        data_str = message.get("data")
                        if channel and data_str:
                            try:
                                data = json.loads(data_str)
                            except Exception:
                                data = {"raw": data_str}
                            cbs = self._subscribers.get(channel, [])
                            for cb in cbs:
                                try:
                                    if inspect.iscoroutinefunction(cb):
                                        await cb(data)
                                    else:
                                        cb(data)
                                except Exception as e:
                                    logger.error(f"Error in subscriber callback for channel {channel}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Redis pubsub listen loop: {e}")
                await asyncio.sleep(1.0)


_global_broker: Optional[BaseSwarmBroker] = None

def get_broker(redis_url: Optional[str] = None, workspace_path: str = ".", reset: bool = False) -> BaseSwarmBroker:
    global _global_broker
    if _global_broker is not None and not reset:
        return _global_broker

    url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")
    
    if REDIS_AVAILABLE:
        try:
            broker = RedisSwarmBroker(url)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(broker.start())
            except RuntimeError:
                temp_loop = asyncio.new_event_loop()
                temp_loop.run_until_complete(broker.start())
                temp_loop.close()
            _global_broker = broker
            logger.info("Initialized Redis Swarm Broker successfully.")
            return _global_broker
        except Exception as e:
            logger.warning(f"Redis is unavailable ({e}). Falling back dynamically and silently to InMemorySwarmBroker.")
    else:
        logger.info("redis package is missing. Falling back dynamically and silently to InMemorySwarmBroker.")

    _global_broker = InMemorySwarmBroker()
    return _global_broker
