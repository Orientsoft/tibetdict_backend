from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List
from loguru import logger
from datetime import datetime
from config import timezone, max_limit
from model.user import User
from model.work_history import WorkHistoryCreateModel, WorkTypeEnum
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database
from common.upload import MinioUploadPrivate

from crud.file import get_file, update_file
from crud.work_history import create_work_history, get_work_history_list, count_work_history_by_query, \
    get_work_history, get_work_history_result_sum, update_work_history

from common.word_count import WordCount

router = APIRouter()


@router.post('/work', tags=['work'], name='用户根据文件id开始任务')
async def add_work_history(file_ids: List[str] = Body(...), work_type: WorkTypeEnum = Body(...),
                           user: User = Depends(get_current_user_authorizer(required=True)),
                           db: AsyncIOMotorClient = Depends(get_database)):
    if len(file_ids) > max_limit:
        raise HTTPException(HTTP_400_BAD_REQUEST, '超过限制')
    data_id = []
    w = WordCount(conn=db)
    for file_id in file_ids:
        db_file = await get_file(db, {'id': file_id, 'user_id': user.id})
        if not db_file:
            continue
        db_his = await get_work_history(db, {'user_id': user.id, 'file_id': file_id, 'work_type': work_type})
        if db_his:
            continue
        # 新增work_history
        data = WorkHistoryCreateModel(
            user_id=user.id,
            file_id=file_id,
            file_name=db_file.file_name,
            origin=db_file.origin,
            parsed=db_file.parsed,
            o_hash=db_file.o_hash,
            p_hash=db_file.p_hash,
            work_type=work_type,
            status=0  # 0：统计中，1：统计成功，2：统计失败
        )
        await create_work_history(db, data)
        # 修改file.last_stat, file.last_new
        now = datetime.now(tz=timezone).isoformat()
        if work_type == WorkTypeEnum.stat:
            await update_file(db, {'id': file_id}, {'$set': {'last_stat': now}})
        elif work_type == WorkTypeEnum.new:
            await update_file(db, {'id': file_id}, {'$set': {'last_new': now}})
        data_id.append(data.id)
        result = await w.word_count(_id=data.id)
        update_obj = {}
        if result:
            update_obj['status'] = 1
            update_obj['result'] = result
        else:
            update_obj['status'] = 2
        await update_work_history(db, {'id': data.id}, {'$set': update_obj})
    return {'data': data_id}


@router.get('/work', tags=['work'], name='历史记录')
async def history_stat(work_type: WorkTypeEnum, user_id: str = None, file_name: str = None, status: int = None,
                       page: int = 1, limit: int = 20,
                       user: User = Depends(get_current_user_authorizer(required=True)),
                       db: AsyncIOMotorClient = Depends(get_database)):
    if 0 in user.role:
        u_id = user_id
    else:
        u_id = user.id
    query_obj = {'user_id': u_id, 'work_type': work_type}
    if file_name is not None:
        query_obj['file_name'] = {'$regex': file_name}
    if status is not None:
        query_obj['status'] = status
    data = await get_work_history_list(db, query_obj, page, limit)
    total = await count_work_history_by_query(db, query_obj)
    return {'data': data, 'total': total}


@router.post('/work/result', tags=['work'], name='统计结果')
async def work_result(ids: List[str] = Body(..., embed=True),
                      user: User = Depends(get_current_user_authorizer(required=True)),
                      db: AsyncIOMotorClient = Depends(get_database)):
    db_his = await get_work_history_result_sum(db, {'id': {'$in': ids}, 'user_id': user.id})
    temp_obj = {}
    for r in db_his:
        temp_obj[r['word']] = r['total']
    returnArr = []
    # 计算颜色
    w = WordCount(conn=db)
    color_result = w.colouration(temp_obj)
    for item in db_his:
        item['color'] = color_result.get(item['total'])
        returnArr.append(item)
    return {'data': returnArr}


@router.get('/work/review', tags=['work'], name='文档审阅')
async def work_review(id: str, user: User = Depends(get_current_user_authorizer(required=True)),
                      db: AsyncIOMotorClient = Depends(get_database)):
    # 不过滤result
    db_his = await get_work_history(db, {'id': id}, show_result=True)
    if db_his.status != 2 or not db_his.result:
        raise HTTPException(HTTP_400_BAD_REQUEST, '文档无法审阅')
    if db_his.user_id != user.id or 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '权限不足')
    m = MinioUploadPrivate()
    content = m.get_object(db_his.parsed)
    returnObj = {
        'id': db_his.id,
        'file_name': db_his.file_name,
        'content': content.decode('utf-8'),
        'result': db_his.result
    }
    return returnObj

# @router.post('/worksssssss', tags=['work'], deprecated=True, name='开始任务')
# async def start_stat(ids: List[str] = Body(..., embed=True),
#                      user: User = Depends(get_current_user_authorizer(required=True)),
#                      db: AsyncIOMotorClient = Depends(get_database)):
#     db_data = await get_work_history_list(db, {'user_id': user.id, 'id': {'$in': ids}}, page=1, limit=len(ids))
#     m = MinioUploadPrivate()
#     db_code = await get_word_stat_dict_list(db, {'type': DictTypeEnum.stat, 'is_exclude': False}, page=1, limit=0)
#     need_code = [{'word': item.word, 'nature': item.word} for item in db_code]
#     need_update_ids = []
#     for item in db_data:
#         # todo 任务类型可能不同
#         # TODO 异步调用统计算法 calc_result(content,need_code)
#         # content = m.get_object(item.parsed)
#         need_update_ids.append(item.id)
#     # 统计中
#     await batch_update_work_history(db, {'id': {'$in': need_update_ids}}, {'$set': {'status': 1}})
#     return {'msg': '2002'}
