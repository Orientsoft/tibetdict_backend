from common.mongodb import AsyncIOMotorClient
from typing import Optional
from model.file import FileInDB, FileCreateModel
from config import database_name, file_collection_name


async def get_file(conn: AsyncIOMotorClient, query: Optional[dict]) -> FileInDB:
    row = await conn[database_name][file_collection_name].find_one(query, {'file_content': 0})
    return FileInDB(**row) if row else None


async def get_file_content(conn: AsyncIOMotorClient, query: Optional[dict]) -> FileInDB:
    row = await conn[database_name][file_collection_name].find_one(query)
    return FileInDB(**row) if row else None


async def create_file(conn: AsyncIOMotorClient, data: FileCreateModel) -> str:
    conn[database_name][file_collection_name].insert_one(data.dict())
    return data.id


async def get_file_list(conn: AsyncIOMotorClient, query: Optional[dict], page: int, limit: int):
    result = conn[database_name][file_collection_name].find(query, {'file_content': 0}).skip((page - 1) * limit).limit(
        limit)
    return [FileInDB(**x) async for x in result]


async def count_file_by_query(conn: AsyncIOMotorClient, query: Optional[dict]):
    result = await conn[database_name][file_collection_name].count_documents(query)
    return result


async def update_file(conn: AsyncIOMotorClient, query: Optional[dict], item: dict):
    conn[database_name][file_collection_name].update_one(query, item)
    return True


async def delete_file(conn: AsyncIOMotorClient, query: Optional[dict]):
    conn[database_name][file_collection_name].delete_many(query)
    return True
