from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Depends, Header
from jwt import PyJWTError
from starlette.exceptions import HTTPException
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND
from fastapi.security import OAuth2PasswordBearer
from model.user import UserInDB, TokenPayload, User
from common.mongodb import AsyncIOMotorClient, get_database

from config import JWT_TOKEN_PREFIX, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, timezone, \
    database_name, user_collection_name


async def get_user(conn: AsyncIOMotorClient, query: Optional[dict]) -> UserInDB:
    row = await conn[database_name][user_collection_name].find_one(query)
    return UserInDB(**row) if row else None


# Header中authorization信息校验，校验token的前缀
def _get_authorization_token(Authorization: str = Header(...)):
    token_prefix, token = Authorization.split(" ")
    if token_prefix != JWT_TOKEN_PREFIX:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="40006"
        )
    return token


# Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")


# 解密token，从db中获取用户信息
async def _get_current_user(db: AsyncIOMotorClient = Depends(get_database),
                            token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, str(SECRET_KEY), algorithms=[ALGORITHM])
        # TokenPayload可校验解密后内容
        token_data = TokenPayload(**payload)
    except PyJWTError:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="40006"
        )
    '''
    从redis中读取用户数据，如无数据，再从mongo中查询，如有，直接返回
    '''

    dbuser = await get_user(db, {'id': token_data.id})
    if not dbuser:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="40007")

    user = User(**dbuser.dict(), token=token)
    return user


# 公开内容，无token可访问
def _get_authorization_token_optional(Authorization: str = Header(None)):
    if Authorization:
        return _get_authorization_token(Authorization)
    return ""


# 可选项，用户信息
async def _get_current_user_optional(db: AsyncIOMotorClient = Depends(get_database),
                                     token: str = Depends(_get_authorization_token_optional), ) -> Optional[User]:
    if token:
        return await _get_current_user(db, token)

    return None


# 获取当前用户信息，required=True,必须拥有token才可访问，False,公开内容
def get_current_user_authorizer(*, required: bool = True):
    if required:
        return _get_current_user
    else:
        return _get_current_user_optional


# 创建token
# token包含exp,和用户自定义的json数据
def create_access_token(*, data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(tz=timezone) + expires_delta
    else:
        expire = datetime.now(tz=timezone) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, str(SECRET_KEY), algorithm=ALGORITHM)
    return encoded_jwt
