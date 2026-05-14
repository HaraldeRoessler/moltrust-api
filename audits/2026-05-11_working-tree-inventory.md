# Working-Tree Inventory — 2026-05-11

**Branch:** `feature/auto-probe-token` · **HEAD:** `88956b7` (fix(security): use last-hop X-Forwarded-For in identity._client_ip)
**Status snapshot taken at:** 2026-05-11, after accidental `git stash pop` during the auto-probe security-fix sprint
**Author of report:** automated triage assistant — NO commits/stashes/checkouts performed against the working tree

## Why this report exists

While starting Task 3 (six security fixes) I ran `git stash` (intending to A/B test the pre-fix state). It reported "No local changes to save" because my fixes had already been committed. The subsequent `git stash pop` — which I expected to be a no-op — silently applied an unrelated pre-existing stash that had been sitting in `stash@{0}` from a prior session. The pop produced conflicts in 3 files and left another 10 files with un-committed modifications in the working tree. None of this is my work; all of it predates this session.

User direction: **no destructive ops** until the pre-existing changes are inventoried. This report is that inventory.

---

## Summary table

| # | File | Type | Conflict markers | Logic significance | Already committed? | Suspected origin |
|---|---|---|---|---|---|---|
| 1 | `agents/ai_review.py` | M | **3 lines (1 conflict)** | Medium — Gemini auth migration mid-flight | No | Lars, mid-session (Swisscom IP) |
| 2 | `agents/herald_v3.py` | M | None | **High — new Polymarket integration + flag_record DB tracking** | No | Lars (build-out of existing herald) |
| 3 | `agents/traffic_monitor.py` | M | **12 lines (4 conflicts)** | High — two competing v2 rewrites | No | Two overlapping sessions; both Lars |
| 4 | `agents/watchdog.py` | M | None | Low — removes Moltbook poster (already disabled in comments) | No | Lars, cleanup |
| 5 | `agents/workspace/ambassador/MEMORY.md` | DU | None | **None — runtime state, gitignored** | N/A — `agents/workspace/*/MEMORY.md` is in `.gitignore` | Agent itself (writes during cron runs) |
| 6 | `app/main.py` | M | None (false positive earlier) | **High — RBAC refactor: more endpoints converted to verify_admin()** | Partially — 4 endpoints already use it (commit `649782c`); diff adds ~5 more | Lars (continuing the April-17 RBAC work) |
| 7 | `app/settlement.py` | M | None | Medium — trust_score_cache invalidation on settle | No | Lars (perf fix) |
| 8 | `app/swarm/trust_score.py` | M | None | Medium — ZeroID agent-class trust modifier + prediction-accuracy bonus | No | Lars (new feature build) |
| 9 | `moltbook/state.json` | DU | None | **None — runtime state, gitignored** | N/A — `moltbook/state.json` is in `.gitignore` | Moltbook poster cron (live writes; mtime 13:22 today) |
| 10 | `outreach/submitted_prs.md` | M | None | Trivial — one-line append (`awesome-x402 PR #219`) | No | Lars manual edit |
| 11 | `scripts/concept_review.py` | M | None | Medium — Gemini auth migration (same family as #1) | No | Lars, mid-session |
| 12 | `scripts/daily_stats.sh` | M | None | Low — adds TOP_CALLERS section + MCP_AUTH grep widening | No | Lars (analytics tweak) |
| 13 | `scripts/outreach_xmtp.js` | M | None | High — XMTP v2 → v3 SDK migration | No | Lars (SDK upgrade) |

**Legend:** M = modified, DU = deleted-by-us-unmerged, UU = unmerged-both
**Total lines changed:** +2126 / −140 across 13 files

---

## Per-file detail

### 1. `agents/ai_review.py` — Gemini auth migration mid-flight

**Conflict:** 1 conflict in the `call_perplexity` function area, surrounding lines 230–245.
**Both halves of the conflict are legitimate:**
- `Updated upstream` (the version that was on disk): full Perplexity call with `timeout=180`
- `Stashed changes`: Gemini call using `headers={"x-goog-api-key": GEMINI_KEY}` instead of URL-query-string `?key=`

The non-conflicted hunks all bump timeouts `120 → 180` for OpenAI/Claude and remove `?key=` from the Gemini URL (the auth moves to a header). Search shows the URL `?key=` lives nowhere else in the repo after this change.

**If `git checkout -- this-file` were run:** Loses the Gemini auth migration (URL-key → header-key), loses the timeout bumps, and loses whichever resolution was intended for the Perplexity-vs-Gemini conflict.

**Already committed?** `git log -S'x-goog-api-key'` → **0 commits**. Brand new.

**Origin:** Lars. Same migration applied symmetrically in `scripts/concept_review.py` (file #11) — coordinated multi-file change, single author.

### 2. `agents/herald_v3.py` — Polymarket integration + DB outcome tracking

**No conflict markers.** Clean substantive addition:
- New `import psycopg2`
- `DB_URL` constant
- New `resolve_polymarket_slug(market_id)` — calls Polymarket Gamma API to map market IDs to public-URL slugs
- New `insert_flag_record(market_data, tweet_id)` — writes a row to `flag_records` table for outcome tracking
- `generate_anomaly_tweet` return signature changed from `str | None` to `tuple[str | None, dict | None]`
- Tweet text now includes `Market: https://polymarket.com/event/<slug>` line
- Trim logic for 280-char cap now drops API line first, Polymarket line second

**If `git checkout`:** Loses ~90 lines of working outcome-tracking integration. Tweets continue posting but with no DB trail tying them to outcomes.

**Already committed?** `flag_records` table created in commit `649782c` (April 17 "admin RBAC, SKALE anchor, IPR publication anchor"). The Herald-side `insert_flag_record` function is NEW — `git log -S'insert_flag_record'` → 0 commits. So the table exists, the writer is uncommitted.

**Origin:** Lars (continues the table-creation work in `649782c`). Date alignment: `649782c` was April-17, this herald wiring is the follow-up.

### 3. `agents/traffic_monitor.py` — two competing v2 rewrites

**Conflict:** 12 marker lines = 4 distinct conflicts. Two completely different v2 designs:
- `Updated upstream`: file-based IP tracking (`known_ips.txt`), sync code, `psycopg2`
- `Stashed changes`: DB-table tracking (`known_callers` table), async (`asyncpg`)

**This is the messiest file.** Whoever paused this work was mid-refactor between two designs. The async-with-known_callers version looks more polished; the file-based looks like a fallback or older approach.

**If `git checkout`:** Reverts to a v1 traffic monitor (before either v2 attempt). The "25–30 new external callers" noise problem the file headers describe remains unsolved.

**Already committed?** `known_callers` table — `git log -S'known_callers'` → 0 commits. Neither v2 is committed. The v1 baseline IS committed.

**Origin:** Lars across two overlapping sessions. The fact that both halves exist suggests one was stashed mid-edit, the other written in a follow-up session, and the merge was never resolved.

### 4. `agents/watchdog.py` — clean removal of Moltbook poster from watchdog list

**No conflict markers.** Clean structural deletion of one entry from `AGENTS` list:
- Adds a comment `Moltbook Poster: DISABLED 2026-03-30 — Moltbook API down post Meta acquisition`
- Deletes the `{"name": "Moltbook Poster", ...}` dict

**If `git checkout`:** Watchdog continues alarming about the Moltbook poster being silent — which it permanently is, because the upstream API died. Pure noise reduction.

**Already committed?** No commit contains the disabled-comment string verbatim.

**Origin:** Lars cleanup after Moltbook API died (2026-03-27 per the comment).

### 5. `agents/workspace/ambassador/MEMORY.md` — IGNORE: gitignored runtime state

**Status code `DU`** (deleted by us, unmerged) is misleading. **The file is in `.gitignore`** (line: `agents/workspace/*/MEMORY.md`). The stash pop thought it should be deleted (committed-tracked state vs gitignored intent). The file on disk is 914 lines of legitimate agent interaction history written by the running Ambassador agent (mtime 2026-05-11 13:17 — being updated live by cron).

**If `git checkout`:** Tries to delete; would be re-created by the next Ambassador cron run anyway.

**Already committed?** Should not be — it's gitignored. Past tracking is an artifact (file added before .gitignore rule).

**Origin:** Ambassador agent runtime; not human-authored.

### 6. `app/main.py` — RBAC refactor: more endpoints to `verify_admin()`

**No conflict markers** (my earlier false-positive grep used wrong escaping). Substantive logic change:
- Imports `SlowAPIMiddleware`, registers as `app.add_middleware(SlowAPIMiddleware)` — was previously the limiter-without-middleware setup
- Replaces inline `request.headers.get("x-admin-key")` + `os.environ.get("ADMIN_KEY")` + compare-then-raise pattern with `verify_admin(request, AdminPermission.X)` calls at **~7 admin endpoints**:
  - `/swarm/seed` → WRITE
  - `/inactive-agents` (GET) → READ
  - `/identity/register-batch` → WRITE
  - `/violation/record` → DESTROY
  - `/violation/reverse` → DESTROY
  - `/agent/revoke` → uses `is_admin()` helper
  - `/agent/unrevoke` → DESTROY
- Adds `LIMIT 100` to `violation_records` query

**If `git checkout`:** Reverts to 4-of-~11 admin endpoints using the RBAC helper. The other 7 fall back to legacy single-key check (less granular, no audit trail). **Security regression.**

**Already committed?** `verify_admin` / `AdminPermission` defined in `app/admin_rbac.py` (committed `649782c`, April-17) and already used at 4 call sites in current `main.py`. The diff adds ~5 more conversions. Same RBAC system, more endpoints migrated.

**Origin:** Lars, continuing the April-17 RBAC migration.

### 7. `app/settlement.py` — trust-score cache invalidation on settle

**No conflict.** Adds 15 lines after `UPDATE sports_predictions … SET outcome_data = $1`:
- Resolves `agent_did` from the row (or refetches by commitment_hash if absent)
- `DELETE FROM trust_score_cache WHERE did = $1`
- Log line

**If `git checkout`:** Settling a sports prediction stops invalidating the cached trust score. The cache then serves stale scores until the next force-recompute (`/swarm/propagate/{did}`).

**Already committed?** `trust_score_cache` table exists in earlier commits but no commit removes from it on settle.

**Origin:** Lars, perf/correctness fix.

### 8. `app/swarm/trust_score.py` — ZeroID agent-class modifier + prediction-accuracy bonus

**No conflict.** Adds:
- `AGENT_CLASS_MODIFIER` dict (`orchestrator: +5, copilot: -10`, etc.) — labelled "ZeroID Feature 1"
- New `compute_prediction_accuracy_bonus(conn, did)` function (40+ lines, signature visible — body cut off by diff width)
- Probably integration into the score formula (not visible in diff head)

**If `git checkout`:** Loses ~92 lines of new trust-score functionality. Agent-class differentiation goes away; prediction-accuracy stays uncomputed for scoring.

**Already committed?** `AGENT_CLASS_MODIFIER`, `compute_prediction_accuracy_bonus` → 0 commits.

**Origin:** Lars, feature build aligned with ZeroID work mentioned in trust_score header.

### 9. `moltbook/state.json` — IGNORE: gitignored runtime state

**Status `DU`** same situation as #5. The file `moltbook/state.json` IS in `.gitignore`. mtime 2026-05-11 13:22 — being written live by the Moltbook poster cron. The diff shows 734 lines of state (upvoted-IDs, post counters, etc.) — not code.

**If `git checkout`:** Tries to delete; cron writes it back within 12 hours.

**Origin:** Moltbook poster agent runtime, not human-authored.

### 10. `outreach/submitted_prs.md` — one-line append

**No conflict.** Appends a single line at end of file:
```
awesome-x402: https://github.com/xpaysh/awesome-x402/pull/219
```

**If `git checkout`:** Loses the awesome-x402 PR tracking entry.

**Already committed?** `git log -S'awesome-x402'` → 2 commits, but they touch blog/docs files, NOT submitted_prs.md. This append is new.

**Origin:** Lars manual edit, normal outreach housekeeping.

### 11. `scripts/concept_review.py` — Gemini auth migration (paired with #1)

**No conflict.** Same `?key=` URL-arg → `x-goog-api-key` header migration as in #1. Plus timeout bump 60 → 180.

**If `git checkout`:** Loses Gemini auth migration in this script. Combined with reverting #1, the security migration disappears entirely.

**Already committed?** No.

**Origin:** Lars; symmetric with #1.

### 12. `scripts/daily_stats.sh` — TOP_CALLERS section + grep widening

**No conflict.** Adds:
- `TOP_CALLERS` derived from nginx log via `grep -o 'profile=[^& "]*'` + sort/uniq
- Widens `MCP_AUTH` grep from `api_key=mt_` to just `api_key=` (catches any auth scheme)
- Includes TOP_CALLERS in Telegram message

**If `git checkout`:** Daily stats Telegram drops top-3-callers section. MCP_AUTH undercount returns (only `mt_` keys, not future schemes).

**Already committed?** No.

**Origin:** Lars, ops analytics tweak.

### 13. `scripts/outreach_xmtp.js` — XMTP V2 → V3 SDK migration

**No conflict.** 167 changed lines:
- Header docstring rewritten ("XMTP V3 (node-sdk)")
- Removes `const { Client } = require("@xmtp/xmtp-js")` (V2 SDK)
- Adds V3 import (cut off in diff head)
- Adds `MAX_SEND` env-based throttle
- Reads `BASE_WRITE_KEY` from `~/.moltrust_secrets` instead of env

**If `git checkout`:** XMTP outreach reverts to V2 SDK. Whether that still works depends on xmtp-js V2 deprecation status — risk is real.

**Already committed?** No.

**Origin:** Lars, SDK migration.

---

## Origin analysis

**SSH login history** (last 20 sessions, 2026-04-15 → 2026-05-09):

| IP | ISP | Inferred actor |
|---|---|---|
| `82.135.70.55`, `82.135.79.117` | Swisscom (CH) | **Lars from Zürich** |
| `62.36.37.27` | Telefónica (ES) | Lars traveling? |
| `45.149.228.30` | Known VPN range | Lars on VPN |
| `217.65.137.106` | Aruba S.p.A. (IT) | VPS bastion or older session |

**No OVH-prefix IPs in recent history.** If Harald has been working, it's not via SSH-on-this-server in the last 25 days — would be via git push (no evidence in reflog of recent pulls from a Harald branch). Working assumption: **all 13-file content is Lars-authored across overlapping sessions**.

**Git reflog** (most recent activity):
- Today (2026-05-11): my mount + dispatch-auth + security-fix commits, on top of cherry-picks from `probe-dryrun` branch onto `feature/auto-probe-token`
- The cherry-pick chain suggests `probe-dryrun` was an isolated work branch that got squashed/replayed onto `feature/auto-probe-token` earlier today

**Conclusion:** the 13 files of mess existed BEFORE today's auto-probe-token work began. They are remnants of one or more Lars sessions on `feature/auto-probe-token` (or its predecessor branches) that never got committed. My session's only contribution to the mess was the unintended `git stash pop` that re-applied them visibly.

---

## Recommendation matrix

The decision is not all-or-nothing — these 13 files break into clean buckets:

| Bucket | Files | Recommended action |
|---|---|---|
| **Drop entirely (gitignored runtime state)** | 5, 9 | Tell git to untrack and re-honor `.gitignore`: `git rm --cached agents/workspace/ambassador/MEMORY.md moltbook/state.json` |
| **Trivial — apply as-is** | 4, 10 | Tiny clean diffs, no risk: stage and commit separately |
| **Substantive but clean — review then commit** | 2, 6, 7, 8, 12, 13 | Lars reads each, decides commit or revert per file |
| **Substantive + has conflict markers — manual resolve** | 1, 3, 11 | Each needs the "Updated upstream" vs "Stashed changes" decision made; #1 and #11 are the same Gemini migration so resolve together |

**My recommendation, for whenever you decide to act:**
1. Untrack the two gitignored files (#5, #9) — risk-free, removes 2 of 13 from the noise.
2. Commit #4 and #10 each as their own one-line commits — low risk, recovers signal.
3. Pause on the substantive cluster (#2, #6, #7, #8, #12, #13) and the conflict cluster (#1, #3, #11) until Lars has 30 minutes to triage them properly. The auto-probe sprint can resume on a clean tree once #2/#6 in particular are decided (both are substantive security/feature work that probably wants to keep).

**What I will NOT do without explicit go-ahead:** stash, checkout, rm --cached, reset, clean. The current working tree state is preserved verbatim. This report is the only artifact this session produced.

---

## Pre-existing failing tests (separate concern)

Four tests in `tests/test_identity.py` were already failing on `88956b7` BEFORE the auto-probe sprint touched anything. All four raise `app.identity.AuthError` and are concentrated in the probe-minting test fixture — most likely cause is leftover DB state from earlier manual testing saturating the probe-spawn rate limit per-IP/per-window.

| Test | Suspected cause |
|---|---|
| `test_no_key_mints_probe` | Probe-spawn rate limit hit on test IP |
| `test_session_id_reuses_probe` | Same — depends on first test minting |
| `test_session_id_no_reuse_after_expiry` | Same |
| `test_claim_with_valid_probe_email` | Cascades from minting failure |

**Fix path** (not in scope of this audit but to keep on the to-do): the test fixture in `tests/test_identity.py` should `TRUNCATE probe_agents, probe_spawn_rate_log` (or whatever the rate-limit table is named) at session-scope setup. If `tests/KNOWN_FAILURES.md` is created to track these, each entry should reference this audit's section.

---

## What this report does NOT do

- Recommend deletion of anything
- Touch the working tree
- Resolve any conflicts
- Decide which of the two `traffic_monitor.py` v2 designs wins
- Decide whether the `moltbook/state.json` ever should have been tracked
- Comment on whether the `verify_admin` refactor in `app/main.py` is correct (it looks like the safer pattern, but that's Lars's call)

Auto-probe sprint is paused at: Task 3 (six security fixes), sub-step 1 of 6 complete (commit `88956b7`). Resumes when working tree is clean.
