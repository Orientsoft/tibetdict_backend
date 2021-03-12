from pydantic import BaseModel
from model.common import IDModel, UpdatedAtModel, CreatedAtModel


class SelfDictBaseModel(BaseModel):
    word: str
    user_id: str
    is_check: bool = False
    work_history_id: str = None


class SelfDictCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, SelfDictBaseModel):
    pass


class SelfDictUpdateModel(BaseModel):
    id: str
    word: str = None
    is_check: bool = None


class SelfDictInDB(SelfDictBaseModel):
    id: str
    createdAt: str
    updatedAt: str


class SelfDictWithFilename(BaseModel):
    id: str
    word: str
    user_id: str
    is_check: bool = False
    createdAt: str
    updatedAt: str
    file_name: str
