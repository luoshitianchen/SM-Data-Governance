"""数据资产管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.data_asset import AssetCreate, AssetStatusUpdate, AssetUpdate
from app.services.data_asset import AssetService

router = APIRouter(prefix="/api/governance/assets", tags=["governance-assets"])


@router.get("")
async def list_assets(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None, max_length=64),
    keyword: str | None = Query(default=None, max_length=128),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AssetService.list_assets(
        session, limit=limit, offset=offset,
        status_filter=status_filter, category=category, keyword=keyword,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_asset(
    payload: AssetCreate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AssetService.create_asset(session, payload, request)


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AssetService.get_asset(session, asset_id)


@router.patch("/{asset_id}")
async def update_asset(
    asset_id: str, payload: AssetUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AssetService.update_asset(session, asset_id, payload, request)


@router.patch("/{asset_id}/status")
async def update_asset_status(
    asset_id: str, payload: AssetStatusUpdate, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AssetService.change_status(session, asset_id, payload.status, request)


@router.delete("/{asset_id}", status_code=status.HTTP_200_OK)
async def delete_asset(
    asset_id: str, request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await AssetService.delete_asset(session, asset_id, request)
