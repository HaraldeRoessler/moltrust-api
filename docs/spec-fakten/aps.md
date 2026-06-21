# APS Spec Facts — Verified Reference

**Status: STUB — most facts UNVERIFIED, awaiting full spec verification**

**Source (existence-confirmed 2026-06-21; CONTENT not yet verified):**
- **Normative spec:** IETF Internet-Draft `draft-pidlisnyi-aps` — latest **rev -01**, title "Agent Passport System (APS): Cryptographic Identity, Faceted Authority" (datatracker.ietf.org doc page HTTP 200). Plus "eight APS papers" on Zenodo (per `aeoess/aps-conformance-suite` README, 2026-06-19) — Zenodo DOIs not yet collected.
- **Reference implementation:** `aeoess/agent-passport-system` (TypeScript, Apache-2.0).
- **Conformance corpus:** `aeoess/aps-conformance-suite` (JCS/RFC 8785 byte-vectors, InstructionProvenanceReceipt v0.2, AIVSS §3.6 scenarios). Self-described as "Not a normative spec."
- **Guessed repo names that DO NOT EXIST (404, not adopted):** `aeoess/aps-core`, `aeoess/aps-spec`, `aeoess/agent-protocol-spec`.

**Verification date:** Not yet performed (source identified, draft text not fetched/parsed)
**SHA-256 of spec text:** Not yet computed

## Pre-verification: facts from cosai #99 thread (UNVERIFIED)

These are statements made by @aeoess in the cosai #99 thread (2026-06-19, 2026-06-20). They are NOT verified against the APS spec text itself. Must be confirmed before any public citation:

- **ActionReceipt structure:** `receipt_id = sha256(jcs(payload))` — *partially corroborated:* `aps-conformance-suite` README confirms APS uses JCS canonicalization (RFC 8785); the exact `receipt_id` field/formula is still README/thread-level, not draft-verified.
- **scope_of_claim field:** carries `capture_mode` and `self_attested` flag.
- **delegation_chain_root:** sha256 of canonical delegation chain.
- **Time anchor support:** `transparency_log_inclusion` and `rfc3161_timestamp` as OPTIONAL fields (claimed by aeoess in cosai #99, 2026-06-19).

## Pre-verification: known structural elements (UNVERIFIED)

From cosai #99 + A2A #1716 cross-references — aeoess has APS sub-delegation with a numeric monotonicity check gated on spend-unit matching. Currency-change in sub-delegation is caught at the payment-rails preAuthorize boundary, NOT at the narrowing layer.

## What this stub does NOT yet contain

- Verified section numbers
- Verified hash algorithms beyond those stated above
- Verified field requirement levels (MUST/SHOULD/MAY)
- Verified terminology canonical to APS

## Workflow before first APS citation

1. Identify authoritative APS spec source — **partly done:** `draft-pidlisnyi-aps-01` confirmed to exist; still confirm it (vs. the Zenodo papers) is the citation-authoritative surface, ideally via aeoess's cross-spec PR to `aae-conformance-vectors`.
2. Fetch full text (`draft-pidlisnyi-aps-01`), compute sha256.
3. Replace this stub with verified Section Map + Hash Mechanics + Common Attribution Errors.
4. Update Memory #30 status if needed.

## Citation rule (active until full verification)

Until this file is replaced with verified content: **no APS section numbers in public comments.** Statements like "APS has X" or "APS handles Y" only based on direct paraphrase of aeoess' own thread comments (with cosai #99 / A2A #1716 cross-reference).
