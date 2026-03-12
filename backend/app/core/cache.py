import json


async def get_cached_lmp_data(redis, key) -> list[dict] | None:
    value = await redis.get(key)

    if value is not None:
        return json.loads(value)
    else:
        return None

async def set_cached_lmp_data(redis, key, data, ttl_seconds=300) -> None: 
    await redis.set(key, json.dumps(data), ex=ttl_seconds)