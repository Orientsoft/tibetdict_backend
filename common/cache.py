from aioredis import Redis
import json
from typing import List


async def set_cache(rd: Redis, key: str, info, expire: int = 3600) -> bool:
    try:
        save_info = json.dumps(info, ensure_ascii=False)
        await rd.set(key, save_info, expire=expire)
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


async def word_pool_check_cache(rd: Redis, key: str, word_pool: List):
    result = []

    # 不参与排序
    _link = ['འི་', 'འི།', 'འུ་', 'འུ།', 'འོ་', 'འོ།']
    _tmp_result = []

    for item in word_pool:
        _key = item.word.strip()
        _value = item.nature.strip()
        _id = item.id

        # 如果末尾不为་   , 末尾则加上་
        _tt = _key.split('་')
        _length = len(_tt) - 1

        if _tt[-1] != '':
            _length = _length + 1
            _key = "%s་" % _key

        if _key in _link:
            _tmp_result.append({
                'id': _id,
                'word': _key,
                'nature': _value
            })
        else:
            result.append({
                'id': _id,
                'word': _key,
                'nature': _value
            })
    save_result = result + _tmp_result
    await set_cache(rd, key, save_result, 3600)
