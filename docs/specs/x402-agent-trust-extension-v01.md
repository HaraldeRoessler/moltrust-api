# x402 `agent-trust` Extension — Spec v0.1
# Author: MolTrust / CryptoKRI GmbH
# Date: 2026-04-10
# Status: Draft — for review before submission as GitHub Issue

---

## Review Context (for reviewers)

MolTrust is proposing an `agent-trust` extension for x402 V2. x402 V2 (Dec 2025) introduced a formal extensions system. Official extensions so far: `discovery` (live), `sign-in-with-x` / SIWx (announced). Our proposal: `agent-trust` as the third extension.

**Narrative:** SIWx = who is paying (Wallet Identity) → agent-trust = is the payer trustworthy (Behavior History).

**What we want reviewers to assess:**
1. Is the technical spec correct and compatible with x402 V2 architecture?
2. Is the use of `extra` and `extensions` fields formally allowed in V2?
3. Is the vendor-neutral naming (`agentTrust` not `moltrust`) credible?
4. What are the risks of the extra HTTP call for trust verification?
5. How does this compare to Arch Tools' "patent-pending agent auth"?
6. Should we submit as Issue first or direct PR?

**Team:** 1 founder, 1 part-time engineer. Live implementation: `@moltrust/x402` v1.0.1 on npm.

---

## Kontext & Timing

x402 V2 (Dec 2025) introduced a formal extensions system. Official extensions: `discovery` (live), `sign-in-with-x` / SIWx (announced). Our proposal: `agent-trust` as the third extension.

Narrative: SIWx = who is paying (Wallet Identity) → agent-trust = is the payer trustworthy (Behavior History).

---

## Technical Spec

### Server — PaymentRequirements `extra` Field

```json
{
  "scheme": "exact",
  "network": "eip155:8453",
  "amount": "1000000",
  "asset": "0x833589f...",
  "payTo": "0x...",
  "extra": {
    "name": "USDC",
    "version": "2",
    "agentTrust": {
      "minScore": 60,
      "registryUrl": "https://api.moltrust.ch",
      "required": false
    }
  }
}
```

The `agentTrust` object in `extra` tells paying agents:
- What minimum trust score is required (`minScore`)
- Which trust registry to check against (`registryUrl`)
- Whether trust verification is mandatory or optional (`required`)

### Client — PAYMENT-SIGNATURE Extensions

```json
{
  "x402Version": 2,
  "scheme": "exact",
  "network": "eip155:8453",
  "payload": { "...": "..." },
  "extensions": {
    "agentTrust": {
      "did": "did:moltrust:vcone",
      "score": 85,
      "verifyUrl": "https://api.moltrust.ch/api/agent/score-free/0x..."
    }
  }
}
```

The paying agent includes its trust credentials in the `extensions` field:
- `did`: The agent's W3C DID
- `score`: Self-reported trust score (server verifies independently)
- `verifyUrl`: URL where the server can verify the score

### Server-Side Verification via Lifecycle Hook

```typescript
import { requireScore } from '@moltrust/x402';

app.use('/api/premium',
  requireScore({ minScore: 60 }),
  paymentMiddleware({...})
);
```

---

## Design Decisions

### Vendor-Neutral Naming
The extension is named `agentTrust`, not `moltrust`. Any trust registry provider can implement the same interface. The `registryUrl` field allows endpoint operators to choose their trust provider.

### Self-Reported Score + Server Verification
The client includes a self-reported score for fast pre-filtering, but the server MUST verify independently by calling the `verifyUrl`. This prevents score spoofing.

### `required: false` Default
Trust verification is optional by default. Endpoint operators opt in by setting `required: true`. This enables gradual adoption without breaking existing x402 flows.

---

## Strengths
- Live implementation: `@moltrust/x402` v1.0.1 on npm — not a concept-only PR
- Fits V2 architecture: Extensions system, no fork, no breaking change
- Vendor-neutral: `agentTrust` not `moltrust` — any registry provider can fill the field
- W3C standard: DID/VC, no proprietary format

---

## Open Questions Before Submission

1. **Is `extra` formally specified?** — Check if `extra` is an official extension field in V2 spec
2. **Is `extensions` in PAYMENT-SIGNATURE allowed?** — Must be formally permitted in V2 spec
3. **Verifier trust:** Server calls `verifyUrl` itself → extra HTTP call — justify as cacheable trade-off
4. **Competitor: Arch Tools** — "patent-pending agent auth" in awesome-x402 — check content overlap
5. **PR type:** Issue first (Discussion), then PR with spec document `specs/extensions/agent-trust.md`

---

## Recommended Approach

1. Spec-check: `curl https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification.md | grep -A10 "extra\|extensions"`
2. Arch Tools competitor check
3. Open Issue first: *"[Discussion] agent-trust extension proposal for x402 V2"*
4. After positive maintainer feedback: PR via VCOne-AI

---

## References

- x402 V2 Spec: https://github.com/coinbase/x402/blob/main/specs/x402-specification.md
- @moltrust/x402: https://www.npmjs.com/package/@moltrust/x402
- MolTrust API: https://api.moltrust.ch
- W3C DID Core: https://www.w3.org/TR/did-core/
