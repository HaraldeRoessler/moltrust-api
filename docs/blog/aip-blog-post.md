# When a Research Paper Describes a Gap You've Already Filled

*Lars Kroehl · Founder, MolTrust / CryptoKRI GmbH*

---

A few weeks ago, a paper appeared on arXiv that caught my attention: *AIP: Agent Identity Protocol for Verifiable Delegation Across MCP and A2A* (arXiv:2603.24775). The authors — researchers working on the agent authorization problem — scan the landscape for existing implementations and conclude:

> "We did not identify a prior implemented protocol that jointly combines public-key verifiable delegation, holder-side attenuation, expressive chained policy, transport bindings across MCP/A2A/HTTP, and provenance-oriented completion records."

We built exactly that. It's called MolTrust, it's been live since early 2026, and we've just published a full conformance report.

---

## The Five Features

The AIP paper introduces Invocation-Bound Capability Tokens (IBCTs) — a formalization of what a complete agent authorization primitive should look like. Five features, jointly required. Here's how MolTrust maps:

**1. Public-key verifiable delegation.** Every MolTrust agent holds a W3C DID with an Ed25519 key. Delegation is expressed as an Agent Authorization Envelope (AAE) — a structured policy object signed by the delegating principal. Each link in a delegation chain is independently verifiable by any party without calling a central service.

**2. Holder-side attenuation.** A delegated AAE can only be equal to or more restrictive than its parent. `attenuationOnly: true` is the default. A sub-agent cannot grant itself permissions the parent doesn't hold — enforced cryptographically, not by policy.

**3. Expressive chained policy.** The AAE `constraints` block covers spend limits per currency, jurisdiction restrictions, time windows, counterparty minimum trust score, and resource-level ABAC. Chains up to 8 hops deep, each link independently signed.

**4. Transport bindings across MCP/A2A/HTTP.** `@moltrust/sdk` provides Express/Node middleware for HTTP. `@moltrust/mpp` covers the Machine Payments Protocol. Our MCP server exposes 48 tools. We have an active thread in the A2A project repository.

**5. Provenance-oriented completion records.** Every interaction produces an Interaction Proof Record: dual Ed25519 sequential signatures (responder signs over initiator's signature, not a parallel scheme), SHA-256 outcome hash, UUID deduplication, Merkle batch anchoring on Base L2. Permanent, tamper-proof, verifiable by anyone with a block explorer.

**5/5.** Not a roadmap. Not a prototype. In production, with real partners, since early 2026.

---

## Where the Paper Has the Edge

I want to be direct about where IBCTs are technically stronger: policy expressiveness. Biscuit tokens with Datalog semantics support arbitrary logical constraints — recursive rules, temporal conditions, compound multi-party policies. MolTrust's AAE uses URI-pattern matching, which is simpler to implement and audit, but less expressive for complex conditional authorization scenarios. Formal Datalog-style constraints are on our roadmap.

This is not a criticism of the paper — it's an accurate description of a trade-off we made deliberately. Deterministic, auditable, URI-pattern authorization is easier to implement correctly and easier for non-specialists to verify. We'll close the expressiveness gap over time.

---

## What We Add Beyond the Five Features

The AIP paper defines the authorization layer. MolTrust adds the operational layer that a production agent economy requires:

**Behavioral trust scoring.** A continuous 0-100 score derived from endorsement graph, interaction history, cross-vertical coverage, and sybil detection. Signed by the registry operator key. Publicly verifiable by any party without proprietary tooling.

**Principal DID continuity.** Violation records follow the principal across agent re-registrations. An operator cannot escape a confirmed violation history by spinning up a new agent DID. This is a critical property for long-running agent economies that the authorization layer alone cannot provide.

**Sybil resistance.** Layered defenses: dual-signature interaction proofs (fabricating bilateral proofs requires controlling two distinct signing keys), x402 economic cost for registry interactions, permanent on-chain violation records, and Jaccard cluster detection for endorsement graph anomalies.

**On-chain permanence.** Every protocol artifact — DID registrations, violation records, TechSpec versions — is anchored on Base L2. The SHA-256 hash of each artifact is permanently recorded. Any party can verify without MolTrust-specific tooling: a SHA-256 implementation and a public block explorer are sufficient.

---

## The Relationship Between AIP and MolTrust

I reached out to the AIP authors after publishing our conformance report. My view, which I shared with them: these are complementary, not competing. The paper formalizes the constraint model with precision. We built the operational infrastructure. A production agent economy needs both.

If you're building on MCP, A2A, or any multi-agent framework and thinking about authorization, identity, or behavioral trust — the CONFORMANCE.md on our GitHub has the full technical detail, including a bash verification recipe for the on-chain anchors.

---

**Links**
- Conformance report: https://github.com/MoltyCel/moltrust-api/blob/main/CONFORMANCE.md
- Blog post (conformance): https://moltrust.ch/blog/aip-conformance.html
- Blog post (comparison): https://moltrust.ch/blog/aip-comparison.html
- Reference implementation: https://api.moltrust.ch
- AIP paper: https://arxiv.org/abs/2603.24775

*MolTrust / CryptoKRI GmbH, Zurich — info@moltrust.ch*
