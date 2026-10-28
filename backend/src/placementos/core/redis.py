"""PlacementOS Redis Client Connection."""

import asyncio

import redis.asyncio as aioredis

from placementos.core.config import settings

redis_client: aioredis.Redis | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def get_redis_client() -> aioredis.Redis:
    """Return async Redis client bound to current active event loop."""
    global redis_client, _client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if redis_client is not None and (_client_loop is None or _client_loop.is_closed() or _client_loop != current_loop):
        redis_client = None

    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=5.0,
            retry_on_timeout=True,
        )
        _client_loop = current_loop

    return redis_client


async def close_redis_client() -> None:
    """Close redis connection pool."""
    global redis_client, _client_loop
    if redis_client is not None:
        try:
            await redis_client.aclose()
        except Exception:
            pass
        redis_client = None
        _client_loop = None
