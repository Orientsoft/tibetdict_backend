from fastapi import APIRouter, Body, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from model.user import UserCreateModel, User, UserInDB
from common.jwt import get_current_user_authorizer
from common.mongodb import AsyncIOMotorClient, get_database
from crud.user import create_user

router = APIRouter()


@router.post('/user', tags=['用户模块'], name='单个用户添加')
async def post_users(
        username: str = Body(...),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    if 0 not in user.role:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40005')
    data_user = await db.user.find_one({'username': username})
    # 用户名重复
    if data_user:
        return '40001', 400
    user_model = UserCreateModel(
        username=username,
        password=username,
        role=[1]
    )
    await create_user(conn=db, user=user_model)
    return {'data': {'id': UserCreateModel.id}}


@router.patch('/user', tags=['用户模块'], name='用户修改自己密码')
async def patch_user(
        old_password: str = Body(...), new_password: str = Body(...),
        user: User = Depends(get_current_user_authorizer(required=True)),
        db: AsyncIOMotorClient = Depends(get_database)
):
    dbuser = await db.user.find_one({'id': user.id})
    user_check = UserInDB(**dbuser)
    if not user_check.check_password(old_password):
        return '40003', 400
    db.user.update({'id': user.id}, {'$set': {'password': new_password}})
    return '2002', 200
#
# # 用户自身详情查询
# elif request.method == 'GET':
# if not session.get('id'):
#     return '40004', 403
# data_user = db.user.find_one({'id': session['id']})
# return jsonify({'data': data_user})
# # 用户注销(暂无)
# elif request.method == 'DELETE':
# pass
#
#
# @user.route('/user_list', methods=['GET'])
# def get_user_list():
#     from app import db
#     if not session.get('role') or 0 not in session['role']:
#         return '40005', 400
#     search = request.args.get('search')
#
#     data_user = db.user.find()
