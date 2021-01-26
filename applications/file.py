from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from starlette.status import HTTP_400_BAD_REQUEST
from io import BytesIO
from typing import List
from loguru import logger
from copy import deepcopy
import docx
import os, subprocess
import platform
import shutil

from model.user import User
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database

from crud.file import create_file, get_file_list, count_file_by_query, delete_file, update_file, get_file
from crud.work_history import count_work_history_by_query
from model.file import FileCreateModel
from common.upload import MinioUploadPrivate
from common.common import contenttomd5, tokenize_words

router = APIRouter()
_platform = platform.system().lower()


@router.post('/file', tags=['file'], name='文档上传')
async def upload_file(file: UploadFile = File(...), user: User = Depends(get_current_user_authorizer()),
                      db: AsyncIOMotorClient = Depends(get_database)):
    attr = file.filename.rsplit('.')[-1]
    if attr not in ['txt', 'docx', 'doc']:
        raise HTTPException(status_code=400, detail='100141')
    data = FileCreateModel(
        user_id=user.id,
        file_name=file.filename,
    )
    '''
    1.txt 本地存储，
    2.docx python-docx转换
    3.doc 不同平台不同方法，windows暂不支持
    '''
    origin_content = None
    if attr == 'txt':
        origin_content = file.file.read().decode('utf-8')
    elif attr in ['docx', 'doc']:
        # 临时目录 存储到本地
        if not os.path.exists('temp'):
            os.mkdir('temp')
        origin_temp_file_name = f"temp/{data.id}.{attr}"
        with open(origin_temp_file_name, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if attr == 'docx':
            tmp = []
            doc_file = docx.Document(origin_temp_file_name)
            for para in doc_file.paragraphs:
                tmp.append(para.text)
            origin_content = '\n'.join(tmp)
        elif attr == 'doc':
            saveas_txt_file_name = f"temp/{data.id}.txt"
            if _platform == 'linux':
                cmd = f"catdoc {origin_temp_file_name} > {saveas_txt_file_name}"
                os.system(cmd)
            elif _platform == 'darwin':
                cmd = f"textutil -convert txt {origin_temp_file_name} -output {saveas_txt_file_name}"
                os.system(cmd)
            else:
                raise HTTPException(status_code=400, detail='100141')
            with open(saveas_txt_file_name, 'r') as f:
                origin_content = f.read()
            os.remove(saveas_txt_file_name)
        # 删除临时文件
        os.remove(origin_temp_file_name)

    m = MinioUploadPrivate()

    # 原始文件
    data.origin = f'origin/{user.id}/{data.id}.txt'
    data.parsed = f'parsed/{user.id}/{data.id}.txt'
    # 上传原始文件
    m.commit(origin_content.encode('utf-8'), data.origin)
    # 已分词
    if len(origin_content[:500].split(' ')) <= 5:
        logger.info('未分词文档，自动分词中')
        parsed_content = tokenize_words(origin_content)
        # logger.info(parsed_content)
        data.is_check = True
    else:
        parsed_content = origin_content
    # 提交分词结果
    m.commit(parsed_content.encode('utf-8'), data.parsed)
    # 文件指纹
    data.p_hash = contenttomd5(parsed_content.encode('utf-8'))
    data.o_hash = contenttomd5(origin_content.encode('utf-8'))
    await create_file(db, data)
    return {'id': data.id}


@router.get('/my/file', tags=['file'], name='我的文件')
async def get_my_file(user_id: str = None, search: str = None, is_check: bool = None, page: int = 1, limit: int = 20,
                      user: User = Depends(get_current_user_authorizer()),
                      db: AsyncIOMotorClient = Depends(get_database)):
    if 0 in user.role:
        u_id = user_id or user.id
    else:
        u_id = user.id
    query_obj = {'user_id': u_id}
    if search is not None:
        query_obj['file_name'] = {'$regex': search}
    if is_check is not None:
        query_obj['is_check'] = is_check
    data = await get_file_list(db, query_obj, page=page, limit=limit)
    count = await count_file_by_query(db, query_obj)
    return {
        'data': data,
        'count': count
    }


@router.get('/file/content', tags=['file'], name='某一文件内容')
async def get_file_content(file_id: str,
                           user: User = Depends(get_current_user_authorizer()),
                           db: AsyncIOMotorClient = Depends(get_database)):
    db_file = await get_file(db, {'id': file_id})
    if not db_file:
        raise HTTPException(HTTP_400_BAD_REQUEST, '文件不存在')
    if db_file.user_id != user.id and 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '权限不足')
    m = MinioUploadPrivate()
    content = m.get_object(db_file.parsed)
    return {'data': content}


@router.patch('/file', tags=['file'], name='修改文件（parsed,is_check）')
async def patch_file(file_id: str = Body(...), content: str = Body(None), is_check: bool = Body(None),
                     user: User = Depends(get_current_user_authorizer()),
                     db: AsyncIOMotorClient = Depends(get_database)):
    # 1.内容更新到minio，2.更新file的p_hash
    db_file = await get_file(db, {'id': file_id})
    if not db_file:
        raise HTTPException(HTTP_400_BAD_REQUEST, '文件不存在')
    if db_file.user_id != user.id and 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '权限不足')
    update_obj = {}
    if content is not None:
        m = MinioUploadPrivate()
        # 上传文件
        m.commit(content.encode('utf-8'), db_file.parsed)
        new_hash = contenttomd5(content.encode('utf-8'))
        update_obj['p_hash'] = new_hash
    if is_check is not None:
        update_obj['is_check'] = is_check
    await update_file(db, {'id': file_id}, {'$set': update_obj})
    return {'msg': '2002'}


@router.delete('/file', tags=['file'], name='删除文件')
async def del_file(file_id: str,
                   user: User = Depends(get_current_user_authorizer()),
                   db: AsyncIOMotorClient = Depends(get_database)):
    db_file = await get_file(db, {'id': file_id})
    if not db_file:
        raise HTTPException(HTTP_400_BAD_REQUEST, '文件不存在')
    if db_file.user_id != user.id and 0 not in user.role:
        raise HTTPException(HTTP_400_BAD_REQUEST, '权限不足')
    # 文件不能在work_history中出现
    use_count = await count_work_history_by_query(db, {'file_id': file_id})
    if use_count > 0:
        raise HTTPException(HTTP_400_BAD_REQUEST, '此文件不可删除')
    m = MinioUploadPrivate()
    m.remove(db_file.parsed)
    m.remove(db_file.origin)
    await delete_file(db, {'id': id, 'user_id': user.id})
    return {'msg': '2002'}
