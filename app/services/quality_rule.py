"""数据质量规则服务层。"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import internal_write_allowed
from app.models.quality_rule import QualityRule
from app.repositories import data_asset as asset_repo
from app.repositories import quality_rule as repo
from app.schemas.quality_rule import QualityRuleCreate, QualityRuleUpdate
from app.services.audit import record_audit


def _rule_to_dict(r: QualityRule) -> dict:
    return {
        "id": r.id, "code": r.code, "name": r.name, "asset_code": r.asset_code,
        "rule_type": r.rule_type, "expression": r.expression or "",
        "severity": r.severity, "status": r.status, "description": r.description or "",
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "updated_at": r.updated_at.isoformat() if r.updated_at else "",
    }


class QualityRuleService:
    @staticmethod
    async def list_rules(
        session: AsyncSession, limit: int = 100, offset: int = 0,
        status_filter: str | None = None, asset_code: str | None = None,
        keyword: str | None = None,
    ) -> dict:
        rules = await repo.list_rules(
            session, limit=limit, offset=offset,
            status=status_filter, asset_code=asset_code, keyword=keyword,
        )
        total = await repo.count_rules(
            session, status=status_filter, asset_code=asset_code, keyword=keyword
        )
        return {"total": total, "items": [_rule_to_dict(r) for r in rules]}

    @staticmethod
    async def get_rule(session: AsyncSession, rule_id: str) -> dict:
        rule = await repo.get_rule(session, rule_id)
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "质量规则不存在")
        return _rule_to_dict(rule)

    @staticmethod
    async def create_rule(
        session: AsyncSession, payload: QualityRuleCreate, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        if await repo.get_rule_by_code(session, payload.code):
            raise HTTPException(status.HTTP_409_CONFLICT, "规则编码已存在")
        # 引用完整性：所属资产必须存在
        if not await asset_repo.get_asset_by_code(session, payload.asset_code):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"所属资产 {payload.asset_code} 不存在")
        rule = QualityRule(
            id=str(uuid.uuid4()), code=payload.code, name=payload.name,
            asset_code=payload.asset_code, rule_type=payload.rule_type,
            expression=payload.expression, severity=payload.severity,
            description=payload.description or "", status="enabled",
        )
        rule = await repo.create_rule(session, rule)
        await record_audit(session, "governance.rule_created", "internal",
                           f"code={payload.code}", request)
        return _rule_to_dict(rule)

    @staticmethod
    async def update_rule(
        session: AsyncSession, rule_id: str, payload: QualityRuleUpdate, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        rule = await repo.get_rule(session, rule_id)
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "质量规则不存在")
        if payload.name is not None:
            rule.name = payload.name
        if payload.expression is not None:
            rule.expression = payload.expression
        if payload.severity is not None:
            rule.severity = payload.severity
        if payload.description is not None:
            rule.description = payload.description
        rule = await repo.update_rule(session, rule)
        await record_audit(session, "governance.rule_updated", "internal",
                           f"rule_id={rule_id}", request)
        return _rule_to_dict(rule)

    @staticmethod
    async def update_status(
        session: AsyncSession, rule_id: str, new_status: str, request: Request
    ) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        rule = await repo.get_rule(session, rule_id)
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "质量规则不存在")
        rule.status = new_status
        rule = await repo.update_rule(session, rule)
        await record_audit(session, "governance.rule_status_changed", "internal",
                           f"rule_id={rule_id} status={new_status}", request)
        return _rule_to_dict(rule)

    @staticmethod
    async def delete_rule(session: AsyncSession, rule_id: str, request: Request) -> dict:
        if not internal_write_allowed(request):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "内部写入令牌无效")
        rule = await repo.get_rule(session, rule_id)
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "质量规则不存在")
        code = rule.code
        await repo.delete_rule(session, rule)
        await record_audit(session, "governance.rule_deleted", "internal",
                           f"rule_id={rule_id} code={code}", request)
        return {"deleted": True, "id": rule_id}
