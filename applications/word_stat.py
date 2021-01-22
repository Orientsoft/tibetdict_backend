from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List
from loguru import logger
from model.user import User
from model.word_stat import WordStatCreateModel
from model.word_dict import DictTypeEnum
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database
from common.upload import MinioUploadPrivate

from crud.file import get_file
from crud.word_stat import create_word_stat_his, get_word_stat_his_list, count_word_stat_his_by_query, get_word_stat_his
from crud.word_dict import get_word_stat_dict_list, batch_update_word_stat_dict

router = APIRouter()


@router.post('/word/stat', tags=['词频统计'], name='用户添加词频统计任务')
async def add_word_stat(file_id: str = Body(..., embed=True),
                        user: User = Depends(get_current_user_authorizer(required=True)),
                        db: AsyncIOMotorClient = Depends(get_database)):
    db_file = await get_file(db, {'id': file_id})
    if not db_file:
        raise HTTPException(HTTP_400_BAD_REQUEST, '文件不存在')
    db_his = await get_word_stat_his(db, {'user_id': user.id, 'file_id': file_id})
    if db_his:
        raise HTTPException(HTTP_400_BAD_REQUEST, '任务已存在')
    await create_word_stat_his(db, WordStatCreateModel(
        user_id=user.id,
        file_id=file_id,
        file_name=db_file.file_name,
        parsed=db_file.parsed,
        o_hash=db_file.o_hash,
        p_hash=db_file.p_hash,
        status=0  # 未统计
    ))
    return {'msg': '2002'}


@router.get('/word/stat', tags=['词频统计'], name='历史记录')
async def history_stat(file_name: str = None, status: int = None, page: int = 1, limit: int = 20,
                       user: User = Depends(get_current_user_authorizer(required=True)),
                       db: AsyncIOMotorClient = Depends(get_database)):
    query_obj = {}
    if file_name is not None:
        query_obj['file_name'] = {'$regex': file_name}
    if status is not None:
        query_obj['status'] = status
    data = await get_word_stat_his_list(db, query_obj, page, limit)
    total = await count_word_stat_his_by_query(db, query_obj)
    return {'data': data, 'total': total}


@router.post('/word/stat/start', tags=['词频统计'], name='开始词频统计')
async def start_stat(ids: List[str] = Body(..., embed=True),
                     user: User = Depends(get_current_user_authorizer(required=True)),
                     db: AsyncIOMotorClient = Depends(get_database)):
    db_data = await get_word_stat_his_list(db, {'user_id': user.id, 'id': {'$in': ids}}, page=1, limit=len(ids))
    m = MinioUploadPrivate()
    db_code = await get_word_stat_dict_list(db, {'type': DictTypeEnum.stat, 'is_exclude': False}, page=1, limit=0)
    need_code = [{'word': item.word, 'nature': item.word} for item in db_code]
    need_update_ids = []
    for item in db_data:
        # TODO 异步调用统计算法 calc_result(content,need_code)
        # content = m.get_object(item.parsed)
        need_update_ids.append(item.id)
    # 统计中
    await batch_update_word_stat_dict(db, {'id': {'$in': need_update_ids}}, {'$set': {'status': 1}})
    return {'msg': '2002'}


@router.post('/word/stat/result', tags=['词频统计'], name='统计结果')
async def add_word_stat(ids: List[str] = Body(..., embed=True),
                        user: User = Depends(get_current_user_authorizer(required=True)),
                        db: AsyncIOMotorClient = Depends(get_database)):
    pass


@router.get('/word/stat/review', tags=['词频统计'], name='文档审阅')
async def add_word_stat(id: str,
                        user: User = Depends(get_current_user_authorizer(required=True)),
                        db: AsyncIOMotorClient = Depends(get_database)):
    # 不过滤result
    db_his = await get_word_stat_his(db, {'id': id}, show_result=True)
    if db_his.status != 2 or not db_his.result:
        raise HTTPException(HTTP_400_BAD_REQUEST, '文档无法审阅')
    m = MinioUploadPrivate()
    content = m.get_object(db_his.parsed)
    returnObj = {
        'id': db_his.id,
        'file_name': db_his.file_name,
        'content': content.decode('utf-8'),
        'result': db_his.result
    }
    return returnObj
