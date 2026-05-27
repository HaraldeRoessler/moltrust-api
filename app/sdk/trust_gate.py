"""Python helper for the MolTrust trust-gating endpoint (F3).

Designed to be the single line a Python agent needs to insert before any
Agent-to-Agent transaction:

    from app.sdk.trust_gate import verify

    result = verify("did:moltrust:counterparty", min_score=60)
    if not result["allowed"]:
        raise RuntimeError(f"Counterparty not trusted: {result['reason']}")

This module is intentionally dependency-light (requests only) so it can be
lifted out into a standalone `moltrust-sdk` PyPI package without code
changes. Until that package exists, agents in this repo and elsewhere can
import it directly.
"""
from __future__ import annotations

from typing import Optional, TypedDict

import requests

DEFAULT_API_BASE = "https://api.moltrust.ch"
DEFAULT_MIN_SCORE = 50.0
DEFAULT_TIMEOUT_SECONDS = 5.0


class GateResult(TypedDict, total=False):
    allowed: bool
    decision: str        # "ALLOW" | "DENY"
    score: Optional[float]
    reason: Optional[str]
    score_source: Optional[str]


def verify(
    did: str,
    *,
    min_score: float = DEFAULT_MIN_SCORE,
    context: Optional[str] = None,
    allow_cold_start: bool = False,
    api_base: str = DEFAULT_API_BASE,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> GateResult:
    """Ask the MolTrust trust-gating endpoint whether `did` should be allowed.

    Args:
        did: Counter-party DID (e.g. `did:moltrust:abc123`).
        min_score: Minimum trust score required (0–100). Default 50.
        context: Optional label persisted to the gate audit log
            (e.g. "payment", "data_access"). Helpful for retro-analysis.
        allow_cold_start: When `True`, cold-start scores (derived from
            public on-chain / GitHub / ERC-8004 signals) count toward
            ALLOW. Default `False` keeps the flywheel pressure on agents
            to accumulate real endorsements.
        api_base: Override for non-prod environments.
        timeout: Seconds before the HTTP call gives up. Default 5.0 — keep
            short so a slow gate never blocks a hot path.

    Returns:
        A `GateResult` dict. `allowed` is `True` iff `decision == "ALLOW"`.
        On any transport failure (timeout, DNS, 5xx) returns
        `{"allowed": False, "decision": "DENY", "reason": "gate_unreachable"}`
        — fail closed so a network outage cannot grant access.
    """
    url = f"{api_base.rstrip('/')}/trust/gate/{did}"
    params: dict[str, object] = {"min_score": min_score}
    if context:
        params["context"] = context
    if allow_cold_start:
        params["allow_cold_start"] = "true"

    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        body = r.json()
    except (requests.RequestException, ValueError):
        return {
            "allowed": False,
            "decision": "DENY",
            "score": None,
            "reason": "gate_unreachable",
            "score_source": None,
        }

    decision = body.get("decision", "DENY")
    return {
        "allowed": decision == "ALLOW",
        "decision": decision,
        "score": body.get("trust_score"),
        "reason": body.get("reason"),
        "score_source": body.get("score_source"),
    }
