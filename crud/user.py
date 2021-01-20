from common.mongodb import AsyncIOMotorClient
from typing import Optional
from model.user import UserInDB, UserCreateModel
from common.common import generate_salt, get_password_hash
from config import database_name, user_collection_name


async def get_user(conn: AsyncIOMotorClient, query: Optional[dict]) -> UserInDB:
    row = await conn[database_name][user_collection_name].find_one(query)
    return UserInDB(**row) if row else None


async def create_user(conn: AsyncIOMotorClient, user: UserCreateModel) -> UserInDB:
    salt = generate_salt()
    hashed_password = get_password_hash(salt + user.password)
    db_user = user.dict()
    db_user['salt'] = salt
    db_user['hashed_password'] = hashed_password
    del db_user['password']
    conn[database_name][user_collection_name].insert_one(db_user)
    return UserInDB(**user.dict())
