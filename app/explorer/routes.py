"""Explorer routes: public agent discovery with trust math shown.

All endpoints read-only. No authentication required (public explorer).
Data source: v_explorer_agents view (joined erc8004_outreach + agents + trust_score_cache).
Uses asyncpg pool (same as main app).
"""

from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional, Literal
import asyncpg
import os

router = APIRouter(prefix="/explorer", tags=["explorer"])

DB_CONFIG = {
    "host": "localhost",
    "database": os.getenv("DB_NAME", "moltstack"),
    "user": "moltstack",
}

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=5)
    return _pool


@router.get("/stats")
async def get_stats():
    """Aggregate stats across all indexed sources."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM v_explorer_stats")

        total = sum(r["total_indexed"] for r in rows)
        verified = sum(r["moltrust_verified"] for r in rows)
        contacted = sum(r["contacted"] for r in rows)
        indexed = sum(r["indexed_only"] for r in rows)

        by_source = {}
        by_chain = {}
        for r in rows:
            by_source[r["source"]] = by_source.get(r["source"], 0) + r["total_indexed"]
            by_chain[r["chain"]] = by_chain.get(r["chain"], 0) + r["total_indexed"]

        return {
            "total_indexed": total,
            "moltrust_verified": verified,
            "contacted": contacted,
            "indexed_only": indexed,
            "by_source": by_source,
            "by_chain": by_chain,
        }


@router.get("/agents")
async def list_agents(
    source: Optional[str] = Query(None, description="Filter by source (erc8004, virtuals, farcaster)"),
    chain: Optional[str] = Query(None, description="Filter by chain (base, ethereum, solana)"),
    verification: Optional[Literal["moltrust_verified", "contacted_not_verified", "indexed_only"]] = None,
    min_score: Optional[float] = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Paginated agent list with filters."""
    conditions = []
    params = []
    idx = 1

    if source:
        conditions.append(f"source = ${idx}")
        params.append(source)
        idx += 1
    if chain:
        conditions.append(f"chain = ${idx}")
        params.append(chain)
        idx += 1
    if verification:
        conditions.append(f"verification_status = ${idx}")
        params.append(verification)
        idx += 1
    if min_score is not None:
        conditions.append(f"moltrust_trust_score >= ${idx}")
        params.append(min_score)
        idx += 1

    where = " AND ".join(conditions) if conditions else "TRUE"
    query = f"""
        SELECT * FROM v_explorer_agents
        WHERE {where}
        ORDER BY COALESCE(moltrust_trust_score, 0) DESC,
                 external_registered_at DESC NULLS LAST
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    params.extend([limit, offset])

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [
            {
                "external_agent_id": r["external_agent_id"],
                "wallet_address": r["wallet_address"],
                "chain": r["chain"],
                "source": r["source"],
                "verification_status": r["verification_status"],
                "moltrust_did": r["moltrust_did"],
                "moltrust_trust_score": float(r["moltrust_trust_score"]) if r["moltrust_trust_score"] is not None else None,
                "external_registered_at": r["external_registered_at"].isoformat() if r["external_registered_at"] else None,
                "moltrust_registered_at": r["moltrust_registered_at"].isoformat() if r["moltrust_registered_at"] else None,
            }
            for r in rows
        ]


@router.get("/agent/{identifier}")
async def get_agent(identifier: str):
    """
    Single agent detail with full trust math.
    Identifier can be: did:moltrust:..., erc8004:<id>, or 0x wallet address.
    """
    if identifier.startswith("did:moltrust:"):
        where = "moltrust_did = $1"
    elif identifier.startswith("erc8004:"):
        where = "external_agent_id = $1::int AND source = 'erc8004'"
        identifier = identifier.replace("erc8004:", "")
        identifier = int(identifier)
    elif identifier.startswith("0x"):
        where = "wallet_address = $1"
    else:
        try:
            identifier = int(identifier)
            where = "external_agent_id = $1"
        except ValueError:
            raise HTTPException(400, "Invalid identifier format. Use did:moltrust:..., erc8004:<id>, or 0x<wallet>")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM v_explorer_agents WHERE {where} LIMIT 1",
            identifier,
        )

        if not row:
            raise HTTPException(404, f"Agent not found: {identifier}")

        agent = {
            "external_agent_id": row["external_agent_id"],
            "wallet_address": row["wallet_address"],
            "chain": row["chain"],
            "source": row["source"],
            "verification_status": row["verification_status"],
            "moltrust_did": row["moltrust_did"],
            "moltrust_trust_score": float(row["moltrust_trust_score"]) if row["moltrust_trust_score"] is not None else None,
            "external_registered_at": row["external_registered_at"].isoformat() if row["external_registered_at"] else None,
            "moltrust_registered_at": row["moltrust_registered_at"].isoformat() if row["moltrust_registered_at"] else None,
            "metadata_uri": row["metadata_uri"],
        }

        # Trust breakdown if MolTrust-verified
        trust_breakdown = None
        if row["moltrust_did"] and row["moltrust_trust_score"] is not None:
            cached = await conn.fetchrow(
                """SELECT score, endorser_count, propagated_score, cross_vertical_bonus,
                          computation_method, cache_valid_until
                   FROM trust_score_cache WHERE did = $1""",
                row["moltrust_did"],
            )
            if cached:
                trust_breakdown = {
                    "final_score": float(cached["score"]) if cached["score"] is not None else None,
                    "components": {
                        "direct_endorsements": {"weight": 0.6, "note": f"{cached['endorser_count']} endorsers"},
                        "propagated_trust": {"value": float(cached["propagated_score"] or 0), "weight": 0.3},
                        "cross_vertical": {"value": float(cached["cross_vertical_bonus"] or 0), "weight": 0.1},
                    },
                    "computation_method": cached["computation_method"],
                    "formula": "score = 0.6*direct + 0.3*propagated + 0.1*cross_vertical + bonuses - sybil_penalty*20",
                    "methodology_url": "/explorer/methodology",
                }

        # Flags stub (Phase B: real sybil/anomaly data)
        flags = []

        return {
            "agent": agent,
            "trust_breakdown": trust_breakdown,
            "flags": flags,
            "metadata_uri": row["metadata_uri"],
        }


@router.get("/methodology")
async def get_methodology():
    """Static methodology document."""
    return {
        "version": "1.0",
        "trust_score_formula": {
            "formula": "score = alpha*direct + beta*propagated + gamma*cross_vertical + bonuses - sybil_penalty*20",
            "parameters": {
                "alpha": {"value": 0.6, "meaning": "Weight on direct endorsements from verified agents"},
                "beta": {"value": 0.3, "meaning": "Weight on propagated trust through endorsement graph"},
                "gamma": {"value": 0.1, "meaning": "Bonus for endorsements spanning multiple verticals"},
            },
            "time_decay": "90-day half-life on endorsement evidence",
            "score_range": "0 to 100, advisory not enforcement",
        },
        "sybil_detection": {
            "signals": [
                {"name": "jaccard_clustering", "weight": 6, "description": "Densely interconnected endorsement subgraphs with no external bridging"},
                {"name": "common_funder", "weight": 6, "description": "Multiple wallets funded from the same source address"},
                {"name": "inhuman_velocity", "weight": 5, "description": "Endorsement patterns beyond plausible human cadence"},
                {"name": "score_clustering", "weight": 1, "description": "Wallets giving near-identical scores across many agents"},
                {"name": "sweep_pattern", "weight": 3, "description": "Reviewers endorsing many agents then never returning"},
            ],
            "severity_tiers": {"low": "0-2", "moderate": "3-9", "elevated": "10-19", "heavy": "20+"},
        },
        "flag_philosophy": {
            "framing": "Patterns detected. You decide.",
            "disclaimer": "A flag describes what happened, not why.",
        },
        "enforcement_class": "advisory",
        "standards_alignment": ["W3C DID 1.0", "W3C VC 2.0", "DIF Universal Resolver", "A2A v0.3"],
        "sources_indexed": {
            "erc8004": {"status": "live", "chain": "base", "scanner_cron": "daily 06:30 UTC"},
            "virtuals": {"status": "planned", "chain": "base"},
            "farcaster": {"status": "planned", "chain": "farcaster"},
        },
    }
