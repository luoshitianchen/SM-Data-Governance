"""数据资产仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_asset import DataAsset


async def get_asset(session: AsyncSession, asset_id: str) -> DataAsset | None:
    result = await session.execute(select(DataAsset).where(DataAsset.id == asset_id))
    return result.scalar_one_or_none()


async def get_asset_by_code(session: AsyncSession, code: str) -> DataAsset | None:
    result = await session.execute(select(DataAsset).where(DataAsset.code == code))
    return result.scalar_one_or_none()


async def list_assets(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, category: str | None = None, keyword: str | None = None,
) -> list[DataAsset]:
    stmt = select(DataAsset).order_by(DataAsset.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(DataAsset.status == status)
    if category:
        stmt = stmt.where(DataAsset.category == category)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(DataAsset.code.like(like), DataAsset.name.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_assets(
    session: AsyncSession, status: str | None = None,
    category: str | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(DataAsset.id))
    if status:
        stmt = stmt.where(DataAsset.status == status)
    if category:
        stmt = stmt.where(DataAsset.category == category)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(DataAsset.code.like(like), DataAsset.name.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_asset(session: AsyncSession, asset: DataAsset) -> DataAsset:
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


async def update_asset(session: AsyncSession, asset: DataAsset) -> DataAsset:
    await session.commit()
    await session.refresh(asset)
    return asset


async def delete_asset(session: AsyncSession, asset: DataAsset) -> None:
    await session.delete(asset)
    await session.commit()
