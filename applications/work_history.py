from fastapi import APIRouter, Body, Depends, HTTPException, BackgroundTasks
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
from common.unit_word import UnitStat

from crud.file import get_file, update_file
from crud.work_history import create_work_history, get_work_history_list, count_work_history_by_query, \
    get_work_history, get_work_history_result_sum, update_work_history
from crud.self_dict import batch_create_self_dict, count_self_dict_by_query, get_work_new_word_result
from crud.word_dict import get_dict

from common.word_count import WordCount

router = APIRouter()


@router.post('/work', tags=['work'], name='用户根据文件id开始任务')
async def add_work_history(background_tasks: BackgroundTasks, file_ids: List[str] = Body(...),
                           work_type: WorkTypeEnum = Body(...),
                           user: User = Depends(get_current_user_authorizer(required=True)),
                           db: AsyncIOMotorClient = Depends(get_database)):
    if len(file_ids) > max_limit:
        raise HTTPException(HTTP_400_BAD_REQUEST, '超过限制')
    resp_data = []
    # word_pool  todo cache
    # word_pool = await get_dict(db, {'type': 'stat', 'is_exclude': False})
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
        background_tasks.add_task(back_calc_parsed_result, db, data.id)
        # background_tasks.add_task(back_calc_origin_result, db, data.id, word_pool)
    return {'data': resp_data}


@router.get('/work', tags=['work'], name='历史记录')
async def history_stat(work_type: WorkTypeEnum, user_id: str = None, file_name: str = None, p_status: int = None,
                       o_status: int = None,
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
    if p_status is not None:
        query_obj['p_status'] = p_status
    if o_status is not None:
        query_obj['o_status'] = o_status
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
    if db_his.p_status != 1 or not db_his.p_result:
        raise HTTPException(HTTP_400_BAD_REQUEST, '文档无法审阅')
    if db_his.user_id != user.id or 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '权限不足')
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
async def work_new_result(ids: List[str] = Body(..., embed=True),
                          user: User = Depends(get_current_user_authorizer(required=True)),
                          db: AsyncIOMotorClient = Depends(get_database)):
    db_self_dict = await get_work_new_word_result(db, {'work_history_id': {'$in': ids}, 'user_id': user.id})
    return db_self_dict


async def back_calc_parsed_result(db: AsyncIOMotorClient, work_id: str):
    data = await get_work_history(db, {'id': work_id})
    m = MinioUploadPrivate()
    w = WordCount(db)
    # 修改file.last_stat, file.last_new
    now = datetime.now(tz=timezone).isoformat()
    if data.work_type == WorkTypeEnum.stat:
        p_result, p_context = await w.word_count(_id=data.id)
        update_obj = {}
        # parsed 结果
        if p_result is not None:
            update_obj['p_status'] = 1
            update_obj['p_result'] = p_result
            m.commit(p_context.encode('utf-8'), f'result/parsed/{data.user_id}/{data.id}.txt')
        else:
            update_obj['p_status'] = 2
        await update_work_history(db, {'id': data.id}, {'$set': update_obj})
        await update_file(db, {'id': data.file_id}, {'$set': {'last_stat': now}})
    elif data.work_type == WorkTypeEnum.new:
        result = []  # 新词发现算法结果
        update_obj = {}
        if result is not None:
            update_obj['p_status'] = 1
            update_obj['p_result'] = result
            add_self_dict_data = []
            for r in result:
                word = r.get('word')
                nature = r.get('nature', None),
                context = r.get('context', None),
                count = await count_self_dict_by_query(db, {'word': word, 'context': context, 'user_id': data.user_id,
                                                            'is_check': True})
                if count > 0:
                    continue
                temp_data = SelfDictCreateModel(
                    word=word,
                    nature=nature,
                    context=context,
                    user_id=data.user_id,
                    word_history_id=data.id,
                )
                add_self_dict_data.append(temp_data.dict())
            await batch_create_self_dict(db, add_self_dict_data)
        else:
            update_obj['p_status'] = 2
        await update_work_history(db, {'id': data.id}, {'$set': update_obj})
        await update_file(db, {'id': data.file_id}, {'$set': {'last_new': now}})


async def back_calc_origin_result(db: AsyncIOMotorClient, work_id: str, word_pool: List):
    data = await get_work_history(db, {'id': work_id})
    m = MinioUploadPrivate()
    origin = m.get_object(data.origin)
    u = UnitStat(word_pool)
    now = datetime.now(tz=timezone).isoformat()
    if data.work_type == WorkTypeEnum.stat:
        update_obj = {}
        # origin 结果
        o_result, tmp_text = u.run(origin.decode('utf-8'))
        if o_result is not None:
            update_obj['o_status'] = 1
            update_obj['o_result'] = o_result
            m.commit(tmp_text.encode('utf-8'), f'result/origin/{data.user_id}/{data.id}.txt')
        else:
            update_obj['o_status'] = 2
        await update_work_history(db, {'id': data.id}, {'$set': update_obj})
        await update_file(db, {'id': data.file_id}, {'$set': {'last_stat': now}})
    elif data.work_type == WorkTypeEnum.new:
        pass
