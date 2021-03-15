from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List
from model.user import UserCreateModel, User, TokenResponse, UserListResponse, UserBaseModel
from common.jwt import get_current_user_authorizer, create_access_token
from common.mongodb import AsyncIOMotorClient, get_database
from crud.user import create_user, get_user, get_user_list_by_query_with_page_and_limit, count_user_by_query, \
    update_password, init_index, update_user
from config import API_KEY, SHARE_USER_ID

router = APIRouter()


@router.post('/user', tags=['admin'], name='单个用户添加')
async def post_users(
        username: str = Body(..., embed=True), role: List[int] = Body(...),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    if 0 not in user.role:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40005')
    data_user = await get_user(conn=db, query={'username': username})
    # 用户名重复
    if data_user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40001')
    user_model = UserCreateModel(
        username=username,
        password=username,
        role=role
    )
    await create_user(conn=db, user=user_model)
    return {'data': {'id': user_model.id}}


@router.post('/user/menu', tags=['admin'], name='管理员修改用户菜单权限')
async def set_user_menu(
        user_id: str = Body(...), role: List[int] = Body(...),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    if 0 not in user.role:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40005')
    data_user = await get_user(conn=db, query={'id': user_id})
    if not data_user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40002')
    if 0 in data_user.role:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40005')
    await update_user(conn=db, query={'id': user_id}, item={'role': role})
    return {'msg': '2001'}


@router.patch('/user', tags=['user'], name='用户修改自己密码')
async def patch_user(
        old_password: str = Body(...), new_password: str = Body(...),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    dbuser = await get_user(conn=db, query={'id': user.id})
    if not dbuser.check_password(old_password):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40003')
    await update_password(conn=db, query={'id': user.id}, password=new_password)
    return {'msg': '2002'}


@router.post("/users/login", response_model=TokenResponse, tags=["user"], name='账号密码登录')
async def login(user: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorClient = Depends(get_database)):
    dbuser = await get_user(conn=db, query={'username': user.username})
    if not dbuser:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40008')
    elif not dbuser.check_password(user.password):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40009')
    token = create_access_token(data={"id": dbuser.id})
    # swaggerui 要求返回此格式
    return TokenResponse(access_token=token)


@router.get('/user/me', tags=['user'], name='我的信息')
async def user_me(
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    dbuser = await get_user(conn=db, query={'id': user.id})
    return {'username': dbuser.username, 'role': dbuser.role}


@router.get('/user_list', tags=['admin'], response_model=UserListResponse, name='用户列表获取')
async def get_user_list(
        search: str = None, page: int = 1, limit: int = 20,
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    if 0 not in user.role:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40005')
    data_user = await get_user_list_by_query_with_page_and_limit(conn=db, query={
        'username': {'$regex': search}} if search else {}, page=page, limit=limit)
    total = await count_user_by_query(conn=db, query={'username': {'$regex': search}} if search else {})
    return UserListResponse(data=data_user, total=total)


@router.get('/init_admin', tags=['admin'], name='初始化超级管理员')
async def get_init_admin(
        key: str,
        db: AsyncIOMotorClient = Depends(get_database)
):
    if key != API_KEY:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40009')
    # 共享语料库所有者
    user_model = UserCreateModel(
        username='admin',
        password='welcome1',
        role=[0, 1, 2, 3]
    )
    user_model.id = SHARE_USER_ID
    await create_user(conn=db, user=user_model)
    return {'msg': '2001'}


@router.get('/init_sys', tags=['admin'], name='初始化系统')
async def get_init_sys(
        key: str,
        db: AsyncIOMotorClient = Depends(get_database)
):
    if key != API_KEY:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40009')
    # 初始化索引
    await init_index(db)
    return {'msg': '2001'}


@router.get('/reset_password', tags=['admin'], name='管理员重置密码')
async def get_reset_password(
        user_id: str, new_pass: str,
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    if 0 not in user.role:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40005')
    data_user = await get_user(conn=db, query={'id': user_id})
    if not data_user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40002')
    if 0 in data_user.role:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40005')
    await update_password(conn=db, query={'id': user_id}, password=new_pass)
    return {'msg': '2001'}


@router.get('/language/code', tags=['user'], name='i18n码表获取')
async def get_language_code():
    from respcode import data

    return {'data': data}

