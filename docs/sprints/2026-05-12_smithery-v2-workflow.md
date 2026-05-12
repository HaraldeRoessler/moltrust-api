# Smithery V2 Re-Deploy — Preparation Workflow (V2.1)

**Status:** Preparation, GPT-5-reviewed, all Lars-decisions incorporated. Ready as reference for Re-Deploy V2 sprint. No deployment yet.
**Owner:** Lars (decisions) + Claude Code (execution when go-live)
**Last updated:** 2026-05-12 (V2.1 — supersedes V2 + V1)
**Linked:** Auto-Probe-Token Spec (`docs/auto-probe-token-spec.md`), GPT-5 D3 Architecture (audits/2026-05-12_gpt5-verification-bundle.md), GPT-5 Workflow Review (this revision)

---

## 1. What we're solving

After the Auto-Probe-Sprint rollback (Memory: "Auto-Probe-Drama 12.05.26"), the Smithery listing `@moltrust/moltrust-mcp-server` is back to Pre-Sprint state — 39 tools, Quality Score 82, weekly tool-call traffic ~22, **zero signup conversions to date**. The listing description still says *"Without it your agent is anonymous and read-only. Mint: POST api.moltrust.ch/auth/signup"* — directing users to a form that has converted nobody.

The V2 of Auto-Probe-Token will be deployed in a separate sprint with opt-in sub-app mount architecture (per GPT-5 D3). This document covers the **Smithery-side preparation and post-deploy steps** for V2 go-live: description templates, schema updates, manual UI sequence on Smithery, conversion measurement, alerting, decision points.

**No code changes in this document.** Code changes are in the Re-Deploy V2 sprint plan (to be written separately).

## 2. Goals — reordered after GPT-5 review

**Goal B — Smithery-Quality-Score progression (PRIMARY).** Current 82/100. Target 90+. Quality Score directly drives discovery volume on Smithery. Optimizing conversion without sufficient discovery is noise. Levers: schema clarity, free-tier badge, active tool-call traffic, tooling completeness.

**Goal A — Zero-friction first-value path.** Lower-friction onboarding moves users from "Smithery listing seen" to "first tool successfully executed." Target: ≥30 Smithery-attributed probes with ≥3 distinct tool calls within 30 days. Frame this as discovery-to-engagement, not signup-to-conversion.

**Goal C — Attribution functional and verified (GATING CHECKLIST).** Not an outcome goal. A hard prerequisite for measuring A and B. Smithery-source attribution must produce <5% false-positives and <5% false-negatives. If C is broken, A/B metrics are meaningless. Treat as deploy-blocker.

Underlying first-principle: **remove friction from discovery to first value.** The 30-tools-without-signup mechanic is the implementation of this principle.

## 3. What we don't do here

- Re-Implement Auto-Probe V2 code — separate sprint
- Modify `services/mcp_http.py` or `app/main.py` — handled in Re-Deploy V2
- Change the Smithery listing today — only on V2 go-live
- Migrate existing api_keys — they continue to work; auto-probe is additive

## 4. Pre-V2-Deploy verification

### 4.1 Header inventory from Smithery traffic (CRITICAL — wrong method in V1)

We need to know what Smithery's gateway actually sends. **GPT-5 corrected V1's tcpdump suggestion: TLS-terminated traffic cannot be sniffed.** Use app-level Header-Capture-Middleware instead.

**Approach: Starlette middleware on test-server.** Spawn V2 stack locally on Cloudflare-tunnel, point Smithery's test-connection at it. Middleware logs Smithery-source headers in structured format:

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SmitheryHeaderDump(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ua = request.headers.get("user-agent", "").lower()
        origin = request.headers.get("origin", "").lower()
        if "smithery" in ua or "run.tools" in ua or origin.endswith(".smithery.ai"):
            logger.info("smithery_headers", extra={
                "ua": request.headers.get("user-agent"),
                "origin": request.headers.get("origin"),
                "session_id": request.headers.get("mcp-session-id"),
                "xff": request.headers.get("x-forwarded-for"),
                "real_ip": request.headers.get("x-real-ip"),
                "all_headers": dict(request.headers),  # for unknown-headers discovery
            })
        return await call_next(request)
```

**Critical:** This middleware runs ONLY in V2-pre-deploy verification environment. **Removed before production deploy or guarded via feature flag.** Logs go to a dedicated `smithery_headers.log` file (NOT the regular log stream — keeps probe_keys, api_keys, and personal data off the conversion-funnel-logging surface).

Required headers to identify:
- `User-Agent` — stable Smithery UA pattern? Or client-pass-through?
- `Mcp-Session-Id` — Smithery's pattern (we suspect prefix-stable; verify)
- `X-Forwarded-For` and `X-Real-IP` — Smithery-Gateway IP visible?
- `Origin` — set by Smithery web-UI initiator?
- Custom Smithery headers — any `X-Smithery-*`?

Also test both Smithery code-paths:
- **Test connection** feature (Smithery's internal QA tool — may use different gateway behavior)
- **Production gateway** via real public URL `smithery.ai/server/@moltrust/...` "Open in MCP Inspector"

Save findings as `audits/2026-05-13_smithery-header-inventory.md` (date approximate, before V2-deploy decision).

### 4.2 Composite-Token Identifier strategy

Per GPT-5 D3 Punkt 4 + GPT-5 Review D5: tighten attribution. Three possible compositions, decided after 4.1:

| Composite | When viable | Trade-off |
|---|---|---|
| **A: Mcp-Session-Id only** | Smithery sends stable session ID per distinct user | Strongest identification; fails if multiple users share one session |
| **B: Mcp-Session-Id + IP /24** | Always | Conservative; partial Shared-NAT mitigation |
| **C: Origin + Mcp-Session-Id + Session-Pattern-Check** | Smithery sends Origin or session-format matches a recognizable pattern | Most robust against false positives |

Default recommendation pending 4.1 findings: **C — strictly conjunct check (multiple signals required).** Attribution code shape:

```python
def attribute_source(request) -> str:
    origin = request.headers.get("Origin", "")
    sess = request.headers.get("Mcp-Session-Id", "")
    xff = request.headers.get("X-Forwarded-For", "")
    if origin.endswith(".smithery.ai") and sess and session_matches_smithery_pattern(sess):
        return "smithery"
    if sess and session_matches_smithery_pattern(sess) and ip_in_smithery_range(xff):
        return "smithery"
    if request.headers.get("X-API-Key"):
        return "direct"
    return "anonymous"
```

`session_matches_smithery_pattern()` and `ip_in_smithery_range()` are derived from 4.1 findings. If Smithery's signals are too weak, fall back to conservative `anonymous` rather than misattribute.

### 4.3 Bypass-Mechanism for known callers

Cron jobs, the published `@moltrust/agent-firewall` library (CAEP polls), and admin dashboards should NEVER go through the auto-probe spawn path. Already handled by Auto-Probe-Spec section 4.2 (X-API-Key → claimed identity path bypasses mint). Verify:

- Smithery itself doesn't accidentally bypass via setting an X-API-Key header
- Smithery's test-connection request pattern doesn't trigger spawn-rate-limit on first connection

## 5. Smithery-side preparation

### 5.1 Description templates (English, no locale variants)

GPT-5 Review D4: drop EN+DE locale question — Smithery does not support locales.

**Tagline (Server Card on /servers list, ~80 chars):**
```
Trust registry for autonomous AI agents — try free, no signup.
```

Alternatives for sequential A/B-testing later (not simultaneous — Smithery doesn't support simultaneous A/B):
- `Agent identity & trust scores. Connect with no key, try every tool.` (79 chars)
- `Decentralized AI agent identity. Auto-probe — no signup required.` (66 chars)
- `Trust scores, agent identity, CAEP events. Free tier auto-minted.` (66 chars)

**Description (Server detail page, ~300-character field):**
```
MolTrust is a trust registry for autonomous AI agents on Base L2. Every tool works in a free probe mode — connect without an API key, get a probe DID auto-minted instantly (24h TTL, 50 calls). Try CAEP events, signed trust scores, verifiable credentials, and 40 tools across 7 verticals. Existing api_key users are unaffected.
```

(Last sentence per GPT-5 Review D5: tell existing users they're not impacted.)

**Tool Description for `moltrust_identity`:**
```
Returns your current agent identity (probe DID + key) and claim instructions. Call this first to see what you're working with.
```

### 5.2 Quick-Setup Schema update — concrete probe limits documented

Per Lars's decision: keep limits concrete in public schema, accept Smithery-cache-cycle cost on any future change.

```yaml
api_key:
  type: string
  description: |
    Optional. Without an api_key, MolTrust auto-mints a probe DID for your 
    session (24h TTL, 50 tool calls). Existing api_key users are unaffected.
    To make your probe permanent, call moltrust_identity to get your probe_key,
    then POST /auth/claim {probe_key, email} to claim. With an api_key (mt_*), 
    you get a permanent agent identity.
  required: false
```

### 5.3 Post-Deploy Smithery actions — schema first, marketing later

GPT-5 Review D3: reorder. Per Lars-stated principle of avoiding Smithery-cache + Display-Drift, schema verification before description changes.

Each step has rollback-snapshot before destructive operation. Each step independently reversible.

1. **Pre-step: snapshot current state.** Export Smithery config JSON if API exists, otherwise copy/paste current Tagline + Description + api_key schema text to `audits/2026-XX-XX_smithery-pre-v2-snapshot.md`. Required for rollback.

2. **Update api_key field description in schema.** Schema is authoritative for what Smithery shows in their UI. Schema change requires re-publish (manually or via CI).

3. **Trigger "Re-scan tools" + verify.** GPT-5 Review D3: no 5-min wait. Trigger immediately on Smithery server-detail-page. Verify `Last scanned at` updates within 60s. If no change in 60s: trigger again. If second attempt fails: contact Smithery support, don't proceed.

4. **Verify tool count change visible: 39 → 40.** `moltrust_identity` must appear in Smithery's tool list. If missing: schema rendering issue, do not proceed.

5. **Test connection from clean session.** Smithery has "Test Server" feature. Use incognito + new Smithery workspace context (avoid auth-cached state). Verify: connection succeeds, `tools/list` returns 40, `moltrust_identity` call without api_key returns probe DID + claim instructions in response body.

6. **Smoke-test public URL via real gateway.** Click "Try it" or "Open in MCP Inspector" on `smithery.ai/server/@moltrust/moltrust-mcp-server`. This is the proper Shared-NAT test path (different from test-connect feature). Confirm same behavior.

7. **Verify conversion attribution writes correctly.**
   ```sql
   SELECT source, event, count(*) 
   FROM conversion_funnel 
   WHERE created_at > NOW() - INTERVAL '1 hour' 
   GROUP BY 1, 2;
   ```
   Expected: `smithery` rows present from steps 5-6 above. If `anonymous` instead: attribution logic mis-fires, fix before continuing.

8. **Verify rate-limit behavior in tight loop.** From single Smithery-attributed source, fire 6+ probes-fresh requests within 1 minute. Expected: 5 succeed (probes minted), 6th returns 429 with claim_url in body. Verify only 5 rows appear in `probe_agents` for the test IP. If 6+ rows: spawn-rate-gate not enforcing, fix before continuing.

9. **Update Tagline + Description.** Now safe — schema + attribution + rate-limits are validated. Paste Tagline into Settings → General → Display Name area. Paste Description into Description field.

10. **Verify Quality Score.** Expected: still 82+, ideally bumped if Smithery rewards "free tier available" with a badge.

11. **Final check: listing-page CTAs.** Reload `smithery.ai/server/@moltrust/moltrust-mcp-server` from clean browser. Verify rendered description matches submitted, tool list shows 40 with `moltrust_identity` discoverable.

### 5.4 Things we deliberately do NOT change

- The api_key configuration field itself — keep as optional string, secret-masked. Description change only.
- Default scope or visibility settings.
- MCP Server URL `https://api.moltrust.ch/mcp` — Re-Deploy V2 routes /mcp back to :8000 via correct opt-in mount.
- Display name `MolTrust`.

### 5.5 Pre-Deploy Hygiene Fix (independent of V2 timing)

Smithery Homepage URL currently `https://smithery.ai` due to old typo. Should be `https://moltrust.ch`. **Fix today, 30 seconds**, decoupled from V2 deploy.

## 6. Soft-Launch Protection — Alerting Thresholds (Lars-decided)

Per Lars: full Caps from Day 1 (no Soft-Launch ramp), but alerting on abuse-patterns. Three threshold tiers:

**Tier 1 — Composite-Token bucket:**
- `>5 probe_mints/min per composite_token` → auto-block the composite-token-bucket for 5 minutes + Signal alert to Lars

**Tier 2 — Global mint rate:**
- `>50 probe_mints/min globally` → Signal alert to Lars (no auto-block, observation-mode)

**Tier 3 — Sustained sybil-farm pattern:**
- `>500 probe_agents created per hour globally` → temporary rate-limit reduction from 5/h per composite-token to 2/h per composite-token (auto-trigger), revert when rate normalizes for 3 consecutive 10-min windows

Implementation in V2 sprint, but values fixed here as product decision.

Alert delivery: Telegram bot (existing) or Signal-via-bridge. Format:
```
🚨 Probe-Sybil-Alert
Tier: {1|2|3}
Window: {timestamp}
Composite-Token: {token_hash_first_8} (if Tier 1)
Mints/min: {count}
Auto-action: {none|composite-block|tier3-rate-reduction}
```

## 7. Conversion measurement and reporting

`conversion_funnel` table already exists (created in Auto-Probe-V1 migration, harmless after rollback). Source attribution via 4.2 logic.

**GPT-5 Review D5 improvement: track distinct tools used and categories, not just call count.** Harder to game, better signal of perceived value:

```sql
-- engagement-depth metric, not just call count
SELECT 
  probe_did,
  count(distinct tool_name) AS distinct_tools,
  count(distinct split_part(tool_name, '_', 1)) AS distinct_vertical_prefixes,
  count(*) AS total_calls
FROM probe_activity
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY probe_did
HAVING count(distinct tool_name) >= 3;
```

DB indices for efficient reporting (GPT-5 Review D5):
```sql
CREATE INDEX IF NOT EXISTS idx_conv_source_time 
  ON conversion_funnel(source, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_event_time 
  ON conversion_funnel(event, created_at DESC);
```

### Reporting cadence — Day-1/D3/D7/D30 checkpoints

GPT-5 Review D5: 30-day window too coarse. Early-signal layers:

| Checkpoint | Action |
|---|---|
| **Day 1 (24h post-deploy)** | Sanity: probes minted, no abuse-tier alerts, attribution-rate looks normal (>50% of Smithery-sourced traffic correctly attributed). Auto-mail to Lars. |
| **Day 3 (72h)** | First trend signal: ≥5 probes with ≥3 distinct tools? If not, early warning — investigate before week ends. Auto-mail. |
| **Day 7** | Baseline established. Daily-rate stable. If ≥10 probes with ≥3 distinct tools: on track. If <5: trigger root-cause analysis (description, Smithery placement, Discovery surface). |
| **Day 30** | Final report against floor + stretch targets. Decide: ship to vertical landings, iterate description, or reconsider hypothesis. |

Implementation: cron + python script reading `conversion_funnel` and `probe_activity`, sending markdown report to Lars via Signal/email. Skeleton ready before V2-deploy.

## 8. Risks — expanded per GPT-5 Review

Per GPT-5 Review D2: 13 risks identified, ranked by severity.

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | Smithery listing deprecation/gateway change mid-window | Medium | Monitor Smithery release notes weekly. Have V1-state (39 tools) as rollback target |
| 2 | Upstream auth/rate-limit conflicts (OAuth or stricter 429) | Medium | Smithery support contact prepared. Verify in 4.1 if Smithery's gateway adds rate-limit headers |
| 3 | Probe DID auto-mint DB load spike (Smithery promotion) | **High** | Tier 2 alert at 50 mints/min. Tier 3 auto-reduction at 500/h. DB connection-pool sized headroom |
| 4 | Smithery caching/CDN hides schema/description changes | Medium | Re-scan + 60s verification step. If still stale: contact Smithery |
| 5 | A/B on Smithery not supported (sequential only) | Low-Medium | 5.1 alternatives are sequential variants, not simultaneous. 7-day baseline before swap |
| 6 | Source attribution false positives (substring too weak) | Medium | Conjunct check in 4.2 (multiple signals required). Conservative-fallback to `anonymous` |
| 7 | Security/logging leak of probe_key | **High** | Probe-keys never logged in conversion_funnel. Header-dump-middleware logs to dedicated file, removed before prod |
| 8 | Compliance/consent for auto-minted identities (DSAR, privacy policy) | Medium | Update `moltrust.ch/privacy` to explicitly cover probe-DIDs as automatic-minted-anonymous-identifiers. GDPR Art 11 (no need to identify natural person) applies |
| 9 | Abuse/farm traffic via "no-key" mode | **High** | Tier 1+2+3 alerts. Hard composite-token cap. Hard global mint-rate cap |
| 10 | Smithery SDK/UI enforces OAuth (later breaking change) | Low-Medium | Monitor Smithery release-notes. Compose D3 architecture allows OAuth-bridge if needed |
| 11 | Tool list order hides moltrust_identity | Low | Lars-decision: keep MCP-convention naming. If Smithery has tool-pinning feature, use it; if not, accept |
| 12 | tcpdump plan won't reveal HTTP headers over TLS | Low (fixed in V2) | Replaced with app-level header-capture-middleware in 4.1 |
| 13 | Metrics integrity during rollback (no version segmentability) | Medium | Add `deploy_version` column to conversion_funnel or use timestamp ranges to segment in queries |

## 9. Decision points — pre-V2-Deploy

**Decisions Lars must answer before V2 sprint kicks off:**

| # | Decision | Recommended | Status |
|---|---|---|---|
| 1 | Composite-token strategy (A/B/C per 4.2) | C — strictly conjunct | Pending 4.1 findings |
| 2 | Soft-launch with reduced caps first 48h | NO — full caps from Day 1, alerting from Tier 1 (per Lars) | ✓ Decided |
| 3 | Concrete vs vague probe limits in schema | Concrete ("24h TTL, 50 calls") — per Lars | ✓ Decided |
| 4 | Tool-name prefix for discovery (moltrust_identity → 00_) | NO — keep MCP convention (per Lars) | ✓ Decided |
| 5 | Locale support (EN+DE) | NO — Smithery doesn't support, EN only | ✓ Decided (per GPT-5) |
| 6 | Sequential A/B-test plan (Phase 1 / Phase 2) | See Sektion 13 — two-phase plan | ✓ Decided |
| 7 | Free-Tier badge request from Smithery | Automatic-first, request only at Day 7 if missing | ✓ Decided |
| 8 | Rollback trigger thresholds (error-rate / 5xx-per-min) | Defaults in 11.1 accepted | ✓ Decided |

## 10. Pre-V2-Sprint open prep items

To do before V2 sprint starts (decoupled from V2 timing):

- [ ] Fix Smithery Homepage URL `https://smithery.ai` → `https://moltrust.ch` (manual UI, 30 sec)
- [ ] Read Smithery docs at smithery.ai/docs/build/publish — verify any platform changes + tool-pinning feature availability
- [ ] Header-capture-middleware on Cloudflare-tunnel test stack to identify Smithery's gateway pattern (4.1)
- [ ] Confirm Smithery API/CLI for atomic config push (5.3 step 1 efficiency)
- [ ] Update `moltrust.ch/privacy` for probe-DID compliance (Risk #8)
- [ ] Build weekly Day-1/D3/D7/D30 report-script skeleton (cron + python, ready to deploy)

## 11. Rollback plan

### 11.1 Rollback triggers (automatic-action thresholds)

- **5xx rate >1% over 5-min window** → Tier 3 auto-reduction (Sektion 6) + alert
- **5xx rate >5% over 1-min window** → Auto-disable probe-spawn endpoint (return 503 with claim_url body) + alert
- **DB connection-pool exhausted >2 consecutive 1-min windows** → Auto-disable probe-spawn endpoint + alert
- **Conversion_funnel writes failing >10 errors/min** → Alert (no auto-action, observation-only — attribution may be broken but operations continue)

### 11.2 Manual rollback procedure

If V2 needs to be rolled back:

1. **Code rollback** — revert main HEAD to pre-V2 commit. Standard git operation, same as today's morning rollback.
2. **Service restart** — `systemctl restart moltstack.service` + verify pre-V2 endpoints respond.
3. **Smithery description revert** — manual on Smithery UI. Paste back V1 Tagline + Description from `audits/2026-XX-XX_smithery-pre-v2-snapshot.md`.
4. **Smithery schema revert** — re-publish prior schema. Trigger Smithery re-scan.
5. **DB state** — probe_agents tables are additive, no rollback needed. New rows from V2-period stay (harmless).
6. **Conversion_funnel** — same as DB state.
7. **Alert closeout** — disable Tier 1/2/3 alert thresholds while in rolled-back state, re-enable on next deploy.

Acceptable downtime: <5 minutes if all steps execute smoothly.

## 12. Success criteria — Day-30 final report

| Metric | Floor (V2 must hit) | Stretch goal |
|---|---|---|
| Smithery-attributed probe spawns | ≥100 | ≥300 |
| Probes ≥3 distinct tools used | ≥30 | ≥75 |
| Probes ≥3 distinct vertical prefixes | ≥15 | ≥50 |
| Probes → claim | ≥10 | ≥30 |
| Smithery Quality Score | maintain ≥82 | ≥90 |
| Weekly Smithery tool-calls | ≥40 (vs current 22) | ≥100 |
| Source attribution accuracy | ≥95% (false-positives + false-negatives <5%) | ≥98% |

If floor not hit at Day 30:
- If Smithery probe spawn count is low (<50): Discovery is the bottleneck. Re-evaluate Smithery Quality Score levers (Goal B failed).
- If spawn count is OK but engagement-depth low (<15 with ≥3 distinct tools): Engagement is the bottleneck. Re-evaluate description, tool ordering, value-message.
- If engagement OK but claim rate low (<10): Claim-friction is the bottleneck. Re-evaluate claim-flow (email-required vs anonymous).

If stretch hit: expand auto-probe to vertical landings as per Auto-Probe-Spec section 7.

---

## 13. Sequential A/B-Test Plan (Decision 6 detail)

Two-phase strategy with explicit decision gate at Day 7. Smithery does not support simultaneous A/B testing — sequential observation with clear hypothesis per phase.

### 13.1 Phase 1: Schema-Only-Change (Day 0–7)

**What changes on Smithery:**
- Schema description for `api_key` field updates per 5.2 (documents Probe-Mechanismus, 24h TTL, 50 calls)
- Tool `moltrust_identity` appears in tool list (was absent in V1 listing)
- Tagline + Server-Description remain at V1 wording

**Hypothesis:** Schema-level signal alone is sufficient for discovery. Users browsing Smithery's tool-inspector and api_key documentation will discover the probe-mechanism without needing marketing-language changes.

**Success criterion at Day 7:**
- ≥10 Smithery-attributed probes with ≥3 distinct tools used
- Source-attribution false-positive rate <5%

**If success:** stay on Phase 1 wording. Don't change Description. The lever is working without it.

**If failure (<10 probes at Day 7):** proceed to Phase 2 — Description is the missing piece.

### 13.2 Phase 2: Description Swap (Day 7–30, conditional)

**Triggered only if Phase 1 falls short.**

**What changes:**
- Tagline updates to V2.1 5.1 default ("Trust registry for autonomous AI agents — try free, no signup.")
- Server-Description updates to V2.1 5.1 default (includes "Every tool works in a free probe mode... 24h TTL, 50 calls... Existing api_key users are unaffected")
- Schema and tool list stay unchanged from Phase 1

**Hypothesis:** Description carries the value-proposition that schema alone doesn't communicate. Users need to *read* about the probe-mechanism in plain English before discovering the schema.

**Success criterion at Day 30 (cumulative since Day 0):**
- ≥30 Smithery-attributed probes with ≥3 distinct tools used (Floor)
- ≥10 claim conversions (Floor)

### 13.3 Why this design

- **Sequential not parallel:** Smithery doesn't allow split-traffic A/B on listings
- **Schema-first:** Less commitment, less Smithery-cache disruption, easier to roll back
- **7-day baseline:** Statistically enough to see if signal is established, short enough to iterate
- **Decision-gate at Day 7:** Prevents change-for-change's-sake. If Phase 1 wins, save the Description-change as future ammunition
- **No simultaneous changes:** isolates the variable. After Day 30 we know which lever moved which metric

### 13.4 Free-Tier badge (Decision 7 detail)

**Strategy: passive-first, manual-fallback.**

Smithery may auto-classify our listing as "Free Tier" or "No Signup" once schema documents the no-key path. Their classification logic is opaque but suspected to read schema description patterns.

**No proactive request at go-live.** Day 7 check during Phase 1 review:
- Has Smithery automatically added a Free-Tier/No-Signup badge?
- If YES: do nothing, badge is working
- If NO: send a single email to Smithery support requesting badge consideration

This avoids cluttering Smithery's support queue with redundant requests when their automatic classifier may handle it. If we're wrong about auto-classification, we lose 7 days of badge visibility — acceptable tradeoff for cleaner relationship.

---

## V1 → V2 → V2.1 Diff Summary (for memory)

What changed from V1 to V2 after GPT-5 review:

1. **Goals reordered** B → A → C (was A → B → C). C is now gating-checklist, not goal.
2. **Header-capture method fixed** — Starlette middleware not tcpdump (TLS-termination blocker).
3. **Post-deploy Smithery sequence reordered** — schema/rescan/test first, marketing-text last (was tagline-first).
4. **Attribution logic tightened** — conjunct check, not substring match.
5. **13 risks identified** (was 3), three at High severity (DB load, probe-key leak, abuse).
6. **Day-1/D3/D7/D30 checkpoints added** (was just Day 30).
7. **Engagement metric refined** — distinct tools + verticals, not just call count (harder to game).
8. **Soft-launch dropped per Lars** — full caps from Day 1 with Tier 1/2/3 alerting.
9. **Concrete probe limits in schema per Lars** — "24h TTL, 50 calls" (not vague).
10. **MCP-convention preserved per Lars** — no tool-name prefix hack.
11. **Existing-user note added** — Description includes "Existing api_key users are unaffected" per GPT-5 D5.
12. **Rollback plan formalized** — automatic triggers + manual procedure.
13. **DB indices added** for conversion_funnel reporting performance.
14. **Smithery Homepage URL fix decoupled** — fix today, independent of V2 timing.

**V2 → V2.1 changes (after Lars decisions on Decisions 6/7/8):**

15. **Decision 6 (A/B-Test-Plan) detailed** — two-phase plan in Section 13. Phase 1 Schema-Only (Day 0–7), Phase 2 Description-Swap conditional on Phase 1 outcome.
16. **Decision 7 (Free-Tier-Badge) re-strategized** — automatic-first, manual request only at Day 7 if missing. Saves Smithery-support queue burden.
17. **Decision 8 (Rollback thresholds) accepted** — Section 11.1 defaults stand.
18. **Decision-table status updated** — all 8 decisions now ✓ Decided.
19. **Prep-items list cleaned** — removed redundant Decision-8-pending and tool-pinning-standalone items (folded into Smithery-docs check).

End of V2.1 workflow document. Reference for Re-Deploy V2 sprint.
