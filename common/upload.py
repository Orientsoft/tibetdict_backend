#!/usr/bin/python
# -*- coding:utf-8 -*-
from minio import Minio
from minio.error import ResponseError, BucketAlreadyExists, BucketAlreadyOwnedByYou
from io import BytesIO
from datetime import timedelta
import traceback
from loguru import logger

import config

mc = Minio(config.MINIO_URL,
           access_key=config.MINIO_ACCESS,
           secret_key=config.MINIO_SECRET,
           secure=config.MINIO_SECURE)


class MinioUploadPrivate:
    def __init__(self):
        self.bucket = config.MINIO_BUCKET
        try:
            mc.make_bucket(self.bucket, location="us-east-1")
        except BucketAlreadyOwnedByYou as err:
            pass
        except BucketAlreadyExists as err:
            pass
        except ResponseError as err:
            pass

    def commit(self, stream: bytes, full_path: str):
        data = BytesIO(stream)
        mc.put_object(self.bucket, full_path, data, len(stream))
        return full_path

    def presign(self, full_path: str, resp_header=None):
        return mc.presigned_get_object(self.bucket, full_path, timedelta(days=1), response_headers=resp_header)

    def get_object(self, full_path: str) -> bytes:
        try:
            data = mc.get_object(self.bucket, full_path).data
        except Exception as e:
            logger.error(e)
            logger.error(full_path)
            data = b''
        return data

    def remove(self, full_path: str):
        mc.remove_object(self.bucket, full_path)
