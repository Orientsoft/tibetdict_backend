import pytz

HOST = '0.0.0.0'
PORT = '5555'
DEBUG = True
VERSION = '0.0.1'
SECRET_KEY = 'welcome1'
MONGODB_URL = 'mongodb://192.168.0.61:31711'
timezone = pytz.timezone('Asia/Shanghai')
MAX_CONNECTIONS_COUNT = 10
MIN_CONNECTIONS_COUNT = 10
ALLOWED_HOSTS = ''
database_name = 'tibetan'
JWT_TOKEN_PREFIX = "Bearer"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
ALGORITHM = "HS256"
user_collection_name = 'user'
