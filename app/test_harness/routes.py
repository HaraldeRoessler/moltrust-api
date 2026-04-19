"""Test harness endpoint for bilateral cross-verify interactions.

Enables partner agents (AgentNexus, AKF, others) to execute a
bilateral skill-invocation handshake that:
  1. Records a signed interaction proof
  2. Returns a signed attestation
  3. Trust score updates happen asynchronously via endorsement pipeline

NOT a production skill. Reference implementation for ecosystem handshake tests.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import json
import hashlib
import os

router = APIRouter(prefix="/test-harness", tags=["test-harness"])

TEST_HARNESS_DID = "did:moltrust:te5tharne550001"
SK_PATH = os.path.expanduser("~/.testharness_sk_b58")

DB_CONFIG = {
    "host": "localhost",
    "database": "moltstack",
    "user": "moltstack",
}


def _sign_message(message: str) -> str:
    """Sign a message with the test-harness Ed25519 key."""
    import base58
    from nacl.signing import SigningKey
    with open(SK_PATH) as f:
        sk_b58 = f.read().strip()
    sk = SigningKey(base58.b58decode(sk_b58))
    sig = sk.sign(message.encode()).signature
    return base58.b58encode(sig).decode()


class InvokeRequest(BaseModel):
    caller_did: str = Field(..., description="The invoking agent's DID (any method)")
    intent: str = Field("ping", description="Test intent: ping, handshake, or custom")
    nonce: Optional[str] = Field(None, description="Optional nonce for replay protection")


@router.post("/invoke")
async def invoke(req: InvokeRequest):
    """Execute a test cross-verify interaction.

    Accepts any DID method. Records interaction, signs attestation.
    Trust score updates are asynchronous.
    """
    if not req.caller_did.startswith("did:") or len(req.caller_did.split(":")) < 3:
        raise HTTPException(400, f"Invalid DID format: {req.caller_did}")

    now = datetime.now(timezone.utc)
    caller_short = req.caller_did.split(":")[-1][:8]
    interaction_id = f"ipr_test_{now.strftime('%Y%m%d%H%M%S')}_{caller_short}"

    ipr_payload = {
        "interaction_id": interaction_id,
        "target": TEST_HARNESS_DID,
        "caller": req.caller_did,
        "intent": req.intent,
        "nonce": req.nonce,
        "timestamp": now.isoformat(),
    }

    ipr_json = json.dumps(ipr_payload, sort_keys=True)
    ipr_hash = hashlib.sha256(ipr_json.encode()).hexdigest()
    signature = _sign_message(ipr_hash)

    # Try to persist + look up caller score (non-fatal)
    score_before = None
    db_status = "ok"
    try:
        import asyncpg
        conn = await asyncpg.connect(**DB_CONFIG)

        # Caller score lookup
        cached = await conn.fetchrow(
            "SELECT score FROM trust_score_cache WHERE did = $1", req.caller_did
        )
        if cached and cached["score"] is not None and cached["score"] >= 0:
            score_before = float(cached["score"])

        # Record interaction in interaction_proof_records
        import uuid
        await conn.execute(
            """INSERT INTO interaction_proof_records
               (id, schema_version, agent_did, output_hash, output_type,
                source_hashes, source_refs, confidence, confidence_basis,
                agent_signature, produced_at, created_at, anchor_status,
                anchor_retries, chain)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)""",
            uuid.uuid4(), "1.0", TEST_HARNESS_DID, f"sha256:{ipr_hash}", "test_harness_invoke",
            json.dumps([]), json.dumps([]), 1.0, "bilateral_handshake",
            signature, now, now, "pending", 0, "base",
        )

        await conn.close()
    except Exception as e:
        db_status = f"non_fatal_error: {str(e)[:100]}"

    return {
        "interaction_id": interaction_id,
        "target_did": TEST_HARNESS_DID,
        "caller_did": req.caller_did,
        "intent": req.intent,
        "timestamp": now.isoformat(),
        "ipr_hash": ipr_hash,
        "signature": signature,
        "signature_algorithm": "Ed25519",
        "trust_score_update": {
            "caller_score_before": score_before,
            "note": "Score updates are asynchronous; re-check via /skill/trust-score/{did} after 60s",
        },
        "db_status": db_status,
    }


@router.get("/info")
async def info():
    """Public metadata for test harness — for partner discovery."""
    return {
        "target_did": TEST_HARNESS_DID,
        "endpoint": "/test-harness/invoke",
        "purpose": "Bilateral cross-verify handshake testing",
        "method": "POST",
        "accepts_did_methods": [
            "did:moltrust", "did:agentnexus", "did:ethr",
            "did:web", "did:key", "did:pkh",
        ],
        "request_schema": {
            "caller_did": "string (required) — your agent's DID",
            "intent": "string (optional, default: ping)",
            "nonce": "string (optional) — replay protection",
        },
        "response_includes": [
            "interaction_id", "ipr_hash (SHA-256)",
            "signature (Ed25519, base58)", "caller trust score",
        ],
        "signature_algorithm": "Ed25519",
        "public_key_hex": "1a821b21d7ce5e6825d9b5f091738f3405c84faa50053903794368a40d3b403e",
        "resolution_url": f"https://uresolver.moltrust.ch/1.0/identifiers/{TEST_HARNESS_DID}",
        "trust_score_url": f"https://api.moltrust.ch/skill/trust-score/{TEST_HARNESS_DID}",
        "documentation": "Public test endpoint for ecosystem partner handshake tests.",
    }
