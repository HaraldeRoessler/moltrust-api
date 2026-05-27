# Trust-Gating (F3)

A one-line check that any agent can insert before an Agent-to-Agent
transaction:

> "Does this counter-party have a trust score above my threshold?"

If yes, proceed. If no, refuse and surface a clear reason. The endpoint
is public (no API key) and rate-limited per IP — call it like DNS.

## Endpoint

```
GET /trust/gate/{did}
```

| Query param | Type | Default | Meaning |
| --- | --- | --- | --- |
| `min_score` | float 0–100 | `50` | Minimum trust score required |
| `context` | string ≤ 100 | _none_ | Optional label persisted to the audit log (e.g. `payment`, `data_access`) |
| `allow_cold_start` | bool | `false` | When `true`, cold-start scores (derived from public on-chain / GitHub / ERC-8004 signals) count toward ALLOW. Default `false` keeps registration pressure on agents to accumulate real endorsements. |

Always returns **HTTP 200**. The decision is in the body. Consumers
inspect `decision` and `reason`, never the HTTP status.

### Response — ALLOW

```json
{
  "did": "did:moltrust:abc123",
  "decision": "ALLOW",
  "trust_score": 74.5,
  "min_score_required": 50,
  "score_source": "behavioral",
  "verified_at": "2026-05-27T10:00:00Z"
}
```

### Response — DENY (score too low)

```json
{
  "did": "did:moltrust:abc123",
  "decision": "DENY",
  "reason": "insufficient_trust_score",
  "trust_score": 34.0,
  "min_score_required": 60,
  "score_source": "behavioral",
  "register_url": "https://moltrust.ch/register"
}
```

### Response — DENY (score not yet released)

```json
{
  "did": "did:moltrust:abc123",
  "decision": "DENY",
  "reason": "score_withheld",
  "trust_score": null,
  "min_score_required": 50,
  "register_url": "https://moltrust.ch/register"
}
```

A score is "withheld" when the agent has fewer than three endorsements
and `allow_cold_start` was not set (or no public data exists to compute
a cold-start score). Consumers can retry with `allow_cold_start=true`
for a softer policy.

### Response — DENY (unknown agent)

```json
{
  "did": "did:moltrust:unknown",
  "decision": "DENY",
  "reason": "agent_not_found",
  "trust_score": null,
  "min_score_required": 50,
  "register_url": "https://moltrust.ch/register"
}
```

### Decision tree

```
1. Agent unknown                                             → DENY agent_not_found
2. Phase 2 returns a real score:
     score >= min_score                                      → ALLOW (behavioral)
     score <  min_score                                      → DENY  insufficient_trust_score (behavioral)
3. Phase 2 withholds (< 3 endorsers, score is null):
     allow_cold_start = false                                → DENY  score_withheld
     allow_cold_start = true:
       cold_start_score is null                              → DENY  score_withheld
       cold_start_score >= min_score                         → ALLOW (cold_start)
       cold_start_score <  min_score                         → DENY  insufficient_trust_score (cold_start)
```

### Rate limit

100 requests per minute per IP. Bursty? Cache the result for a few
minutes on your side — a trust score does not change second by second.

## Audit log

Every call lands in `gate_events`:

| column | type | notes |
| --- | --- | --- |
| `queried_did` | varchar(255) | The DID that was looked up |
| `decision` | varchar(10) | `ALLOW` or `DENY` |
| `reason` | varchar(50) | `insufficient_trust_score` / `score_withheld` / `agent_not_found` |
| `score_source` | varchar(20) | `behavioral` or `cold_start` (null when no score evaluated) |
| `trust_score` | float | The score the decision was based on |
| `min_score_required` | float | What the caller asked for |
| `allow_cold_start` | bool | Whether the cold-start fallback was enabled |
| `context` | varchar(100) | Caller-supplied label, free-form |
| `caller_ip` | varchar(50) | Anonymised |
| `created_at` | timestamp | Default `NOW()` |

Indexed on `queried_did` and `created_at` for fast retro queries.

## Python — one-liner

```python
from app.sdk.trust_gate import verify

result = verify("did:moltrust:counterparty123", min_score=60)
if not result["allowed"]:
    raise RuntimeError(f"Counterparty not trusted: {result['reason']}")
```

Fails closed: a network error returns `{"allowed": False, "reason": "gate_unreachable"}`,
so a gate outage cannot accidentally grant access.

## TypeScript — code snippet (no npm package yet)

The npm helper ships once the endpoint has been verified live. Until
then, copy this two-function helper into your agent code:

```typescript
type GateResult = {
  allowed: boolean;
  decision: "ALLOW" | "DENY";
  score: number | null;
  reason?: string;
  score_source?: "behavioral" | "cold_start";
};

export async function verify(
  did: string,
  opts: {
    minScore?: number;
    context?: string;
    allowColdStart?: boolean;
    apiBase?: string;
  } = {},
): Promise<GateResult> {
  const base = opts.apiBase ?? "https://api.moltrust.ch";
  const params = new URLSearchParams({ min_score: String(opts.minScore ?? 50) });
  if (opts.context) params.set("context", opts.context);
  if (opts.allowColdStart) params.set("allow_cold_start", "true");
  try {
    const r = await fetch(`${base}/trust/gate/${encodeURIComponent(did)}?${params}`);
    if (!r.ok) throw new Error(`gate ${r.status}`);
    const body = await r.json();
    return {
      allowed: body.decision === "ALLOW",
      decision: body.decision,
      score: body.trust_score,
      reason: body.reason,
      score_source: body.score_source,
    };
  } catch {
    // Fail closed.
    return { allowed: false, decision: "DENY", score: null, reason: "gate_unreachable" };
  }
}
```

Usage:

```typescript
const result = await verify("did:moltrust:counterparty123", { minScore: 60 });
if (!result.allowed) {
  throw new Error(`Counterparty not trusted: ${result.reason}`);
}
```
