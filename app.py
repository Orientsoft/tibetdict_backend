from fastapi import FastAPI
from config import HOST, PORT, DEBUG, VERSION, ALLOWED_HOSTS
from starlette.requests import Request
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from starlette.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from common.mongodb import connect_to_mongodb, close_mongo_connection
from pydantic import ValidationError
from respcode import data
from loguru import logger
from typing import Union
import fastapi_plugins
from applications.user import router as user_router
from applications.word_dict import router as word_dict_router
from applications.self_dict import router as self_dict_router
from applications.file import router as file_router
from applications.work_history import router as work_router
import traceback
import uvicorn
from common.redis import redis_config

app = FastAPI(title='tibetan', debug=DEBUG, version=VERSION)


async def catch_exceptions_middleware(request: Request, call_next) -> JSONResponse:
    try:
        return await call_next(request)
    except Exception as e:
        traceback.print_exc()
        logger.error(e)
        return JSONResponse({"errors": [{'msg': "Internal server error"}]}, status_code=500)


async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    logger.error(exc.detail)
    logger.error(data['zh-cn'].get(exc.detail))
    return JSONResponse({"errors": [{'msg': exc.detail}]}, status_code=exc.status_code)


async def http422_error_handler(
        _: Request, exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    logger.error(exc.errors())
    return JSONResponse(
        {"errors": exc.errors()}, status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    )


# 普通异常全局捕获
app.middleware('http')(catch_exceptions_middleware)


async def catch_exceptions_middleware(request: Request, call_next) -> JSONResponse:
    try:
        return await call_next(request)
    except Exception as e:
        traceback.print_exc()
        logger.error(e)
        # you probably want some kind of logging here
        return JSONResponse({"errors": [{'msg': "Internal server error"}]}, status_code=500)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_HOSTS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_event_handler("startup", connect_to_mongodb)
app.add_event_handler("shutdown", close_mongo_connection)


@app.on_event('startup')
async def startup() -> None:
    await fastapi_plugins.redis_plugin.init_app(app, config=redis_config)
    await fastapi_plugins.redis_plugin.init()


@app.on_event('shutdown')
async def on_shutdown() -> None:
    await fastapi_plugins.redis_plugin.terminate()


app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, http422_error_handler)

app.include_router(user_router, prefix='/api')
app.include_router(word_dict_router, prefix='/api')
app.include_router(self_dict_router, prefix='/api')
app.include_router(file_router, prefix='/api')
app.include_router(work_router, prefix='/api')

if __name__ == '__main__':
    uvicorn.run(
        app="app:app",
        host=HOST,
        port=PORT,
        reload=False,
        workers=4
    )
