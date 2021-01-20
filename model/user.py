from pydantic import BaseModel, validator
from model.common import IDModel, UpdatedAtModel, CreatedAtModel
from common.common import verify_password
from datetime import datetime
from typing import List


class UserBaseModel(BaseModel):
    username: str
    # 0-管理员；1-普通用户
    role: List[int]


class UserCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, UserBaseModel):
    password: str


class User(UserBaseModel):
    id: str
    token: str


class UserInDB(UserBaseModel):
    id: str = ""
    salt: str = ""
    hashed_password: str = ""
    updatedAt: str
    createdAt: str

    def check_password(self, password: str):
        return verify_password(self.salt + password, self.hashed_password)


class TokenPayload(BaseModel):
    id: str
    exp: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class UserListModel(BaseModel):
    id: str
    username: str


class UserListResponse(BaseModel):
    data: List[UserListModel]
    total: int


class UserResetPasswordModel(BaseModel):
    password: str
