# AAE Spec Facts — Verified Reference

**Source:** draft-kroehl-agentic-trust-aae-00, IETF Datatracker, uploaded 2026-05-21
**Verified:** 2026-06-20 (Console verification against live Datatracker fetch)
**SHA-256 of draft text:** `2847f4daf3f0a088afb1bd1bd3b9c001947a9905426753673d9da8275a038b0a`
(source: `https://www.ietf.org/archive/id/draft-kroehl-agentic-trust-aae-00.txt`, 48500 bytes)
**Status:** -00 public, -01 in preparation (Backlog: see MEMORY #24)

## Section Map

- §1 Introduction
- §2 The Agent Authorization Envelope
  - §2.1 Structure
  - §2.2 MANDATE
  - §2.3 CONSTRAINTS
  - §2.4 VALIDITY — `not_before` (REQUIRED), `not_after` (REQUIRED), `revocation_check` (OPTIONAL), `single_use` (OPTIONAL, Boolean, default false)
- §3 Delegation Chains (mechanics, structure, `delegator_aae_hash` — OPTIONAL)
- §4 Action Vocabulary Schemas
- §5 Verification Algorithm (9 steps; step 9 = delegation chain walk)
- §6 Security Considerations
  - §6.1 Replay Attacks
  - §6.2 Constraint Bypass
  - §6.3 Key Compromise
  - §6.4 Delegation Amplification
  - §6.5 Delegation Revocation (normative level: SHOULD; AAE-01 Backlog: SHOULD→MUST)
  - §6.6 Clock Skew and Time Synchronization
  - §6.7 On-Chain Anchoring
- §7 Privacy Considerations
- §8 IANA Considerations
- §9 References

## Hash Mechanics

AAE defines exactly ONE content hash: `delegator_aae_hash`

- **Location:** §3, OPTIONAL field
- **Form:** `sha-256:<base64url-digest>`
- **Input:** the exact ASCII octet sequence of the parent AAE JWS-compact-serialization as retrieved
- **Explicit exclusions (§3, lines 544–545):** no additional whitespace, no decode/re-encode, no JSON canonicalization
- **Algorithm:** SHA-256 per RFC 6234
- **Mismatch handling:** relying party MUST reject the delegated AAE

(Note: the JWS compact serialization itself — `BASE64URL(header).BASE64URL(payload).BASE64URL(signature)` — is the envelope encoding, not a separate content-hash definition.)

## NOT in AAE (common attribution errors)

- No `receipt_id`. That belongs to receipt-format specs, not AAE. *(Attribution to a specific spec such as an "APS ActionReceipt with sha256(jcs(payload))" is UNVERIFIED here — confirm against the APS spec / a future `aps.md` before citing it externally.)*
- No JCS canonicalization (RFC 8785) — explicitly excluded.
- No content-canonicalization of any kind.
- "Cycle detection" — NOT specified in the -00 draft (was incorrectly attributed in the cosai #99 comment 2026-06-20, corrected same day).

## Update Triggers

- AAE -01 revision release → update Section Map + Hash Mechanics.
- Any section renumbering or hash-algorithm change → immediate update + citation-rule reminder.
