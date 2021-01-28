from pydantic import BaseModel, Field
from model.common import IDModel, UpdatedAtModel, CreatedAtModel
from typing import List
from enum import Enum
from model.file import FileInDB


class WorkTypeEnum(str, Enum):
    stat = 'stat'  # 词频统计
    new = 'new'  # 新词发现


class WorkHistoryBaseModel(BaseModel):
    user_id: str
    file_id: str
    file_name: str
    origin: str
    parsed: str
    o_hash: str
    p_hash: str
    work_type: WorkTypeEnum
    p_status: int = Field(None, ge=0, le=2)
    o_status: int = Field(None, ge=0, le=2)
    p_result: List[dict] = None
    o_result: List[dict] = None


class WorkHistoryCreateModel(IDModel, UpdatedAtModel, CreatedAtModel, WorkHistoryBaseModel):
    pass


class WorkHistoryInDB(WorkHistoryBaseModel):
    id: str
    createdAt: str
    updatedAt: str


class WorkHistoryListModel(WorkHistoryInDB):
    file: FileInDB
