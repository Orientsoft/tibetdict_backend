from pydantic import BaseModel, validator
from model.common import IDModel, UpdatedAtModel, CreatedAtModel


class FileBaseModel(BaseModel):
    user_id: str
    file_name: str
    path: str = None


class FileCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, FileBaseModel):
    pass


class FileInDB(FileBaseModel):
    id: str
    createdAt: str
    updatedAt: str
