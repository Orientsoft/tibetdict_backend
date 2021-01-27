from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List
from collections import Counter
from loguru import logger
from datetime import datetime
from config import timezone, max_limit
from model.user import User
from model.work_history import WorkHistoryCreateModel, WorkTypeEnum
from model.self_dict import SelfDictCreateModel
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database
from common.upload import MinioUploadPrivate

from crud.file import get_file, update_file
from crud.work_history import create_work_history, get_work_history_list, count_work_history_by_query, \
    get_work_history, get_work_history_result_sum, update_work_history
from crud.self_dict import batch_create_self_dict, count_self_dict_by_query

from common.word_count import WordCount

router = APIRouter()


@router.post('/work', tags=['work'], name='用户根据文件id开始任务')
async def add_work_history(file_ids: List[str] = Body(...), work_type: WorkTypeEnum = Body(...),
                           user: User = Depends(get_current_user_authorizer(required=True)),
                           db: AsyncIOMotorClient = Depends(get_database)):
    if len(file_ids) > max_limit:
        raise HTTPException(HTTP_400_BAD_REQUEST, '超过限制')
    resp_data = []
    w = WordCount(conn=db)
    for file_id in file_ids:
        db_file = await get_file(db, {'id': file_id, 'user_id': user.id})
        if not db_file:
            continue
        # 历史记录不再计算
        db_his = await get_work_history(db, {'user_id': user.id, 'file_id': file_id, 'work_type': work_type})
        if db_his:
            resp_data.append({'work_id': db_his.id,
                              'file_id': db_his.file_id,
                              'file_name': db_his.file_name})
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
            result = await w.word_count(_id=data.id)
            update_obj = {}
            if result is not None:
                update_obj['status'] = 1
                update_obj['result'] = result
            else:
                update_obj['status'] = 2
            await update_work_history(db, {'id': data.id}, {'$set': update_obj})
            await update_file(db, {'id': file_id}, {'$set': {'last_stat': now}})
        elif work_type == WorkTypeEnum.new:
            # todo 新词发现结果，存储到self_dict（需去重）
            result = []  # 新词发现算法结果
            update_obj = {}
            if result is not None:
                update_obj['status'] = 1
                update_obj['result'] = result
                add_self_dict_data = []
                for r in result:
                    word = r.get('word')
                    nature = r.get('nature', None),
                    context = r.get('context', None),
                    count = await count_self_dict_by_query(db, {'word': word, 'context': context, 'user_id': user.id,
                                                                'is_check': True})
                    if count > 0:
                        continue
                    temp_data = SelfDictCreateModel(
                        word=word,
                        nature=nature,
                        context=context,
                        user_id=user.id,
                        word_history_id=data.id,
                    )
                    add_self_dict_data.append(temp_data.dict())
                await batch_create_self_dict(db, add_self_dict_data)
            else:
                update_obj['status'] = 2
            await update_work_history(db, {'id': data.id}, {'$set': update_obj})
            await update_file(db, {'id': file_id}, {'$set': {'last_new': now}})
        resp_data.append({
            'work_id': data.id,
            'file_id': data.file_id,
            'file_name': data.file_name
        })

    return {'data': resp_data}


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


@router.post('/work/result', tags=['work'], name='统计结果--词频统计')
async def work_result(ids: List[str] = Body(..., embed=True),
                      user: User = Depends(get_current_user_authorizer(required=True)),
                      db: AsyncIOMotorClient = Depends(get_database)):
    db_his = await get_work_history_result_sum(db, {'id': {'$in': ids}, 'user_id': user.id,
                                                    'work_type': WorkTypeEnum.stat.value})
    temp_obj = {}
    for r in db_his:
        temp_obj[r['word']] = r['total']
    returnArr = []
    if not temp_obj:
        raise HTTPException(HTTP_400_BAD_REQUEST, '暂无结果')
    # 计算颜色
    w = WordCount(conn=db)
    color_result = w.colouration(temp_obj)  # {829:0,100:1}
    for item in db_his:
        item['color'] = color_result.get(item['total'])
        returnArr.append(item)
    temp_color = color_result.values()
    return {'data': returnArr, 'chart': Counter(temp_color)}


@router.get('/work/review', tags=['work'], name='文档审阅')
async def work_review(id: str, user: User = Depends(get_current_user_authorizer(required=True)),
                      db: AsyncIOMotorClient = Depends(get_database)):
    # 不过滤result
    db_his = await get_work_history(db, {'id': id}, show_result=True)
    if db_his.status != 1 or not db_his.result:
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


@router.post('/work/new/result', tags=['work'], name='统计结果--新词发现')
async def work_new_result(ids: List[str] = Body(..., embed=True),
                          user: User = Depends(get_current_user_authorizer(required=True)),
                          db: AsyncIOMotorClient = Depends(get_database)):
    pass
