"""SM Data Governance —— 数据治理平台：数据资产、分级分类、治理策略与访问审批。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from app import base

SERVICE = "sm-data-governance"
VERSION = "2.0.0"
NAME = "SM Data Governance"
DESCRIPTION = "数据治理平台：数据资产、分级分类、治理策略与访问审批"
PORT = 8360


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _init() -> None:
    with base.db_ctx() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, owner TEXT NOT NULL,
                classification TEXT NOT NULL DEFAULT 'internal',
                location TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS policies (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, rule TEXT NOT NULL,
                action TEXT NOT NULL DEFAULT 'allow', enabled INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS access_requests (
                id TEXT PRIMARY KEY, asset_id TEXT NOT NULL, requester TEXT NOT NULL,
                reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL, decided_at TEXT, decided_by TEXT
            );
            """
        )


app = base.create_app(
    service=SERVICE, name=NAME, description=DESCRIPTION, version=VERSION, port=PORT,
    dependencies=["sm-iam", "sm-mdm", "sm-audit-log-center"],
    events=["asset.registered", "access.requested", "access.approved", "access.denied"],
    overview_fn=lambda _r: {
        "summary": {
            "assets": base.get_db().execute("SELECT COUNT(*) FROM assets").fetchone()[0],
            "pending_requests": base.get_db().execute("SELECT COUNT(*) FROM access_requests WHERE status='pending'").fetchone()[0],
        }
    },
)
_init()


class AssetIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    owner: str = Field(min_length=1, max_length=80)
    classification: str = Field(pattern=r"^(public|internal|confidential|restricted)$")
    location: str = Field(min_length=2, max_length=200)


class PolicyIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    rule: str = Field(min_length=2, max_length=300)
    action: str = Field(default="allow", pattern=r"^(allow|deny|review)$")


class AccessRequestIn(BaseModel):
    asset_id: str = Field(min_length=8)
    requester: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=2, max_length=300)


class DecisionIn(BaseModel):
    decided_by: str = Field(min_length=1, max_length=80)


@app.get("/api/governance/assets")
def list_assets() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM assets ORDER BY created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/governance/assets", status_code=status.HTTP_201_CREATED)
def register_asset(payload: AssetIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    asset_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO assets VALUES (?,?,?,?,?,?)", (asset_id, payload.name, payload.owner, payload.classification, payload.location, _now()))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "数据资产已存在") from exc
        base.record_audit("asset.registered", "internal", f"asset={payload.name} class={payload.classification}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": asset_id, "name": payload.name}


@app.post("/api/governance/policies", status_code=status.HTTP_201_CREATED)
def create_policy(payload: PolicyIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    policy_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        try:
            conn.execute("INSERT INTO policies VALUES (?,?,?,?,1)", (policy_id, payload.name, payload.rule, payload.action))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status.HTTP_409_CONFLICT, "策略已存在") from exc
    return {"id": policy_id, "name": payload.name}


@app.get("/api/governance/policies")
def list_policies() -> dict[str, Any]:
    with base.db_ctx() as conn:
        rows = conn.execute("SELECT * FROM policies").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/governance/requests", status_code=status.HTTP_201_CREATED)
def create_access_request(payload: AccessRequestIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    req_id = str(uuid.uuid4())
    with base.db_ctx() as conn:
        asset = conn.execute("SELECT * FROM assets WHERE id=?", (payload.asset_id,)).fetchone()
        if not asset:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "数据资产不存在")
        conn.execute("INSERT INTO access_requests (id, asset_id, requester, reason, status, created_at, decided_at, decided_by) VALUES (?,?,?,?,?,?,?,?)", (req_id, payload.asset_id, payload.requester, payload.reason, "pending", _now(), None, None))
        base.record_audit("access.requested", payload.requester, f"asset={payload.asset_id} request={req_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": req_id, "status": "pending"}


@app.get("/api/governance/requests")
def list_requests(status_: str | None = None) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if status_:
            rows = conn.execute("SELECT * FROM access_requests WHERE status=? ORDER BY status='pending' DESC, created_at DESC", (status_,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM access_requests ORDER BY status='pending' DESC, created_at DESC").fetchall()
    return {"items": [dict(r) for r in rows], "total": len(rows)}


@app.post("/api/governance/requests/{request_id}/approve")
def approve_request(request_id: str, payload: DecisionIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    return _decide(request_id, "approved", payload.decided_by, request)


@app.post("/api/governance/requests/{request_id}/deny")
def deny_request(request_id: str, payload: DecisionIn, request: Request) -> dict[str, Any]:
    base.require_internal_token(request)
    return _decide(request_id, "denied", payload.decided_by, request)


def _decide(request_id: str, decision: str, decided_by: str, request: Request) -> dict[str, Any]:
    with base.db_ctx() as conn:
        if conn.execute("UPDATE access_requests SET status=?, decided_at=?, decided_by=? WHERE id=? AND status='pending'", (decision, _now(), decided_by, request_id)).rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "审批请求不存在或已处理")
        base.record_audit(f"access.{decision}", decided_by, f"request={request_id}", getattr(request.state, "request_id", ""), getattr(request.state, "trace_id", ""), SERVICE)
    return {"id": request_id, "status": decision}


@app.get("/api/governance/stats")
def stats() -> dict[str, Any]:
    with base.db_ctx() as conn:
        def _count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        classifications = [dict(r) for r in conn.execute("SELECT classification, COUNT(*) AS count FROM assets GROUP BY classification").fetchall()]
        return {
            "assets": _count("SELECT COUNT(*) FROM assets"),
            "policies": _count("SELECT COUNT(*) FROM policies"),
            "pending": _count("SELECT COUNT(*) FROM access_requests WHERE status='pending'"),
            "approved": _count("SELECT COUNT(*) FROM access_requests WHERE status='approved'"),
            "classifications": classifications,
        }
