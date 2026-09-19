"""数据血缘服务层：上下游依赖登记。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.data_lineage import DataLineage
from app.repositories import data_asset as asset_repo
from app.repositories import data_lineage as repo
from app.schemas.data_lineage import LineageCreate
from app.services.audit import record_audit


def _lineage_to_dict(edge: DataLineage) -> dict:
    return {
        "id": edge.id, "upstream_code": edge.upstream_code,
        "downstream_code": edge.downstream_code, "relation_type": edge.relation_type,
        "transform_logic": edge.transform_logic or "",
        "created_at": edge.created_at.isoformat() if edge.created_at else "",
    }


class LineageService:
    @staticmethod
    async def list_lineages(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        upstream: str | None = None, downstream: str | None = None,
    ) -> dict:
        rows = await repo.list_lineages(
            session, limit=limit, offset=offset, upstream=upstream, downstream=downstream
        )
        total = await repo.count_lineages(session, upstream=upstream, downstream=downstream)
        return {"total": total, "items": [_lineage_to_dict(r) for r in rows]}

    @staticmethod
    async def create_lineage(session: AsyncSession, payload: LineageCreate, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        # 禁止自环
        if payload.upstream_code == payload.downstream_code:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "上下游资产不能相同（禁止自环）")
        # 引用完整性：两端资产必须存在
        if not await asset_repo.get_asset_by_code(session, payload.upstream_code):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"上游资产 {payload.upstream_code} 不存在")
        if not await asset_repo.get_asset_by_code(session, payload.downstream_code):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"下游资产 {payload.downstream_code} 不存在")
        # 唯一边
        if await repo.get_edge(session, payload.upstream_code, payload.downstream_code, payload.relation_type):
            raise HTTPException(status.HTTP_409_CONFLICT, "相同血缘边已存在")
        lineage = DataLineage(
            id=str(uuid.uuid4()), upstream_code=payload.upstream_code,
            downstream_code=payload.downstream_code, relation_type=payload.relation_type,
            transform_logic=payload.transform_logic or "",
        )
        lineage = await repo.create_lineage(session, lineage)
        await record_audit(session, "governance.lineage_created", "internal",
                           f"{payload.upstream_code}->{payload.downstream_code}", request)
        return _lineage_to_dict(lineage)

    @staticmethod
    async def delete_lineage(session: AsyncSession, lineage_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        lineage = await repo.get_lineage(session, lineage_id)
        if not lineage:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "血缘关系不存在")
        await repo.delete_lineage(session, lineage)
        await record_audit(session, "governance.lineage_deleted", "internal",
                           f"lineage_id={lineage_id}", request)
        return {"deleted": True, "id": lineage_id}
