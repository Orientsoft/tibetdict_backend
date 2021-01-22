from common.mongodb import AsyncIOMotorClient
from typing import Optional
from model.word_stat import WordStatCreateModel, WordStatInDB, WordStatListModel
from config import database_name, word_stat_his_collection_name, file_collection_name


async def get_word_stat_his(conn: AsyncIOMotorClient, query: Optional[dict], show_result: bool = False) -> WordStatInDB:
    if show_result:
        row = await conn[database_name][word_stat_his_collection_name].find_one(query)
    else:
        row = await conn[database_name][word_stat_his_collection_name].find_one(query, {'result': show_result})
    return WordStatInDB(**row) if row else None


async def create_word_stat_his(conn: AsyncIOMotorClient, data: WordStatCreateModel) -> str:
    conn[database_name][word_stat_his_collection_name].insert_one(data.dict())
    return data.id


async def get_word_stat_his_list(conn: AsyncIOMotorClient, query: Optional[dict], page: int, limit: int):
    result = conn[database_name][word_stat_his_collection_name].aggregate([
        {'$project': {'result': 0}},  # result 内容较大
        {'$match': query},
        {'$lookup': {'from': file_collection_name, 'localField': 'file_id', 'foreignField': 'id', 'as': 'file'}},
        {'$unwind': '$file'},
        {'$sort': {'createdAt': -1}},
        {'$skip': (page - 1) * limit},
        {'$limit': limit}
    ])
    return [WordStatListModel(**x) async for x in result]


async def count_word_stat_his_by_query(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = await conn[database_name][word_stat_his_collection_name].count_documents(query)
    return result


async def update_word_stat_his(conn: AsyncIOMotorClient, query: Optional[dict], item: dict):
    conn[database_name][word_stat_his_collection_name].update_one(query, item)
    return True


async def delete_word_stat_his(conn: AsyncIOMotorClient, query: Optional[dict]):
    conn[database_name][word_stat_his_collection_name].delete_many(query)
    return True
