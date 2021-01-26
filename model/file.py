from pydantic import BaseModel, validator
from model.common import IDModel, UpdatedAtModel, CreatedAtModel


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


class FileCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, FileBaseModel):
    pass


class FileInDB(FileBaseModel):
    id: str
    createdAt: str
    updatedAt: str
