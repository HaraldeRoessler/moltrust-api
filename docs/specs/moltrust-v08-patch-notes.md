# MolTrust Protocol — v0.8 Patch Notes
# For inclusion in: Protocol Whitepaper v0.8 + TechSpec v0.8
# Date: 2026-04-10
# Status: Draft — for review before anchoring on Base L2

---

## Summary

MolTrust v0.8 establishes MolTrust as a protocol-agnostic trust layer
for AI agent payments. Two npm packages now live:

- `@moltrust/x402` v1.0.0 — x402 (Coinbase/Cloudflare ecosystem)
- `@moltrust/mpp` v1.0.0 — MPP (Stripe/Tempo/Visa ecosystem)

Together these packages cover the two dominant agent payment protocols
with real production traffic in 2026.

---

## Whitepaper v0.8 — New Section (4.10)

### 4.10 Protocol-Agnostic Trust Layer

The MolTrust trust infrastructure is designed to be independent of any
specific agent payment protocol. As the agent payment landscape has
fragmented into multiple competing standards — x402 (Coinbase/Cloudflare),
MPP (Stripe/Tempo/Visa), AP2 (Google), ACP (OpenAI/Stripe) — the need
for a neutral, portable trust layer has become structurally evident.

No payment protocol defines how an endpoint operator verifies whether
a paying agent is legitimate, trustworthy, or has been flagged for abuse.
They handle payment mechanics, not agent trust. MolTrust fills this gap.

**The DigiCert Analogy**

DigiCert does not compete with HTTPS — it makes HTTPS trustworthy.
MolTrust does not compete with x402 or MPP — it makes agent payments
trustworthy, regardless of which payment rail the agent uses.

**Protocol Coverage (April 2026)**

| Protocol | Ecosystem | MolTrust Integration |
|---------|-----------|---------------------|
| x402 | Coinbase, Cloudflare, 50M+ tx | `@moltrust/x402` v1.0.0 ✅ |
| MPP | Stripe, Tempo, Visa, 100+ services | `@moltrust/mpp` v1.0.0 ✅ |
| AP2 | Google, 60+ partners | Roadmap v0.9 Q3 2026 — W3C VC mandate → AAE mapping |
| ACP | OpenAI, Stripe | Roadmap v0.9 Q4 2026 |

**Portable Agent Identity**

An agent that registers a W3C DID with MolTrust receives a trust score
that is queryable by any endpoint operator regardless of which payment
protocol the agent uses. The agent registers once; the trust score is
valid everywhere.

This is the structural advantage of building on W3C DID/VC standards
rather than protocol-specific identity systems: portability is
guaranteed by the standard, not by bilateral agreements.

---

## TechSpec v0.8 — New Section (8.4)

### 8.4 MPP Interoperability

**Status:** Live — April 2026
**npm:** `@moltrust/mpp` v1.0.0

#### 8.4.1 Overview

The Machine Payments Protocol (MPP), co-authored by Stripe and Tempo,
uses the same HTTP 402 challenge-response pattern as x402 but extends
it with session-based payments, card support via Stripe SPTs, and
Bitcoin Lightning support.

MPP endpoints identify paying agents via an `Authorization: MPP <credential>`
header where the credential is a base64-encoded JSON object containing
the paying wallet address.

#### 8.4.2 Trust Score Integration

MolTrust extracts the paying agent's wallet address from the MPP
Authorization credential and queries the MolTrust trust score API:

```
GET /wallet/{address}
→ { shadow_score: 45, trust_score: 78, registered: true }
```

If the agent is registered, the full trust score is returned.
If the agent is unregistered, the shadow score (derived from
on-chain x402/MPP transaction history) is returned.

#### 8.4.3 Middleware Integration

```javascript
const { requireScore } = require('@moltrust/mpp');
const { Mppx, tempo } = require('mppx/server');

// MolTrust trust check runs before MPP payment middleware
app.use(requireScore({ minScore: 60 }));
app.use(mppx.charge({ amount: '0.01' }));
```

The middleware supports three wallet extraction paths from the
MPP credential payload:
1. `credential.challenge.request.payer.address`
2. `credential.payer.address`
3. `credential.from`

#### 8.4.4 Response Format

On trust check failure (score below threshold):

```json
{
  "error": "trust_score_insufficient",
  "wallet": "0x...",
  "score": 23,
  "required": 60,
  "message": "Trust score 23 is below required 60.",
  "profile": "https://moltrust.ch/wallet/0x...",
  "register": "https://moltrust.ch/register?wallet=0x..."
}
```

#### 8.4.5 Position in Stack

```
L1  Identity Check (did:moltrust: / ERC-8004)
L2  AAE Authorization (MANDATE + CONSTRAINTS + VALIDITY)
L2.5 SAS Pre-Execution (Sequential Action Safety)
L3  Trust Score Gate ← @moltrust/mpp OR @moltrust/x402
L4  MPP Payment Flow (mppx.charge)
L5  Falco Enforcement (Kernel-level)
L6  IPR Anchor (Base L2 non-repudiation)
```

#### 8.4.6 Protocol Comparison

| Dimension | x402 | MPP |
|-----------|------|-----|
| Payment rails | USDC on Base/Solana | Stablecoins, Cards (Stripe), Bitcoin Lightning |
| Settlement | On-chain per request | Sessions + batch settlement |
| Latency | ~2s (on-chain) | <100ms (off-chain vouchers) |
| Ecosystem | Coinbase, Cloudflare | Stripe, Tempo, Visa, Anthropic |
| MolTrust middleware | `@moltrust/x402` | `@moltrust/mpp` |
| Trust extraction | `X-Payment` header | `Authorization: MPP` header |

Both middlewares expose identical API: `requireScore({ minScore })`.
Endpoint operators can use both simultaneously for multi-protocol support:

```javascript
const x402Trust = require('@moltrust/x402');
const mppTrust = require('@moltrust/mpp');

// Auto-detect protocol and apply appropriate trust check
app.use((req, res, next) => {
  if (req.headers['authorization']?.startsWith('MPP ')) {
    return mppTrust.requireScore({ minScore: 60 })(req, res, next);
  }
  return x402Trust.requireScore({ minScore: 60 })(req, res, next);
});
```

---

## TechSpec v0.8 — Update Section 8.1 (Cross-Protocol Interoperability)

Add to existing Section 8.1 table:

| Protocol | MolTrust Integration | Status |
|---------|---------------------|--------|
| qntm/APS | AAE ↔ ConstraintEvaluation mapping | Live (5/5 test vectors) |
| x402 | `@moltrust/x402` npm middleware | Live v1.0.0 |
| **MPP** | **`@moltrust/mpp` npm middleware** | **Live v1.0.0** |
| AP2 | W3C VC mandate → AAE mapping | Planned v0.9 |
| ACP | Adapter layer | Planned v0.9 |

---

## TechSpec v0.8 — New Section (8.5): Trust Score Specification

### 8.5.1 Shadow Score (Unregistered Agents)

Agents without a MolTrust DID receive a shadow score derived from
on-chain transaction history. The shadow score provides a baseline
trust signal without requiring registration.

**Formula:**
```
shadow_score = 25 (base)
             + min(10, tx_count × 0.5)
             + min(5,  total_usdc × 0.1)

Range: 25–40. Capped at 40 without DID registration.
```

Data sources:
- `tx_count` — number of x402/MPP transactions from the wallet on Base L2
- `total_usdc` — cumulative USDC volume from the wallet

A shadow score of 25 means zero on-chain activity. A score of 40 means
20+ transactions with meaningful USDC volume. Endpoint operators using
`requireScore({ minScore: 60 })` will block all unregistered agents,
incentivizing DID registration.

### 8.5.2 Full Trust Score (Registered Agents)

Registered agents receive a full trust score computed from the
MolTrust endorsement graph and behavioral history:

```
score = clamp(
  0.6 × direct_score
  + 0.3 × propagated_score
  + 0.1 × cross_vertical_bonus
  + interaction_bonus
  + graph_bonus
  - sybil_penalty,
  0, 100
)
```

See TechSpec Section 4 (Reference Reputation Model) for full formula.

**Cache:** Trust scores are cached in PostgreSQL (`trust_score_cache`)
with a 1-hour TTL (`cache_valid_until`). Cache is invalidated on new
endorsement, revocation event, or violation recording.

### 8.5.3 Score Update Frequency

| Event | Cache Behavior |
|-------|---------------|
| New endorsement received | Invalidated immediately |
| Revocation event | Invalidated immediately |
| Violation recorded | Invalidated immediately |
| No events | 1-hour TTL |
| Shadow score (unregistered) | Computed on-demand, not cached |

---

## TechSpec v0.8 — New Section (8.6): Security Model

### 8.6.1 API Authentication

Trust score queries to `/wallet/{address}` are public (no API key required)
by design — trust scores are intended to be publicly verifiable, consistent
with the W3C VC principle of open verifiability. Scores cannot be set or
manipulated externally; they are computed deterministically from on-chain
and registry data.

Rate limit: 30 requests/minute per IP on `/wallet/{address}`.

### 8.6.2 Score Integrity

Trust scores are computed server-side from tamper-proof inputs:
- On-chain transaction data (Base L2, immutable)
- Endorsements (Ed25519 signed, anchored on Base L2)
- Interaction Proof Records (dual-signed, on-chain anchored)

No external party can submit or modify a trust score. The score is
a deterministic function of verifiable inputs.

### 8.6.3 Failure Behavior

Both `@moltrust/x402` and `@moltrust/mpp` implement **fail-closed**
behavior on API unavailability:

- API unreachable → score returned as `0`
- Score `0` < any configured `minScore` → request denied
- Endpoint operators MAY configure `allowUnregistered: true` for
  explicit fail-open behavior (not recommended for production)

This fail-closed default is deliberate. In an autonomous agent economy,
the cost of admitting an untrusted agent (potential abuse, financial loss)
exceeds the cost of temporarily blocking a legitimate agent (retry).

### 8.6.4 did:moltrust: Method

`did:moltrust:` is a registry-based DID method operated by MolTrust /
CryptoKRI GmbH. DIDs follow the format:

```
did:moltrust:<16-hex-char-identifier>
```

Resolution: `GET https://api.moltrust.ch/identity/did/{did}`

The identifier is derived from UUID v4 (128-bit), providing
collision resistance equivalent to UUID birthday-bound (~2^64).
DID Documents contain Ed25519 public keys and optional service endpoints.
Registration: `POST https://api.moltrust.ch/identity/register`

The method is not yet registered with the W3C DID Method Registry.
Registration is planned for v0.9.

---

## TechSpec v0.8 — New Section (8.7): Performance

### 8.7.1 Current Capacity

| Metric | Value |
|--------|-------|
| Trust score cache | PostgreSQL, 1h TTL |
| Rate limit (/wallet/) | 30 req/min per IP |
| Middleware latency (cache hit) | <10ms |
| Middleware latency (cache miss) | ~100-200ms (DB query) |
| Horizontal scaling | Not yet implemented |

### 8.7.2 Scale Projection

At 10,000 registered agents with 100 daily transactions each:
- Expected trust score lookups: ~1M/day (~12/sec average, ~100/sec peak)
- Current single-node capacity: ~30 req/min = ~0.5 req/sec sustained
- **Gap:** Horizontal scaling required before 1,000+ active agents

Scaling path: Redis cache layer for trust scores (replacing PostgreSQL
cache), read replicas, CDN-cached public score responses.

---

## Corrections from v0.7

- **@moltrust/x402 v1.0.1:** Fixed fail-open behavior to fail-closed.
  API error now returns score `0` (blocked) instead of `null` (pass-through).
  Both `@moltrust/x402` and `@moltrust/mpp` now have identical failure semantics.

---

## On-Chain Anchoring

Both npm packages and this patch note should be anchored on Base L2
at v0.8 release, alongside updated PDF versions of WP and TechSpec.

Anchor format:
```
MolTrust/ProtocolUpdate/v0.8 SHA256:<hash-of-this-document>
```

---

## References

- @moltrust/x402: https://www.npmjs.com/package/@moltrust/x402
- @moltrust/mpp: https://www.npmjs.com/package/@moltrust/mpp
- MPP Protocol: https://mpp.dev
- MPP Stripe Docs: https://docs.stripe.com/payments/machine/mpp
- x402 Protocol: https://x402.org
- MolTrust TechSpec v0.7: https://moltrust.ch/MolTrust_Protocol_TechSpec_v0.7.pdf
- MolTrust Whitepaper v0.7: https://moltrust.ch/MolTrust_Protocol_Whitepaper_v0.7.pdf
