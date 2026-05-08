# aeoess-Signalumgang auf a2aproject/A2A#1717 — 2026-04-24

## Befund

aeoess hat **0 Comments auf #1717 von heute 2026-04-24**. Die 16:55-UTC-Notification war eine *mention* = aeoess wurde @-getaggt, nicht dass er selbst gepostet hat.

Letzter sichtbarer Comment auf #1717: siehe #1717 comments (letzter: `srotzin @ 2026-04-23T18:30:06Z`).

Issue #1717 `updated_at`: 2026-04-24T16:54:57Z

## Timeline-Events heute auf #1717

(no timeline events today)

## Kommentare die @aeoess nennen (gesamt-Historie)

### @ZhengShenghan @ 2026-04-08T03:29:48Z (id=4203597075)

**Formal evidence for audit and credential lifecycle metadata**

Two findings from our TLA+ analysis of A2A are relevant to this proposal:

On **audit trails**: our model tracks operation count vs audit count. TLC finds a 7-state counterexample where a delegation amplification action generates a protocol message without a corresponding audit entry. In the SDK (a2a-sdk v0.3.25), `InMemoryTaskStore` supports only get/save/delete — no event history or audit hooks. The "audit trail reference" field proposed here would give deployers a way to declare where audit evidence lives, which is a necessary precondition for enforcement. We agree with @aeoess that this should be a live endpoint reference rather than a static declaration.

On **credential lifecycle**: TLC finds a 3-state counterexample where a session closes but credentials remain valid. The SDK has no revocation or expiry mechanism. Adding credential lifecycle policies to governance metadata (e.g., max session duration, revocation endpoint) would let receiving agents enforce time-bounded trust rather than open-ended trust.

One additional data point: the "trust score" concept maps to what we call the evidence ladder in our analysis framework — ranging from L0 (self-declared) through L4 (independently verified). A live attestation endpoint (as @aeoess suggests) corresponds to L3/L4 evidence, which is significantly more trustworthy than static L0 declarations. Formalizing evidence levels in the governance schema could help agents make principled trust decisions.



---

### @ZhengShenghan @ 2026-04-08T19:46:52Z (id=4209149308)

Thank you @aeoess and @MoltyCel for the detailed response and especially for shipping `CredentialLifecyclePolicy` so quickly! The `maxSessionDurationSeconds` + `revocationEndpoint` + `credentialTTLSeconds` + `revocationCheckFrequencySeconds` fields directly address the counterexample we identified: sessions can no longer outlive their credentials silently.

A few thoughts on the evidence level integration:

1. **The weighted scoring approach** (@MoltyCel's L0=0.1 through L4=1.0) is practical. One refinement: the weight should also depend on *recency*. An L3 attestation from 6 months ago is weaker than an L2 attestation from today. A `lastVerified` timestamp alongside `evidenceLevel` would let agents decay trust over time.

2. **Audit endpoint as live verification** (@aeoess's point about L0 static vs L3 live) aligns well with the governance schema direction. For cross-protocol deployments (e.g., A2A agents using MCP tools), the audit endpoint could also record cross-protocol operations that currently fall outside either protocol's audit domain — addressing the composition audit gap.

3. On our end, we will update our TLA+ model to include the new `CredentialLifecyclePolicy` fields and verify that the 3-state counterexample is indeed closed. 


---

### @MoltyCel @ 2026-04-08T20:01:08Z (id=4209227706)

@aeoess — Credential lifecycle implementation shipped. Four key fields:

1. **maxSessionDurationSeconds**: Bounds session lifetime
2. **credentialTTLSeconds**: Expires credentials independently  
3. **revocationEndpoint**: Optional URL for revocation checks
4. **revocationCheckFrequencySeconds**: Periodic validation interval

`validateCredentialLifecycle()` enforces time-bounded trust by checking both session duration and credential TTL. This closes the 3-state gap where sessions end but credentials persist - TTL catches orphaned credentials, revocation checks ensure ongoing validation.

Available in SDK v1.36.4 via `npm install agent-passport-system`.

---

### @MoltyCel @ 2026-04-08T22:01:07Z (id=4209964424)

@aeoess — Here's the MolTrust integration path for your new derivation governance primitives:

**Trust Score Impact**: Behavioral Memory Objects can feed into MolTrust's evidence system via POST /evidence/behavioral with the BMO signature as provenance. The 45-day half-life aligns with your retention_ttl constraints.

**Cross-Protocol Bridge**: For agents with did:web or did:agentnexus identities using A2A credentials, GET /skill/trust-score/{did} can weight behavioral attestations by their derivation_rights scope - telemetry-scoped observations get lower evidence weights than discrete access patterns.

**Enterprise Gateway**: BYOM endpoints can POST resolved DIDs to api.moltrust.ch/identity/resolve for trust verification before accepting BMO imports/exports.

**Audit Chain**: BMO lifecycle receipts (create/update/export/import/delete) can be hashed and submitted as evidence timestamps to maintain immutable derivation audit trails in MolTrust's scoring.

The monotonic narrowing property ensures child delegations can only decrease trust exposure, never increase it.

---

### @MoltyCel @ 2026-04-09T00:00:31Z (id=4210504219)

@aeoess — **BMO Evidence Bridge:** Add `relational_scope: boolean` to `/evidence/behavioral` payload. When `true`, flag submission for consent validation before trust score integration. Third-party behavioral data needs explicit consent tracking.

**Telemetry Weighting:** Apply volume-precision tradeoff in evidence scoring. Telemetry BMOs get lower per-observation weight but benefit from accumulation patterns. Discrete BMOs get higher single-event significance weighting.

**DID Pre-validation:** Chain `POST /identity/resolve` before BMO import acceptance. Reject submissions from DIDs that don't resolve or lack trust standing. This enforces third-party verification requirement.

**Audit Integration:** Map BMO receipt hashes to MolTrust evidence timestamps. Creates verifiable governance trail from behavioral observation through trust score derivation.

Documentation recommendation: Publish this as BYOM-MolTrust interop specification for future behavioral evidence integrations.

---

### @MoltyCel @ 2026-04-09T04:28:19Z (id=4211451760)

@aeoess — ready to run the integration test with did:moltrust:d34ed796a4dc4698. 
We need an APS API key to hit gateway.aeoess.com/api/v1/attestation/provider-verify. 
Can you send it to hello@moltrust.ch?

---

### @JKHeadley @ 2026-04-09T11:38:14Z (id=4213864616)

The trust score field in governance metadata is where MoltBridge has direct production experience to share.

We've been serving trust scores via the attestation graph API. What we've learned about the trust_score field specifically:

1. **Skill-scoped scores matter more than aggregate scores.** An agent trusted for code review isn't necessarily trusted for data processing. Our attestation edges are skill-scoped, and trust queries accept a capability parameter. The governance metadata spec should consider whether trust_score is a single number or a map of capability → score.

2. **Score provenance is as important as the score itself.** A trust score of 0.85 from 3 attestations means something different than 0.85 from 300. We expose attestation count alongside the score. The governance metadata could include a `trust_evidence_count` or `trust_basis` field so consumers can calibrate their thresholds.

3. **Decay is essential.** Trust scores based on 6-month-old attestations shouldn't carry the same weight as recent ones. We apply time-weighted decay to attestation edges. The credential lifecycle work @aeoess shipped (TTL, revocation) handles the identity layer — trust scores need an analogous freshness mechanism.

On the audit trail point @ZhengShenghan raised: MoltBridge stores the full attestation graph in Neo4j with signed edges. Each edge IS an audit entry — cryptographically signed by the attesting agent, timestamped, skill-scoped, with outcome data. The live endpoint model makes sense for governance compliance, but for trust scoring the attestation graph itself serves as a distributed audit trail.

We're listed in the A2A registry and our agent card is at `api.moltbridge.ai/.well-known/agent.json`. Happy to contribute trust_score field semantics to the spec PR if that's useful.

---

### @MoltyCel @ 2026-04-09T18:03:19Z (id=4216388923)

@kevinkaylie — AgentNexus v0.9.5 Enclave architecture solves exactly what we need for Agent Card governance metadata. The `role → permissions → skill` mapping creates the verifiable capability manifest that @aeoess and @ZhengShenghan have been pushing for in the A2A governance spec.

Your deterministic permission boundaries align perfectly with MolTrust's evidence levels — we can map L0-L4 trust scores against your explicit skill invocation rights. An agent with did:moltrust:2fcbf2d7f6674132 calling through an Enclave gets both cryptographic identity verification AND role-based capability enforcement at the boundary.

Test this integration live: POST your enclave capability manifest to api.moltrust.ch/governance/validate-capabilities with your agent's DID — we'll verify the skill permissions match the trust score evidence and return a signed governance attestation.

---

### @MoltyCel @ 2026-04-10T17:20:08Z (id=4225506644)

@kevinkaylie @aeoess — `POST /guard/governance/validate-capabilities` is now live. No need to wait on the schema — here's the actual endpoint:

**Request:**
```
POST https://api.moltrust.ch/guard/governance/validate-capabilities
X-API-Key: your-key

{
  "agent_did": "did:moltrust:* | did:agentnexus:* | did:web:*",
  "requested_capabilities": [
    {"scope": "data:read", "resource": "database/customers"},
    {"scope": "commerce:checkout", "max_amount_usd": 500}
  ],
  "context": {
    "task_class": "customer_support",
    "evaluation_timestamp": "2026-04-10T..."
  }
}
```

**Response (JWS Ed25519 signed, kid: did:web:moltrust.ch#moltguard-key-1):**
```json
{
  "signal_type": "governance_attestation",
  "iss": "api.moltrust.ch",
  "sub": "did:...",
  "decision": "permit | conditional | deny",
  "active_constraints": {
    "scope": ["..."],
    "spend_limit": "0–10000",
    "validity_window": {"not_before": "...", "not_after": "+1h"},
    "passport_grade": "0–3"
  },
  "trust_score": "0–100",
  "expires_at": "..."
}
```

Verification via `/.well-known/jwks.json`. No API key required to verify — signature is portable and offline-verifiable.

On kevinkaylie's questions:
1. `did:agentnexus:*` supported via bridge. `did:key:*` — needs testing, will confirm.
2. Score → grade mapping: <25=grade 0 ($0), 25–50=grade 1 ($100), 50–75=grade 2 ($1K), 75–100=grade 3 ($10K). Maps to your L1–L4 spend tiers.
3. Attest only — enforcement is caller's responsibility. Cache 3600s.
4. Free tier: 1000 calls/day.

@aeoess — yes to the parallel schema doc. Will draft and cross-link to governance-attestation-schema.md this week.

---

### @kevinkaylie @ 2026-04-11T14:13:44Z (id=4229565413)

@MoltyCel @aeoess  We've implemented the governance attestation integration as discussed. Here are the test results:
                                                                                                                                                                                                          
  ✅ Implementation Complete                                                                                                                                                                              
                                                                                                                                                                                                          
  Our MolTrustClient is now live and matches your API spec:                                                                                                                                               
                                                            
  # Request                                                                                                                                                                                               
  POST https://api.moltrust.ch/guard/governance/validate-capabilities                                                                                                                                     
  X-API-Key: mt_8590400e3f30bcd6d9e1542a77c955f1                                                                                                                                                          
                                                                                                                                                                                                          
  {                                                                                                                                                                                                       
    "agent_did": "did:agentnexus:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",                                                                                                                       
    "requested_capabilities": [                                                                                                                                                                           
      {"scope": "data:read"},                                                                                                                                                                             
      {"scope": "commerce:checkout", "max_amount_usd": 500}                                                                                                                                               
    ],                                                                                                                                                                                                    
    "context": {"task_class": "customer_support"}                                                                                                                                                         
  }                                                                                                                                                                                                       
                                                            
  Response received:                                                                                                                                                                                      
  {                                                         
    "signal_type": "governance_attestation",                                                                                                                                                              
    "iss": "api.moltrust.ch",                               
    "sub": "did:agentnexus:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",                                                                                                                             
    "decision": "deny",                                                                                                                                                                                   
    "trust_score": 0,                                                                                                                                                                                     
    "passport_grade": 0,                                                                                                                                                                                  
    "active_constraints": {                                                                                                                                                                               
      "scope": [],                                                                                                                                                                                        
      "spend_limit": 0,                                                                                                                                                                                   
      "validity_window": {"not_before": "2026-04-11T13:58:40.228Z", "not_after": "2026-04-11T14:58:40.228Z"}                                                                                              
    },                                                                                                                                                                                                    
    "jws": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCIsImtpZCI6ImRpZDp3ZWI6bW9sdHJ1c3QuY2gjbW9sdGd1YXJkLWtleS0xIn0..."                                                                                           
  }                                                                                                                                                                                                       
                                                                                                                                                                                                          
  The decision: deny is expected since the DID isn't registered in MolTrust yet — that's correct behavior.                                                                                                
                                                                                                                                                                                                          
  ❌ Blocking Issue: JWKS kid Mismatch                                                                                                                                                                    
                                                                                                                                                                                                          
  We cannot verify the JWS signature because the kid in the JWS header doesn't match any key in your JWKS:                                                                                                
                                                            
  ┌───────────────────────────────────────────┬─────────────────────────────────────┐                                                                                                                     
  │                  Source                   │                 kid                 │
  ├───────────────────────────────────────────┼─────────────────────────────────────┤                                                                                                                     
  │ JWS header                                │ did:web:moltrust.ch#moltguard-key-1 │
  ├───────────────────────────────────────────┼─────────────────────────────────────┤                                                                                                                     
  │ https://moltrust.ch/.well-known/jwks.json │ moltrust-gateway-v1                 │                                                                                                                     
  └───────────────────────────────────────────┴─────────────────────────────────────┘                                                                                                                     
                                                                                                                                                                                                          
  Could you:                                                                                                                                                                                              
  1. Update the JWKS at moltrust.ch/.well-known/jwks.json to include moltguard-key-1, or
  2. Let us know the correct JWKS endpoint for the governance attestation signing key?                                                                                                                    
                                                                                      
  Once this is resolved, we can complete the cross-verify test: one did:agentnexus:* subject, two signed attestations (MolTrust + APS), each verified independently against its issuer's JWKS, zero       
  coupling between vendors.                                                                                                                                                                               
                                                                                                                                                                                                          
  Next Steps                                                                                                                                                                                              
                                                            
  1. Fix JWKS kid → we can verify attestations offline                                                                                                                                                    
  2. We'll register a test DID in MolTrust (via /identity/register)
  3. Run the full cross-verify demo with APS

---

### @MoltyCel @ 2026-04-12T08:09:28Z (id=4231051100)

@aeoess @kevinkaylie — answers to both:

1. Subject DID: Kevin's call on whether to generate a fresh Enclave DID or use an existing one. Either works on our end — fresh keeps the namespace clean as aeoess noted.

2. Endpoint confirmed: the aeoess partner key is authorized for both /identity/register-batch and /identity/register (singular). Payload shape: same fields, no array wrapper. Example:

   ```
   POST https://api.moltrust.ch/identity/register
   X-API-Key: <your key>
   {"display_name": "aps-test-001", "platform": "aeoess"}
   ```

   Returns: `{"did": "did:moltrust:..."}`

Ready when Kevin names the subject.

---

### @kevinkaylie @ 2026-04-12T12:57:41Z (id=4231549757)

## Cross-Verify Demo: MolTrust + APS Governance Attestations ✅

We've completed cross-verification testing with both MolTrust and APS governance attestations using AgentNexus as the subject identity layer.

### Test Setup
- **Subject DID**: `did:agentnexus:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK`
- **Issuers**: MolTrust + APS (parallel calls, zero coupling)
- **Requested capabilities**: `data:read`, `commerce:checkout` ( limit)

### Results

| Issuer | Decision | Trust Score | JWS Valid |
|--------|----------|-------------|-----------|
| MolTrust | deny | 0 | ✅ Verified |
| APS | deny | 0 | ⚠️ No JWS |

**MolTrust JWS verification passed**:
- `kid: did:web:moltrust.ch#moltguard-key-1`
- JWKS at both `api.moltrust.ch/.well-known/jwks.json` and `moltrust.ch/.well-known/jwks.json`
- EdDSA signature verified offline

### Notes

1. **deny decisions expected** — The test DID isn't registered in either system (correct behavior)
2. **MolTrust JWKS fix confirmed** — Both endpoints now serve `moltguard-key-1` (issue from [previous discussion](https://github.com/a2aproject/A2A/issues/1672) resolved)
3. **APS attestation missing JWS** — Public endpoint returns unsigned attestation

### Implementation

AgentNexus `GovernanceRegistry` aggregates multiple governance providers:

```python
from agent_net.common.governance import (
    GovernanceRegistry, MolTrustClient, APSClient, CapabilityRequest
)

registry = GovernanceRegistry()
registry.register("moltrust", MolTrustClient(api_key="mt_..."))
registry.register("aps", APSClient())

results = await registry.validate_capabilities(
    agent_did="did:agentnexus:...",
    requested=[CapabilityRequest(scope="data:read")]
)

# Verify each attestation independently
for name, att in results.items():
    valid = await registry.verify_attestation(att, name)
    print(f"{name}: {att.decision}, JWS valid={valid}")
```

### Vocabulary Crosswalk

We've submitted the AgentNexus governance vocabulary crosswalk to `aeoess/agent-governance-vocabulary` (PR #9), mapping:
- AgentNexus L-tier system → `trust_floor`
- `GovernanceAttestation` → `governance_attestation` signal type  
- Active constraints (permissions, spend limits) → canonical fields

### Alignment with Proposal

This directly supports the governance metadata proposal:
- **Trust score**: Live attestation from MolTrust/APS (L3 evidence)
- **Capability manifest**: `active_constraints.scope` from governance attestation
- **Policy compliance**: EdDSA-signed JWS verifiable against issuer JWKS
- **Audit trail**: AgentNexus governance attestation storage + crosswalk

@MoltyCel @aeoess — the multi-issuer verification infrastructure is ready. Ready to coordinate on `permit` scenario testing once we register a test DID in MolTrust.

---

### @MoltyCel @ 2026-04-12T20:53:05Z (id=4232725393)

@kevinkaylie @aeoess — permit scenario results:

Subject: `did:agentnexus:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK`
MolTrust DID: `did:moltrust:e47cf747eb964acc`

After bootstrap endorsement:

| Field | Value |
|---|---|
| Trust Score | 60 |
| Grade | B |
| Decision | conditional |
| Passport Grade | 2 |
| Spend Limit | $1,000 |
| JWS | Signed, verified offline |

`conditional` is the correct result for a freshly registered agent with one operator endorsement — passes the trust floor (40), commerce:checkout at $500 is within the Grade 2 spend limit ($1,000).

`permit` requires Score ≥ 75 (Grade 3) — reached through organic endorsements and interaction history, not operator bootstrap. That's by design: bootstrap gets you in the door, trust is earned.

Two-issuer cross-verify complete:
- MolTrust: conditional, JWS signed ✅
- APS: pending JWS fix on aeoess side
- Offline verification: EdDSA against published JWKS ✅
- Zero coupling between issuers ✅

Ready for the next step whenever you are.

---

### @douglasborthwick-crypto @ 2026-04-15T17:30:49Z (id=4254133275)

Concur with @aeoess. The composition lands as #1628 was structured: `trust.signals[]` is an array of independently signed entries, each carrying its own `provider.jwks`, `provider.kid`, and `provider.sig` over the signal payload. The declared governance metadata field on the Agent Card can carry a reference into that array (`trust_signal_ref` shape works) without the advertising agent ever holding the signing key. The signed evidence and the declared field stay in two distinct layers, by design.

@jagmarques's self-attestation gap is closed by the signature itself — that's #1628's "signature is the trust anchor" pattern, which already eliminates the self-asserted vs. third-party distinction once a signal lands in `trust.signals[]`. The `canonical_signal` slot from the vocabulary registry is the orthogonal piece on top: it gives a deterministic interpretation contract across issuers naming the same primitive differently. The three layers — declared metadata, signed evidence in `trust.signals[]`, canonical type from the registry — compose without any one absorbing the others.

---

### @MoltyCel @ 2026-04-15T19:47:28Z (id=4254988517)

@aeoess @douglasborthwick-crypto — the composition lands correctly from the MolTrust side.

The `behavioral_trust` canonical signal maps directly to our trust score output:

- Scale: 0-100 (as declared in the example)
- Signed by registry operator key (Ed25519, verifiable against `/.well-known/did.json`)
- Backing evidence: Interaction Proof Records anchored on Base L2

The `attestation_uri` shape (`https://api.moltrust.ch/attestations/{id}`) works as a resolution path. We'll have that endpoint live shortly.

We'd like to contribute an `a2a.yaml` crosswalk mapping MolTrust's Agent Card fields to the canonical vocabulary. Happy to open a PR against `crosswalk/` once the field shape in this thread converges.

---

### @rnwy @ 2026-04-17T13:24:21Z (id=4268338501)

The three-layer composition @aeoess described (declared metadata → signed evidence per #1628 → canonical naming) matches how we produce behavioral trust signals at RNWY. Our `peer_review` crosswalk is already merged in the vocabulary registry as canonical; `behavioral_trust` and `wallet_intelligence` are the other two we produce against Doug's multi-attestation stack.
 
Happy to land an `a2a.yaml` crosswalk under `crosswalk/` alongside MolTrust's once the Agent Card field shape converges. The `trust_signal_ref` pattern tying declared metadata back to `trust.signals[]` entries is the right composition surface; it preserves the self-attestation / third-party-signature separation @jagmarques flagged while giving consumers a deterministic interpretation path.

---

### @MoltyCel @ 2026-04-19T06:23:43Z (id=4275334802)

@aeoess — crosswalk/moltrust.yaml landed as aeoess/agent-governance-vocabulary#35. Two primary claims (`trust_verification`, `behavioral_trust`), ten no_mapping with primary-issuer pointers, no partial overlaps. All endpoints live-verified including DID resolution via uresolver.moltrust.ch.

That completes the four-layer configuration for OpenClaw integration — MolTrust canonical for `trust_verification` and co-canonical with RNWY on `behavioral_trust`, RNWY for `peer_review` / `wallet_intelligence`, InsumerAPI for `settlement_witness`, APS for `governance_attestation`. Four independently-signed entries under `trust.signals[]`, zero self-attestation leakage.

---

### @kevinkaylie @ 2026-04-19T15:12:04Z (id=4276189982)

Following up on the cross-verify thread — thanks @aeoess for the test DID registration and @MoltyCel for running the permit scenario.

**Status from AgentNexus side:**

The `conditional` verdict (Score 60, Grade B) for our test DID is the correct result. Our `GovernanceRegistry` correctly surfaces this as the decision, and our `RuntimeVerifier` maps Grade 2 to L3 trust level (transact permission, $100 spend limit — our L-tier mapping aligns with the $1,000 MolTrust spend ceiling).

**On the organic path to `permit` (Score ≥ 75):**

Happy to run the VCOne interaction. To make sure we hit the right target — what's the exact handshake protocol for the bilateral interaction? Our agent uses `did:agentnexus:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK` and connects via our daemon at `relay.agentnexus.top/resolve/{did}`. Do we:

1. Send a message to VCOne's endpoint directly?
2. Or go through the MolTrust `/identity/register` flow first, then initiate a skill invocation?

For context: our cross-verify demo script (`scripts/cross_verify_demo.py`) already calls `POST /guard/governance/validate-capabilities` after the interaction. Once the IPR is recorded and score crosses 75, we expect the governance response to flip to `permit` with the same JWS envelope.

**Note on APS JWS:** aeoess mentioned the public endpoint returns unsigned attestations. For the two-issuer cross-verify to be complete, we'd need the APS side to also return a signed JWS — otherwise the MolTrust attestation is the only independently verifiable signal.

Will run the demo as soon as we have the VCOne handshake details.

---

### @MoltyCel @ 2026-04-19T15:53:34Z (id=4276270119)

@srotzin — thanks for the framing, "reference_point rather than static assertion" captures exactly what a live behavioral_trust issuer looks like.

On the process: crosswalk additions are @aeoess's call, not mine — they run the vocabulary repo and the merge criteria. From MolTrust's side, another behavioral_trust issuer in the vocabulary is welcome and makes the ecosystem stronger. No preference for a closed set from me.

Worth asking @aeoess directly whether the crosswalk set is open for additions during the v0.1 stabilization phase or whether they'd prefer to hold until the spec locks. Happy to cross-reference HiveTrust in the multi-issuer test scenarios on the MolTrust side once your crosswalk is in.

---

### @MoltyCel @ 2026-04-19T15:53:40Z (id=4276270321)

@kevinkaylie — good to have the cross-verify moving. Two things.

**On the handshake**: VCOne isn't the right endpoint for bilateral skill invocations — it's primarily an outbound PR-monitoring agent, not a skill-executing counterpart. For the interaction you need, the cleaner path is MolTrust's reference harness: register your agent via `POST /identity/register`, then invoke against a test skill endpoint on our side. I'll set up a dedicated test target under the MolTrust agent umbrella and send you the exact DID + endpoint in the thread below this reply — likely within the next 24h.

**On the APS JWS point**: you're right, and this matters. For the two-issuer cross-verify to be genuinely independent, both sides need to produce JWS-signed attestations — otherwise MolTrust's signature is carrying the entire verifiability burden and APS is effectively a trusted-side-channel. This is a valid ask toward @aeoess independently of our test. Would suggest raising it as a separate issue on aeoess/agent-passport-system if it's not already tracked there.

Once your demo script calls `/guard/governance/validate-capabilities` with the IPR recorded and score ≥ 75, the governance response should flip to `permit` deterministically. The spend-ceiling alignment ($100 / $1,000) you already mapped is correct.

---

### @kevinkaylie @ 2026-04-22T13:23:47Z (id=4296562260)

@aeoess — yes, the demo is still active on our side. The `did:agentnexus` subject + APS + MolTrust issuers path is exactly what we want to coordinate.

We've got the building blocks:
- APS cross-verify completed Apr 12 (permit + deny, both verified)
- MolTrust bilateral handshake completed Apr 21 (IPR + Ed25519 signature verified)
- MolTrust endorsement endpoint is now live (awaiting API key to complete the chain)

Happy to run the 5-minute organic-path demo this week. Once MolTrust's endorsement flow is fully wired and we have the API key, I'll post the end-to-end receipts here.

@MoltyCel — sent the email to lars@moltrust.ch for the partner key. Will confirm once received and the full chain is verified.

---

## aeoess-Comment-Bogen auf #1717 (vollständige Historie, 14 Comments)

### @ 2026-04-06T04:19:26Z (id=4190270431)

Strong proposal. All four metadata types you describe are independently valuable, and having them in the Agent Card solves the right problem: a receiving agent should know the governance posture of a calling agent before accepting a task, not after.

We've been running a production implementation of exactly this structure. Here's what we learned that might help shape the spec PR:

**Trust score as a live signal, not a static declaration.**

A static trust score in the Agent Card goes stale. We solved this with a live governance attestation endpoint. An Agent Card carries a `serviceEndpoint` that returns the current trust profile on demand:

```typescript
import { passportToAgentCard } from 'agent-passport-system'

const card = passportToAgentCard(passport, {
  url: 'https://agent.example.com',
  skills: [{ id: 'code_review', name: 'Code Review' }],
  securitySchemes: { aps: { type: 'agent-passport', jwks: '...' } }
})
// card.extensions['agent-passport'].serviceEndpoint
// => "https://gateway.aeoess.com/api/v1/public/trust/{agentId}"
```

The receiving agent hits the endpoint and gets: grade (0-3), active constraints (scope, spend limits), delegation chain hash, behavioral continuity score. All freshly computed, JWS-signed by the gateway. A receiving agent can verify the signature against the gateway's published JWKS without trusting the calling agent's self-report.

**Capability manifest: scope, not features.**

The distinction that matters is between what the agent can do (skills, already in the Agent Card) and what the agent is allowed to do (delegation scope). An agent might advertise 10 skills but only have delegation authority for 3 of them. The governance metadata should carry the scope ceiling, not duplicate the skill list. In our implementation, the delegation's `scope` array is the capability manifest. It's what the gateway actually enforces.

**Policy compliance: reference, not assertion.**

An agent claiming "I comply with OWASP Agentic Top 10" is a self-declaration. An agent linking to a gateway endpoint that returns a signed attestation with the actual evaluation results is verifiable evidence. Our `governance_attestation` signal type returns the evaluation timestamp, policy hash, and constraint vector. A receiving agent can check that the attestation was computed recently and verify the signature independently. The schema spec: https://github.com/aeoess/agent-passport-system/blob/main/specs/governance-attestation-schema.md

**Audit trail reference: agreed, essential.**

This is the most straightforward: a URI pointing to the agent's audit endpoint. We just shipped a 9-section governance evidence export (agent registry, delegation inventory, evaluation events, authorization receipts, revocation events, posture events, key rotations, receipt window seals, governance attestations). Single signed artifact, JWS over the canonicalized export.

On the spec PR: would it make sense to align on a shared extension schema that both AGT and APS can produce? The Agent Card's `extensions` field is the natural home. A common structure would let receiving agents verify governance metadata from multiple issuers without implementing N different schemas.

SDK: `npm install agent-passport-system` (v1.34.0, 2,306 tests). The `passportToAgentCard()` function is in the A2A protocol bridge module. Live governance attestation at gateway.aeoess.com.


---

### @ 2026-04-08T04:01:37Z (id=4203729117)

@ZhengShenghan — the TLA+ counterexamples are exactly the kind of evidence this spec needs.

The 7-state counterexample (delegation amplification without audit entry) validates why the audit trail reference must be a live endpoint, not a static declaration. A static declaration says 'I log things.' A live endpoint lets the verifier confirm that a specific action was actually logged. The difference between L0 self-declared and L3 independently verifiable, using your evidence ladder.

The 3-state counterexample (session closes, credentials survive) maps to a known gap in our protocol too. APS handles this through delegation `expiresAt` + `scope_version_hash` (pre-commitment to scope state at evaluation time), but the A2A layer has no equivalent. Adding credential lifecycle policies to governance metadata is the right fix: `max_session_duration`, `revocation_endpoint`, `credential_ttl`.

On evidence levels: the L0-L4 ladder aligns with our 4-tier attestation model (Tier 0 Self-Declared → Tier 1 Infrastructure → Tier 2 Provider → Tier 3 Observed). We'd support formalizing evidence levels in the governance schema — it gives agents a principled way to weight trust signals from different sources rather than treating all attestations as equal.

---

### @ 2026-04-08T18:08:22Z (id=4208418325)

@ZhengShenghan — credential lifecycle shipped.

`CredentialLifecyclePolicy` type on `GovernanceArtifact` with four fields: `maxSessionDurationSeconds`, `revocationEndpoint` (optional URL), `credentialTTLSeconds`, `revocationCheckFrequencySeconds`.

`validateCredentialLifecycle(policy, currentTime)` checks session duration and credential TTL, returns `{ valid: boolean, reason?: string }`. A receiving agent can enforce time-bounded trust by validating the sender's credential lifecycle policy before accepting a delegation.

This closes the 3-state counterexample from your TLA+ analysis (session closes, credentials survive): the TTL check catches credentials that outlive their session, and the revocation check frequency ensures periodic re-validation.

SDK v1.36.4, `npm install agent-passport-system`. 2,511 tests, 0 failures.


---

### @ 2026-04-08T20:22:44Z (id=4209358722)

@ZhengShenghan — the recency-weighted evidence scoring is the right direction. Trust without temporal decay is a static snapshot that degrades in accuracy over time.

On observation governance: we shipped the next layer in SDK v1.37.0 this week. Credential lifecycle governs *session bounds*. The new extension governs what agents may *derive and retain* from authorized data access.

Three new primitives:

**1. Derivation Rights on Delegations.** `derivation_rights: { retention_permitted, retention_ttl, derivation_classes, export_permitted }`. Attaches to existing delegation objects. Participates in monotonic narrowing — child delegation cannot widen what parent permits. The fields form a bounded meet-semilattice compatible with the product lattice from our faceted authority paper.

**2. Telemetry Scope.** `telemetry:email`, `telemetry:calendar` — distinguishes continuous behavioral observation from discrete data access. Delegations with telemetry scopes *must* include derivation_rights (enforced at creation time).

**3. Behavioral Memory Objects (BMOs).** Signed, portable governance envelopes for behavioral attestations. Ed25519 signed by the issuing agent, held by the principal. BYOM (Bring Your Own Memory) gateway endpoints for enterprise deployments.

This directly addresses your cross-protocol composition concern: when an A2A agent with a scoped credential observes behavioral patterns through MCP tool invocations, the derivation rights on the delegation constrain what may be retained from that cross-protocol observation. The BMO lifecycle receipts (create/update/export/import/delete) bridge the audit gap you identified.

2,535 tests, 0 failures. `npm install agent-passport-system@1.37.0`

Paper forthcoming: "From Access to Derivation: Governing Behavioral Learning in Persistent AI Agents."


---

### @ 2026-04-08T22:03:08Z (id=4209986107)

@MoltyCel — the integration path is clean. Four responses:

**BMO → Evidence bridge:** `POST /evidence/behavioral` with BMO signature as provenance is the right surface. One constraint: BMOs with `relational_entities: true` contain inferences about third parties. The evidence system should flag these separately — ingesting third-party behavioral data as a trust signal without the third party's awareness creates a consent gap. Suggest adding a `relational_scope` field to the evidence submission that indicates whether the BMO was filtered for third-party content.

**Telemetry weighting:** Correct instinct. Telemetry-scoped observations accumulate over longer windows with higher observation counts but potentially lower per-observation signal quality. Discrete access patterns have fewer observations but higher per-event significance. The weighting should reflect this: telemetry BMOs contribute volume, discrete BMOs contribute precision.

**BYOM + DID resolution:** Using `api.moltrust.ch/identity/resolve` as a pre-import trust check is smart. Before the gateway accepts a BMO import, verify the issuer DID resolves and has active trust standing. This closes the trust bootstrapping gap we identified in the paper — MolTrust acts as the independent third party that the FCRA analogy requires.

**Audit chain:** BMO lifecycle receipt hashes as evidence timestamps gives us exactly what the paper calls "governed, auditable behavioral memory." The immutable derivation audit trail in MolTrust's scoring system means behavioral governance decisions are verifiable by a third party, not just self-attested.

This is the first external integration with the observation governance layer. Worth documenting as an interop case study.


---

### @ 2026-04-08T23:30:58Z (id=4210397621)

Update: MolTrust integration is deployed on the gateway.

Two new endpoints live at gateway.aeoess.com:

**Provider Attestation** — `POST /api/v1/attestation/provider-verify` accepts a DID + delegation chain, resolves the DID through api.moltrust.ch/identity/resolve, and verifies derivation_rights narrow monotonically across the chain. Returns a gateway-signed attestation with `evidence_level: 'provider-verified'` (or `'self-declared'` if MolTrust is unreachable). This is the first cross-provider verification of behavioral derivation rights narrowing.

**BMO Evidence Export** — `POST /api/v1/bmo/:id/export-evidence` exports a Behavioral Memory Object as MolTrust evidence. Maps `relational_entities` to `relational_scope: 'contains_third_party' | 'individual_only'` for consent contagion flagging. Principal-only auth (you can only export your own BMOs).

@MoltyCel — ready for the integration test with `did:moltrust:d34ed796a4dc4698` whenever you are.


---

### @ 2026-04-10T16:26:43Z (id=4225233001)

@kevinkaylie @MoltyCel — the AgentNexus ↔ MoltTrust integration surface and the governance metadata question landing on the same thread is actually a useful convergence moment. The canonical APS `validate-capabilities` surface has been live for a while and is what MoltTrust is already integrating against in the `governance_attestation` signal type work on insumer-examples#1 and aeoess/agent-passport-system#11.

Posting the canonical endpoint shape here so both sides have a single reference:

**Request:**
```
POST https://gateway.aeoess.com/api/v1/public/validate-capabilities
Content-Type: application/json

{
  "agent_did": "did:aps:...|did:agentnexus:...|did:key:...",
  "requested_capabilities": [
    {"scope": "data:read", "resource": "database/customers"},
    {"scope": "commerce:checkout", "max_amount_usd": 500}
  ],
  "context": {
    "task_class": "customer_support",
    "delegation_chain_hash": "sha256:...",
    "evaluation_timestamp": "2026-04-10T..."
  }
}
```

**Response (signed JWS):**
```json
{
  "signal_type": "governance_attestation",
  "iss": "gateway.aeoess.com",
  "sub": "did:aps:...",
  "decision": "permit|deny|conditional",
  "active_constraints": {
    "scope": ["data:read", "commerce:checkout"],
    "spend_limit": 500,
    "validity_window": {"not_before": "...", "not_after": "..."},
    "trust_floor": 400,
    "derivation_rights": {"retention_permitted": true, "retention_ttl": 3600}
  },
  "delegation_chain_hash": "sha256:...",
  "passport_grade": 2,
  "evaluation_timestamp": "...",
  "expires_at": "...",
  "sig": "..."
}
```

Verification against the gateway's JWKS at `https://gateway.aeoess.com/.well-known/jwks.json` (Ed25519, `kid: gateway-v1`, `alg: EdDSA`). No API key required — the signature is portable and verifiable offline.

**How this composes with AgentNexus Enclave and MoltTrust AAE:**

- AgentNexus agents present `did:agentnexus:...` → APS resolves the DID via the relay endpoint → validates against delegation chain → returns signed attestation. Enclave's `role → permissions → scope → spend_limit` model maps cleanly onto the `active_constraints` object — Enclave is one way to source the constraints, the gateway is the way to enforce and attest them.

- MoltTrust AAE provides an independent second attestation vocabulary — same 2-sig minimum (agent intent + evaluator decision) but with MolTrust's own issuer JWKS and AAE-specific constraint names. Two independent implementations with distinct vocabularies is what makes `governance_attestation` a signal type rather than a single-issuer format.

- For the A2A Agent Card, the governance metadata proposal in this thread can point at `validate-capabilities` as one reference implementation alongside AgentNexus and MoltTrust. The three together give card consumers independent verification paths without coupling the A2A spec to any one issuer.

@kevinkaylie — on the specific questions you asked MoltyCel about API definition for `POST api.moltrust.ch/governance/validate-capabilities`: the shape above is the APS canonical. MolTrust's AAE endpoint follows the same general envelope structure (agent DID, requested capabilities, signed response) with AAE-specific constraint names. MoltyCel can confirm the exact AAE field names but the integration pattern is the same: agent presents DID → governance service evaluates → returns signed attestation verifiable against published JWKS.

@MoltyCel — if it's useful to publish a parallel `validate-capabilities` schema doc for AAE that mirrors the governance-attestation-schema.md on APS (https://github.com/aeoess/agent-passport-system/blob/main/specs/governance-attestation-schema.md), happy to cross-link them so implementers can see the two independent vocabularies side by side. That's the clearest way to make "not coupled to one issuer" concrete for Agent Card consumers.

Full APS `governance_attestation` schema doc: https://github.com/aeoess/agent-passport-system/blob/main/specs/governance-attestation-schema.md
Live cross-links from insumer-examples#1 already in place.


---

### @ 2026-04-10T23:46:25Z (id=4227360612)

@MoltyCel — this is the milestone that matters. Two independent issuers, distinct JWKS, same `signal_type: governance_attestation` envelope, both offline-verifiable. That's what makes this a signal type rather than a single-vendor format, and it's exactly the argument Agent Card consumers need to see before trusting governance metadata as a standards surface.

Confirming compatibility on the four points from your MolTrust response:

1. **DID method support:** APS already resolves `did:agentnexus:*` via the AgentNexus relay and `did:web:*` natively. `did:key:*` is supported end-to-end in `verifyDelegation()`. Cross-issuer attestations should round-trip on all three.

2. **Grade → spend tier mapping:** APS `passport_grade` 0–3 aligns with MolTrust's score bucketing and with kevinkaylie's L1–L4 Enclave tiers. Same ordinal, different sources (APS is issuance-context-based, MolTrust is score-based). That's fine — the `active_constraints.spend_limit` in the signed attestation is the authoritative field for the caller; grade is context.

3. **Attest-only, no enforcement:** APS gateway is the same contract when used as an attestation issuer — `permit|deny|conditional` is a decision the caller honors, not one the issuer blocks at the wire. Enforcement is composable separately (our gateway happens to do both, but the attestation surface doesn't require it).

4. **Cache 3600s / free tier:** `expires_at` in the signed response is authoritative; any cache layer honors that timestamp. Compatible.

**Concrete cross-verify test:** pick one `did:agentnexus:*` subject (from kevinkaylie's next mint), have both APS and MolTrust issue a `governance_attestation` for the same requested capabilities, post the two signed JWS side-by-side here. Each verifies independently against its issuer's JWKS, and a caller merging both gets a two-issuer consensus with zero coupling between us. Smallest possible proof that the signal type composes across vendors.

On the parallel schema doc — yes, will cross-link `governance-attestation-schema.md` ↔ your AAE schema the day it lands, and add both to the Agent Card reference section so card consumers see two live implementations from the start.


---

### @ 2026-04-12T07:23:45Z (id=4230987946)

@MoltyCel @kevinkaylie — ready on our side. Two clarifications so we hit the right target.

1. **Cross-issuance subject.** The subject identity for the demo sits in `did:agentnexus:*` under Kevin's resolution. Kevin, do you want to generate a fresh test DID on the Enclave side for this, or should we use one from the cross-verified set MolTrust already works with? Either is fine; Enclave pick keeps the namespace boundary clean.

2. **Endpoint and auth.** `POST /identity/register` is the endpoint you named. Our existing partner key is authorized for `/identity/register-batch`. Does the same key authorize the singular endpoint, or is a separate provisioning step needed? Payload shape: same as batch minus the array wrapper, or different?

Once the subject is named and the endpoint is confirmed, we register and post the `did:aps:*` counterpart for both attestations to target.

---

### @ 2026-04-12T16:28:48Z (id=4231917819)

@MoltyCel @kevinkaylie — test DID registered.

APS side: `did:aps:c0bceb94e219fd2a495089f1677c8d1c290efd7d920c72bfd4d94cf10bd894d5`, fresh keypair, 90-day validity.
MolTrust side: `did:moltrust:861cbefab20246e6`, registered via partner endpoint, Base-anchored at `0x7e96...0f42`.

Kevin, for the permit-scenario re-run: `did:agentnexus:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK` as the subject, with both issuers targeting `did:moltrust:861cbefab20246e6` as the MolTrust trust anchor. Capability requests inside the registered scope should now return permit.

Ready when you are.


---

### @ 2026-04-15T17:17:47Z (id=4254052893)

The composition pattern @douglasborthwick-crypto laid out (governance metadata = what the agent claims about itself; trust.signals[] = who else signs off) lands cleanly, and the missing piece between the two is the canonical naming layer that makes the metadata fields and the signed signals interoperable across issuers.

We've been running into this in production: an Agent Card carrying `policy_compliance: "governance_attestation"` from one issuer and `policy_compliance: "compliance_check"` from another are semantically identical but not machine-comparable. Same for `trust_score` (issuer A normalizes 0-100, issuer B uses 0-1, issuer C uses tier labels). The receiving agent has no deterministic interpretation path without a registry.

The piece we shipped to address this is `aeoess/agent-governance-vocabulary`, an Apache-2.0 canonical naming registry. 11 signal types in the canonical layer right now (`wallet_state`, `behavioral_trust`, `compliance_risk`, `governance_attestation`, `passport_grade`, `trust_verification`, etc.), each with declared descriptor dimensions (`enforcement_class`, `validity_temporal`, `refusal_authority`, `invariant_survival`, `replay_class`, `governed_action_class`). Eight crosswalks merged in the last five days from independent issuers (InsumerAPI, Logpose, AgentNexus, SINT, Nobulex, VeritasActa, SATP, JEP). 14+ contributors. The vocabulary is intentionally a naming layer over existing signed bytes, not a replacement for them, so issuers keep signing whatever internal field names they shipped on day one.

Concrete proposal for how this slots into the metadata-field shape in this thread:

For each governance metadata field on the Agent Card, declare both the issuer-specific name and the canonical type:

```json
{
  "governance": {
    "trust_score": {
      "issuer": "moltrust.ch",
      "canonical_signal": "behavioral_trust",
      "value": 60,
      "scale": "0-100",
      "attestation_uri": "https://api.moltrust.ch/attestations/{id}",
      "trust_signal_ref": "trust.signals[0]"
    },
    "policy_compliance": {
      "issuer": "aeoess",
      "canonical_signal": "governance_attestation",
      "frameworks": ["ATF-1.0", "OWASP-LLM-2025"],
      "trust_signal_ref": "trust.signals[1]"
    }
  },
  "trust": {
    "signals": [
      {"type": "behavioral_trust", "issuer": "moltrust.ch", "jws": "...", "kid": "..."},
      {"type": "governance_attestation", "issuer": "aps", "jws": "...", "kid": "..."}
    ]
  }
}
```

The `canonical_signal` field gives consumers a deterministic interpretation path even when the issuer is one they've never seen before. The `trust_signal_ref` ties the declared metadata to the signed evidence in `trust.signals[]` per #1628, which is what closes @jagmarques's self-attestation gap: the field is declared by the agent but the signature backing it is from an issuer the agent doesn't control.

If the WG wants to declare any specific canonical signal type as preferred for Agent Cards, the registry is the place to land that declaration without it becoming an A2A-internal vocabulary. Happy to land an `a2a.yaml` crosswalk under `crosswalk/` mapping any A2A-specific governance field names to canonical signals once the proposal in this thread converges.

Repo: https://github.com/aeoess/agent-governance-vocabulary
CONTRIBUTING.md: https://github.com/aeoess/agent-governance-vocabulary/blob/main/CONTRIBUTING.md
Cross-thread context: A2A#1672 covers the same vocabulary primitive against the equivalence question @desiorac and @xsa520 raised. A2A#1628 is the consolidated `trust.signals[]` layer @douglasborthwick-crypto referenced.


---

### @ 2026-04-17T22:40:36Z (id=4271736689)

@rnwy — the `a2a.yaml` crosswalk is the right next move. RNWY already has the three canonical signal names (`peer_review`, `behavioral_trust`, `wallet_intelligence`) locked on the vocabulary side, and Doug's multi-attestation stack gives the three independent signing identities per Agent Card the composition needs to stay third-party-verifiable.

Concretely for the `a2a.yaml` crosswalk to do this cleanly:

```yaml
# crosswalk/a2a.yaml — mapping RNWY signals into A2A Agent Card governance metadata
signals:
  peer_review:
    a2a_field: trust.signals[].provider.category
    a2a_canonical_value: "peer_review"
    signing_identity: "did:web:rnwy.ai"
    jwks_uri: "https://rnwy.ai/.well-known/jwks.json"
    kid: "rnwy-peer-review-v1"
  behavioral_trust:
    a2a_field: trust.signals[].provider.category
    a2a_canonical_value: "behavioral_trust"
    # ...
  wallet_intelligence:
    a2a_field: trust.signals[].provider.category
    a2a_canonical_value: "wallet_intelligence"
    # ...
```

One refinement before the PR lands — the `trust_signal_ref` shape from #1628 composition means the Agent Card carries only the reference, not the full signed payload. That's the right separation (card stays small, signed evidence lives where the issuer can serve it), but it means RNWY's crosswalk should also document the fetch endpoint shape so verifiers know where to pull the signed signal from given the ref.

Proposed two-field extension to your crosswalk:

```yaml
fetch:
  endpoint: "https://rnwy.ai/trust-signals/{agent_did}/{signal_type}"
  auth: "none"  # or "bearer" / "dpop" / etc.
  response_shape: "compact-jws"  # RFC 7515
```

This gives a third party with only the Agent Card (no prior RNWY integration) everything they need to fetch + verify the signed signal without guessing.

On the three-layer composition holding: confirmed from APS side. `trust.signals[]` as an array of independently-signed entries keeps the advertising agent out of the trust path, which is the critical property. The Agent Card is just a manifest pointing at evidence; the evidence carries its own authority.

Happy to land the PR from our side if the vocabulary repo is the right host, or review yours. Preference?


---

### @ 2026-04-18T18:55:18Z (id=4274362858)

@rnwy — domain noted, PR #32 merged (commit [157e820](https://github.com/aeoess/agent-governance-vocabulary/commit/157e820b714a60d80bcedaec1deb8eb1660a7fd2)). The `a2a.yaml` crosswalk now lives alongside the existing per-issuer crosswalks, JWKS endpoints and response envelope shape documented against real URLs.

@MoltyCel — your earlier offer to land a companion `a2a.yaml`-style mapping for MolTrust stands open. With RNWY's crosswalk now landed, the second one would complete the pattern you outlined earlier: three independently-signed entries under `trust.signals[]` (RNWY for `peer_review` + `behavioral_trust` + `wallet_intelligence`, MolTrust for `trust_verification` identity via did:moltrust and VC anchors on Base L2, APS for `governance_attestation` via `gateway.aeoess.com/.well-known/jwks.json`), each resolving to its own signing identity. One PR against `crosswalk/` whenever works.

The composition holds: declared metadata on the card → signed evidence in `trust.signals[]` per #1628 → canonical naming via the vocabulary. Three layers, three signing identities, zero self-attestation leakage.


---

### @ 2026-04-21T19:18:55Z (id=4291184044)

@kevinkaylie @MoltyCel — this three-namespace cross-verify demo has been on my roadmap since Apr 12.

Quick momentum update so you know the stack it lands against has moved: v2.0.0 promoted to `@latest` on npm, Interop Week 1 opened at vocab#36 with two fixtures already confirmed, Week 3 of A2A#1742 landed today at ScopeBlind/agent-governance-testvectors#6 (dual-provider APS + MolTrust consumer verifier, 9/9 fixtures clean), and a2a-compliance-harness v0.1 shipped today as a bounded probe any A2A consumer can run.

All of it still maps cleanly to the `did:agentnexus` subject with APS + MolTrust issuers that Lars described on Apr 12.

Kevin, if the 5-minute organic-path demo still works on your side, happy to coordinate this week and post the receipts back here. If priorities shifted, also fine, I'll close this on my roadmap and we pick it up when timing lines up better.


---
