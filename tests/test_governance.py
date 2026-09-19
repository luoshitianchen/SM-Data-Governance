"""SM-Data-Governance 业务深化测试：资产/血缘/质量规则全生命周期。"""
from __future__ import annotations

import pytest

H = {"X-Internal-Token": "test-internal-key-12345"}


async def _create_asset(client, code: str, name: str = "资产") -> dict:
    resp = await client.post("/api/governance/assets", json={
        "code": code, "name": name, "category": "业务域", "owner": "数据组",
        "sensitivity": "internal",
    }, headers=H)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_rule(client, code: str, asset_code: str) -> dict:
    resp = await client.post("/api/governance/rules", json={
        "code": code, "name": f"规则-{code}", "asset_code": asset_code,
        "rule_type": "not_null", "expression": "user_id IS NOT NULL", "severity": "warning",
    }, headers=H)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ═══════════════════════════════════════════════════════════
# 数据资产
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_asset_success(client):
    data = await _create_asset(client, "DS-USER-01", "用户主数据")
    assert data["code"] == "DS-USER-01"
    assert data["status"] == "registered"
    assert data["sensitivity"] == "internal"


@pytest.mark.asyncio
async def test_create_asset_requires_token(client):
    resp = await client.post("/api/governance/assets", json={"code": "DS-NOAUTH", "name": "无令牌"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_asset_duplicate_code(client):
    await _create_asset(client, "DS-DUP")
    resp = await client.post("/api/governance/assets", json={"code": "DS-DUP", "name": "重复"}, headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_assets_filter_and_keyword(client):
    await _create_asset(client, "DS-FILT", "关键词资产")
    resp = await client.get("/api/governance/assets?keyword=DS-FILT", headers=H)
    assert resp.status_code == 200
    assert any(a["code"] == "DS-FILT" for a in resp.json()["items"])
    resp2 = await client.get("/api/governance/assets?status=registered", headers=H)
    assert all(a["status"] == "registered" for a in resp2.json()["items"])


@pytest.mark.asyncio
async def test_get_asset_not_found(client):
    resp = await client.get("/api/governance/assets/no-such-id", headers=H)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_asset(client):
    a = await _create_asset(client, "DS-UPD")
    resp = await client.patch(f"/api/governance/assets/{a['id']}", json={
        "name": "更新资产", "sensitivity": "confidential",
    }, headers=H)
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新资产"
    assert resp.json()["sensitivity"] == "confidential"


@pytest.mark.asyncio
async def test_asset_state_machine_certify(client):
    a = await _create_asset(client, "DS-CERT")
    r1 = await client.patch(f"/api/governance/assets/{a['id']}/status", json={"status": "certified"}, headers=H)
    assert r1.status_code == 200 and r1.json()["status"] == "certified"
    r2 = await client.patch(f"/api/governance/assets/{a['id']}/status", json={"status": "deprecated"}, headers=H)
    assert r2.status_code == 200 and r2.json()["status"] == "deprecated"


@pytest.mark.asyncio
async def test_asset_invalid_transition(client):
    a = await _create_asset(client, "DS-BADTR")
    await client.patch(f"/api/governance/assets/{a['id']}/status", json={"status": "deprecated"}, headers=H)
    # 终态 deprecated 不能再 certified
    resp = await client.patch(f"/api/governance/assets/{a['id']}/status", json={"status": "certified"}, headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_deprecated_asset_locked(client):
    a = await _create_asset(client, "DS-LOCK")
    await client.patch(f"/api/governance/assets/{a['id']}/status", json={"status": "deprecated"}, headers=H)
    resp = await client.patch(f"/api/governance/assets/{a['id']}", json={"name": "改名"}, headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_asset_with_rules_blocked(client):
    a = await _create_asset(client, "DS-USED")
    await _create_rule(client, "R-USED", "DS-USED")
    resp = await client.delete(f"/api/governance/assets/{a['id']}", headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_empty_asset_ok(client):
    a = await _create_asset(client, "DS-EMPTY")
    resp = await client.delete(f"/api/governance/assets/{a['id']}", headers=H)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════════════════
# 数据血缘
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_lineage_success(client):
    await _create_asset(client, "DS-LINE-UP")
    await _create_asset(client, "DS-LINE-DOWN")
    resp = await client.post("/api/governance/lineage", json={
        "upstream_code": "DS-LINE-UP", "downstream_code": "DS-LINE-DOWN",
        "relation_type": "derived_from", "transform_logic": "每日快照",
    }, headers=H)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["upstream_code"] == "DS-LINE-UP"
    assert data["downstream_code"] == "DS-LINE-DOWN"


@pytest.mark.asyncio
async def test_lineage_self_loop_forbidden(client):
    await _create_asset(client, "DS-SELF")
    resp = await client.post("/api/governance/lineage", json={
        "upstream_code": "DS-SELF", "downstream_code": "DS-SELF",
    }, headers=H)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_lineage_asset_not_found(client):
    await _create_asset(client, "DS-EXIST")
    resp = await client.post("/api/governance/lineage", json={
        "upstream_code": "DS-EXIST", "downstream_code": "DS-MISSING",
    }, headers=H)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_lineage_duplicate_edge(client):
    await _create_asset(client, "DS-E1")
    await _create_asset(client, "DS-E2")
    payload = {"upstream_code": "DS-E1", "downstream_code": "DS-E2", "relation_type": "derived_from"}
    await client.post("/api/governance/lineage", json=payload, headers=H)
    resp = await client.post("/api/governance/lineage", json=payload, headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_lineages_by_upstream(client):
    await _create_asset(client, "DS-LUP")
    await _create_asset(client, "DS-LDOWN")
    await client.post("/api/governance/lineage", json={
        "upstream_code": "DS-LUP", "downstream_code": "DS-LDOWN",
    }, headers=H)
    resp = await client.get("/api/governance/lineage?upstream=DS-LUP", headers=H)
    assert resp.status_code == 200
    assert all(e["upstream_code"] == "DS-LUP" for e in resp.json()["items"])


@pytest.mark.asyncio
async def test_delete_lineage(client):
    await _create_asset(client, "DS-DELUP")
    await _create_asset(client, "DS-DELDOWN")
    created = await client.post("/api/governance/lineage", json={
        "upstream_code": "DS-DELUP", "downstream_code": "DS-DELDOWN",
    }, headers=H)
    lid = created.json()["id"]
    resp = await client.delete(f"/api/governance/lineage/{lid}", headers=H)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════════════════
# 数据质量规则
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_rule_success(client):
    await _create_asset(client, "DS-RULE-OWN")
    data = await _create_rule(client, "R-NOTNULL-01", "DS-RULE-OWN")
    assert data["code"] == "R-NOTNULL-01"
    assert data["severity"] == "warning"
    assert data["status"] == "enabled"


@pytest.mark.asyncio
async def test_create_rule_duplicate_code(client):
    await _create_asset(client, "DS-RDUP")
    await _create_rule(client, "R-DUP", "DS-RDUP")
    resp = await client.post("/api/governance/rules", json={
        "code": "R-DUP", "name": "重复", "asset_code": "DS-RDUP", "expression": "x > 0",
    }, headers=H)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_rule_asset_not_found(client):
    resp = await client.post("/api/governance/rules", json={
        "code": "R-BADASSET", "name": "坏资产", "asset_code": "DS-NOASSET",
        "expression": "x > 0",
    }, headers=H)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_rules_filter_and_keyword(client):
    await _create_asset(client, "DS-RLIST")
    await _create_rule(client, "R-LIST", "DS-RLIST")
    resp = await client.get("/api/governance/rules?asset_code=DS-RLIST", headers=H)
    assert resp.status_code == 200
    assert all(r["asset_code"] == "DS-RLIST" for r in resp.json()["items"])
    resp2 = await client.get("/api/governance/rules?keyword=R-LIST", headers=H)
    assert any(r["code"] == "R-LIST" for r in resp2.json()["items"])


@pytest.mark.asyncio
async def test_update_rule(client):
    await _create_asset(client, "DS-RUPD")
    rule = await _create_rule(client, "R-UPD", "DS-RUPD")
    resp = await client.patch(f"/api/governance/rules/{rule['id']}", json={
        "severity": "critical", "expression": "amount >= 0",
    }, headers=H)
    assert resp.status_code == 200
    assert resp.json()["severity"] == "critical"
    assert resp.json()["expression"] == "amount >= 0"


@pytest.mark.asyncio
async def test_disable_rule(client):
    await _create_asset(client, "DS-RDIS")
    rule = await _create_rule(client, "R-DIS", "DS-RDIS")
    resp = await client.patch(f"/api/governance/rules/{rule['id']}/status", json={
        "status": "disabled",
    }, headers=H)
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


@pytest.mark.asyncio
async def test_delete_rule(client):
    await _create_asset(client, "DS-RDEL")
    rule = await _create_rule(client, "R-DEL", "DS-RDEL")
    resp = await client.delete(f"/api/governance/rules/{rule['id']}", headers=H)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
