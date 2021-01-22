from common.mongodb import AsyncIOMotorClient
from typing import Optional
from model.word_dict import WordStatDictCreateModel, WordStatDictInDB
from config import database_name, word_stat_dict_collection_name


async def get_word_stat_dict(conn: AsyncIOMotorClient, query: Optional[dict]) -> WordStatDictInDB:
    row = await conn[database_name][word_stat_dict_collection_name].find_one(query)
    return WordStatDictInDB(**row) if row else None


async def create_word_stat_dict(conn: AsyncIOMotorClient, data: WordStatDictCreateModel) -> WordStatDictInDB:
    conn[database_name][word_stat_dict_collection_name].insert_one(data.dict())
    return WordStatDictInDB(**data.dict())


async def get_word_stat_dict_list(conn: AsyncIOMotorClient, query: Optional[dict], page: int,
                                  limit: int):
    result = conn[database_name][word_stat_dict_collection_name].find(query).skip((page - 1) * limit).limit(limit)
    return [WordStatDictInDB(**x) async for x in result]


async def count_word_stat_dict_by_query(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = await conn[database_name][word_stat_dict_collection_name].count_documents(query)
    return result


async def update_word_stat_dict(conn: AsyncIOMotorClient, query: Optional[dict], item: dict):
    conn[database_name][word_stat_dict_collection_name].update_one(query, item)
    return True


async def batch_update_word_stat_dict(conn: AsyncIOMotorClient, query: Optional[dict], item: dict):
    conn[database_name][word_stat_dict_collection_name].update_many(query, item)
    return True
