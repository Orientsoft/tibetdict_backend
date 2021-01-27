from pydantic import BaseModel, validator
from model.common import IDModel, UpdatedAtModel, CreatedAtModel
from typing import List
from enum import Enum


class DictTypeEnum(str, Enum):
    stat = 'stat'
    used = 'used'


class WordStatDictBaseModel(BaseModel):
    word: str
    nature: str
    type: DictTypeEnum
    is_exclude: bool = False
    name: str = None


class WordStatDictCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, WordStatDictBaseModel):
    pass

    @validator("word", pre=True, always=True)
    def replace_word(cls, v, values, **kwargs) -> str:
        return v.replace(u'༌', u'་')

    @validator("nature", pre=True, always=True)
    def replace_nature(cls, v, values, **kwargs) -> str:
        return v.replace(u'༌', u'་')


class WordStatDictUpdateModel(BaseModel):
    id: str
    word: str = None
    nature: str = None
    is_exclude: bool = None
    name: str = None


class WordStatDictInDB(WordStatDictBaseModel):
    id: str
    createdAt: str
    updatedAt: str
