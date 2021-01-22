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
word_stat_his_collection_name = 'word_stat_his'

MINIO_URL = 'storage.mooplab.com'
MINIO_ACCESS = 'moop'
MINIO_SECRET = 'd2VsY29tZTEK'
MINIO_SECURE = True
MINIO_BUCKET = 'tibetdict'
