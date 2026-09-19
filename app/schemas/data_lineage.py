"""数据血缘 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LineageCreate(BaseModel):
    upstream_code: str = Field(min_length=1, max_length=64)
    downstream_code: str = Field(min_length=1, max_length=64)
    relation_type: Literal["derived_from", "transformed_from", "aggregated_from"] = "derived_from"
    transform_logic: str = Field(default="", max_length=2000)


class LineageResponse(BaseModel):
    id: str
    upstream_code: str
    downstream_code: str
    relation_type: str
    transform_logic: str
    created_at: datetime | str


class LineageListResponse(BaseModel):
    total: int
    items: list[LineageResponse]
