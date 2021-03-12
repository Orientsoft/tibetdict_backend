from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List

from model.user import User
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database

from model.self_dict import SelfDictCreateModel, SelfDictUpdateModel
from crud.self_dict import create_self_dict, get_self_dict, get_self_dict_without_limit, count_self_dict_by_query, \
    update_self_dict, delete_self_dict, get_self_dict_list_by_query_with_filename
from datetime import datetime
from config import timezone
import re
import os

router = APIRouter()


@router.post('/self/dict', tags=['自有词库'], name='用户添加自有词库')
async def add_dict(
        word: str = Body(..., embed=True),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    db_w = await get_self_dict(db, {'word': word, 'user_id': user.id})
    if db_w:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40013')
    await create_self_dict(db, SelfDictCreateModel(
        word=word,
        user_id=user.id,
        is_check=False
    ))
    return {'msg': '2001'}


@router.get('/self/dict', tags=['自有词库', 'admin'], name='用户获取自有词库')
async def get_dict(user_id: str = None, search: str = None, page: int = 1, limit: int = 20, is_check: bool = None,
                   user: User = Depends(get_current_user_authorizer(required=True)),
                   db: AsyncIOMotorClient = Depends(get_database)
                   ):
    # 管理员可查看其他人
    if 0 in user.role:
        u_id = user_id or user.id
    else:
        u_id = user.id
    query_obj = {'user_id': u_id}
    if search is not None:
        search = re.compile(re.escape(search))
        query_obj['$or'] = [{'word': {'$regex': search}}]
    if is_check is not None:
        query_obj['is_check'] = is_check
    data = await get_self_dict_list_by_query_with_filename(db, query_obj, page, limit)
    total = await count_self_dict_by_query(db, query_obj)
    return {'data': data, 'total': total}


@router.patch('/self/dict', tags=['自有词库'], name='用户修改自有词库')
async def patch_dict(data: SelfDictUpdateModel = Body(...),
                     user: User = Depends(get_current_user_authorizer(required=True)),
                     db: AsyncIOMotorClient = Depends(get_database)
                     ):
    await update_self_dict(db, {'id': data.id, 'user_id': user.id}, {'$set': data.dict(exclude_none=True)})
    return {'msg': '2001'}


@router.patch('/self/dict/operator', tags=['自有词库'], name="用户自有词库(删除:'1'或校验:'2')")
async def batch_operator(ids: List[str] = Body(...), operator: str = Body(...),
                         user: User = Depends(get_current_user_authorizer(required=True)),
                         db: AsyncIOMotorClient = Depends(get_database)
                         ):
    if operator == '1':
        # 删除
        await delete_self_dict(db, {'id': {'$in': ids}, 'user_id': user.id})
    elif operator == '2':
        # 校验
        await update_self_dict(db, {'id': {'$in': ids}, 'user_id': user.id}, {'$set': {'is_check': True}})
    else:
        pass
    return {'msg': '2001'}


@router.post('/self/dict/export', tags=['自有词库'], name='新词发现导出')
async def post_self_dict_export(
        ids: List[str] = Body(..., embed=True),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    data_dict = await get_self_dict_without_limit(conn=db, query={'work_history_id': {'$in': ids}, 'is_check': True})
    if not os.path.exists('temp'):
        os.mkdir('temp')
    file_path = f'temp/new-word-{datetime.now(tz=timezone).isoformat()[:10]}.txt'
    words = []
    for x in data_dict:
        words.append(x.word + '\n')
    if not words:
        words.append('')
    with open(file_path, 'w+', encoding='utf-8') as f:
        f.writelines(words)
    headers = {'content-type': 'text/plain'}
    return FileResponse(file_path, headers=headers,
                        filename=f'new-word-{datetime.now(tz=timezone).isoformat()[:10]}.txt')
