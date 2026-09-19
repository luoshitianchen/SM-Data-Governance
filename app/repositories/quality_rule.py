"""数据质量规则仓储层。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality_rule import QualityRule


async def get_rule(session: AsyncSession, rule_id: str) -> QualityRule | None:
    result = await session.execute(select(QualityRule).where(QualityRule.id == rule_id))
    return result.scalar_one_or_none()


async def get_rule_by_code(session: AsyncSession, code: str) -> QualityRule | None:
    result = await session.execute(select(QualityRule).where(QualityRule.code == code))
    return result.scalar_one_or_none()


async def count_rules_by_asset(session: AsyncSession, asset_code: str) -> int:
    result = await session.execute(
        select(func.count(QualityRule.id)).where(QualityRule.asset_code == asset_code)
    )
    return result.scalar_one()


async def list_rules(
    session: AsyncSession, limit: int = 100, offset: int = 0,
    status: str | None = None, asset_code: str | None = None, keyword: str | None = None,
) -> list[QualityRule]:
    stmt = select(QualityRule).order_by(QualityRule.created_at.desc()).limit(limit).offset(offset)
    if status:
        stmt = stmt.where(QualityRule.status == status)
    if asset_code:
        stmt = stmt.where(QualityRule.asset_code == asset_code)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(QualityRule.code.like(like), QualityRule.name.like(like)))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_rules(
    session: AsyncSession, status: str | None = None,
    asset_code: str | None = None, keyword: str | None = None,
) -> int:
    stmt = select(func.count(QualityRule.id))
    if status:
        stmt = stmt.where(QualityRule.status == status)
    if asset_code:
        stmt = stmt.where(QualityRule.asset_code == asset_code)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(QualityRule.code.like(like), QualityRule.name.like(like)))
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_rule(session: AsyncSession, rule: QualityRule) -> QualityRule:
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


async def update_rule(session: AsyncSession, rule: QualityRule) -> QualityRule:
    await session.commit()
    await session.refresh(rule)
    return rule


async def delete_rule(session: AsyncSession, rule: QualityRule) -> None:
    await session.delete(rule)
    await session.commit()
