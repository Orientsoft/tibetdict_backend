from pydantic import BaseModel, validator
from model.common import IDModel, UpdatedAtModel, CreatedAtModel
from typing import List


class FileBaseModel(BaseModel):
    user_id: str
    file_name: str
    is_check: bool = False
    last_stat: str = None
    last_new: str = None
    origin: str = None
    parsed: str = None
    o_hash: str = None
    p_hash: str = None
    book_name: str = None
    author: str = None
    version: str = None
    tags: List = None


class FileCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, FileBaseModel):
    pass


class FileInDB(FileBaseModel):
    id: str
    createdAt: str
    updatedAt: str
