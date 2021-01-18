from flask import Flask
from flask_cors import CORS
import pymongo
import traceback

app = Flask(__name__)
app.config.from_pyfile('config.py')
CORS(app, supports_credentials=True)
client = pymongo.MongoClient(app.config['MONGODB_URL'])
db = client[app.config['DATABASE']]


@app.errorhandler(TypeError)
def TypeError_handler(error):
    traceback.print_exc()
    return '格式异常', 400


@app.errorhandler(ValueError)
def TypeError_handler(error):
    traceback.print_exc()
    return '数据格式异常', 400


@app.errorhandler(404)
def not_found_hanlder(error):
    from flask import request
    print(request.base_url)
    return '错误的访问地址', 404


if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], host=app.config['HOST'], port=app.config['PORT'], threaded=True)
