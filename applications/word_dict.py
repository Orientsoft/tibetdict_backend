from flask import Blueprint, jsonify, request, session
from model.word_dict import WordStatDictCreateModel, WordStatDictUpdateModel, WordDictQueryModel

word_dict = Blueprint('word_dict', __name__)


# 单个词典的CRUD
@word_dict.route('/word/dict', methods=['POST', 'PATCH', 'GET', 'DELETE'])
def post_word_dict():
    from app import db
    if request.method == 'POST':
        db_word = db.word_stat_dict.find_one({'word': request.json.get('word')})
        if db_word:
            return '40001', 400
        request_model = WordStatDictCreateModel(**request.json)
        db.word_stat_dict.insert_one(request_model.dict())
        return jsonify({'data': {'id': request_model.id}})
    elif request.method == 'PATCH':
        request_model = WordStatDictUpdateModel(**request.json)
        db.word_stat_dict.update_one({'id': request_model.id}, {'$set': request_model.dict()})
    elif request.method == 'DELETE':
        req_id = request.args.get('id')
        db.word_stat_dict.delete_one({'id': req_id})
    elif request.method == 'GET':
        req_model = WordDictQueryModel(**request.args)
        page = req_model.page
        limit = req_model.limit
        query_obj = {}
        if req_model.search:
            query_obj['$or'] = [{'word': {'$regex': req_model.search}}, {'nature': {'$regex': req_model.search}}]
        if req_model.type:
            query_obj['type'] = req_model.type
        data = db.word_stat_dict.find(query_obj, {'_id': 0}).skip((page - 1) * limit).limit(limit)
        total = db.word_stat_dict.count(query_obj)
        return jsonify({'data': data, 'total': total})
