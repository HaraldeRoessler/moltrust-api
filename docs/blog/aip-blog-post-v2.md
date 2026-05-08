# Mapping MolTrust to the AIP Protocol Feature Set — and Beyond

*Lars Kroehl · Founder, MolTrust / CryptoKRI GmbH*

---

A few weeks ago, a paper appeared on arXiv that caught my attention: *AIP: Agent Identity Protocol for Verifiable Delegation Across MCP and A2A* (arXiv:2603.24775¹). The authors scan the landscape for existing implementations and conclude:

> "We did not identify a prior implemented protocol that jointly combines public-key verifiable delegation, holder-side attenuation, expressive chained policy, transport bindings across MCP/A2A/HTTP, and provenance-oriented completion records."

MolTrust implements these five features — not as a roadmap, but in production since March 2026. Here is how each one maps.

---

## The Five Features

**1. Public-key verifiable delegation.** Every MolTrust agent holds a W3C DID with an Ed25519 key. Delegation is expressed as an Agent Authorization Envelope (AAE) signed by the delegating principal. Each link in a delegation chain is independently verifiable by any party without calling a central service.

**2. Holder-side attenuation.** A delegated AAE can only be equal to or more restrictive than its parent. `attenuationOnly: true` is the default. A sub-agent cannot grant itself permissions the parent doesn't hold — enforced cryptographically, not by policy.

**3. Expressive chained policy within a URI-pattern model.** The AAE `constraints` block covers spend limits, jurisdiction restrictions, time windows, counterparty minimum trust score, and resource-level ABAC. Chains up to 8 hops, each link independently signed. For complex conditional authorization — recursive rules, temporal Datalog — IBCTs are technically stronger, and this is on our roadmap.

**4. Transport bindings across MCP/A2A/HTTP.** `@moltrust/sdk` provides Express/Node middleware for HTTP. `@moltrust/mpp` covers the Machine Payments Protocol. Our MCP server exposes 48 tools. Active thread in the A2A project repository (a2aproject/A2A#1628).

**5. Provenance-oriented completion records.** Every interaction produces an Interaction Proof Record: dual Ed25519 sequential signatures (responder signs over initiator's signature — not parallel), SHA-256 outcome hash, UUID deduplication, Merkle batch anchoring on Base L2. Permanent, tamper-proof, verifiable by anyone with a block explorer.

---

## Verify It Yourself

TechSpec v0.8 is anchored at Base L2 Block 44638521. Anyone can verify:

```
https://basescan.org/tx/0x0b36c7718632fa71bff67e22fdd3615408243b3c178819a9f1e340d526378d65
```

Decode the calldata — it contains `MolTrust/DocumentIntegrity/1 SHA256:cbf10c2e...`. Recompute the SHA-256 of the PDF. They match. No proprietary tooling required.

---

## Where AIP Is Technically Superior

Biscuit tokens with Datalog semantics support arbitrary logical constraints — recursive rules, temporal conditions, compound multi-party policies. MolTrust's URI-pattern approach is simpler to implement and audit, but less expressive for complex conditional authorization. We made this trade-off deliberately. We'll close the gap over time.

---

## What We Add Beyond the Five Features

**Behavioral trust scoring.** A continuous 0-100 score from endorsement graph, interaction history, cross-vertical coverage, and sybil detection. Signed by the registry operator. Publicly verifiable.

**Principal DID continuity.** Violation records follow the principal across agent re-registrations. An operator cannot escape a confirmed violation history by spinning up a new agent DID.

**Sybil resistance.** Layered: dual-signature proofs, x402 economic cost, permanent on-chain violation records, Jaccard cluster detection.

**On-chain permanence.** Every protocol artifact anchored on Base L2. Verifiable via any block explorer without MolTrust-specific tooling.

---

## In Production

aeoess — an A2A-based agent platform operated by Tymofii Pidlisnyi — runs trust verification through MolTrust in production, with a live webhook integration for grade changes and revocation events.

---

## The Relationship Between AIP and MolTrust

I reached out to the AIP authors after publishing our conformance report. My view: these are complementary, not competing. The paper formalizes the constraint model. We built the operational infrastructure. A production agent economy needs both.

Full technical detail, including a bash verification recipe for the on-chain anchors, is in CONFORMANCE.md on our GitHub.

---

¹ Molinari et al. (2026). *AIP: Agent Identity Protocol for Verifiable Delegation Across MCP and A2A.* arXiv:2603.24775 [cs.CR]. See also IETF draft-prakash-aip-00.

**Links**
- Conformance report: https://github.com/MoltyCel/moltrust-api/blob/main/CONFORMANCE.md
- Blog (conformance): https://moltrust.ch/blog/aip-conformance.html
- Blog (comparison): https://moltrust.ch/blog/aip-comparison.html
- Reference implementation: https://api.moltrust.ch

*MolTrust / CryptoKRI GmbH, Zurich — info@moltrust.ch*
