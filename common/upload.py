#!/usr/bin/python
# -*- coding:utf-8 -*-
from minio import Minio
from minio.error import ResponseError, BucketAlreadyExists, BucketAlreadyOwnedByYou
from io import BytesIO
from datetime import timedelta
import traceback
from loguru import logger

import config


class MyTree:
    def __init__(self):
        self.tree = {}

    # onepoint 是 list
    def append_Point_to_tree(self, onepoint):
        nowPositon = self.tree
        index = 0
        while index < len(onepoint):

            if nowPositon.__contains__(onepoint[index]):
                nowPositon = nowPositon[onepoint[index]]
                index += 1

            else:
                # 创建新节点
                nowPositon[onepoint[index]] = {}
        return self.tree

    # 把【 【路径1 a,b,c,d】 ，【路径2】 】
    # 多条路径一次性插入到树中
    def insert_list_to_tree(self, pointlist):
        for onepoint in pointlist:
            self.append_Point_to_tree(onepoint)


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

    def list_content(self, path: str, recursive: bool = False):
        content = []
        try:
            objects = mc.list_objects_v2(self.bucket, prefix=path, recursive=recursive)
            for obj in objects:
                object_name = obj.object_name
                tmp_path = obj.object_name.replace(path, '')
                content.append({
                    'size': obj.size,
                    'is_dir': obj.is_dir,
                    'last_modified': obj.last_modified,
                    'file_name': tmp_path.rsplit('/', 1)[-1],
                    'object_name':object_name,
                    'path': tmp_path.rsplit('/', 1)[0]
                })
        except Exception as e:
            print(e)
            pass
        return content

    def list_tree(self, path: str):
        result = self.list_content(path,True)
        tree_array = []
        for r in result:
            if '.' not in r['path']:
                path_item = r['path'].split('/')
                tree_array.append(path_item)
        t = MyTree()
        t.insert_list_to_tree(tree_array)
        return t.tree