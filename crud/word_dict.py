from common.mongodb import AsyncIOMotorClient
from typing import Optional, List
from model.word_dict import WordStatDictCreateModel, WordStatDictInDB, WordPoolModel
from config import database_name, word_stat_dict_collection_name


async def get_word_stat_dict(conn: AsyncIOMotorClient, query: Optional[dict]) -> WordStatDictInDB:
    row = await conn[database_name][word_stat_dict_collection_name].find_one(query)
    return WordStatDictInDB(**row) if row else None


async def create_word_stat_dict(conn: AsyncIOMotorClient, data: WordStatDictCreateModel) -> WordStatDictInDB:
    conn[database_name][word_stat_dict_collection_name].insert_one(data.dict())
    return WordStatDictInDB(**data.dict())


async def batch_create_word_stat_dict(conn: AsyncIOMotorClient, data: List):
    conn[database_name][word_stat_dict_collection_name].insert_many(data)
    return True


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


async def get_dict(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = conn[database_name][word_stat_dict_collection_name].aggregate([{'$match': query},
                                                                            {'$project': {'_id': 0, 'id': 1, 'word': 1,
                                                                                          'nature': 1,
                                                                                          'length': {
                                                                                              '$strLenCP': "$word"}}},
                                                                            {'$sort': {'length': -1}}
                                                                            ])
    return [WordPoolModel(**item) async for item in result]


async def remove_word_stat_dict(conn: AsyncIOMotorClient, item: dict):
    conn[database_name][word_stat_dict_collection_name].remove_many(item)
    return True
