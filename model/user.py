from pydantic import BaseModel, validator
from model.common import IDModel, UpdatedAtModel, CreatedAtModel
from typing import List


class UserBaseModel(BaseModel):
    username: str
    password: str
    role: List[int]


class UserCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, UserBaseModel):
    pass
