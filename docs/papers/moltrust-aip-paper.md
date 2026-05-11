# MolTrust: A Production Implementation of the AIP Feature Set for Autonomous Agent Authorization

**Authors:** Lars Kroehl  
**Affiliation:** CryptoKRI GmbH, Zurich, Switzerland  
**Contact:** info@moltrust.ch  
**Date:** April 2026  
**Repository:** https://github.com/MoltyCel/moltrust-api  
**Reference Implementation:** https://api.moltrust.ch  
**Classification:** cs.CR, cs.MA

---

## Abstract

Molinari et al. (2026) introduce Invocation-Bound Capability Tokens (IBCTs) and identify five features jointly required for complete autonomous agent authorization, reporting that no prior implemented protocol combines them. This paper documents that the MolTrust Protocol — a production registry operational since March 2026 — implements all five features identified in Molinari et al.: public-key verifiable delegation, holder-side attenuation, expressive chained policy, transport bindings across MCP/A2A/HTTP, and provenance-oriented completion records. We describe the technical implementation of each feature, report five conformance test vectors verified against the live endpoint (April 2026), and document three additional capabilities outside the AIP scope: a behavioral trust scoring model anchored on a public blockchain, principal DID continuity for violation record persistence across agent re-registrations, and layered sybil resistance mechanisms. We also identify one area where the AIP formalization is technically superior — Biscuit/Datalog policy expressiveness — and document this as a roadmap item (H2 2026). All protocol artifacts are anchored on Base L2 and independently verifiable without proprietary tooling.

---

## 1. Introduction

The emergence of autonomous software agents operating across the Model Context Protocol (MCP) and Agent-to-Agent (A2A) protocol creates a critical need for verifiable agent identity, delegation, and behavioral attestation. Molinari et al. (2026) formalize this need through the concept of Invocation-Bound Capability Tokens (IBCTs), survey approximately 2,000 MCP servers (finding zero with authentication), and conclude that no prior implemented protocol jointly addresses five core requirements.

MolTrust is a W3C DID/VC-based trust infrastructure platform for autonomous AI agents, operational since March 2026. This paper presents a systematic conformance analysis of MolTrust against the AIP feature set defined by Molinari et al., documents the implementation details for each feature, and describes the additional operational capabilities MolTrust provides beyond the authorization layer.

We note that this paper is an implementation report, not a competing proposal. The AIP formalization by Molinari et al. and the MolTrust implementation address complementary aspects of the agent authorization problem: the former provides formal precision in constraint modeling; the latter provides the operational infrastructure — trust scoring, behavioral continuity, sybil resistance, and on-chain permanence — that a production agent economy requires.

---

## 2. Background and Related Work

### 2.1 The AIP Feature Set (Molinari et al., 2026)

Molinari et al. (arXiv:2603.24775) introduce Invocation-Bound Capability Tokens as a primitive that fuses identity, attenuated authorization, and provenance binding into a single append-only token chain. The authors identify five features that must be jointly present:

- **F1 — Public-key verifiable delegation:** Agent authority must be cryptographically bound to a verifiable identity and independently verifiable without a trusted intermediary.
- **F2 — Holder-side attenuation:** Delegated authority must be enforceable as a strict subset of the delegating principal's authority.
- **F3 — Expressive chained policy:** Policies must support multi-hop delegation chains with expressive per-hop constraints.
- **F4 — Transport bindings:** The protocol must operate across MCP, A2A, and HTTP transport layers.
- **F5 — Provenance-oriented completion records:** Interactions must produce tamper-evident, non-repudiable records of their outcomes.

IBCTs operate in two wire formats: compact mode (signed JWT for single-hop cases) and chained mode (Biscuit token with Datalog policies for multi-hop delegation). Reference implementations are provided in Python and Rust.

### 2.2 MolTrust Protocol Overview

MolTrust is organized around three layers. Layer A (Protocol Standard) defines normative data formats, signing rules, verification flows, and lifecycle semantics. Layer B (Reference Registry) defines the MolTrust-operated service layer. Layer C (Reference Reputation Model) is an informative scoring model. All five AIP features are implemented at Layer A.

The core authorization primitive is the Agent Authorization Envelope (AAE) — a machine-evaluable policy object embedded in or accompanying a W3C Verifiable Credential. The AAE consists of three top-level objects: `mandate` (what the agent may do), `constraints` (operational boundaries), and `validity` (issuer, holder binding, and temporal scope).

---

## 3. Feature Implementation

### 3.1 F1 — Public-Key Verifiable Delegation

MolTrust implements agent identity through W3C Decentralized Identifiers conforming to DID Core v1.0. Each agent holds a `did:moltrust` identifier with an Ed25519 verification key. The AAE `validity.holderBinding` field cryptographically binds the delegation to a specific agent DID. Verifiers authenticate the binding by resolving the DID Document and verifying the Ed25519 signature over the RFC 8785 canonical JSON serialization of the AAE, without calling a central service.

Key rotation is supported: revoked keys are retained in the DID Document with `"revoked": true` and a `revokedDate`, preserving a verifiable timeline of key epochs.

### 3.2 F2 — Holder-Side Attenuation

The AAE `delegation` sub-object includes `attenuationOnly: true` as default. Conformant AAE evaluators enforce that any delegated AAE has `allowedActions` as a strict subset of the parent's effective allowed actions (after deny exclusion), `limits` equal to or more restrictive, and `scope.jurisdictions` as a subset of the parent's. The `deniedActions` field implements deny-precedence: an action matching both `allowedActions` and `deniedActions` is denied.

Conformance test vector TV-005 (Section 4) specifically covers attenuation enforcement.

### 3.3 F3 — Expressive Chained Policy

The AAE `constraints` block provides: spend limits (`autonomousThreshold`, `stepUpThreshold`, `approvalThreshold`) per currency (USDC, EUR, CHF, USD); jurisdiction restrictions (ISO 3166-1 alpha-2); time window constraints (`allowedDays`, `allowedHours`, `timezone`); counterparty minimum trust score gate (`counterpartyMinScore`); and resource-level ABAC via `mandate.resources`. Delegation chains support up to 8 hops, each link independently signed.

**Comparison with AIP:** Biscuit/Datalog semantics as used in IBCTs support arbitrary logical constraints — recursive rules, temporal conditions, compound multi-party policies. MolTrust's URI-pattern approach is simpler to implement and audit but less expressive for complex conditional authorization. Datalog-style formal constraints are a planned roadmap item (H2 2026). We consider this an honest limitation of the current implementation.

### 3.4 F4 — Transport Bindings

MolTrust provides transport bindings through: `@moltrust/sdk` v1.1.0 (HTTP middleware — `middleware()` / `register()` / `verify()`); `@moltrust/mpp` v1.0.3 (Machine Payments Protocol / x402 HTTP 402 challenge-response, `requireScore({ minScore, failBehavior })`); and a Model Context Protocol server (`@moltrust/openclaw` v0.1.0, 48 tools). An active implementation thread in the A2A project repository (a2aproject/A2A#1628) documents A2A integration. MolTrust is referenced in OpenClaw RFC #49971 for agent identity binding.

### 3.5 F5 — Provenance-Oriented Completion Records

MolTrust Interaction Proof Records (IPRs) use a sequential dual-signature scheme. The initiator signs the canonical proof object first; the responder's signature covers the initiator's signature, creating a non-repudiable commitment chain. This is explicitly sequential — independent implementations signing the same payload in parallel are non-conformant. Outcome hashes (SHA-256 of the RFC 8785 canonical outcome object) and UUID deduplication prevent replay and fabrication. Completed proofs are Merkle batch-anchored on Base L2.

---

## 4. Conformance Test Vectors

Five test vectors were executed against the live MolTrust endpoint (April 2026):

| Vector | Description | Result |
|---|---|---|
| TV-001 | AAE delegation narrowing — top-level agent | Pass |
| TV-002 | AAE delegation narrowing — sub-agent depth 2 | Pass |
| TV-003 | AAE delegation narrowing — sub-agent depth 3 | Pass |
| TV-004 | Deny-precedence: action matched by both allowedActions and deniedActions | Pass |
| TV-005 | Attenuation enforcement: sub-agent scope exceeds parent | Correctly rejected |

Shared canonicalization: JCS RFC 8785. Shared signing: Ed25519.

---

## 5. Capabilities Beyond the AIP Scope

### 5.1 Behavioral Trust Scoring

MolTrust maintains a continuous trust score (0-100) for each registered agent, derived from a weighted endorsement graph, interaction history, cross-vertical coverage, and sybil detection heuristics. Score formula: `score = clamp(0.6 * direct_score + 0.3 * propagated_score + 0.1 * cross_vertical_bonus + interaction_bonus - sybil_penalty, 0, 100)`. The score is signed by the registry operator key and publicly verifiable.

### 5.2 Principal DID Continuity

Violation records in MolTrust are associated with both the agent DID and the principal DID. Re-registration of a new agent DID for a principal with confirmed, unresolved violations is flagged by the registry. Behavioral history is therefore portable across agent re-deployments — a property the authorization layer alone cannot provide.

### 5.3 Sybil Resistance

MolTrust implements layered sybil resistance: dual-signature interaction proofs (fabricating bilateral proofs requires controlling two distinct signing keys); x402 payment protocol creating measurable economic cost for registry interactions; permanent on-chain violation records associated with principal DIDs; and Jaccard similarity cluster detection for endorsement graph anomalies (threshold J > 0.7).

### 5.4 On-Chain Anchoring and Independent Verification

All protocol artifacts are anchored on Base L2 using the format: `MolTrust/<event-type>/<version> SHA256:<64-char-hex-hash>`. TechSpec v0.8 is anchored at Block 44638521 (TX: 0x0b36c7718632fa71bff67e22fdd3615408243b3c178819a9f1e340d526378d65). KYA v3.1 is anchored at Block 44098421 (TX: 0x56d81e14...). Independent verification requires only a SHA-256 implementation and a public block explorer.

---

## 6. Discussion

### 6.1 Complementarity with AIP

This paper does not claim MolTrust supersedes or replaces the AIP formalization by Molinari et al. The two approaches address different aspects of the agent authorization problem. AIP provides formal constraint modeling through Biscuit/Datalog — a mathematically rigorous framework suitable for formal verification. MolTrust provides the operational layer: a live registry, behavioral trust history, sybil resistance, and on-chain permanence.

We believe both layers are necessary for a production agent economy and that the AIP formalization could serve as the theoretical foundation for a future MolTrust constraint model revision.

### 6.2 Limitations

The primary limitation relative to AIP is policy expressiveness (Section 3.3). A second limitation is the 2-month production history at time of writing — on-chain anchors with timestamps provide the primary evidence of operational continuity. A third limitation is the absence of a formal security proof for the trust scoring model; Section 4 of TechSpec v0.8 explicitly describes the scoring model as a heuristic.

---

## 7. Conclusion

MolTrust implements all five features the AIP paper by Molinari et al. identifies as jointly absent in prior protocols, as a production system operational since March 2026. We acknowledge the superiority of IBCTs in policy expressiveness and treat this as a roadmap item. The research formalization (AIP) and the production implementation (MolTrust) are complementary contributions to the agent authorization problem.

---

## References

- Molinari et al. (2026). *AIP: Agent Identity Protocol for Verifiable Delegation Across MCP and A2A.* arXiv:2603.24775 [cs.CR]. https://arxiv.org/abs/2603.24775
- IETF draft-prakash-aip-00. https://datatracker.ietf.org/doc/draft-prakash-aip/
- W3C DID Core v1.0. https://www.w3.org/TR/did-core/
- W3C VC Data Model 2.0. https://www.w3.org/TR/vc-data-model-2.0/
- W3C Bitstring Status List v1.0. https://www.w3.org/TR/vc-bitstring-status-list/
- RFC 8785 — JSON Canonicalization Scheme. https://www.rfc-editor.org/rfc/rfc8785
- RFC 9396 — Rich Authorization Requests. https://www.rfc-editor.org/rfc/rfc9396
- NIST SP 800-162 — Guide to ABAC. https://csrc.nist.gov/pubs/sp/800/162/final
- MolTrust TechSpec v0.8. https://moltrust.ch/techspec (Base L2 Block 44638521)
- MolTrust CONFORMANCE.md. https://github.com/MoltyCel/moltrust-api/blob/main/CONFORMANCE.md
- OpenClaw RFC #49971. https://github.com/openclaw/openclaw/issues/49971

---

*This document is released under CC BY 4.0. The MolTrust protocol is open (Apache 2.0). The reference implementation is operated by MolTrust / CryptoKRI GmbH, Zurich. Contact: info@moltrust.ch*
