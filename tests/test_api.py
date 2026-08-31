"""SM Data Governance 领域测试：数据资产、分级、策略、访问审批。"""

import pytest
from fastapi.testclient import TestClient

from app import base
from app.main import VERSION, app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(base, "internal_api_key", lambda: "TEST")
    base.reset_state()
    from app.main import _init as init_db
    init_db()
    with TestClient(app) as c:
        c.headers["X-Internal-Token"] = "TEST"
        yield c


def _asset(client, name="customer-db", classification="confidential"):
    return client.post("/api/governance/assets", json={"name": name, "owner": "数据中台", "classification": classification, "location": "hive://dw/customer"}).json()["id"]


def test_health_and_version(client):
    r = client.get("/health", headers={"X-Request-Id": "suite-test"})
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_asset_crud(client):
    _asset(client)
    assert client.post("/api/governance/assets", json={"name": "customer-db", "owner": "x", "classification": "internal", "location": "xx"}).status_code == 409
    assert client.get("/api/governance/assets").json()["total"] == 1


def test_policy(client):
    assert client.post("/api/governance/policies", json={"name": "restricted-read", "rule": "classification == restricted", "action": "review"}).status_code == 201
    assert client.post("/api/governance/policies", json={"name": "restricted-read", "rule": "xx", "action": "allow"}).status_code == 409
    assert client.get("/api/governance/policies").json()["total"] == 1


def test_access_request_flow(client):
    asset_id = _asset(client)
    req = client.post("/api/governance/requests", json={"asset_id": asset_id, "requester": "张敏", "reason": "月度报表需要"}).json()
    assert req["status"] == "pending"
    assert client.post(f"/api/governance/requests/{req['id']}/approve", json={"decided_by": "数据负责人"}).json()["status"] == "approved"
    assert client.get("/api/governance/requests").json()["total"] == 1


def test_access_deny(client):
    asset_id = _asset(client)
    req = client.post("/api/governance/requests", json={"asset_id": asset_id, "requester": "李雷", "reason": "查询客户数据"}).json()
    assert client.post(f"/api/governance/requests/{req['id']}/deny", json={"decided_by": "安全组"}).json()["status"] == "denied"
    assert client.post(f"/api/governance/requests/{req['id']}/approve", json={"decided_by": "x"}).status_code == 404


def test_missing_asset(client):
    assert client.post("/api/governance/requests", json={"asset_id": "no-such-asset", "requester": "r", "reason": "测试"}).status_code == 404


def test_stats(client):
    _asset(client, classification="restricted")
    stats = client.get("/api/governance/stats").json()
    assert stats["assets"] == 1
    assert stats["classifications"][0]["classification"] == "restricted"


def test_manifest_and_crypto(client):
    assert client.get("/api/integration/manifest").json()["version"] == VERSION
    enc = client.post("/api/crypto/encrypt", json={"value": "x"}).json()["ciphertext"]
    assert client.post("/api/crypto/decrypt", json={"value": enc}).json()["plaintext"] == "x"


def test_write_requires_auth(client):
    del client.headers["X-Internal-Token"]
    assert client.post("/api/governance/assets", json={"name": "a", "owner": "o", "classification": "internal", "location": "l"}).status_code == 401
