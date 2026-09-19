"""数据血缘仓储层。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_lineage import DataLineage


async def get_lineage(session: AsyncSession, lineage_id: str) -> DataLineage | None:
    result = await session.execute(select(DataLineage).where(DataLineage.id == lineage_id))
    return result.scalar_one_or_none()


async def get_edge(
    session: AsyncSession, upstream: str, downstream: str, relation_type: str
) -> DataLineage | None:
    result = await session.execute(
        select(DataLineage).where(
            DataLineage.upstream_code == upstream,
            DataLineage.downstream_code == downstream,
            DataLineage.relation_type == relation_type,
        )
    )
    return result.scalar_one_or_none()


async def count_edges_for_asset(session: AsyncSession, asset_code: str) -> int:
    result = await session.execute(
        select(func.count(DataLineage.id)).where(
            (DataLineage.upstream_code == asset_code) | (DataLineage.downstream_code == asset_code)
        )
    )
    return result.scalar_one()


async def list_lineages(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    upstream: str | None = None, downstream: str | None = None,
) -> list[DataLineage]:
    stmt = select(DataLineage).order_by(DataLineage.created_at.desc()).limit(limit).offset(offset)
    if upstream:
        stmt = stmt.where(DataLineage.upstream_code == upstream)
    if downstream:
        stmt = stmt.where(DataLineage.downstream_code == downstream)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_lineages(
    session: AsyncSession, upstream: str | None = None, downstream: str | None = None,
) -> int:
    stmt = select(func.count(DataLineage.id))
    if upstream:
        stmt = stmt.where(DataLineage.upstream_code == upstream)
    if downstream:
        stmt = stmt.where(DataLineage.downstream_code == downstream)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_lineage(session: AsyncSession, lineage: DataLineage) -> DataLineage:
    session.add(lineage)
    await session.commit()
    await session.refresh(lineage)
    return lineage


async def delete_lineage(session: AsyncSession, lineage: DataLineage) -> None:
    await session.delete(lineage)
    await session.commit()
