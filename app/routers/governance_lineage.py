"""数据血缘管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.data_lineage import LineageCreate
from app.services.data_lineage import LineageService

router = APIRouter(prefix="/api/governance/lineage", tags=["governance-lineage"])


@router.get("")
async def list_lineages(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    upstream: str | None = Query(default=None, max_length=64),
    downstream: str | None = Query(default=None, max_length=64),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await LineageService.list_lineages(
        session, limit=limit, offset=offset, upstream=upstream, downstream=downstream
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_lineage(
    payload: LineageCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await LineageService.create_lineage(session, payload, request)


@router.delete("/{lineage_id}", status_code=status.HTTP_200_OK)
async def delete_lineage(
    lineage_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await LineageService.delete_lineage(session, lineage_id, request)
