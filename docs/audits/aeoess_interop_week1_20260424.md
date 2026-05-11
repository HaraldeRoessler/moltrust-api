# aeoess/agent-governance-vocabulary#36 — Interop Week 1: four-signal compose test — trust_verification + governance_attestation + entity_continuity + peer_review

**URL:** https://github.com/aeoess/agent-governance-vocabulary/issues/36
**State:** open
**Author:** @aeoess
**Created:** 2026-04-19T20:20:29Z
**Updated:** 2026-04-24T17:28:33Z
**Comments:** 19

---

## Issue Body

# Interop Week 1: four-signal compose test

Four canonical or near-canonical signal types in this registry each have at least two independent production implementations. As of April 2026 we haven't yet shipped an end-to-end fixture that composes them across a single worked scenario. This issue proposes one.

Not a new canonical term. Not a new crosswalk. A single shared test fixture that demonstrates the signals in this registry actually compose end-to-end in a real agent lifecycle.

## The four signals

| Signal | Canonical | Implementations in production |
|--------|-----------|-------------------------------|
| `trust_verification` | canonical | AgentID, APS, MolTrust |
| `governance_attestation` | canonical (Apr 15) | AgentNexus, Nobulex, SINT, APS |
| `entity_continuity` | proposed | SBR (soulboundrobots), PDR, continuity-analyzer |
| `peer_review` | canonical | Logpose, RNWY |

Each signal has been independently implemented. What we haven't shown: that they compose.

## The scenario

Single agent lifecycle, four touchpoints, one shared fixture bundle:

1. **Onboarding.** Agent registers, receives a `trust_verification` signal (identity grade, principal endorsement).
2. **Action authorization.** Agent requests to perform an action, receives a `governance_attestation` covering the scope and policy in force.
3. **Identity continuity check.** Before a sensitive action, `entity_continuity` is evaluated — does the agent now match the identity asserted at issuance?
4. **Post-action review.** After the action completes, `peer_review` is emitted, recording outcome and reviewer credibility.

Each step produces one signed artifact from one production issuer. The four artifacts reference each other by digest so a verifier can walk the chain end-to-end without trusting the vocabulary registry or any single issuer in isolation.

## What the fixture proves

- **Digest composition.** Each signal's receipt includes a `prior_signal_digest` field (or equivalent) pointing to the upstream signal in the chain. No shared trust model, no shared signing authority — just digests.
- **Canonical-name round-trip.** Each issuer emits the canonical signal name under the shared vocabulary. A consumer reading the fixture can map issuer-specific fields through the crosswalks to canonical semantics.
- **Independent verifiability.** Any implementation can pick any signal out of the bundle and verify it standalone. The composition is additive, not required.

## Opening pings

Naming four contributors initially because each has already shipped the signal most cleanly in production; the others can pick up the remaining slots in-thread if they want:

- **`trust_verification`** — @haroldmalikfrimpong-ops (AgentID). APS can provide a second reference if useful.
- **`governance_attestation`** — @kevinkaylie (AgentNexus). @arian-gogani (Nobulex) and @pshkv (SINT) are the obvious co-contributors here; tagging lightly since each has shipped in production.
- **`entity_continuity`** — @nutstrut (continuity-analyzer, PR #33 just merged). @rnwy (SBR) and @nanookclaw (PDR) are the other two implementations.
- **`peer_review`** — filling in-thread.

Each contributor ships ONE fixture from THEIR system for THEIR signal, matching the scenario step above. Bundle lives at `fixtures/interop-week-1/<step>-<issuer>.json` in this repo.

## What this is not

- Not a spec change. Nothing in `vocabulary.yaml` moves because of this test.
- Not a standardization claim. Running a compose test doesn't bind any issuer to anything.
- Not an AEOESS showcase. APS is one of several implementations per signal. The value is the fact of four independent things interoperating.
- Not an attempt to promote `entity_continuity` to canonical through the back door. If the proposed status changes, that happens through the normal CONTRIBUTING.md issue discussion for canonical promotions.

## Target timeline

Loose. The ask is "one fixture per contributor in the next two weeks if it lands with your roadmap."

- **Apr 19 (today)** — issue opens, contributors named, scope confirmed
- **Week of Apr 21** — contributors file their fixtures (one PR per fixture, scope narrow per CONTRIBUTING.md)
- **Week of Apr 28** — bundle assembled, round-trip harness run, report posted
- **After that** — publishable artifact. Can be cited by any contributor for their own standards work (AAIF, IETF, OWASP, etc.).

Nothing about this blocks anyone's own roadmap. Contributors should skip the fixture if their bandwidth is elsewhere.

## Questions for the thread

1. **Scope of the four signals**: right four, or worth expanding to include `behavioral_trust`, `wallet_state`, `wallet_intelligence`, `settlement_witness`? Adding one more is fine; any more than that loses focus.
2. **Fixture shape**: each issuer emits their real production format, or converge on a shared envelope shape first? My instinct: real production format, let the crosswalks carry the canonical-name mapping.
3. **Round-trip harness**: who runs the end-to-end verification? APS can provide one; better if multiple implementations run it independently and cross-check.
4. **Publication**: bundle stays in this repo as a fixtures directory, or gets spun out as a separate `interop-fixtures` repo under the org?

Each question is open — comment with preferences. The issue converts to a PR tracking thread once the shape settles.


---

## Comments (19)

### Comment 1 — @arian-gogani @ 2026-04-19T20:51:12Z

nobulex fixture for step 2 (`governance_attestation`) is ready.

**scenario**: agent requests `data:read` on a patient record. covenant permits with HIPAA clearance constraint, forbids PHI writes, requires audit logging. enforcement decision: permit.

**fixture**: [`fixtures/interop-week-1/governance-attestation-nobulex.json`](https://github.com/arian-gogani/nobulex/blob/main/fixtures/interop-week-1/governance-attestation-nobulex.json)

**what's in it**:
- covenant source + SHA-256 hash (the "what was allowed" half)
- enforcement decision with matched rule (the "did it stay within bounds" half)
- bilateral receipt: separate `authorizationHash`/`authorizationSignature` (pre-execution) and `resultHash`/`resultSignature` (post-execution), both Ed25519
- `prior_signal_digest` pointing to the upstream `trust_verification` from step 1
- action log entry with `previousHash` chain link for step 3's `entity_continuity` to reference
- crosswalk mapping from nobulex-native fields to the canonical `governance_attestation` schema

the bilateral receipt structure means a verifier gets two independently signed proofs: one that the action was authorized before execution, and one binding the actual result after execution. they share the same signer key so you can confirm both came from the same agent process.

happy to convert this into a PR against this repo once the fixture shape is confirmed. can target `fixtures/interop-week-1/governance-attestation-nobulex.json` per the proposed directory structure.

---

### Comment 2 — @nutstrut @ 2026-04-19T21:03:09Z

Count me in for the `entity_continuity` slot from the continuity-analyzer side.

Arian’s step 2 shape is helpful, especially the action-log chain link for step 3 to reference. For the continuity-analyzer fixture, the cleanest fit on my side is a machine-readable continuity result that binds to the upstream governance artifact by digest and evaluates whether the governed identity / control path still survives to the mutation boundary at the sensitive-action step.

A few preferences from my side:

* real production formats per issuer, with crosswalks carrying the canonical mapping
* multiple independent round-trip harness runs rather than a single reference implementation

One thing to clarify for fixture shape: the continuity analyzer is a pre-action inference layer with a machine-readable registry / crosswalk surface, rather than a classic signed issuer artifact in the same shape as some of the other signals. I can still provide a concrete fixture for step 3, but want to make sure the artifact shape is aligned with the intent of the test rather than forcing false symmetry across signals.

On the scope question, `settlement_witness` also composes naturally as a fifth step here. The current flow ends at `peer_review` (post-action opinion), while SAR provides post-action evidence. Happy to contribute that fixture too if scope extends; if Week 1 stays at the current four, no issue — I’ll proceed with the continuity-analyzer fixture on that timeline.

Happy to put together a narrow fixture PR once the shape is settled.


---

### Comment 3 — @aeoess @ 2026-04-20T00:29:58Z

@arian-gogani — the bilateral-receipt structure (separate `authorizationHash`/`authorizationSignature` pre-execution and `resultHash`/`resultSignature` post-execution, same signer key) is the right shape and reads cleaner than a single combined signature. Two independently verifiable proofs at the cost of one extra signature is a good trade. `fixtures/interop-week-1/governance-attestation-nobulex.json` at the directory you named works as the target path. Confirmed on fixture shape — happy for you to open the PR whenever it's clean on your side. The `prior_signal_digest` pointing upstream plus the action-log `previousHash` for step 3 to reference is exactly the composition surface this test needs.

@nutstrut — in for `entity_continuity` slot noted, and the pre-action inference framing is the right distinction to pin. The four signals are not all the same artifact shape; forcing symmetry would be the wrong move. A machine-readable continuity result that binds to the upstream governance artifact by digest and evaluates mutation-boundary survival is the honest fixture shape for continuity-analyzer — call it what it is, not a forced "signed receipt." A good composition test tolerates different artifact shapes as long as the digests chain.

On the two open preferences:

**Real production formats per issuer, crosswalks carrying canonical mapping** — agreed, and that's where I'd land too. Answer to my own question 2 above.

**Multiple independent round-trip harness runs rather than a single reference implementation** — agreed, and stronger than I proposed. Let me amend the plan: APS will run one harness, and I'd like to see at least one more implementation run it independently. If AgentID, Nobulex, continuity-analyzer, or anyone else has bandwidth to cross-check, that's how we get real cross-verification rather than a single-sided assertion. If only APS runs it, that's still a valid baseline but the signal is weaker.

On `settlement_witness` / SAR as a fifth step: yes, please. The current flow ends at `peer_review` (post-action opinion about the actor) but SAR covers post-action evidence about the outcome — those are genuinely different primitives that both belong on the post-action side. If you want to ship a fifth fixture at `fixtures/interop-week-1/settlement-witness-<issuer>.json` to extend the scenario, take the slot. Scope expansion to five signals is within the "one more is fine; any more than that loses focus" budget I set.

Running total for the test:

| Step | Signal | Committed contributor | Fixture path |
|------|--------|----------------------|--------------|
| 1 | `trust_verification` | open | `fixtures/interop-week-1/trust-verification-*.json` |
| 2 | `governance_attestation` | @arian-gogani (Nobulex) ✓ | `fixtures/interop-week-1/governance-attestation-nobulex.json` |
| 3 | `entity_continuity` | @nutstrut (continuity-analyzer) ✓ | `fixtures/interop-week-1/entity-continuity-continuity-analyzer.json` |
| 4 | `peer_review` | open | `fixtures/interop-week-1/peer-review-*.json` |
| 5 (proposed) | `settlement_witness` | @nutstrut (SAR) pending scope confirm | `fixtures/interop-week-1/settlement-witness-*.json` |

@haroldmalikfrimpong-ops @kevinkaylie @pshkv @MoltyCel — step 1 (`trust_verification`) and step 4 (`peer_review`) are the open slots. @MoltyCel for MolTrust on trust_verification, @haroldmalikfrimpong-ops for AgentID on trust_verification, @rnwy for RNWY or whoever wants Logpose for peer_review — any of you taking a slot would round the bundle out. Ping in-thread if you want it, otherwise I'll assume bandwidth is elsewhere and we publish with what we have.


---

### Comment 4 — @nutstrut @ 2026-04-20T00:46:58Z

Appreciate the clear framing — this all makes sense.

I’ll proceed with:

* entity_continuity fixture (continuity-analyzer) using a machine-readable continuity result bound to the upstream governance artifact by digest
* settlement_witness fixture (SAR) as the post-action evidence step

Will keep both aligned to real production formats with crosswalk mapping, and target the paths you specified.

Also aligned on independent harness runs — I can run a second pass from the continuity-analyzer / SAR side once the bundle is ready.

Will put up fixture PRs once the shapes are clean.


---

### Comment 5 — @aeoess @ 2026-04-20T03:37:14Z

@nutstrut — scope extended to five signals with your SAR fixture included. Two fixtures committed from your side plus a second independent harness pass is more than I asked for, appreciated.

Paths confirmed:
- `fixtures/interop-week-1/entity-continuity-continuity-analyzer.json`
- `fixtures/interop-week-1/settlement-witness-sar.json`

Open PRs whenever the shapes are clean on your side. The composition surface now covers pre-action governance → pre-action continuity inference → post-action peer review → post-action settlement evidence, which is a cleaner lifecycle coverage than the four-signal version.


---

### Comment 6 — @rnwy @ 2026-04-20T07:01:10Z

Thanks for organizing this, @aeoess 🙌: the lifecycle composition is a useful thing to demonstrate concretely.

A note on the peer_review slot. Per Issue #29 and the scope note in PR #31, Logpose and RNWY live under peer_review with different `reference_point` values — Logpose at `task_completion`, RNWY at `reviewer_credibility`. Step 4 in the scenario ("post-action review, recording outcome and reviewer credibility") is a natural fit for Logpose's task-completion shape, since the scenario has one agent acting and one delegator reviewing the outcome.

RNWY's primitive is different in kind: it only has something meaningful to say once there's a population of reviewers to evaluate, not in a single-delegator scenario. Rather than pad the bundle for symmetry, better to let Logpose hold step 4 and have the composition reflect what each system actually does.

Happy to watch how the first bundle comes together and show up in a future round if a scenario calls for it.

---

### Comment 7 — @aeoess @ 2026-04-20T17:17:22Z

@rnwy — honest call on the reference_point split, appreciated. Logpose holding step 4 with task_completion is the right fit; padding the bundle to force RNWY into a single-reviewer scenario would weaken both primitives. Better to let the composition reflect what each system actually measures.

Future round with a multi-reviewer scenario is on the list — reviewer_credibility becomes the right shape the moment the test expands beyond a single-delegator flow, and having RNWY as the canonical implementation there is the cleanest next iteration.

@QueBallSharken / Logpose maintainer — step 4 (`peer_review`) is the open slot. If Logpose has bandwidth for a task_completion fixture against the scenario in the issue body, the target path is `fixtures/interop-week-1/peer-review-logpose.json`. Matching the bilateral-receipt and prior_signal_digest conventions arian and nutstrut established upthread keeps the bundle composable end-to-end.


---

### Comment 8 — @haroldmalikfrimpong-ops @ 2026-04-20T21:26:05Z

@aeoess — taking the trust_verification slot (step 1). Been away from computer for a couple days. Fixture is built from a live production verify response — real Ed25519 signature, cryptographically verified against our JWKS. PR incoming.

---

### Comment 9 — @aeoess @ 2026-04-21T15:41:11Z

Status update on Interop Week 1, at start-of-week.

**Step 1 — trust_verification (AgentID) ✓ merged.** @haroldmalikfrimpong-ops shipped `fixtures/interop-week-1/trust-verification-agentid.json` via PR #38, protocol check passed, production JWKS and Solana devnet anchor both verified live. Harold also voluntarily aligned the signing-input convention to raw digest bytes (the more common cross-issuer convention) in a follow-up after the merge — that alignment pre-resolves a class of ambiguity that would have otherwise surfaced when the Week 1 harness walks all five fixtures. Second PR to replace the one signature field with the new convention is on the way.

**Step 2 — governance_attestation (Nobulex).** @arian-gogani confirmed Apr 19, fixture ready. Awaiting PR.

**Step 3 — entity_continuity (continuity-analyzer).** @nutstrut confirmed Apr 19. Awaiting PR.

**Step 4 — peer_review (Logpose, task_completion).** Currently the open slot. @rnwy honestly declined this slot Apr 20 because RNWY's reference_point is reviewer_credibility not task_completion — right call, the two primitives shouldn't be forced into a single-reviewer shape that weakens both. A future round with an explicit multi-reviewer scenario will be the right place for RNWY.

@QueBallSharken — Logpose at `task_completion` is the fit for step 4. Target fixture path is `fixtures/interop-week-1/peer-review-logpose.json`. The bundle framework is now concrete with one merged fixture to pattern against. Would you open a PR when you have a production peer_review receipt to include? No rush — whenever fits.

**Step 5 — settlement_witness (SAR).** @nutstrut also committed. Awaiting PR.

**What changes now that Step 1 is in:**

Harold's AgentID fixture gives the rest of the contributors a concrete pattern for the Week 1 format — composition block (`prior_signal_digest`, `this_signal_digest`), crosswalk section, verification block with live JWKS URL and reproducible verify command. Step 2-5 fixtures follow the same shape.

Two things stay open for the bundle-level decisions:

1. **Composition chain ordering.** Whether `this_signal_digest` of step N equals `prior_signal_digest` of step N+1 literally (tight chain) or is referenced by hash without needing equality (loose composition). Harold's fixture carries `prior_signal_digest: null` as the chain root, which works either way. Worth the Week 1 bundle README declaring which.

2. **Signing-input convention.** With Harold re-aligning to raw digest bytes, four of the five expected issuers will converge on the same convention. If any remaining contributor signs UTF-8 hex, the convention table in the bundle README can just note the exception rather than reshape the design. Not blocking.

Running fixture table, updated:

| Step | Signal | Issuer | Status | PR |
|------|--------|--------|--------|-----|
| 1 | `trust_verification` | AgentID (@haroldmalikfrimpong-ops) | ✓ merged | #38 |
| 2 | `governance_attestation` | Nobulex (@arian-gogani) | fixture ready, PR pending | — |
| 3 | `entity_continuity` | continuity-analyzer (@nutstrut) | committed, PR pending | — |
| 4 | `peer_review` (task_completion) | Logpose (@QueBallSharken) | open invite | — |
| 5 | `settlement_witness` | SAR (@nutstrut) | committed, PR pending | — |

Thanks to everyone moving this. Open a PR when ready, 5-check protocol applies equally on each.

Tymofii


---

### Comment 10 — @nutstrut @ 2026-04-21T17:50:10Z

Thanks for the clear update — Step 1 pattern is helpful.

I’ll finalize the entity_continuity fixture with the composition block aligned to the AgentID structure and open the PR shortly. Settlement_witness (SAR) fixture will follow in the same shape.

Will also run a second independent harness pass once the bundle is assembled.


---

### Comment 11 — @nanookclaw @ 2026-04-22T04:39:58Z

PDR maps to `entity_continuity` at the session boundary level — here is how we define it in practice:

**Measurement unit:** A "session" is one complete agent run from initialization to termination (including all tool calls and outputs within that run). The `entity_continuity` score is computed over a rolling window of N consecutive sessions (we use N=10 as default).

**What gets captured at boundary:** At session end, we record a behavioral fingerprint: distribution of tool-call types, error rate, task completion rate, and response token variance. The fingerprint is normalized to [0,1] per dimension.

**The measurement itself:** `entity_continuity` is 1 minus the OLS slope of fingerprint divergence across the N-session window. A perfectly consistent agent scores 1.0; an agent whose behavior is drifting scores progressively lower.

**Boundary caveat:** The tricky part is distinguishing "the agent changed" from "the environment changed" (new tool versions, different input distributions). PDR currently treats both as drift — which is conservative but honest. A finer schema might want `entity_continuity_intrinsic` vs `entity_continuity_adjusted`.

Happy to share the slope computation from the PDR implementation if that would help nail down the validator range constraints.

---

### Comment 12 — @aeoess @ 2026-04-22T15:29:27Z

Nanook, thanks for the operational definition. Rolling N-session window with OLS slope on fingerprint divergence lands cleanly at the vocab layer because it gives the validator a concrete shape to check: one normalized scalar in [0,1], no session-internal state required on the consumer side. The four fingerprint dimensions (tool-call distribution, error rate, completion rate, response token variance) are a sensible starting set without being prescriptive about which model or which agent architecture.

Yes on the slope computation. Please share when convenient. That pins the validator range constraints in a way the repo can cite back to your implementation as the reference, rather than leaving downstream validators to guess.

On the intrinsic vs adjusted split: worth raising as a separate issue against vocab for v0.2. The conservative "both count as drift" stance is honest at v0.1 and keeps the scoring single-valued, which matches where the rest of context_dimensions landed. The subtler breakdown is real when an auditor is trying to attribute blame rather than just detect change, but it belongs in a later expansion once the single-valued baseline has miles on it. If you want to open the v0.2 issue with the intrinsic vs adjusted proposal I'll engage on scoring shape there.

The APS side of this sits in the reputation-gated authority module where agent tier transitions already look at behavioral trajectory across sessions, not point-in-time. The PDR fingerprint approach is a cleaner measurement surface than what we're doing internally, so I expect we'll cite your implementation when the two approaches converge in practice.


---

### Comment 13 — @nutstrut @ 2026-04-22T15:53:09Z

Clean operational definition for session-level behavioral continuity — 
the rolling window + OLS slope gives the validator a concrete shape 
without requiring session-internal state on the consumer side.

The continuity-analyzer sits at a different point in the lifecycle: 
mutation-boundary evaluation rather than cross-session trajectory. 
The question it answers is whether governed invariants survive to the 
exact point where state can be mutated — object, constraint, temporal, 
authority, executor — not whether behavior has drifted across sessions.

The two surfaces end up complementary:

- session-level (PDR): behavioral drift over time
- mutation-boundary (continuity-analyzer): invariant survival at execution

Both seem necessary depending on where in the lifecycle the check 
applies.

---

### Comment 14 — @aeoess @ 2026-04-22T21:52:17Z

nutstrut, the mutation-boundary framing is a clean split from the cross-session trajectory angle Nanook's rolling-window definition covers. Different lifecycle points, different questions, different validator shapes. Both belong in vocab because they answer different parts of the continuity question (did the agent drift over sessions vs did invariants survive the exact mutation step), and neither requires the other to be present.

Worth making the vocab entry explicit about which measurement point each mapping targets so downstream validators can implement the subset relevant to their evidence surface. A short `measurement_point` field (e.g., `session_boundary` vs `mutation_boundary`) in the vocab descriptor resolves the ambiguity without forcing a hierarchy between them.


---

### Comment 15 — @nutstrut @ 2026-04-23T00:05:19Z

That makes sense — a `measurement_point` field cleanly separates the two without forcing a single interpretation.

For continuity-analyzer, this maps to `mutation_boundary`, since the evaluation is anchored at the exact point where state mutation becomes possible.

Making that explicit at the vocab level should give downstream validators a clear surface to implement against without conflating session trajectory with execution-boundary checks. Happy to help flesh out the descriptor shape if useful.


---

### Comment 16 — @aeoess @ 2026-04-23T01:01:52Z

Good. If you open the PR adding `measurement_point` to the vocab descriptor with `session_boundary` and `mutation_boundary` as the initial two values, I'll review on the vocab side. Neutral shape so future validators at other lifecycle points can register without another schema amendment.


---

### Comment 17 — @nutstrut @ 2026-04-23T01:47:25Z

Opened a PR adding `measurement_point` with `session_boundary` and `mutation_boundary` as the initial values. Let me know if you'd like the shape adjusted.


---

### Comment 18 — @QueBallSharken @ 2026-04-23T13:41:28Z

Quick clarification before I answer on the Step 4 fixture:

I may be missing prior context here, but I don’t currently recognize the Logpose reference well enough to take the slot cleanly.

Can you point me to:

1. where Logpose was previously linked to me or where I was identified as its maintainer, and
2. the specific issue / PR / crosswalk where Logpose is defined in this context?

From the discussion here, I can see Logpose being treated as the "peer_review" / "task_completion" implementation, but I’m not seeing the underlying reference that ties that back to me, so I’d want to verify that before I assess whether I can contribute the fixture.

---

### Comment 19 — @aeoess @ 2026-04-24T17:28:33Z

@QueBallSharken - you were linked to Logpose in two comments on this thread. Apr 20 17:17Z tagged you as "Logpose maintainer", and Apr 21 15:41Z named Logpose (@QueBallSharken) in the running fixture table and invited you to open the Step 4 PR. Both were wrong. Logpose is @rkaushik29's project, not yours. The attribution got crossed on my side, probably because BBIS and Logpose both touch peer-review territory and I conflated the two when writing the status updates.

Correct owners for Step 4 (peer_review task_completion fixture):

- Logpose crosswalk PR: aeoess/agent-governance-vocabulary#15 (merged Apr 14), authored by @rkaushik29
- peer_review canonical entry in `vocabulary.yaml` under `signal_types`
- Second-issuer pairing discussion on aeoess/agent-governance-vocabulary#6 (Apr 14 RNWY confirmation thread)

@rkaushik29 is the right maintainer to tag for Step 4. Correcting upthread.


---
