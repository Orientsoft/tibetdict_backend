from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List
from model.user import User
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database

from model.word_dict import WordStatDictCreateModel, WordStatDictUpdateModel, DictTypeEnum
from crud.word_dict import create_word_stat_dict, get_word_stat_dict_list, get_word_stat_dict, update_word_stat_dict, \
    count_word_stat_dict_by_query

router = APIRouter()


@router.post('/word/stat', tags=['词频统计'], name='用户添加词频统计任务')
async def add_word_stat(file_id: str = Body(...), user: User = Depends(get_current_user_authorizer(required=True)),
                        db: AsyncIOMotorClient = Depends(get_database)):
    '''
    1.文件的id
    '''
    pass


@router.get('/word/stat', tags=['词频统计'], name='历史记录')
async def history_stat(search: str = None, status: int = None, page: int = 1, limit: int = 20,
                       user: User = Depends(get_current_user_authorizer(required=True)),
                       db: AsyncIOMotorClient = Depends(get_database)):
    pass


@router.post('/word/stat/start', tags=['词频统计'], name='开始词频统计')
async def start_stat(ids: List[str] = Body(...), user: User = Depends(get_current_user_authorizer(required=True)),
                     db: AsyncIOMotorClient = Depends(get_database)):
    pass


@router.post('/word/stat/result', tags=['词频统计'], name='统计结果')
async def add_word_stat(ids: List[str] = Body(...), user: User = Depends(get_current_user_authorizer(required=True)),
                        db: AsyncIOMotorClient = Depends(get_database)):
    pass


@router.get('/word/stat/review', tags=['词频统计'], name='文档审阅')
async def add_word_stat(id: str = Body(...), user: User = Depends(get_current_user_authorizer(required=True)),
                        db: AsyncIOMotorClient = Depends(get_database)):
    pass
