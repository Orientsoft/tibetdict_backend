from common.mongodb import AsyncIOMotorClient
from typing import Optional
import pymongo
from model.user import UserInDB, UserCreateModel, UserListModel
from common.common import generate_salt, get_password_hash
from config import database_name, user_collection_name, work_history_collection_name, file_collection_name, \
    self_dict_collection_name, word_stat_dict_collection_name


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


async def get_user_list_by_query_with_page_and_limit(conn: AsyncIOMotorClient, query: Optional[dict], page: int,
                                                     limit: int):
    result = conn[database_name][user_collection_name].find(query).skip((page - 1) * limit).limit(limit)
    return [UserListModel(**x) async for x in result]


async def count_user_by_query(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = await conn[database_name][user_collection_name].count_documents(query)
    return result


async def update_user(conn: AsyncIOMotorClient, query: Optional[dict], item: Optional[dict]):
    conn[database_name][user_collection_name].update_one(query, {'$set': item})
    return True


async def update_password(conn: AsyncIOMotorClient, query: Optional[dict], password: str):
    salt = generate_salt()
    hashed_password = get_password_hash(salt + password)
    item = {'salt': salt, 'hashed_password': hashed_password}
    conn[database_name][user_collection_name].update_one(query, {'$set': item})
    return True


async def init_index(conn: AsyncIOMotorClient) -> bool:
    # word_stat_dict
    try:
        await conn[database_name][word_stat_dict_collection_name].create_index(
            [('word', pymongo.ASCENDING), ('nature', pymongo.ASCENDING), ('type', pymongo.ASCENDING)], unique=True)
    except:
        pass
    try:
        await conn[database_name][word_stat_dict_collection_name].create_index(
            [('id', pymongo.ASCENDING)], unique=True)
    except:
        pass
    try:
        # work_history
        await conn[database_name][work_history_collection_name].create_index(
            [('id', pymongo.ASCENDING)], unique=True)
    except:
        pass
    try:
        # user
        await conn[database_name][user_collection_name].create_index(
            [('id', pymongo.ASCENDING)], unique=True)
    except:
        pass
    try:
        # self_dict
        await conn[database_name][self_dict_collection_name].create_index(
            [('id', pymongo.ASCENDING)], unique=True)
        # self_dict
        await conn[database_name][self_dict_collection_name].create_index(
            [('word', pymongo.ASCENDING), ('user_id', pymongo.ASCENDING)], unique=True)
    except:
        pass
    try:
        # self_dict
        await conn[database_name][self_dict_collection_name].create_index(
            [('work_history_id', pymongo.ASCENDING)])
    except:
        pass
    try:
        # file
        await conn[database_name][file_collection_name].create_index(
            [('id', pymongo.ASCENDING)], unique=True)
    except:
        pass
    try:
        await conn[database_name][file_collection_name].create_index([('file_name', pymongo.ASCENDING)])
    except:
        pass
    return True
