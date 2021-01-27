from common.mongodb import AsyncIOMotorClient
from typing import Optional, List
from model.self_dict import SelfDictInDB, SelfDictCreateModel
from config import database_name, self_dict_collection_name


async def get_self_dict(conn: AsyncIOMotorClient, query: Optional[dict]) -> SelfDictInDB:
    row = await conn[database_name][self_dict_collection_name].find_one(query)
    return SelfDictInDB(**row) if row else None


async def create_self_dict(conn: AsyncIOMotorClient, data: SelfDictCreateModel) -> SelfDictInDB:
    conn[database_name][self_dict_collection_name].insert_one(data.dict())
    return SelfDictInDB(**data.dict())


async def batch_create_self_dict(conn: AsyncIOMotorClient, data: List):
    conn[database_name][self_dict_collection_name].insert_many(data)
    return True


async def get_self_dict_list(conn: AsyncIOMotorClient, query: Optional[dict], page: int,
                             limit: int):
    result = conn[database_name][self_dict_collection_name].find(query).skip((page - 1) * limit).limit(limit)
    return [SelfDictInDB(**x) async for x in result]


async def count_self_dict_by_query(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = await conn[database_name][self_dict_collection_name].count_documents(query)
    return result


async def update_self_dict(conn: AsyncIOMotorClient, query: Optional[dict], item: dict):
    conn[database_name][self_dict_collection_name].update_one(query, item)
    return True


async def delete_self_dict(conn: AsyncIOMotorClient, query: Optional[dict]):
    conn[database_name][self_dict_collection_name].delete_many(query)
    return True
