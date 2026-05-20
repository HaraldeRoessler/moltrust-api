"""
Build-time MoltGuard Discovery lookup (Discovery-Phase-2 §9.4 Variante A).

Fetches /guard/openapi.json from MoltGuard, caches it, and exposes
helper functions to build the extendedAgentCard fields without any
MoltGuard-specific hardcodes.

Acceptance criterion (SPEC §9.4):
    grep -nE "events-feed|/guard/api/|/guard/events" app/main.py
    → must produce 0 hits after P3.

Architecture decisions (confirmed 2026-05-20):
  - Fetch timing: hybrid — eager at FastAPI startup with 3s timeout,
    falls back to lazy on first request if startup-fetch failed.
  - Cache TTL: 1 hour. Refresh runs in background via asyncio.create_task.
  - Fail mode: graceful-degrade on cold-start failure (extendedAgentCard
    returns without MoltGuard fields); stale-while-revalidate for
    subsequent refresh failures (serves last-known-good cache).
  - Skills granularity: single 'moltguard-discovery' skill replaces the
    previous 3 hardcoded MoltGuard skill entries.

This module is the only place that knows MoltGuard's path/pricing/skill
shape. Adding/removing endpoints in MoltGuard requires no change here —
they flow through automatically via /guard/openapi.json refresh.
"""

import asyncio
import json
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

MOLTGUARD_OPENAPI_URL = "https://api.moltrust.ch/guard/openapi.json"
FETCH_TIMEOUT_S = 3.0
CACHE_TTL_S = 3600  # 1 hour

# Hardening limits — addresses §2.3 cross-review P0/P1 findings (2026-05-20):
MAX_RESPONSE_SIZE_BYTES = 1_000_000  # 1 MB. Current spec is ~53 KB; generous headroom + DoS cap.
MAX_PATHS = 500   # Spec has ~67 paths; cap prevents amplification injection.
MAX_TAGS = 50     # Spec has 14 tags; same.
MIN_FETCH_INTERVAL_S = 30.0  # Circuit breaker: at most one fetch attempt per 30s per process.

# Module-level cache state. Matches the style of _AGENT_CARD_CACHE in main.py.
_cache: Optional[dict] = None
_cache_at: float = 0.0
_last_fetch_attempt_at: float = 0.0
_refresh_lock = asyncio.Lock()
_background_refresh_in_progress: bool = False


async def _fetch_spec() -> Optional[dict]:
    """
    Fetch /guard/openapi.json with timeout, size cap, and basic shape validation.
    Returns None on any failure (logged with exception type only, no message).

    Hardening (§2.3 cross-review P0/P1):
    - Circuit breaker: skips fetch when last attempt < MIN_FETCH_INTERVAL_S ago.
    - Streamed fetch with hard size cap (MAX_RESPONSE_SIZE_BYTES).
    - Shape validation: paths must be dict, tags must be list, both within size caps.
    - No exception message in logs (only type name).
    """
    global _last_fetch_attempt_at
    now = time.time()
    if (now - _last_fetch_attempt_at) < MIN_FETCH_INTERVAL_S:
        return None
    _last_fetch_attempt_at = now

    try:
        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_S) as client:
            async with client.stream("GET", MOLTGUARD_OPENAPI_URL) as r:
                r.raise_for_status()
                buf = bytearray()
                async for chunk in r.aiter_bytes(chunk_size=65536):
                    buf.extend(chunk)
                    if len(buf) > MAX_RESPONSE_SIZE_BYTES:
                        logger.warning(
                            f"moltguard_discovery: response exceeded {MAX_RESPONSE_SIZE_BYTES} bytes, aborting"
                        )
                        return None
        data = json.loads(bytes(buf))
        if not isinstance(data, dict):
            logger.warning("moltguard_discovery: response root is not a JSON object")
            return None
        paths = data.get("paths")
        if not isinstance(paths, dict):
            logger.warning("moltguard_discovery: spec.paths is missing or not a dict")
            return None
        if len(paths) > MAX_PATHS:
            logger.warning(
                f"moltguard_discovery: spec has {len(paths)} paths, exceeds cap {MAX_PATHS}"
            )
            return None
        tags = data.get("tags", [])
        if not isinstance(tags, list) or len(tags) > MAX_TAGS:
            logger.warning("moltguard_discovery: spec.tags malformed or exceeds cap")
            return None
        return data
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"moltguard_discovery: fetch failed: {type(e).__name__}")
        return None


async def warm_cache_on_startup() -> None:
    """Eager cache warmup at FastAPI startup. Failure logs a warning but does not block startup."""
    global _cache, _cache_at
    spec = await _fetch_spec()
    if spec is not None:
        _cache = spec
        _cache_at = time.time()
        logger.info(f"moltguard_discovery: cache warmed at startup, {len(spec.get('paths', {}))} paths")
    else:
        logger.warning("moltguard_discovery: cold-start fetch failed; extendedAgentCard will graceful-degrade until lazy-retry succeeds")


async def _background_refresh() -> None:
    """
    Refresh cache in background. Only updates cache on success (stale-while-revalidate).
    Guarded by `_background_refresh_in_progress` to prevent task-flood under load
    (§2.3 cross-review P1 finding).
    """
    global _cache, _cache_at, _background_refresh_in_progress
    if _background_refresh_in_progress:
        return  # another background task is already running
    _background_refresh_in_progress = True
    try:
        async with _refresh_lock:
            if (time.time() - _cache_at) <= CACHE_TTL_S:
                return  # another task already refreshed
            spec = await _fetch_spec()
            if spec is not None:
                _cache = spec
                _cache_at = time.time()
                logger.info("moltguard_discovery: cache refreshed (background)")
            # On failure, keep the stale cache — stale-while-revalidate.
    finally:
        _background_refresh_in_progress = False


async def get_spec() -> Optional[dict]:
    """
    Return cached MoltGuard spec, refreshing if empty or stale.

    Returns None only if cache is empty AND a synchronous fetch attempt fails
    (graceful-degrade signal — extendedAgentCard renders without MoltGuard fields).

    When cache is populated but stale, returns the stale cache and triggers a
    background refresh (stale-while-revalidate).
    """
    global _cache, _cache_at
    now = time.time()
    cache_empty = _cache is None
    cache_stale = (now - _cache_at) > CACHE_TTL_S

    if cache_empty:
        async with _refresh_lock:
            if _cache is None:  # double-check inside lock
                spec = await _fetch_spec()
                if spec is not None:
                    _cache = spec
                    _cache_at = time.time()
        return _cache  # None if fetch still failed → graceful degrade

    if cache_stale:
        asyncio.create_task(_background_refresh())

    return _cache


def _paid_endpoints_from_spec(spec: dict) -> dict:
    """
    Build the paid-endpoints inventory from spec.paths.

    Key is the operation's `operationId` (stable across spec versions).
    Value preserves the public-card shape consumers may rely on:
    method (uppercase), path (with /guard prefix), price, currency, cluster (first tag).
    """
    endpoints: dict = {}
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            if not op.get("security"):
                continue
            pricing = op.get("x-moltrust-pricing")
            if not pricing:
                continue
            opid = op.get("operationId") or f"{method}-{path.lstrip('/')}"
            tags = op.get("tags", ["uncategorized"])
            endpoints[opid] = {
                "method": method.upper(),
                "path": f"/guard{path}",
                "price": pricing.get("amount"),
                "currency": pricing.get("currency", "USDC"),
                "cluster": tags[0] if tags else "uncategorized",
            }
    return endpoints


def _clusters_from_spec(spec: dict) -> list:
    """Extract cluster names from spec.tags."""
    return [
        {"name": t.get("name"), "description": t.get("description", "")}
        for t in spec.get("tags", [])
        if isinstance(t, dict) and t.get("name")
    ]


def build_x402_pricing_extension(spec: Optional[dict]) -> Optional[dict]:
    """
    Build the x402-pricing extension object from a fetched MoltGuard spec.
    Returns None when the spec is missing or malformed (graceful-degrade guarantee
    holds even for spec contents that pass _fetch_spec's basic shape check but
    have unexpected internal types — §2.3 cross-review P1 finding).
    """
    if spec is None:
        return None
    try:
        endpoints = _paid_endpoints_from_spec(spec)
        if not endpoints:
            return None
        return {
            "uri": "https://moltrust.ch/extensions/x402-pricing/v1",
            "description": "x402 micropayment pricing inventory (build-time lookup from MoltGuard OpenAPI)",
            "required": False,
            "params": {
                "currency": "USDC",
                "chain": "eip155:8453",
                "source": MOLTGUARD_OPENAPI_URL,
                "endpoints": endpoints,
            },
        }
    except (TypeError, AttributeError, KeyError) as e:
        logger.warning(f"moltguard_discovery: build_x402_pricing_extension failed: {type(e).__name__}")
        return None


def build_moltguard_extension(spec: Optional[dict]) -> Optional[dict]:
    """
    Build the moltguard/v1 extension object from a fetched MoltGuard spec.
    Returns None when the spec is missing or malformed.
    """
    if spec is None:
        return None
    try:
        clusters = _clusters_from_spec(spec)
        info = spec.get("info") or {}
        if not isinstance(info, dict):
            return None
        return {
            "uri": "https://moltrust.ch/extensions/moltguard/v1",
            "description": info.get("description", "MoltGuard sub-API — risk scoring, sybil detection, market integrity, VC issuance."),
            "required": False,
            "params": {
                "service_url": "https://api.moltrust.ch/guard/",
                "openapi": MOLTGUARD_OPENAPI_URL,
                "version": info.get("version"),
                "capabilities": [c["name"] for c in clusters if c["name"]],
                "paymentProtocol": "x402",
                "paymentChain": "eip155:8453",
                "paymentCurrency": "USDC",
            },
        }
    except (TypeError, AttributeError, KeyError) as e:
        logger.warning(f"moltguard_discovery: build_moltguard_extension failed: {type(e).__name__}")
        return None


def build_moltguard_discovery_skill(spec: Optional[dict]) -> Optional[dict]:
    """
    Build the single 'moltguard-discovery' A2A skill (Discovery-Phase-2 §9.4 decision-3c).
    Replaces the previous 3 hardcoded MoltGuard skill entries.
    Returns None when the spec is missing or malformed.
    """
    if spec is None:
        return None
    try:
        clusters = _clusters_from_spec(spec)
        cluster_names = [c["name"] for c in clusters if c["name"]]
        capability_summary = ", ".join(cluster_names[:6])
        if len(cluster_names) > 6:
            capability_summary += f", … (+{len(cluster_names) - 6} more)"
        return {
            "id": "moltguard-discovery",
            "name": "MoltGuard Sub-API Discovery",
            "description": (
                "Discovery surface for the MoltGuard sub-API — wallet risk scoring, "
                "sybil-cluster detection, market integrity checks, skill/shopping/travel/"
                "prediction credential issuance, transparency proofs, and more. "
                f"Capability clusters: {capability_summary}. "
                f"Full OpenAPI 3.1 specification at {MOLTGUARD_OPENAPI_URL}. "
                "Paid endpoints use the x402 payment protocol on Base L2 (USDC)."
            ),
            "tags": ["moltguard", "discovery", "openapi", "x402", "sub-api"],
            "examples": [
                "What MoltGuard endpoints are available?",
                "Show me the paid MoltGuard endpoints and their x402 prices",
                "Fetch the MoltGuard OpenAPI specification",
            ],
            "inputModes": ["text"],
            "outputModes": ["data"],
        }
    except (TypeError, AttributeError, KeyError) as e:
        logger.warning(f"moltguard_discovery: build_moltguard_discovery_skill failed: {type(e).__name__}")
        return None
