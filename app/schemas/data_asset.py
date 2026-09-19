"""数据资产 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=128)
    category: str = Field(default="general", max_length=64)
    owner: str = Field(default="", max_length=80)
    sensitivity: Literal["public", "internal", "confidential", "restricted"] = "internal"
    description: str = Field(default="", max_length=2000)


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    category: str | None = Field(default=None, max_length=64)
    owner: str | None = Field(default=None, max_length=80)
    sensitivity: Literal["public", "internal", "confidential", "restricted"] | None = None
    description: str | None = Field(default=None, max_length=2000)


class AssetStatusUpdate(BaseModel):
    """资产认证状态迁移：registered -> certified -> deprecated。"""

    status: Literal["certified", "deprecated"]


class AssetResponse(BaseModel):
    id: str
    code: str
    name: str
    category: str
    owner: str
    sensitivity: str
    status: str
    description: str
    created_at: datetime | str
    updated_at: datetime | str


class AssetListResponse(BaseModel):
    total: int
    items: list[AssetResponse]
