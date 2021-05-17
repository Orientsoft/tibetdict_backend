import pytz

HOST = '0.0.0.0'
PORT = 5555
DEBUG = True
VERSION = '0.0.1'
SECRET_KEY = 'welcome1'
MONGODB_URL = 'mongodb://192.168.0.61:37017'
timezone = pytz.timezone('Asia/Shanghai')
MAX_CONNECTIONS_COUNT = 10
MIN_CONNECTIONS_COUNT = 10
ALLOWED_HOSTS = ''
database_name = 'tibetan'
JWT_TOKEN_PREFIX = "Bearer"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
ALGORITHM = "HS256"
API_KEY = 'welcome1'
user_collection_name = 'user'
word_stat_dict_collection_name = 'word_stat_dict'
self_dict_collection_name = 'self_dict'
file_collection_name = 'file'
work_history_collection_name = 'work_history'
upload_failed_collection_name = 'upload_failed'
max_limit = 5
MINIO_URL = 'storage.mooplab.com'
MINIO_ACCESS = 'moop'
MINIO_SECRET = 'd2VsY29tZTEK'
MINIO_SECURE = True
MINIO_BUCKET = 'tibetdictdev'
# 藏语的分隔符，编码问题IDE可能显示不出来
tibetan_full_point = '།'
# redis 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWD = None
WORD_POOL_KEY = 'word_pool_check'
NEW_WORD_POOL_KEY = 'new_word_pool_check'
# celery config
BROKER_URL = 'redis://127.0.0.1:6379/0'
RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
ENABLE_UTC = True

# es地址
ES_URL = 'https://search-tibetandict-oomehhangnyihqg3morcubxkce.cn-northwest-1.es.amazonaws.com.cn'
ES_PORT = 9200
ES_NAME = 'elastic'
ES_PASSWD = 'Welcome@123'
ES_INDEX = 'tibetan-sentence-dev'
# 共享语料库user_id
SHARE_USER_ID = 'b95d552e5add11ebb13ca0a4c56447ad'
EXCLUED_WORD = ['།།', '།', '༑', '[', '༼', '༽', ']', '༄', '༅', '༡', '༢', '༣', '༤', '༥', '༦', '༧', '༨', '༩', '༠', '?',
                '.', '*']
