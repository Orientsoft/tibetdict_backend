from common.mongodb import AsyncIOMotorClient
from typing import Optional, List
from model.self_dict import SelfDictInDB, SelfDictCreateModel, SelfDictWithFilename
from config import database_name, self_dict_collection_name, work_history_collection_name


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


async def get_self_dict_list_by_query_with_filename(conn: AsyncIOMotorClient, query: Optional[dict], page: int,
                                                    limit: int):
    result = conn[database_name][self_dict_collection_name].aggregate([
        {'$match': query},
        {'$lookup': {'from': work_history_collection_name, 'localField': 'work_history_id', 'foreignField': 'id',
                     'as': 'work_history'}},
        {'$unwind': '$work_history'},
        {'$skip': (page - 1) * limit},
        {'$limit': limit}
    ])
    return [SelfDictWithFilename(
        id=x['id'],
        word=x['word'],
        user_id=x['user_id'],
        is_check=x['is_check'],
        createdAt=x['createdAt'],
        updatedAt=x['updatedAt'],
        file_name=x['work_history']['file_name']
    ) async for x in result]


async def count_self_dict_by_query(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = await conn[database_name][self_dict_collection_name].count_documents(query)
    return result


async def update_self_dict(conn: AsyncIOMotorClient, query: Optional[dict], item: dict):
    conn[database_name][self_dict_collection_name].update_many(query, item)
    return True


async def delete_self_dict(conn: AsyncIOMotorClient, query: Optional[dict]):
    conn[database_name][self_dict_collection_name].delete_many(query)
    return True


async def get_work_new_word_result(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = conn[database_name][self_dict_collection_name].aggregate([
        {'$match': query},
        {"$lookup": {'from': work_history_collection_name,
                     'let': {'temp_id': "$work_history_id"},
                     'pipeline': [
                         {'$project': {'file_name': 1, 'file_id': 1, 'id': 1}},
                         {'$match':
                             {'$expr':
                                 {'$and':
                                     [
                                         {'$eq': ["$id", "$$temp_id"]}
                                     ]
                                 }
                             }
                         }
                     ],
                     'as': 'work'}},
        {'$unwind': '$work'},
        {'$project': {'file_name': '$work.file_name', 'file_id': '$work.file_id', 'word': 1,
                      'user_id': 1, 'createdAt': 1, 'is_check': 1, 'work_id': '$work.id', 'id': 1, '_id': 0}},
        {'$sort': {'createdAt': -1}}
    ])
    return [x async for x in result]
