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

from crud.file import create_file
from model.file import FileCreateModel
from common.upload import MinioUploadPrivate
from common.common import contenttomd5, tokenize_words

router = APIRouter()
_platform = platform.system().lower()


@router.post('/upload/file', tags=['upload'], name='文档上传')
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
    logger.info(origin_content)

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
        logger.info(parsed_content)
    else:
        parsed_content = origin_content
    # 提交分词结果
    m.commit(parsed_content.encode('utf-8'), data.parsed)
    # 文件指纹
    data.p_hash = contenttomd5(parsed_content.encode('utf-8'))
    data.o_hash = contenttomd5(origin_content.encode('utf-8'))
    await create_file(db, data)
    return {'id': data.id}


# TODO
'''
1.词频统计词库导入（管理员）
2.已有词典导入（管理员）
3.词频统计上传文档
4.新词查找上传
'''
