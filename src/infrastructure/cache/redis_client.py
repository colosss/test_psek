import redis.asyncio as aioredis
import os
from uuid import UUID
from datetime import date as date_type

_redis: aioredis.Redis | None = None

async def get_redis()-> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis=await aioredis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            encoding="utf-8", decode_responses=True,
        )
    return _redis
async def invalidate_slots_cache(room_id: UUID, slot_date: date_type) -> None:
    redis = await get_redis()
    await redis.delete(f"slots:{room_id}:{slot_date.isoformat()}")