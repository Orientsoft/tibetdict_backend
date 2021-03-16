from aioredis import Redis
import json
from typing import List


async def set_cache(rd: Redis, key: str, info) -> bool:
    try:
        save_info = json.dumps(info, ensure_ascii=False)
        await rd.set(key, save_info)
        return True
    except:
        return False


async def get_cache(rd: Redis, key: str):
    try:
        result = await rd.get(key, encoding='utf-8')
        if result:
            return json.loads(result)
        else:
            return None
    except Exception as e:
        return None


async def del_cache(rd: Redis, key: str):
    try:
        await rd.delete(key)
    except Exception as e:
        return None
    finally:
        return True
