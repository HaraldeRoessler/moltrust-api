"""Operator-level budget cap tests.

Hard requirement (from Lars 2026-05-27 + F3 retro): NO prod-DB artifacts.
The fixture below cleans up *every* row it touches, in the right FK order,
even if the test fails mid-way.

Tests cover:
- Operator-claim flow + authz (only agent owner may claim).
- Cap CRUD via HTTP (PUT/GET/list).
- record_spend_event status transitions: active → warning → capped.
- Monthly lazy reset across month-key boundaries.
- Agents with no operator OR no cap: spend events are still logged but
  return `status: "no_cap"` (passes through).
- Suspended is sticky — accumulation doesn't change it.

Telegram alerts: not asserted directly (the helper is a fire-and-forget
network call; `_send_telegram_alert` no-ops without env vars, which is
the case in the test environment). Status transitions ARE asserted via
the dict returned from `record_spend_event` — that's the contract the
real Telegram-side observer would react to.
"""
from __future__ import annotations

import uuid

import pytest


# ---------------------------------------------------------------------------
# Fixture: create an operator + agent + linked api-key.
# Cleanup runs unconditionally in reverse-FK order.
# ---------------------------------------------------------------------------

@pytest.fixture
async def budget_test_actor(app_with_lifespan):
    """Returns a coroutine: () → (operator_did, agent_did, api_key).

    The operator_did equals the agent_did (current self-sovereign model:
    the API key owner is the agent, and the agent claims itself as its
    own operator). The fixture handles claiming so tests can jump straight
    to cap CRUD.
    """
    from app.main import db_pool, API_KEYS

    created: list[tuple[str, str]] = []  # (did, api_key)

    async def _make():
        did = f"did:moltrust:{uuid.uuid4().hex[:16]}"
        api_key = f"mt_bc_{uuid.uuid4().hex}"
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO agents (did, display_name, platform, agent_type, operator_did) "
                    "VALUES ($1, $2, 'test', 'external', $3)",
                    did, f"bc-{did[-8:]}", did,  # self-operator
                )
                await conn.execute(
                    "INSERT INTO api_keys (key, email, owner_did) VALUES ($1, $2, $3)",
                    api_key, f"test+{did[-8:]}@test.local", did,
                )
        API_KEYS.add(api_key)
        created.append((did, api_key))
        return did, did, api_key  # operator_did, agent_did, api_key

    yield _make

    async with db_pool.acquire() as conn:
        for did, api_key in created:
            await conn.execute("DELETE FROM budget_spend_events WHERE operator_did = $1 OR agent_did = $1", did)
            await conn.execute("DELETE FROM agent_budget_caps   WHERE operator_did = $1 OR agent_did = $1", did)
            await conn.execute("DELETE FROM api_keys            WHERE owner_did    = $1", did)
            await conn.execute("DELETE FROM agents              WHERE did          = $1", did)
            API_KEYS.discard(api_key)


# ---------------------------------------------------------------------------
# Operator-claim endpoint
# ---------------------------------------------------------------------------

async def test_claim_operator_self_succeeds(async_client, app_with_lifespan):
    from app.main import db_pool, API_KEYS

    did = f"did:moltrust:{uuid.uuid4().hex[:16]}"
    api_key = f"mt_bc_{uuid.uuid4().hex}"
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO agents (did, display_name, platform, agent_type) "
                    "VALUES ($1, $2, 'test', 'external')",
                    did, f"bc-{did[-8:]}",
                )
                await conn.execute(
                    "INSERT INTO api_keys (key, email, owner_did) VALUES ($1, $2, $3)",
                    api_key, f"test+{did[-8:]}@test.local", did,
                )
        API_KEYS.add(api_key)

        r = await async_client.post(
            f"/agents/{did}/operator",
            json={"operator_did": did},
            headers={"X-API-Key": api_key},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["agent_did"] == did
        assert body["operator_did"] == did

        async with db_pool.acquire() as conn:
            stored = await conn.fetchval(
                "SELECT operator_did FROM agents WHERE did = $1", did,
            )
        assert stored == did
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM api_keys WHERE owner_did = $1", did)
            await conn.execute("DELETE FROM agents   WHERE did       = $1", did)
        API_KEYS.discard(api_key)


async def test_claim_operator_rejects_non_owner(async_client, budget_test_actor):
    """An API key linked to a different DID cannot claim someone else's agent."""
    from app.main import db_pool, API_KEYS

    _, target_did, _ = await budget_test_actor()
    # Mint a stranger API key — different owner_did.
    stranger_did = f"did:moltrust:{uuid.uuid4().hex[:16]}"
    stranger_key = f"mt_bc_{uuid.uuid4().hex}"
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agents (did, display_name, platform, agent_type) "
                "VALUES ($1, 'stranger', 'test', 'external')", stranger_did,
            )
            await conn.execute(
                "INSERT INTO api_keys (key, email, owner_did) VALUES ($1, $2, $3)",
                stranger_key, f"stranger+{stranger_did[-8:]}@test.local", stranger_did,
            )
        API_KEYS.add(stranger_key)

        r = await async_client.post(
            f"/agents/{target_did}/operator",
            json={"operator_did": stranger_did},
            headers={"X-API-Key": stranger_key},
        )
        assert r.status_code == 403
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM api_keys WHERE owner_did = $1", stranger_did)
            await conn.execute("DELETE FROM agents   WHERE did       = $1", stranger_did)
        API_KEYS.discard(stranger_key)


# ---------------------------------------------------------------------------
# Cap CRUD via HTTP
# ---------------------------------------------------------------------------

async def test_put_budget_cap_creates_and_returns_shape(async_client, budget_test_actor):
    op, agent, key = await budget_test_actor()
    r = await async_client.put(
        f"/operators/{op}/agents/{agent}/budget-cap",
        json={"monthly_cap_chf": 50.0, "warning_threshold": 0.8},
        headers={"X-API-Key": key},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["operator_did"] == op
    assert body["agent_did"] == agent
    assert body["monthly_cap_chf"] == 50.0
    assert body["warning_threshold"] == 0.8
    assert body["current_month_spend"] == 0.0
    assert body["status"] == "active"
    assert body["spend_percentage"] == 0.0


async def test_get_budget_cap(async_client, budget_test_actor):
    op, agent, key = await budget_test_actor()
    await async_client.put(
        f"/operators/{op}/agents/{agent}/budget-cap",
        json={"monthly_cap_chf": 20.0},
        headers={"X-API-Key": key},
    )
    r = await async_client.get(
        f"/operators/{op}/agents/{agent}/budget-cap",
        headers={"X-API-Key": key},
    )
    assert r.status_code == 200
    assert r.json()["monthly_cap_chf"] == 20.0


async def test_get_budget_cap_unset_returns_404(async_client, budget_test_actor):
    op, agent, key = await budget_test_actor()
    r = await async_client.get(
        f"/operators/{op}/agents/{agent}/budget-cap",
        headers={"X-API-Key": key},
    )
    assert r.status_code == 404


async def test_list_all_caps_sums_totals(async_client, budget_test_actor):
    op, agent_a, key = await budget_test_actor()
    # Spin up a second agent under the same operator. We forge a second
    # row via DB directly — cap endpoints need the agent to be operated
    # already.
    from app.main import db_pool
    agent_b = f"did:moltrust:{uuid.uuid4().hex[:16]}"
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agents (did, display_name, platform, agent_type, operator_did) "
                "VALUES ($1, $2, 'test', 'external', $3)",
                agent_b, f"bc-{agent_b[-8:]}", op,
            )
        await async_client.put(
            f"/operators/{op}/agents/{agent_a}/budget-cap",
            json={"monthly_cap_chf": 30.0},
            headers={"X-API-Key": key},
        )
        await async_client.put(
            f"/operators/{op}/agents/{agent_b}/budget-cap",
            json={"monthly_cap_chf": 70.0},
            headers={"X-API-Key": key},
        )
        r = await async_client.get(
            f"/operators/{op}/budget-caps",
            headers={"X-API-Key": key},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total_monthly_cap_chf"] == 100.0
        assert len(body["agents"]) == 2
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_budget_caps WHERE agent_did = $1", agent_b)
            await conn.execute("DELETE FROM agents WHERE did = $1", agent_b)


async def test_authz_rejects_foreign_operator_path(async_client, budget_test_actor):
    op_a, agent_a, key_a = await budget_test_actor()
    op_b, _, _ = await budget_test_actor()  # different operator
    r = await async_client.put(
        f"/operators/{op_b}/agents/{agent_a}/budget-cap",
        json={"monthly_cap_chf": 10.0},
        headers={"X-API-Key": key_a},  # key_a's owner_did is op_a, not op_b
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# record_spend_event — status state machine
# ---------------------------------------------------------------------------

async def test_no_cap_no_restriction(budget_test_actor):
    """An agent with no cap row still has its spend logged but the call
    short-circuits with status=no_cap. No state change anywhere."""
    from app.main import db_pool
    from app.budget import record_spend_event

    op, agent, _ = await budget_test_actor()
    async with db_pool.acquire() as conn:
        result = await record_spend_event(conn, agent, "issuance", 0.30)
    assert result["status"] == "no_cap"
    assert result["transition"] is None


async def test_unmetered_agent_still_logs_event(budget_test_actor):
    """When agents.operator_did is NULL, spend events are still appended
    to budget_spend_events (with operator_did='') so analytics sees usage."""
    from app.main import db_pool
    from app.budget import record_spend_event

    _, agent, _ = await budget_test_actor()
    # Strip the operator link to simulate an unmetered agent.
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE agents SET operator_did = NULL WHERE did = $1", agent)
        result = await record_spend_event(conn, agent, "issuance", 0.30)
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM budget_spend_events WHERE agent_did = $1", agent,
        )
    assert result["status"] == "no_cap"
    assert count == 1


async def test_spend_accumulates_and_crosses_warning(budget_test_actor):
    from app.main import db_pool
    from app.budget import upsert_cap, record_spend_event

    op, agent, _ = await budget_test_actor()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await upsert_cap(conn, op, agent, monthly_cap_chf=10.0, warning_threshold=0.8)

        r1 = await record_spend_event(conn, agent, "issuance", 4.0)
        assert r1["status"] == "active"
        assert r1["transition"] is None

        r2 = await record_spend_event(conn, agent, "issuance", 5.0)  # cumulative 9.0 = 90%
        assert r2["status"] == "warning"
        assert r2["transition"] == "active→warning"
        assert r2["spend_pct"] == 0.9


async def test_spend_crosses_to_capped(budget_test_actor):
    from app.main import db_pool
    from app.budget import upsert_cap, record_spend_event

    op, agent, _ = await budget_test_actor()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await upsert_cap(conn, op, agent, monthly_cap_chf=10.0)
        r = await record_spend_event(conn, agent, "anchor", 11.5)
    assert r["status"] == "capped"
    assert r["transition"] == "active→capped"
    assert r["spend_pct"] >= 1.0


async def test_capped_status_persists_in_cap_table(budget_test_actor):
    """After crossing into capped, the cap row's status reflects that."""
    from app.main import db_pool
    from app.budget import upsert_cap, record_spend_event, get_cap

    op, agent, _ = await budget_test_actor()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await upsert_cap(conn, op, agent, monthly_cap_chf=5.0)
        await record_spend_event(conn, agent, "issuance", 6.0)
        result = await get_cap(conn, op, agent)
    assert result["status"] == "capped"
    assert result["current_month_spend"] == 6.0


async def test_suspended_is_sticky(budget_test_actor):
    """Manually set status='suspended'. record_spend_event must NOT
    flip it back to active/warning/capped."""
    from app.main import db_pool
    from app.budget import upsert_cap, record_spend_event, get_cap

    op, agent, _ = await budget_test_actor()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await upsert_cap(conn, op, agent, monthly_cap_chf=10.0)
        await conn.execute(
            "UPDATE agent_budget_caps SET status='suspended' "
            "WHERE operator_did=$1 AND agent_did=$2", op, agent,
        )
        r = await record_spend_event(conn, agent, "issuance", 3.0)
        result = await get_cap(conn, op, agent)
    assert r["status"] == "suspended"
    assert result["status"] == "suspended"


# ---------------------------------------------------------------------------
# Monthly reset
# ---------------------------------------------------------------------------

async def test_monthly_reset_clears_spend_and_active_status(budget_test_actor):
    from app.main import db_pool
    from app.budget import upsert_cap, record_spend_event, get_cap

    op, agent, _ = await budget_test_actor()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await upsert_cap(conn, op, agent, monthly_cap_chf=10.0)
        # Cross into capped this month.
        await record_spend_event(conn, agent, "issuance", 11.0)

        # Force-stamp the row with a stale month key — the next read should
        # lazily reset spend → 0 and status → active.
        await conn.execute(
            "UPDATE agent_budget_caps SET current_month_key='2020-01' "
            "WHERE operator_did=$1 AND agent_did=$2", op, agent,
        )
        result = await get_cap(conn, op, agent)
    assert result["current_month_spend"] == 0.0
    assert result["status"] == "active"
    assert result["current_month_key"] != "2020-01"


async def test_monthly_reset_does_not_revive_suspended(budget_test_actor):
    from app.main import db_pool
    from app.budget import upsert_cap, get_cap

    op, agent, _ = await budget_test_actor()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await upsert_cap(conn, op, agent, monthly_cap_chf=10.0)
        await conn.execute(
            "UPDATE agent_budget_caps "
            "SET status='suspended', current_month_spend=5.0, current_month_key='2020-01' "
            "WHERE operator_did=$1 AND agent_did=$2", op, agent,
        )
        result = await get_cap(conn, op, agent)
    # Suspended is sticky; spend is left alone too — only the month-key ticks
    # forward so the row reads as up-to-date.
    assert result["status"] == "suspended"
    assert result["current_month_spend"] == 5.0
    assert result["current_month_key"] != "2020-01"
