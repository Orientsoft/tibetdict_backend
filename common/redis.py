from fastapi_plugins import RedisSettings

from config import REDIS_HOST, REDIS_PORT, REDIS_PASSWD


class RedisAppSettings(RedisSettings):
    redis_host: str = REDIS_HOST
    redis_port: int = REDIS_PORT
    redis_password: str = REDIS_PASSWD


redis_config = RedisAppSettings()
