"""数据资产服务层：登记、认证与下线全生命周期。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.data_asset import DataAsset
from app.repositories import data_asset as repo
from app.repositories import data_lineage as lineage_repo
from app.repositories import quality_rule as rule_repo
from app.schemas.data_asset import AssetCreate, AssetUpdate
from app.services.audit import record_audit

# 资产认证状态机：registered -> certified -> deprecated（单向）
_ASSET_TRANSITIONS: dict[str, set[str]] = {
    "registered": {"certified", "deprecated"},
    "certified": {"deprecated"},
    "deprecated": set(),
}


def _asset_to_dict(a: DataAsset) -> dict:
    return {
        "id": a.id, "code": a.code, "name": a.name, "category": a.category,
        "owner": a.owner or "", "sensitivity": a.sensitivity, "status": a.status,
        "description": a.description or "",
        "created_at": a.created_at.isoformat() if a.created_at else "",
        "updated_at": a.updated_at.isoformat() if a.updated_at else "",
    }


class AssetService:
    @staticmethod
    async def list_assets(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        status_filter: str | None = None, category: str | None = None,
        keyword: str | None = None,
    ) -> dict:
        assets = await repo.list_assets(
            session, limit=limit, offset=offset,
            status=status_filter, category=category, keyword=keyword,
        )
        total = await repo.count_assets(
            session, status=status_filter, category=category, keyword=keyword
        )
        return {"total": total, "items": [_asset_to_dict(a) for a in assets]}

    @staticmethod
    async def get_asset(session: AsyncSession, asset_id: str) -> dict:
        asset = await repo.get_asset(session, asset_id)
        if not asset:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "数据资产不存在")
        return _asset_to_dict(asset)

    @staticmethod
    async def create_asset(session: AsyncSession, payload: AssetCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_asset_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "资产编码已存在")
        asset = DataAsset(
            id=str(uuid.uuid4()), code=payload.code, name=payload.name,
            category=payload.category, owner=payload.owner or "",
            sensitivity=payload.sensitivity, description=payload.description or "",
            status="registered",
        )
        asset = await repo.create_asset(session, asset)
        await record_audit(session, "governance.asset_registered", "internal",
                           f"code={payload.code}", request)
        return _asset_to_dict(asset)

    @staticmethod
    async def update_asset(
        session: AsyncSession, asset_id: str, payload: AssetUpdate, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        asset = await repo.get_asset(session, asset_id)
        if not asset:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "数据资产不存在")
        if asset.status == "deprecated":
            raise HTTPException(status.HTTP_409_CONFLICT, "已下线资产禁止编辑")
        if payload.name is not None:
            asset.name = payload.name
        if payload.category is not None:
            asset.category = payload.category
        if payload.owner is not None:
            asset.owner = payload.owner
        if payload.sensitivity is not None:
            asset.sensitivity = payload.sensitivity
        if payload.description is not None:
            asset.description = payload.description
        asset = await repo.update_asset(session, asset)
        await record_audit(session, "governance.asset_updated", "internal",
                           f"asset_id={asset_id}", request)
        return _asset_to_dict(asset)

    @staticmethod
    async def change_status(
        session: AsyncSession, asset_id: str, new_status: str, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        asset = await repo.get_asset(session, asset_id)
        if not asset:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "数据资产不存在")
        allowed = _ASSET_TRANSITIONS.get(asset.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"资产状态不允许从 {asset.status} 迁移到 {new_status}",
            )
        asset.status = new_status
        asset = await repo.update_asset(session, asset)
        await record_audit(session, "governance.asset_status_changed", "internal",
                           f"asset_id={asset_id} status={new_status}", request)
        return _asset_to_dict(asset)

    @staticmethod
    async def delete_asset(session: AsyncSession, asset_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        asset = await repo.get_asset(session, asset_id)
        if not asset:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "数据资产不存在")
        # 引用完整性：存在血缘边或质量规则时禁止删除
        edges = await lineage_repo.count_edges_for_asset(session, asset.code)
        rules = await rule_repo.count_rules_by_asset(session, asset.code)
        if edges > 0 or rules > 0:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"资产存在 {edges} 条血缘边、{rules} 条质量规则，禁止删除",
            )
        code = asset.code
        await repo.delete_asset(session, asset)
        await record_audit(session, "governance.asset_deleted", "internal",
                           f"asset_id={asset_id} code={code}", request)
        return {"deleted": True, "id": asset_id}
