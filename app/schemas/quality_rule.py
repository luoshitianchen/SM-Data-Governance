"""数据质量规则 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class QualityRuleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=128)
    asset_code: str = Field(min_length=1, max_length=64)
    rule_type: Literal["not_null", "unique", "format", "range", "consistency"] = "not_null"
    expression: str = Field(min_length=1, max_length=1000)
    severity: Literal["info", "warning", "critical"] = "warning"
    description: str = Field(default="", max_length=2000)


class QualityRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    expression: str | None = Field(default=None, min_length=1, max_length=1000)
    severity: Literal["info", "warning", "critical"] | None = None
    description: str | None = Field(default=None, max_length=2000)


class QualityRuleStatusUpdate(BaseModel):
    status: Literal["enabled", "disabled"]


class QualityRuleResponse(BaseModel):
    id: str
    code: str
    name: str
    asset_code: str
    rule_type: str
    expression: str
    severity: str
    status: str
    description: str
    created_at: datetime | str
    updated_at: datetime | str


class QualityRuleListResponse(BaseModel):
    total: int
    items: list[QualityRuleResponse]
