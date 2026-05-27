"""F3 trust-gating endpoint tests.

Covers the full decision tree of `/trust/gate/{did}`:
- agent_not_found
- behavioral ALLOW + behavioral DENY (insufficient_trust_score)
- score_withheld (default — cold-start opt-in is `false`)
- cold-start ALLOW + cold-start DENY (insufficient_trust_score)
- cold-start no public data → score_withheld
- default `min_score = 50` when query param omitted
- audit log row written for every call
- always HTTP 200, even for unknown agents

Rate-limiting is configured at decorator level (`@limiter.limit("100/minute")`)
and is not exercised here — it would require 100 rapid in-memory calls
against the slowapi limiter state, which is fragile under parallel tests.

Setup details:
- Test DIDs use the `did:moltrust:<16hex>` pattern that DID_PATTERN accepts
  AND that conftest's existing cleanup ignores by default (no `test_`
  string prefix). We clean our own rows in a fixture.
- "Behavioral" score paths use `swarm_seeds.base_score` to bypass the
  `< 3 endorsers → withheld` rule — seeds always get their `base_score`
  as the trust score directly.
- Cold-start paths pre-populate `agents.cold_start_*` so the 24h cache
  short-circuits any actual Basescan / GitHub HTTP call.
"""
import uuid

import pytest


# ---------------------------------------------------------------------------
# Fixture — make agents with various profiles, clean them up after the test.
# ---------------------------------------------------------------------------

@pytest.fixture
async def gate_test_agent(app_with_lifespan):
    """Factory returning a coroutine: kind → (did,).

    Kinds:
      `bare`              — plain agent, no endorsements, no cold-start data
      `seed:<score>`      — agent + swarm_seeds row with base_score = <score>
      `cold:<score>`      — agent with cold_start_score pre-set (24h cache),
                            basis "onchain", confidence "medium"
    """
    from app.main import db_pool
    created_dids: list[str] = []

    async def _make(kind: str):
        did = f"did:moltrust:{uuid.uuid4().hex[:16]}"
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO agents (did, display_name, platform, agent_type) "
                    "VALUES ($1, $2, 'test', 'external')",
                    did, f"tg-{did[-8:]}",
                )
                if kind.startswith("seed:"):
                    base_score = float(kind.split(":", 1)[1])
                    await conn.execute(
                        "INSERT INTO swarm_seeds (did, base_score) VALUES ($1, $2) "
                        "ON CONFLICT (did) DO UPDATE SET base_score = EXCLUDED.base_score",
                        did, base_score,
                    )
                elif kind.startswith("cold:"):
                    score = float(kind.split(":", 1)[1])
                    await conn.execute(
                        "UPDATE agents SET cold_start_score = $1, "
                        "cold_start_basis = 'onchain', "
                        "cold_start_confidence = 'medium', "
                        "cold_start_computed_at = NOW() "
                        "WHERE did = $2",
                        score, did,
                    )
                elif kind != "bare":
                    raise ValueError(f"unknown kind: {kind}")
        created_dids.append(did)
        return did

    yield _make

    async with db_pool.acquire() as conn:
        for did in created_dids:
            await conn.execute("DELETE FROM gate_events       WHERE queried_did = $1", did)
            await conn.execute("DELETE FROM trust_score_cache WHERE did = $1",         did)
            await conn.execute("DELETE FROM swarm_seeds       WHERE did = $1",         did)
            await conn.execute("DELETE FROM agents            WHERE did = $1",         did)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_deny_unknown_agent_returns_200(async_client):
    did = f"did:moltrust:{uuid.uuid4().hex[:16]}"
    r = await async_client.get(f"/trust/gate/{did}")
    assert r.status_code == 200, "decisions live in the body, not HTTP status"
    body = r.json()
    assert body["decision"] == "DENY"
    assert body["reason"] == "agent_not_found"
    assert body["trust_score"] is None
    assert body["register_url"].startswith("https://moltrust.ch")


async def test_default_min_score_is_50(async_client, gate_test_agent):
    did = await gate_test_agent("bare")
    r = await async_client.get(f"/trust/gate/{did}")
    body = r.json()
    assert body["min_score_required"] == 50


async def test_bare_agent_default_denies_score_withheld(async_client, gate_test_agent):
    did = await gate_test_agent("bare")
    r = await async_client.get(f"/trust/gate/{did}")
    body = r.json()
    assert body["decision"] == "DENY"
    assert body["reason"] == "score_withheld", \
        "fewer than 3 endorsements + cold-start NOT opted-in → score_withheld"
    assert body["trust_score"] is None


async def test_seed_above_min_score_allow_behavioral(async_client, gate_test_agent):
    did = await gate_test_agent("seed:85")
    r = await async_client.get(f"/trust/gate/{did}", params={"min_score": 50})
    body = r.json()
    assert body["decision"] == "ALLOW"
    assert body["score_source"] == "behavioral"
    assert body["trust_score"] == 85.0
    assert "verified_at" in body


async def test_seed_below_min_denies_insufficient_trust_score(async_client, gate_test_agent):
    did = await gate_test_agent("seed:20")
    r = await async_client.get(f"/trust/gate/{did}", params={"min_score": 50})
    body = r.json()
    assert body["decision"] == "DENY"
    assert body["reason"] == "insufficient_trust_score"
    assert body["score_source"] == "behavioral"
    assert body["trust_score"] == 20.0


async def test_cold_start_opt_in_above_min_allow(async_client, gate_test_agent):
    did = await gate_test_agent("cold:70")
    r = await async_client.get(
        f"/trust/gate/{did}",
        params={"min_score": 50, "allow_cold_start": "true"},
    )
    body = r.json()
    assert body["decision"] == "ALLOW"
    assert body["score_source"] == "cold_start"
    assert body["trust_score"] == 70.0


async def test_cold_start_opt_in_below_min_deny(async_client, gate_test_agent):
    did = await gate_test_agent("cold:10")
    r = await async_client.get(
        f"/trust/gate/{did}",
        params={"min_score": 50, "allow_cold_start": "true"},
    )
    body = r.json()
    assert body["decision"] == "DENY"
    assert body["reason"] == "insufficient_trust_score"
    assert body["score_source"] == "cold_start"
    assert body["trust_score"] == 10.0


async def test_cold_start_opt_in_no_public_data_score_withheld(async_client, gate_test_agent):
    # `bare` agent has no cold_start_* row → compute returns null →
    # gate replies score_withheld even though cold-start was opted in.
    did = await gate_test_agent("bare")
    r = await async_client.get(
        f"/trust/gate/{did}",
        params={"min_score": 50, "allow_cold_start": "true"},
    )
    body = r.json()
    assert body["decision"] == "DENY"
    assert body["reason"] == "score_withheld"


async def test_cold_start_default_off_ignores_existing_score(async_client, gate_test_agent):
    """Even when a cold-start score exists, the default `allow_cold_start=false`
    must NOT use it. The flywheel design rests on this — cold-start is opt-in."""
    did = await gate_test_agent("cold:99")
    r = await async_client.get(f"/trust/gate/{did}", params={"min_score": 50})
    body = r.json()
    assert body["decision"] == "DENY"
    assert body["reason"] == "score_withheld"


async def test_gate_event_logged(async_client, gate_test_agent):
    from app.main import db_pool

    did = await gate_test_agent("seed:75")
    r = await async_client.get(
        f"/trust/gate/{did}",
        params={"min_score": 60, "context": "test_payment"},
    )
    assert r.json()["decision"] == "ALLOW"

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT decision, reason, score_source, trust_score, "
            "min_score_required, allow_cold_start, context "
            "FROM gate_events WHERE queried_did = $1 "
            "ORDER BY created_at DESC LIMIT 1",
            did,
        )
    assert row is not None, "gate_events row must be written for every call"
    assert row["decision"] == "ALLOW"
    assert row["reason"] is None
    assert row["score_source"] == "behavioral"
    assert row["trust_score"] == 75.0
    assert row["min_score_required"] == 60.0
    assert row["allow_cold_start"] is False
    assert row["context"] == "test_payment"
