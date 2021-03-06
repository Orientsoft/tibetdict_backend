from fastapi import APIRouter, Body, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List
from collections import Counter
from fastapi_plugins import depends_redis
from aioredis import Redis
from datetime import datetime
from config import timezone, max_limit, API_KEY, ES_INDEX,EXCLUED_WORD
from model.user import User
from model.work_history import WorkHistoryCreateModel, WorkTypeEnum
from model.self_dict import SelfDictCreateModel
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database
from common.upload import MinioUploadPrivate
from crud.file import get_file, update_file, batch_update_file
from crud.work_history import create_work_history, get_work_history_list, count_work_history_by_query, \
    get_work_history, get_work_history_result_sum, update_work_history, delete_work_history, \
    get_work_history_without_limit
from crud.self_dict import count_self_dict_by_query, get_self_dict_list, delete_self_dict, create_self_dict
from crud.word_dict import get_word_stat_dict_list, count_word_stat_dict_by_query
from common.worker import celery_app
from common.utils import colouration
import re
import os
import string

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
        db_file = await get_file(db, {'id': file_id})
        if not db_file:
            continue
        # 历史记录不再计算
        db_his = await get_work_history(db, {'file_id': file_id, 'work_type': work_type})
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
            parsed=None,
            o_hash=db_file.o_hash,
            p_hash=None,
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
    if len(ids) == 0:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40015')
    db_his_data = await get_work_history_list(db, {'id': {'$in': ids}, 'user_id': user.id}, 1, len(ids))
    result = {
        'status': True
    }
    for item in db_his_data:
        if item.o_status == 0:
            result['status'] = False
    return result


@router.post('/work/result', tags=['work'], name='统计结果--词频统计')
async def work_result(ids: List[str] = Body(..., embed=True),
                      user: User = Depends(get_current_user_authorizer(required=True)),
                      db: AsyncIOMotorClient = Depends(get_database)):
    db_his = await get_work_history_result_sum(db, {'id': {'$in': ids}, 'work_type': WorkTypeEnum.stat.value})
    temp_obj = {}
    for r in db_his:
        # r['word'].endswith('点') 加上点
        if not r['word'].endswith('་'):
            r['word'] = f"{r['word']}་"
        temp_obj[r['word']] = r['total']
    returnArr = []
    if not temp_obj:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40015')
    # 计算颜色
    color_result = colouration(temp_obj)  # {829:0,100:1}
    for item in db_his:
        # item['word'].endswith('点') 加上点
        if not item['word'].endswith('་'):
            item['word'] = f"{item['word']}་"
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
    # if db_his.user_id != user.id or 0 not in user.role:
    #     raise HTTPException(HTTP_400_BAD_REQUEST, '40005')
    m = MinioUploadPrivate()
    content = m.get_object(f'result/origin/{db_his.user_id}/{db_his.id}.txt')
    returnObj = {
        'id': db_his.id,
        'file_name': db_his.file_name,
        'content': content.decode('utf-8'),
        'result': db_his.o_result,
    }
    return returnObj


@router.post('/work/new/result', tags=['work'], name='统计结果--新词发现')
async def work_new_result(ids: List[str] = Body(..., embed=True), page: int = Body(...), limit: int = Body(...),
                          search: str = Body(None),
                          user: User = Depends(get_current_user_authorizer(required=True)),
                          db: AsyncIOMotorClient = Depends(get_database)):
    query_obj = {'work_history_id': {'$in': ids}, 'user_id': user.id}
    if search is not None:
        if not search.endswith('་'):
            search = f'{search}་'
        search = re.compile(re.escape(search))
        query_obj['$or'] = [{'word': {'$regex': search}}]
    db_self_dict = await get_self_dict_list(db, query_obj, page, limit)
    count = await count_self_dict_by_query(db, query_obj)
    # get work_history_id with file_id
    work_file_info = {}  # key:work_history_id,value:file_id
    work_data = await get_work_history_list(db, {'id': {'$in': ids}}, 1, len(ids))
    for w in work_data:
        work_file_info[w.id] = w.file_id
    returnData = []
    for item in db_self_dict:
        temp = item.dict()
        # queryObj = {"bool": {
        #     "must": [
        #         {"match_phrase": {"content": item.word}},
        #         {"term": {"id": work_file_info[item.work_history_id]}},
        #     ]
        # }}
        # es_result = query_es(index=ES_INDEX, queryObj=queryObj)
        # temp['sentence'] = es_result['hits']['hits'][0]['highlight']['content'] if es_result['hits']['total'][
        #     'value'] else []
        temp['sentence'] = []
        returnData.append(temp)
    return {'data': returnData, 'total': count}


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
            exclued_word = EXCLUED_WORD
            for i in string.ascii_letters + string.digits:
                exclued_word.append(i)
            for r in result:
                word = r.get('word')
                if word in exclued_word:
                    continue
                _id = r.get('id')
                temp_data = SelfDictCreateModel(
                    id=_id,
                    word=word,
                    user_id=db_work_history.user_id,
                    work_history_id=work_id,
                )
                try:
                    await create_self_dict(db, temp_data)
                except:
                    pass
    else:
        update_obj[_status_key] = 2
    print(update_obj)
    await update_work_history(db, {'id': work_id}, {'$set': update_obj})
    return {}


@router.get('/poscode', tags=['work'], name='词性码表')
async def get_pos_code():
    from poscode import data

    return {'data': data}


@router.post('/work/result/export', tags=['work'], name='词频统计导出')
async def post_work_result_export(
        color: List[int] = Body(...), ids: List[str] = Body(...),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    # data_result = await get_work_history_without_limit(conn=db, query={'id': {'$in': ids}})
    # word_result = {}
    # # 拼装词目为键，值为{'count': int, 'nature': str}的字典，重复词目频率相加
    # for x in data_result:
    #     for y in x.o_result:
    #         # 筛选颜色
    #         if y['color'] not in color:
    #             continue
    #         if y['word'] not in word_result:
    #             word_result[y['word']] = {'count': y['count'], 'nature': y['nature']}
    #         else:
    #             word_result[y['word']] = {'count': word_result[y['word']]['count'] + y['count'], 'nature': y['nature']}
    # words = []
    # for key, value in word_result.items():
    #     if not key.endswith('་'):
    #         key = f"{key}་"
    #     words.append(f'{key}, {value["count"]}, {value["nature"]}\n')
    # if not word_result:
    #     words.append('')
    # else:
    #     # 按照频率排序
    #     words.sort(key=lambda x: int(x.split(', ')[1]), reverse=True)

    db_his = await get_work_history_result_sum(db, {'id': {'$in': ids}, 'work_type': WorkTypeEnum.stat.value})
    temp_obj = {}
    for r in db_his:
        # r['word'].endswith('点') 加上点
        if not r['word'].endswith('་'):
            r['word'] = f"{r['word']}་"
        temp_obj[r['word']] = r['total']
    words = []
    if not temp_obj:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40015')
    # 计算颜色
    color_result = colouration(temp_obj)  # {829:0,100:1}
    for item in db_his:
        # item['word'].endswith('点') 加上点
        if not item['word'].endswith('་'):
            item['word'] = f"{item['word']}་"
        item['color'] = color_result.get(item['total'])
        if item['color'] in color:
            words.append(f"{item['word']}, {item['total']}, {item['nature']}\n")
    if not os.path.exists('temp'):
        os.mkdir('temp')
    file_path = f'temp/stat-word-{datetime.now(tz=timezone).isoformat()[:10]}.txt'
    with open(file_path, 'w+', encoding='utf-8') as f:
        f.writelines(words)
    headers = {'content-type': 'text/plain'}
    return FileResponse(file_path, headers=headers,
                        filename=f'stat-word-{datetime.now(tz=timezone).isoformat()[:10]}.txt')


def by_index(t):
    return (t['ind'])


@router.post('/word/sort', tags=['work'], name='藏语排序')
async def word_sort(content: List = Body(..., embed=True),
                    user: User = Depends(get_current_user_authorizer()),
                    db: AsyncIOMotorClient = Depends(get_database)):
    count = await count_word_stat_dict_by_query(db, {'type': 'word'})
    word_index_data = await get_word_stat_dict_list(db, {'type': 'word'}, 1, count)
    index_obj = {}
    for w in word_index_data:
        index_obj[w.word] = w.nature.zfill(10)

    result = []
    fail_result = []
    # 去重
    content = list(set(content))
    for word in content:
        if not word:
            continue
        word = word.strip()
        single_words = word.split('་')
        temp_index = []
        for s in single_words:
            if not s:
                continue
            ind = index_obj.get(s, None)
            temp_index.append(ind)
        temp_obj = {'ind': temp_index, 'word': word}
        if None in temp_index:
            fail_result.append(temp_obj)
        else:
            result.append(temp_obj)
    result = sorted(result, key=by_index)
    return {
        'success': list(map(lambda x: x['word'], result)),
        'fail': list(map(lambda x: x['word'], fail_result))
    }
