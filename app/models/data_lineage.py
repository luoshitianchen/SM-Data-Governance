"""数据血缘关系模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class DataLineage(Base):
    """血缘关系：描述两个数据资产之间的上下游依赖。"""

    __tablename__ = "data_lineages"
    __table_args__ = (
        UniqueConstraint("upstream_code", "downstream_code", "relation_type", name="uq_lineage_edge"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    upstream_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    downstream_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(32), default="derived_from", index=True)
    transform_logic: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
