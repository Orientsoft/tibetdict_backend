from pydantic import BaseModel, validator, Field
from model.common import IDModel, UpdatedAtModel, CreatedAtModel
from typing import List
from enum import Enum
from model.file import FileInDB


class WordStatBaseModel(BaseModel):
    user_id: str
    file_id: str
    file_name: str
    parsed: str
    o_hash: str
    p_hash: str
    status: int = Field(..., ge=0, le=3)
    result: List[dict] = None


class WordStatCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, WordStatBaseModel):
    pass


class WordStatInDB(WordStatBaseModel):
    id: str
    createdAt: str
    updatedAt: str


class WordStatListModel(WordStatInDB):
    file: FileInDB
