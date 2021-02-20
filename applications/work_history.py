from fastapi import APIRouter, Body, Depends, HTTPException, BackgroundTasks
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List
import re
from collections import Counter
from loguru import logger
from fastapi_plugins import depends_redis
from aioredis import Redis
from datetime import datetime
from config import timezone, max_limit, WORD_POOL_KEY, API_KEY
from model.user import User
from model.work_history import WorkHistoryCreateModel, WorkTypeEnum
from model.self_dict import SelfDictCreateModel
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database
from common.upload import MinioUploadPrivate
from common.unit_word import UnitStat

from crud.file import get_file, update_file, batch_update_file
from crud.work_history import create_work_history, get_work_history_list, count_work_history_by_query, \
    get_work_history, get_work_history_result_sum, update_work_history, delete_work_history
from crud.self_dict import batch_create_self_dict, count_self_dict_by_query, get_work_new_word_result, \
    get_self_dict_list, delete_self_dict
from crud.word_dict import get_dict
from common.cache import set_cache, get_cache, word_pool_check_cache
from common.worker import celery_app

from common.word_count import WordCount

router = APIRouter()


@router.post('/work', tags=['work'], name='用户根据文件id开始任务')
async def add_work_history(file_ids: List[str] = Body(...),
                           work_type: WorkTypeEnum = Body(...),
                           user: User = Depends(get_current_user_authorizer(required=True)),
                           db: AsyncIOMotorClient = Depends(get_database), rd: Redis = Depends(depends_redis)):
    if len(file_ids) > max_limit:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40016')
    resp_data = []
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
            p_status=0,  # 0：统计中，1：统计成功，2：统计失败
            o_status=0  # 0：统计中，1：统计成功，2：统计失败
        )
        await create_work_history(db, data)
        resp_data.append({
            'work_id': data.id,
            'file_id': data.file_id,
            'file_name': data.file_name
        })
        # 更新文件库状态
        now = datetime.now(tz=timezone).isoformat()
        if data.work_type == WorkTypeEnum.stat:
            await update_file(db, {'id': data.file_id}, {'$set': {'last_stat': now}})
        elif data.work_type == WorkTypeEnum.new:
            await update_file(db, {'id': data.file_id}, {'$set': {'last_new': now}})
        # 添加后端任务
        celery_app.send_task('worker:origin_calc', args=[data.id], queue='tibetan',
                             routing_key='tibetan')
        celery_app.send_task('worker:parsed_calc', args=[data.id], queue='tibetan',
                             routing_key='tibetan')
    return {'data': resp_data}


@router.get('/work', tags=['work'], name='历史记录')
async def history_stat(work_type: WorkTypeEnum, user_id: str = None, file_name: str = None, p_status: int = None,
                       o_status: int = None,
                       page: int = 1, limit: int = 20,
                       user: User = Depends(get_current_user_authorizer(required=True)),
                       db: AsyncIOMotorClient = Depends(get_database)):
    if 0 in user.role:
        u_id = user_id or user.id
    else:
        u_id = user.id
    query_obj = {'user_id': u_id, 'work_type': work_type}
    if file_name is not None:
        file_name = re.compile(re.escape(file_name))
        query_obj['file_name'] = {'$regex': file_name}
    if p_status is not None:
        query_obj['p_status'] = p_status
    if o_status is not None:
        query_obj['o_status'] = o_status
    data = await get_work_history_list(db, query_obj, page, limit)
    total = await count_work_history_by_query(db, query_obj)
    return {'data': data, 'total': total}


@router.delete('/work', tags=['work'], name='删除历史记录')
async def delete_work(ids: List[str] = Body(..., embed=True),
                      user: User = Depends(get_current_user_authorizer(required=True)),
                      db: AsyncIOMotorClient = Depends(get_database)):
    db_work = await get_work_history_list(db, {'id': {'$in': ids}}, 1, 20)
    file_id = [r.file_id for r in db_work]
    # 删除self_dict
    await delete_self_dict(db, {'work_history_id': {'$in': ids}, 'user_id': user.id})
    # 删除work_history
    await delete_work_history(db, {'id': {'$in': ids}, 'user_id': user.id})
    # todo 删除对象存储中内容
    await batch_update_file(db, {'id': {'$in': file_id}}, {'$set': {'last_new': None, 'last_stat': None}})
    return {'msg': '2002'}


@router.post('/work/status', tags=['work'], name='计算结果')
async def work_status(ids: List[str] = Body(..., embed=True),
                      user: User = Depends(get_current_user_authorizer(required=True)),
                      db: AsyncIOMotorClient = Depends(get_database)):
    db_his_data = await get_work_history_list(db, {'id': {'$in': ids}, 'user_id': user.id}, 1, len(ids))
    result = {
        'o_status': True,
        'p_status': True
    }
    for item in db_his_data:
        if item.p_status == 0:
            result['p_status'] = False
        if item.o_status == 0:
            result['o_status'] = False
    return result


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
        raise HTTPException(HTTP_400_BAD_REQUEST, '40015')
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
    # if db_his.p_status != 1 or not db_his.p_result:
    #     raise HTTPException(HTTP_400_BAD_REQUEST, '文档无法审阅')
    if db_his.user_id != user.id or 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40005')
    m = MinioUploadPrivate()
    o_content = m.get_object(f'result/origin/{db_his.user_id}/{db_his.id}.txt')
    p_content = m.get_object(f'result/parsed/{db_his.user_id}/{db_his.id}.txt')
    returnObj = {
        'id': db_his.id,
        'file_name': db_his.file_name,
        'p_content': p_content.decode('utf-8'),
        'o_content': o_content.decode('utf-8'),
        'p_result': db_his.p_result,
        'o_result': db_his.o_result
    }
    return returnObj


@router.post('/work/new/result', tags=['work'], name='统计结果--新词发现')
async def work_new_result(ids: List[str] = Body(..., embed=True), page: int = Body(...), limit: int = Body(...),
                          search: str = Body(None),
                          user: User = Depends(get_current_user_authorizer(required=True)),
                          db: AsyncIOMotorClient = Depends(get_database)):
    # db_self_dict = await get_work_new_word_result(db, {'work_history_id': {'$in': ids}, 'user_id': user.id})
    query_obj = {'work_history_id': {'$in': ids}, 'user_id': user.id}
    if search is not None:
        search = re.compile(re.escape(search))
        query_obj['$or'] = [{'word': {'$regex': search}}, {'nature': {'$regex': search}}]
    db_self_dict = await get_self_dict_list(db, query_obj, page, limit)
    count = await count_self_dict_by_query(db, query_obj)
    return {'data': db_self_dict, 'total': count}


@router.post('/work/notify', tags=['work'], name='算法回调接口')
async def work_new_result(work_id: str = Body(...), result: List = Body(...), context: str = Body(...),
                          is_save_to_dict: bool = Body(...), calc_type: str = Body(...), key: str = Body(...),
                          db: AsyncIOMotorClient = Depends(get_database)):
    if key != API_KEY:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40009')
    db_work_history = await get_work_history(db, {'id': work_id})
    if calc_type == 'origin':
        _status_key = 'o_status'
        _result_key = 'o_result'
    elif calc_type == 'parsed':
        _status_key = 'p_status'
        _result_key = 'p_result'
    else:
        return {}
    m = MinioUploadPrivate()
    update_obj = {}
    if result is not None:
        update_obj[_status_key] = 1
        update_obj[_result_key] = list(result)
        m.commit(context.encode('utf-8'), f'result/{calc_type}/{db_work_history.user_id}/{work_id}.txt')
        if is_save_to_dict:
            add_self_dict_data = []
            for r in result:
                word = r.get('word')
                nature = r.get('nature', None)
                context = r.get('context', None)
                _id = r.get('id')
                count = await count_self_dict_by_query(db, {'word': word, 'context': context,
                                                            'user_id': db_work_history.user_id,
                                                            'is_check': True})
                if count > 0:
                    continue
                temp_data = SelfDictCreateModel(
                    id=_id,
                    word=word,
                    nature=nature,
                    context=context,
                    user_id=db_work_history.user_id,
                    work_history_id=work_id,
                )
                add_self_dict_data.append(temp_data.dict())
            await batch_create_self_dict(db, add_self_dict_data)
    else:
        update_obj[_status_key] = 2
    print(update_obj)
    await update_work_history(db, {'id': work_id}, {'$set': update_obj})
    return {}
