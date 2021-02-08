from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List

from model.user import User
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database

from model.self_dict import SelfDictCreateModel, SelfDictUpdateModel
from crud.self_dict import create_self_dict, get_self_dict, get_self_dict_list, count_self_dict_by_query, \
    update_self_dict, delete_self_dict, get_self_dict_list_by_query_with_filename

router = APIRouter()


@router.post('/self/dict', tags=['自有词库'], name='用户添加自有词库')
async def add_dict(
        word: str = Body(...), context: str = Body(...), nature: str = Body(None),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    db_w = await get_self_dict(db, {'word': word, 'nature': nature, 'user_id': user.id})
    if db_w:
        raise HTTPException(HTTP_400_BAD_REQUEST, '内容重复')
    await create_self_dict(db, SelfDictCreateModel(
        word=word,
        nature=nature,
        context=context,
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
        query_obj['$or'] = [{'word': {'$regex': search}}, {'nature': {'$regex': search}},
                            {'context': {'$regex': search}}]
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


@router.delete('/self/dict', tags=['自有词库'], name='用户删除自有词库')
async def batch_add(ids: List[str] = Body(...),
                    user: User = Depends(get_current_user_authorizer(required=True)),
                    db: AsyncIOMotorClient = Depends(get_database)
                    ):
    await delete_self_dict(db, {'id': {'$in': ids}, 'user_id': user.id})
    return {'msg': '2001'}
