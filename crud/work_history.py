from common.mongodb import AsyncIOMotorClient
from typing import Optional
from model.work_history import WorkHistoryCreateModel, WorkHistoryInDB, WorkHistoryListModel
from config import database_name, work_history_collection_name, file_collection_name


async def get_work_history(conn: AsyncIOMotorClient, query: Optional[dict],
                           show_result: bool = False) -> WorkHistoryInDB:
    if show_result:
        row = await conn[database_name][work_history_collection_name].find_one(query)
    else:
        row = await conn[database_name][work_history_collection_name].find_one(query, {'result': show_result})
    return WorkHistoryInDB(**row) if row else None


async def create_work_history(conn: AsyncIOMotorClient, data: WorkHistoryCreateModel) -> str:
    conn[database_name][work_history_collection_name].insert_one(data.dict())
    return data.id


async def get_work_history_list(conn: AsyncIOMotorClient, query: Optional[dict], page: int, limit: int):
    result = conn[database_name][work_history_collection_name].aggregate([
        {'$project': {'result': 0}},  # result 内容较大
        {'$match': query},
        {'$lookup': {'from': file_collection_name, 'localField': 'file_id', 'foreignField': 'id', 'as': 'file'}},
        {'$unwind': '$file'},
        {'$sort': {'createdAt': -1}},
        {'$skip': (page - 1) * limit},
        {'$limit': limit}
    ])
    return [WorkHistoryListModel(**x) async for x in result]


async def count_work_history_by_query(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = await conn[database_name][work_history_collection_name].count_documents(query)
    return result


async def update_work_history(conn: AsyncIOMotorClient, query: Optional[dict], item: dict):
    conn[database_name][work_history_collection_name].update_one(query, item)
    return True


async def delete_work_history(conn: AsyncIOMotorClient, query: Optional[dict]):
    conn[database_name][work_history_collection_name].delete_many(query)
    return True


async def batch_update_work_history(conn: AsyncIOMotorClient, query: Optional[dict], item: dict):
    conn[database_name][work_history_collection_name].update_many(query, item)
    return True


async def get_work_history_result_sum(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = conn[database_name][work_history_collection_name].aggregate([
        {'$match': query},
        {'$unwind': '$result'},
        {'$group': {'_id': {'word': '$result.word', 'nature': '$result.nature'}, 'total': {'$sum': '$result.count'}}},
        {'$sort': {'total': -1}}
    ])
    return [{
        'word': x['_id']['word'],
        'nature': x['_id']['nature'],
        'total': x['total']
    } async for x in result]

