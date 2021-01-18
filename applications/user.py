from flask import Blueprint, jsonify, request, session
from model.user import UserCreateModel
from common.common import sha_key

user = Blueprint('user', __name__)


# 单个用户添加
@user.route('/user', methods=['POST', 'PATCH', 'GET', 'DELETE'])
def post_users():
    from app import db
    if request.method == 'POST':
        data_user = db.user.find_one({'username': request.json.get('username')})
        # 用户名重复
        if data_user:
            return '40001', 400
        request_model = UserCreateModel(
            username=request.json.get('username'),
            password=sha_key(request.json.get('username'))
        )
        db.user.insert_one(request_model.dict())
        return jsonify({'data': {'id': UserCreateModel.id}})
    # 用户修改自己密码
    elif request.method == 'PATCH':
        if not session.get('id'):
            return '40004', 403
        data_user = db.user.find_one(
            {'id': session['id'], 'password': sha_key(request.json.get('old_password'))})
        if not data_user:
            return '40003', 400
        db.user.update({'id': session['id']}, {'$set': {'password': sha_key(request.json.get('new_password'))}})
        return '2002', 200
    # 用户自身详情查询
    elif request.method == 'GET':
        if not session.get('id'):
            return '40004', 403
        data_user = db.user.find_one({'id': session['id']})
        return jsonify({'data': data_user})
    # 用户注销(暂无)
    elif request.method == 'DELETE':
        pass
