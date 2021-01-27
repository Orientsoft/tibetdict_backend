from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from starlette.status import HTTP_400_BAD_REQUEST
from model.user import User
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database

from model.word_dict import WordStatDictCreateModel, WordStatDictUpdateModel, DictTypeEnum
from crud.word_dict import create_word_stat_dict, get_word_stat_dict_list, get_word_stat_dict, update_word_stat_dict, \
    count_word_stat_dict_by_query, batch_create_word_stat_dict

router = APIRouter()


@router.post('/word/stat/dict', tags=['admin'], name='管理员添加词库')
async def add_dict(
        word: str = Body(...), nature: str = Body(...), type: DictTypeEnum = Body(...),
        name: str = Body(None),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    if 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40005')
    db_w = await get_word_stat_dict(db, {'word': word, 'nature': nature, 'type': type})
    if db_w:
        raise HTTPException(HTTP_400_BAD_REQUEST, '内容重复')
    await create_word_stat_dict(db, WordStatDictCreateModel(
        word=word,
        nature=nature,
        type=type,
        is_exclude=False,
        name=name
    ))
    return {'msg': '2001'}


@router.get('/word/stat/dict', tags=['admin'], name='管理员获取词库')
async def get_dict(type: DictTypeEnum, search: str = None, page: int = 1, limit: int = 20, is_exclude: bool = None,
                   user: User = Depends(get_current_user_authorizer(required=True)),
                   db: AsyncIOMotorClient = Depends(get_database)
                   ):
    if 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40005')
    query_obj = {'type': type}
    if search is not None:
        query_obj['$or'] = [{'word': {'$regex': search}}, {'nature': {'$regex': search}}]
    if is_exclude is not None:
        query_obj['is_exclude'] = is_exclude
    data = await get_word_stat_dict_list(db, query_obj, page, limit)
    total = await count_word_stat_dict_by_query(db, query_obj)
    return {'data': data, 'total': total}


@router.patch('/word/stat/dict', tags=['admin'], name='管理员修改词库')
async def patch_dict(data: WordStatDictUpdateModel = Body(...),
                     user: User = Depends(get_current_user_authorizer(required=True)),
                     db: AsyncIOMotorClient = Depends(get_database)
                     ):
    if 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40005')
    await update_word_stat_dict(db, {'id': data.id}, {'$set': data.dict(exclude_none=True)})
    return {'msg': '2001'}


@router.post('/word/stat/dict/batch', tags=['admin'], name='管理员批量导入词库')
async def batch_add(file: UploadFile = File(...), type: DictTypeEnum = Body(..., embed=True),
                    user: User = Depends(get_current_user_authorizer(required=True)),
                    db: AsyncIOMotorClient = Depends(get_database)
                    ):
    if 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '40005')
    attr = file.filename.rsplit('.')[-1]
    if attr not in ['txt']:
        raise HTTPException(status_code=400, detail='100141')
    content = file.file.read().decode('utf-8')
    # content = content.replace(u'༌', u'་')
    need_insert = []
    for line in content.splitlines():
        temp = line.split('\t')
        item = dict(zip(['word', 'nature', 'name'], temp))
        word = item.get('word')
        nature = item.get('nature')
        name = item.get('name')
        if not word or not nature:
            continue
        count = await count_word_stat_dict_by_query(db, {'word': word, 'nature': nature, 'type': type})
        if count:
            continue
        data = WordStatDictCreateModel(
            word=word,
            nature=nature,
            type=type,
            is_exclude=False,
            name=name
        )
        need_insert.append(data.dict())
    await batch_create_word_stat_dict(db, need_insert)
    return {'msg': '2001'}
