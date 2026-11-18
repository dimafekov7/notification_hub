import os
import json
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Асинхронный клиент Redis
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

QUEUE_NAME = "notifications_queue"


async def push_to_queue(task_data: dict):
    """Кладем задачу в хвост очереди Redis (LPUSH)"""
    payload = json.dumps(task_data)
    await redis_client.lpush(QUEUE_NAME, payload)


async def pop_from_queue(timeout: int = 2):
    """Достаем задачу из головы очереди Redis (BRPOP) с ожиданием"""
    # BRPOP блокирует поток до появления задачи или исчерпания таймаута
    result = await redis_client.brpop(QUEUE_NAME, timeout=timeout)
    if result:
        _, data = result
        return json.loads(data)
    return None