from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from starlette.status import HTTP_400_BAD_REQUEST
from io import BytesIO
from typing import List

from model.user import User
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database

from crud.file import create_file
from model.file import FileCreateModel

router = APIRouter()


@router.post('', tags=['upload'], name='文档上传')
async def upload_image(file: UploadFile = File(...), user: User = Depends(get_current_user_authorizer()),
                       db: AsyncIOMotorClient = Depends(get_database)):
    # doc,docx,csv,
    # if 'text' not in file.content_type:
    #     raise HTTPException(status_code=400, detail='100141')
    st = file.file.read()
    data = FileCreateModel(
        user_id=user.id,
        file_name=file.filename,
        file_content=st
    )
    await create_file(db, data)
    return {'id': data.id}


# TODO
'''
1.词频统计词库导入（管理员）
2.已有词典导入（管理员）
3.词频统计上传文档
4.新词查找上传
'''
