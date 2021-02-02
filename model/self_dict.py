from pydantic import BaseModel
from model.common import IDModel, UpdatedAtModel, CreatedAtModel


class SelfDictBaseModel(BaseModel):
    word: str
    user_id: str
    nature: str = None
    context: str = None
    is_check: bool = False
    work_history_id: str = None


class SelfDictCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, SelfDictBaseModel):
    pass


class SelfDictUpdateModel(BaseModel):
    id: str
    word: str = None
    nature: str = None
    context: str = None
    is_check: bool = None


class SelfDictInDB(SelfDictBaseModel):
    id: str
    createdAt: str
    updatedAt: str
