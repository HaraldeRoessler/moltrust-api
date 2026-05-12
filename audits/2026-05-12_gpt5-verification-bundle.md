# GPT-5 Verification Bundle — 2026-05-12

**Purpose:** raw evidence requested to verify 4 claims from `audits/2026-05-12_static-analysis.md` that GPT-5 flagged as unverifiable.
**Generated:** 2026-05-12 ~07:35 UTC
**Branch at generation:** `chore/static-analysis-2026-05-12` (from `feature/auto-probe-token` HEAD `d4f29d2`)
**Author:** automated triage (Claude) — read-only data dump, zero modifications to working tree, services, or remote refs.

---

## 1. Git state snapshot

### 1a. `git fetch --all`
```
```

### 1b. `git rev-parse main origin/main`
```
f11f5571e66eb74d4c8f39d504d2985e94d2b871
90a8364ce3ff34a668a9745d0273b395a68acfea
```

### 1c. `git log --oneline origin/main..main`
```
(empty — local main has 0 commits exclusive of origin/main)
```

### 1d. `git status --porcelain`
```
?? audits/2026-05-11_working-tree-inventory.md
```

---

## 2. `git stash show -p stash@{0}` — full patch

Stash label: `pre-auto-probe-deploy-2026-05-12-WIP-incl-prediction-accuracy`
Stash created: 2026-05-12 06:12:12 UTC (Phase-9 prep)
Files affected: 10 tracked-and-modified

```diff
diff --git a/agents/ai_review.py b/agents/ai_review.py
index 3dfe918..4fcfe7d 100755
--- a/agents/ai_review.py
+++ b/agents/ai_review.py
@@ -165,7 +165,7 @@ async def call_openai(client: httpx.AsyncClient, document: str, mode: str) -> di
             "https://api.openai.com/v1/chat/completions",
             headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
             json=payload,
-            timeout=120
+            timeout=180
         )
         resp.raise_for_status()
         data = resp.json()
@@ -189,7 +189,7 @@ async def call_gemini(client: httpx.AsyncClient, document: str, mode: str) -> di
         "generationConfig": {"maxOutputTokens": GEMINI_MAX_TOKENS, "temperature": 0.3}
     }
 
-    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
+    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
 
     last_error = None
     for attempt in range(3):
@@ -230,12 +230,16 @@ async def call_perplexity(client: httpx.AsyncClient, document: str, mode: str) -
     }
 
     try:
+<<<<<<< Updated upstream
         resp = await client.post(
             "https://api.perplexity.ai/chat/completions",
             headers={"Authorization": f"Bearer {PERPLEXITY_KEY}", "Content-Type": "application/json"},
             json=payload,
             timeout=180
         )
+=======
+        resp = await client.post(url, json=payload, headers={"x-goog-api-key": GEMINI_KEY}, timeout=180)
+>>>>>>> Stashed changes
         resp.raise_for_status()
         data = resp.json()
         content = data["choices"][0]["message"]["content"]
@@ -275,7 +279,7 @@ async def call_claude_synthesis(client: httpx.AsyncClient, openai_result: dict,
                 "Content-Type": "application/json"
             },
             json=payload,
-            timeout=120
+            timeout=180
         )
         resp.raise_for_status()
         data = resp.json()
diff --git a/agents/herald_v3.py b/agents/herald_v3.py
index 553fdc2..50c6fdd 100644
--- a/agents/herald_v3.py
+++ b/agents/herald_v3.py
@@ -9,6 +9,7 @@ Cron: 4x/day (07, 12, 17, 22 UTC)
 
 import os, sys, datetime, json, logging, traceback, random, re
 import httpx
+import psycopg2
 from requests_oauthlib import OAuth1
 import requests as req_lib
 
@@ -20,6 +21,7 @@ HEARTBEAT_FILE = os.path.join(DATA_DIR, "herald_heartbeat.json")
 STATE_FILE = os.path.join(DATA_DIR, "herald_state.json")
 
 FEED_URL = "https://api.moltrust.ch/guard/api/market/feed"
+DB_URL = os.environ.get("DATABASE_URL", "dbname=moltstack user=moltstack")
 DASHBOARD_URL = "https://moltrust.ch/integrity.html"
 X_API_URL = "https://api.twitter.com/2/tweets"
 
@@ -291,11 +293,24 @@ def fetch_feed() -> list:
 
 # ── Tweet generation ──
 
-def generate_anomaly_tweet(markets: list, state: dict) -> str | None:
-    """Generate a tweet from anomaly data via Claude."""
+def resolve_polymarket_slug(market_id: str) -> str | None:
+    """Resolve Polymarket slug from market ID via Gamma API."""
+    try:
+        resp = httpx.get(f"https://gamma-api.polymarket.com/markets/{market_id}", timeout=8)
+        if resp.status_code == 200:
+            slug = resp.json().get("slug")
+            if slug:
+                return f"https://polymarket.com/event/{slug}"
+    except Exception as e:
+        log.warning(f"Polymarket slug resolve failed for {market_id}: {e}")
+    return None
+
+
+def generate_anomaly_tweet(markets: list, state: dict) -> tuple:
+    """Generate a tweet from anomaly data via Claude. Returns (tweet, market_data) or (None, None)."""
     flagged = [m for m in markets if m.get("anomalyScore", 0) >= 30]
     if not flagged:
-        return None
+        return None, None
 
     # Avoid repeating last-tweeted market
     last_market_id = state.get("last_market_id", "")
@@ -320,6 +335,12 @@ def generate_anomaly_tweet(markets: list, state: dict) -> str | None:
 
     market_id = top.get("marketId", "")
     api_cta = f"api.moltrust.ch/integrity/{market_id}" if market_id else ""
+    polymarket_url = resolve_polymarket_slug(market_id) if market_id else None
+
+    cta_lines = f"Check it: {DASHBOARD_URL}"
+    if polymarket_url:
+        cta_lines += f"\nMarket: {polymarket_url}"
+    cta_lines += f"\nAPI: {api_cta}" if api_cta else ""
 
     context = (
         f"Write a single tweet (max 280 chars) based on this real anomaly data:\n\n"
@@ -328,16 +349,27 @@ def generate_anomaly_tweet(markets: list, state: dict) -> str | None:
         f"Signals: {', '.join(active) if active else 'multiple signals active'}\n"
         f"24h Volume Change: {fmt_vol(sigs.get('volumeChange24h', 0))}\n"
         f"Assessment: {top.get('assessment', 'Unusual trading patterns detected')}\n\n"
-        f"End the tweet with:\nCheck it: {DASHBOARD_URL}\nAPI: {api_cta}\n\n"
+        f"End the tweet with:\n{cta_lines}\n\n"
         f"Do NOT just describe the data. Find the sharp angle."
     )
 
     tweet = generate_with_claude(context)
-    if tweet and len(tweet) > 280 and api_cta in tweet:
+    # If too long, trim API line first, then Polymarket link if still over
+    if tweet and len(tweet) > 280 and api_cta and api_cta in tweet:
         tweet = tweet.replace(f"\nAPI: {api_cta}", "").replace(f" | API: {api_cta}", "")
+    if tweet and len(tweet) > 280 and polymarket_url and polymarket_url in tweet:
+        tweet = tweet.replace(f"\nMarket: {polymarket_url}", "").replace(f" | Market: {polymarket_url}", "")
     if tweet:
         state["last_market_id"] = market_id
-    return tweet
+    return tweet, {
+        "market_id": market_id,
+        "question": top.get("marketQuestion", ""),
+        "anomaly_score": top.get("anomalyScore", 0),
+        "signals": sigs,
+        "active_signals": active,
+        "polymarket_url": polymarket_url,
+        "assessment": top.get("assessment", ""),
+    } if tweet else (None, None)
 
 
 def generate_awareness_tweet(state: dict) -> str | None:
@@ -382,6 +414,56 @@ def generate_fallback_tweet(state: dict) -> str:
 
 # ── Main ──
 
+
+def insert_flag_record(market_data: dict, tweet_id: str) -> str | None:
+    """Insert a flag_record for outcome tracking."""
+    if not market_data or not market_data.get("market_id"):
+        return None
+    try:
+        conn = psycopg2.connect(DB_URL)
+        cur = conn.cursor()
+        import uuid
+        flag_id = f"flag-{market_data['market_id']}-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M')}"
+
+        # Get price from Polymarket
+        price_at_flag = None
+        try:
+            resp = httpx.get(f"https://gamma-api.polymarket.com/markets/{market_data['market_id']}", timeout=8)
+            if resp.status_code == 200:
+                price_at_flag = resp.json().get("lastTradePrice")
+        except:
+            pass
+
+        slug = None
+        if market_data.get("polymarket_url"):
+            slug = market_data["polymarket_url"].split("/event/")[-1] if "/event/" in market_data["polymarket_url"] else None
+
+        cur.execute("""
+            INSERT INTO flag_records
+            (flag_id, market_id, market_question, polymarket_slug,
+             anomaly_score, price_at_flag, signals, status, created_tweet_id)
+            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
+            ON CONFLICT (flag_id) DO NOTHING
+        """, (
+            flag_id,
+            market_data["market_id"],
+            market_data.get("question", ""),
+            slug,
+            market_data.get("anomaly_score", 0),
+            price_at_flag,
+            json.dumps(market_data.get("signals", {})),
+            tweet_id,
+        ))
+        conn.commit()
+        cur.close()
+        conn.close()
+        log.info(f"Flag record created: {flag_id} (market {market_data['market_id']})")
+        return flag_id
+    except Exception as e:
+        log.error(f"Failed to insert flag_record: {e}")
+        return None
+
+
 def run(dry_run: bool = False):
     now = datetime.datetime.now(datetime.timezone.utc)
     now_str = now.strftime("%Y-%m-%d %H:%M UTC")
@@ -428,8 +510,9 @@ def run(dry_run: bool = False):
     tweet = None
     mode = "anomaly"
 
+    anomaly_market_data = None
     if markets:
-        tweet = generate_anomaly_tweet(markets, state)
+        tweet, anomaly_market_data = generate_anomaly_tweet(markets, state)
 
     if not tweet:
         mode = "awareness"
@@ -485,6 +568,13 @@ def run(dry_run: bool = False):
         state["last_tweet_id"] = tweet_ids[0]
         state["last_mode"] = mode
         state["consecutive_failures"] = 0
+
+        # Insert flag_record for outcome tracking (anomaly tweets only)
+        if mode == "anomaly" and anomaly_market_data:
+            flag_id = insert_flag_record(anomaly_market_data, tweet_ids[0])
+            if flag_id:
+                log.info(f"Outcome tracking: {flag_id}")
+
         # Track recent tweets for variety
         recent = state.get("recent_tweets", [])
         recent.append(parts[0][:100])
diff --git a/agents/traffic_monitor.py b/agents/traffic_monitor.py
index 0278ecb..75d5480 100644
--- a/agents/traffic_monitor.py
+++ b/agents/traffic_monitor.py
@@ -1,9 +1,19 @@
 #!/usr/bin/env python3
 """
+<<<<<<< Updated upstream
 Traffic Monitor v2 — Persistent IP Tracking
 Solves the "25-30 New External Callers" noise by tracking truly new IPs
 across runs via a state file.
 """
+=======
+New External Caller Alert v2 — runs hourly via cron.
+Uses known_callers table for persistent tracking.
+Alerts ONLY for truly new IPs (never seen before).
+"""
+import os, json, asyncio, logging
+from datetime import datetime, timezone
+from urllib.request import Request, urlopen
+>>>>>>> Stashed changes
 
 import psycopg2
 import requests
@@ -11,12 +21,22 @@ import json
 from datetime import datetime
 import os
 
+<<<<<<< Updated upstream
 # Configuration
 KNOWN_IPS_FILE = "/home/moltstack/known_ips.txt"
 TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
 TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
 DB_PASSWORD = os.getenv('MOLTSTACK_DB_PW', '')
 TRUSTED_PREFIXES = ['127.', '::1', '10.', '172.16.', '192.168.', '88.99.', '116.202.', '46.225.175.']
+=======
+TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
+TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
+
+TRUSTED_PREFIXES = [
+    "127.", "::1", "10.", "172.16.", "192.168.",
+    "46.225.175.",  # Our Hetzner server
+]
+>>>>>>> Stashed changes
 
 
 def load_known_ips():
@@ -164,15 +184,41 @@ def main():
     """Main traffic monitor with persistent tracking"""
     print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Traffic Monitor v2 starting")
 
+<<<<<<< Updated upstream
     known_ips = load_known_ips()
     print(f"  Known IPs from state file: {len(known_ips)}")
 
     current_callers = get_external_callers()
     print(f"  Active external callers (>10 reqs/25h): {len(current_callers)}")
+=======
+    log.info("Checking for new external callers (v2 — known_callers)...")
+    conn = await asyncpg.connect(user="moltstack", database="moltstack")
+
+    try:
+        # Find IPs with >10 requests in last 25h that are NOT in known_callers
+        new_callers = await conn.fetch("""
+            SELECT r.ip, r.calls, r.first_seen, r.last_seen, r.ua, r.org
+            FROM (
+                SELECT ip, COUNT(*) as calls,
+                       MIN(ts) as first_seen,
+                       MAX(ts) as last_seen,
+                       (array_agg(user_agent ORDER BY ts DESC))[1] as ua,
+                       (array_agg(ip_org ORDER BY ts DESC))[1] as org
+                FROM request_log
+                WHERE ts > NOW() - INTERVAL '25 hours'
+                  AND ip NOT IN ('127.0.0.1', '::1')
+                GROUP BY ip
+                HAVING COUNT(*) > 10
+            ) r
+            LEFT JOIN known_callers k ON k.ip = r.ip
+            WHERE k.ip IS NULL
+        """)
+>>>>>>> Stashed changes
 
     new_callers, recurring_callers = categorize_callers(current_callers, known_ips)
     print(f"  Truly new: {len(new_callers)}, Recurring: {len(recurring_callers)}")
 
+<<<<<<< Updated upstream
     # Update known IPs
     all_current_ips = {caller['ip'] for caller in current_callers}
     updated_known_ips = known_ips | all_current_ips
@@ -185,6 +231,39 @@ def main():
         print(f"  Telegram alert sent: {success}")
     else:
         print(f"  No alert — quiet period")
+=======
+        for c in new_callers:
+            ip = c["ip"]
+            org = c["org"] or "Unknown"
+            ua = (c["ua"] or "")[:60]
+            calls = c["calls"]
+            first = c["first_seen"].strftime("%Y-%m-%d %H:%M UTC") if c["first_seen"] else "?"
+
+            # Register in known_callers
+            await conn.execute("""
+                INSERT INTO known_callers (ip, first_seen, label, category)
+                VALUES ($1, $2, $3, 'new')
+                ON CONFLICT (ip) DO NOTHING
+            """, ip, c["first_seen"], f"{org} — {ua}"[:128])
+
+            # Alert
+            msg = (
+                f"\U0001f514 <b>Neuer Caller (erstmals gesehen)</b>\n"
+                f"  {ip} ({org})\n"
+                f"  {ua} — {calls} requests\n"
+                f"  Zum ersten Mal: {first}"
+            )
+            send_telegram(msg)
+            log.info("NEW caller: %s (%s) — %d requests", ip, org, calls)
+
+        if not new_callers:
+            log.info("No new external callers (all known)")
+        else:
+            log.info("Alerted %d new callers, added to known_callers", len(new_callers))
+
+    finally:
+        await conn.close()
+>>>>>>> Stashed changes
 
 
 if __name__ == "__main__":
diff --git a/agents/watchdog.py b/agents/watchdog.py
index 509f136..2c2821e 100644
--- a/agents/watchdog.py
+++ b/agents/watchdog.py
@@ -16,6 +16,7 @@ logging.basicConfig(
 log = logging.getLogger("watchdog")
 
 # Agent definitions: name, max_hours without activity, check method
+# Moltbook Poster: DISABLED 2026-03-30 — Moltbook API down post Meta acquisition (500 errors since 2026-03-27)
 AGENTS = [
     {
         "name": "Herald",
@@ -35,13 +36,6 @@ AGENTS = [
         "max_hours": 1.5,  # runs every 30min, give 1.5h grace
         "fallback_log": "ambassador.log",
     },
-    {
-        "name": "Moltbook Poster",
-        "heartbeat_file": os.path.join(DATA_DIR, "moltbook_state.json"),
-        "heartbeat_ts_key": "last_post_time",
-        "max_hours": 72,  # Moltbook API 500 errors since 2026-03-27 (Meta acquisition)
-        "fallback_glob": "moltbook_*.md",
-    },
     {
         "name": "News Scout",
         "heartbeat_file": os.path.join(DATA_DIR, "news_scout_heartbeat.json"),
@@ -122,6 +116,30 @@ def check_heartbeat(agent: dict, now: datetime.datetime) -> dict:
     return {"ok": False, "detail": "No check method configured"}
 
 
+
+def check_conformance_drift() -> dict:
+    """Check if CONFORMANCE.md files match live API checksum."""
+    import subprocess
+    try:
+        result = subprocess.run(
+            ["/home/moltstack/moltguard/scripts/check_drift.sh"],
+            capture_output=True, text=True, timeout=15,
+        )
+        if result.returncode == 0:
+            return {"ok": True, "detail": "CONFORMANCE.md in sync with API"}
+        elif result.returncode == 1:
+            # Extract drift details from output
+            lines = [l for l in result.stdout.strip().split("\n") if "DRIFT" in l or "Missing" in l]
+            detail = "; ".join(lines[:3]) if lines else "Drift detected"
+            return {"ok": False, "detail": detail}
+        else:
+            return {"ok": False, "detail": f"API unreachable (exit {result.returncode})"}
+    except subprocess.TimeoutExpired:
+        return {"ok": False, "detail": "Drift check timed out (15s)"}
+    except Exception as e:
+        return {"ok": False, "detail": f"Drift check error: {e}"}
+
+
 def run():
     now = datetime.datetime.now(datetime.UTC)
     log.info(f"Watchdog run at {now.strftime('%Y-%m-%d %H:%M UTC')}")
@@ -134,6 +152,13 @@ def run():
         if not result["ok"]:
             alerts.append(f"❌ <b>{agent['name']}</b>: {result['detail']}")
 
+    # CONFORMANCE.md drift check
+    drift = check_conformance_drift()
+    status = "✅" if drift["ok"] else "❌"
+    log.info(f"  {status} CONFORMANCE Drift: {drift['detail']}")
+    if not drift["ok"]:
+        alerts.append(f"❌ <b>CONFORMANCE Drift</b>: {drift['detail']}")
+
     if alerts:
         msg = "🐕 <b>Watchdog Alert</b>\n\n" + "\n".join(alerts)
         log.warning(f"Sending alert for {len(alerts)} agent(s)")
diff --git a/app/settlement.py b/app/settlement.py
index dd8e491..6754063 100644
--- a/app/settlement.py
+++ b/app/settlement.py
@@ -237,6 +237,21 @@ async def settle_prediction(conn, commitment_hash: str, result: dict) -> bool:
         """,
         outcome_data, correct, now, commitment_hash,
     )
+
+    # Invalidate trust score cache so prediction accuracy is recalculated
+    agent_did = row.get("agent_did") if isinstance(row, dict) else None
+    if not agent_did:
+        agent_row = await conn.fetchrow(
+            "SELECT agent_did FROM sports_predictions WHERE commitment_hash = $1",
+            commitment_hash
+        )
+        agent_did = agent_row["agent_did"] if agent_row else None
+    if agent_did:
+        await conn.execute(
+            "DELETE FROM trust_score_cache WHERE did = $1", agent_did
+        )
+        logger.info(f"Trust score cache invalidated for {agent_did}")
+
     return True
 
 
diff --git a/app/swarm/trust_score.py b/app/swarm/trust_score.py
index 2b62555..c582304 100644
--- a/app/swarm/trust_score.py
+++ b/app/swarm/trust_score.py
@@ -37,6 +37,14 @@ ALPHA = 0.6   # direct score weight
 BETA  = 0.3   # propagated score weight
 GAMMA = 0.1   # cross-vertical bonus weight
 
+# Agent class trust modifiers (ZeroID Feature 1)
+AGENT_CLASS_MODIFIER = {
+    "orchestrator": 5.0,
+    "autonomous": 0.0,
+    "human_initiated": 0.0,
+    "copilot": -10.0,
+}
+
 VERTICAL_TYPES = {
     "VerifiedSkillCredential",
     "BuyerAgentCredential",
@@ -48,6 +56,53 @@ VERTICAL_TYPES = {
     "SkillEndorsementCredential",
 }
 
+async def compute_prediction_accuracy_bonus(conn, did: str) -> float:
+    """
+    Prediction accuracy bonus/malus for trust score.
+    Requires >= 3 settled predictions to activate.
+    Accuracy >= 60% → bonus up to +10
+    Accuracy < 40% → malus down to -10
+    Between 40-60% → 0 (neutral)
+    """
+    row = await conn.fetchrow(
+        """SELECT COUNT(*) as total,
+                  SUM(CASE WHEN correct THEN 1 ELSE 0 END) as wins
+           FROM sports_predictions
+           WHERE agent_did = $1 AND settled_at IS NOT NULL""",
+        did
+    )
+    if not row or row["total"] < 3:
+        return 0.0
+
+    total = row["total"]
+    wins = row["wins"] or 0
+    accuracy = wins / total
+
+    if accuracy >= 0.6:
+        # Linear scale: 60% → +2, 100% → +10
+        return round(2 + (accuracy - 0.6) / 0.4 * 8, 1)
+    elif accuracy < 0.4:
+        # Linear scale: 40% → -2, 0% → -10
+        return round(-2 - (0.4 - accuracy) / 0.4 * 8, 1)
+    else:
+        return 0.0
+
+
+
+async def compute_wallet_attestation_bonus(conn, did: str) -> float:
+    """
+    Wallet attestation bonus for trust score.
+    Reads wallet_score (0-20) from wallet_attestations table.
+    Only uses attestations < 30 min old (TTL).
+    """
+    row = await conn.fetchrow(
+        """SELECT wallet_score FROM wallet_attestations
+           WHERE did = $1 AND attested_at > NOW() - INTERVAL '30 minutes'""",
+        did
+    )
+    if not row:
+        return 0.0
+    return float(row["wallet_score"])
 
 def compute_time_decay(issued_at: datetime) -> float:
     """d_i = 2^(-Δt/90), Δt in Tagen. Whitepaper Section 4.2."""
@@ -293,11 +348,41 @@ async def compute_phase2_score(
     except Exception:
         pass
 
-    # 6. Final score
+    # 6. Prediction accuracy bonus/malus
+    prediction_bonus = 0.0
+    try:
+        prediction_bonus = await compute_prediction_accuracy_bonus(conn, did)
+    except Exception:
+        pass
+
+    # 7. Wallet attestation bonus (skin-in-the-game)
+    wallet_bonus = 0.0
+    try:
+        wallet_bonus = await compute_wallet_attestation_bonus(conn, did)
+    except Exception:
+        pass
+
+    # 8. Agent class modifier (ZeroID Feature 1)
+    agent_class_modifier = 0.0
+    try:
+        ac_row = await conn.fetchrow(
+            "SELECT agent_class FROM agents WHERE did = $1", did
+        )
+        if ac_row and ac_row["agent_class"]:
+            agent_class_modifier = AGENT_CLASS_MODIFIER.get(
+                ac_row["agent_class"], 0.0
+            )
+    except Exception:
+        pass
+
+    # 9. Final score
     raw = (ALPHA * direct_score
            + BETA * propagated_score
            + GAMMA * cross_vertical_bonus
-           + interaction_bonus)
+           + interaction_bonus
+           + prediction_bonus
+           + wallet_bonus
+           + agent_class_modifier)
     final_score = max(0, min(100, raw - sybil_penalty * 20 + inactivity_penalty))
     final_score = round(final_score, 1)
 
@@ -316,7 +401,10 @@ async def compute_phase2_score(
         "cross_vertical_bonus": cross_vertical_bonus,
         "interaction_bonus": interaction_bonus,
         "sybil_penalty": round(sybil_penalty, 2),
+        "prediction_bonus": prediction_bonus,
+        "wallet_bonus": wallet_bonus,
         "inactivity_penalty": inactivity_penalty,
+        "agent_class_modifier": agent_class_modifier,
         "endorser_count": len(unique_endorsers),
         "computation_method": "phase2",
         "withheld": False,
diff --git a/outreach/submitted_prs.md b/outreach/submitted_prs.md
index a653482..25043b8 100644
--- a/outreach/submitted_prs.md
+++ b/outreach/submitted_prs.md
@@ -105,3 +105,4 @@ Last updated: 2026-03-09
 - https://moltrust.ch/pypi → PyPI page
 - https://moltrust.ch/smithery → Smithery.ai listing
 - https://moltrust.ch/glama → Glama.ai listing
+awesome-x402: https://github.com/xpaysh/awesome-x402/pull/219
diff --git a/scripts/concept_review.py b/scripts/concept_review.py
index 278be49..3dfa156 100755
--- a/scripts/concept_review.py
+++ b/scripts/concept_review.py
@@ -80,7 +80,7 @@ Format as structured markdown with source citations."""
             "max_tokens": 2000,
             "temperature": 0.2,
         },
-        timeout=60.0,
+        timeout=180.0,
     )
     resp.raise_for_status()
     return resp.json()["choices"][0]["message"]["content"]
@@ -105,14 +105,15 @@ PAPER:
 
 Be specific and constructive. Format as structured markdown."""
 
-    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
+    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
     resp = client.post(
         url,
+        headers={"x-goog-api-key": GEMINI_KEY},
         json={
             "contents": [{"parts": [{"text": prompt}]}],
             "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2000},
         },
-        timeout=60.0,
+        timeout=180.0,
     )
     resp.raise_for_status()
     data = resp.json()
@@ -151,7 +152,7 @@ Questions I Would Ask, and Deal-Breakers (if any).""",
             "max_tokens": 1500,
             "temperature": 0.7,
         },
-        timeout=60.0,
+        timeout=180.0,
     )
     resp.raise_for_status()
     return resp.json()["choices"][0]["message"]["content"]
@@ -202,7 +203,7 @@ Be direct and actionable. No filler.""",
                 }
             ],
         },
-        timeout=90.0,
+        timeout=180.0,
     )
     resp.raise_for_status()
     return resp.json()["content"][0]["text"]
diff --git a/scripts/daily_stats.sh b/scripts/daily_stats.sh
index e793973..2af5167 100755
--- a/scripts/daily_stats.sh
+++ b/scripts/daily_stats.sh
@@ -80,12 +80,17 @@ fi
 # === API Traffic Stats (12h) ===
 NGINX_LOG="/var/log/nginx/access.log"
 MCP_TOTAL=$(grep "/mcp" $NGINX_LOG 2>/dev/null | awk -v d="$(date -d '12 hours ago' '+%d/%b/%Y:%H')" '$4 > "["d' | wc -l)
-MCP_AUTH=$(grep "/mcp.*api_key=mt_" $NGINX_LOG 2>/dev/null | awk -v d="$(date -d '12 hours ago' '+%d/%b/%Y:%H')" '$4 > "["d' | wc -l)
+MCP_AUTH=$(grep "/mcp" $NGINX_LOG 2>/dev/null | grep "api_key=" | awk -v d="$(date -d '12 hours ago' '+%d/%b/%Y:%H')" '$4 > "["d' | wc -l)
 MCP_UNAUTH=$((MCP_TOTAL - MCP_AUTH))
 MCP_429=$(grep "/mcp" $NGINX_LOG 2>/dev/null | awk -v d="$(date -d '12 hours ago' '+%d/%b/%Y:%H')" '$4 > "["d && $9 == 429' | wc -l)
 UNIQUE_MCP_IPS=$(grep "/mcp" $NGINX_LOG 2>/dev/null | awk -v d="$(date -d '12 hours ago' '+%d/%b/%Y:%H')" '$4 > "["d {print $1}' | sort -u | wc -l)
 A2A_CALLS=$(grep 'well-known/a2a\|well-known/agent' $NGINX_LOG 2>/dev/null | awk -v d="$(date -d '12 hours ago' '+%d/%b/%Y:%H')" '$4 > "["d' | wc -l)
 
+TOP_CALLERS=$(grep "/mcp" $NGINX_LOG 2>/dev/null | \
+  awk -v d="$(date -d '12 hours ago' '+%d/%b/%Y:%H')" '$4 > "["d' | \
+  grep -o 'profile=[^& "]*' | sort | uniq -c | sort -rn | head -3 | \
+  awk '{printf "  %s: %s\n", $2, $1}')
+
 TG_MSG="$GREETING — MolTrust Stats
 
 Agents: $TOTAL_AGENTS total (+$NEW_12H last 12h)
@@ -115,6 +120,8 @@ MCP Traffic (12h):
   Rate-limited: $MCP_429
   Unique IPs: $UNIQUE_MCP_IPS
   A2A Discovery: $A2A_CALLS
+  Top profiles:
+$TOP_CALLERS
 
 Platforms:"
 
diff --git a/scripts/outreach_xmtp.js b/scripts/outreach_xmtp.js
index 410ecbc..a0e2032 100644
--- a/scripts/outreach_xmtp.js
+++ b/scripts/outreach_xmtp.js
@@ -1,23 +1,30 @@
 #!/usr/bin/env node
 /**
- * MolTrust XMTP Outreach — sends wallet trust profile links to
- * unregistered wallets with x402 payment activity.
+ * MolTrust XMTP Outreach v3 — sends wallet trust profile links to
+ * unregistered wallets with x402 payment or ERC-8004 activity.
+ *
+ * Uses XMTP V3 (node-sdk).
  *
  * Usage:
- *   node outreach_xmtp.js --dry-run    # check eligible wallets, no send
- *   node outreach_xmtp.js              # send messages
+ *   node outreach_xmtp.js --dry-run    # check eligible wallets + XMTP capability, no send
+ *   MAX_SEND=50 node outreach_xmtp.js  # send up to 50 messages
  *
- * Requires: BASE_WRITE_KEY in env (wallet private key for XMTP client)
+ * Requires: BASE_WRITE_KEY in ~/.moltrust_secrets
  */
 
-const { Client } = require("@xmtp/xmtp-js");
-const { Wallet } = require("ethers");
+const { Client, GroupPermissionsOptions } = require("@xmtp/node-sdk");
+const { createWalletClient, http } = require("viem");
+const { privateKeyToAccount } = require("viem/accounts");
+const { base } = require("viem/chains");
 const { Pool } = require("pg");
+const { toBytes } = require("viem");
 const fs = require("fs");
 const path = require("path");
+const crypto = require("crypto");
 
 const DRY_RUN = process.argv.includes("--dry-run");
 const MIN_TX = parseInt(process.env.MIN_TX || "1", 10);
+const MAX_SEND = parseInt(process.env.MAX_SEND || "50", 10);
 
 // Load secrets
 function loadSecret(name) {
@@ -37,12 +44,17 @@ if (!PRIVATE_KEY) {
   process.exit(1);
 }
 
+const DB_PW = loadSecret("MOLTSTACK_DB_PW");
 const pool = new Pool({
-  connectionString: "postgresql://moltstack@localhost/moltstack",
+  host: "localhost",
+  database: "moltstack",
+  user: "moltstack",
+  password: DB_PW,
   max: 3,
 });
 
 function buildMessage(address, txCount, totalUsdc, source) {
+  const optOut = "\n\nReply STOP to opt out. We will never message you again.";
   if (source === "erc8004") {
     return [
       `You are registered as ERC-8004 Agent #${txCount}.`,
@@ -54,7 +66,7 @@ function buildMessage(address, txCount, totalUsdc, source) {
       "",
       "The MolTrust Team",
       "https://moltrust.ch",
-    ].join("\n");
+    ].join("\n") + optOut;
   }
   return [
     `Your wallet has ${txCount} verified x402 transaction${txCount > 1 ? "s" : ""} on Base L2`,
@@ -67,7 +79,7 @@ function buildMessage(address, txCount, totalUsdc, source) {
     "",
     "The MolTrust Team",
     "https://moltrust.ch",
-  ].join("\n");
+  ].join("\n") + optOut;
 }
 
 async function getEligibleWallets() {
@@ -118,10 +130,53 @@ async function recordOutreach(wallet, xmtpCapable, messageId) {
   );
 }
 
+/**
+ * Create XMTP V3 client from an Ethereum private key.
+ */
+async function createXmtpClient() {
+  const { IdentifierKind } = require("@xmtp/node-sdk");
+  const key = PRIVATE_KEY.startsWith("0x") ? PRIVATE_KEY : "0x" + PRIVATE_KEY;
+  const account = privateKeyToAccount(key);
+
+  // XMTP V3 signer: getIdentifier() + signMessage()
+  const signer = {
+    type: "EOA",
+    getIdentifier: () => ({
+      identifier: account.address.toLowerCase(),
+      identifierKind: 0,  // IdentifierKind.Ethereum = 0
+    }),
+    signMessage: async (message) => {
+      try {
+        const msg = typeof message === "string" ? message : new TextDecoder().decode(message);
+        console.log(`  [XMTP] Signing message (${msg.length} chars)...`);
+        const sig = await account.signMessage({ message: msg });
+        console.log(`  [XMTP] Signed OK (${sig.length} chars)`);
+        return toBytes(sig);
+      } catch (err) {
+        console.error(`  [XMTP] Sign error: ${err.message}`);
+        throw err;
+      }
+    },
+  };
+
+  // Generate a stable encryption key from the private key
+  const encryptionKey = crypto.createHash("sha256")
+    .update(key)
+    .digest();
+
+  // V3: create client (auto-registers if new inbox)
+  const client = await Client.create(signer, encryptionKey, {
+    env: "production",
+  });
+
+  return client;
+}
+
 async function main() {
-  console.log(`\n=== MolTrust XMTP Outreach ===`);
+  console.log(`\n=== MolTrust XMTP Outreach v3 ===`);
   console.log(`Mode: ${DRY_RUN ? "DRY RUN" : "LIVE"}`);
-  console.log(`Min TX threshold: ${MIN_TX}\n`);
+  console.log(`Min TX threshold: ${MIN_TX}`);
+  console.log(`Max send: ${MAX_SEND}\n`);
 
   // Get eligible wallets
   const wallets = await getEligibleWallets();
@@ -133,63 +188,71 @@ async function main() {
     return;
   }
 
-  for (const w of wallets) {
+  // Deduplicate wallets (same wallet may appear multiple times from erc8004)
+  const seen = new Set();
+  const uniqueWallets = wallets.filter(w => {
+    const key = w.wallet.toLowerCase();
+    if (seen.has(key)) return false;
+    seen.add(key);
+    return true;
+  });
+  console.log(`Unique wallets: ${uniqueWallets.length}`);
+
+  for (const w of uniqueWallets.slice(0, 10)) {
     console.log(`  ${w.wallet}  tx=${w.tx_count}  usdc=${parseFloat(w.total_usdc).toFixed(2)}  src=${w.source || "payment"}`);
   }
+  if (uniqueWallets.length > 10) console.log(`  ... and ${uniqueWallets.length - 10} more`);
 
-  // Initialize XMTP client
-  const wallet = new Wallet(PRIVATE_KEY);
-  console.log(`\nXMTP sender: ${wallet.address}`);
-
+  // Initialize XMTP V3 client
+  console.log(`\nInitializing XMTP V3 client...`);
   let xmtpClient;
-  if (!DRY_RUN) {
-    try {
-      xmtpClient = await Client.create(wallet, { env: "production" });
-      console.log("XMTP client initialized (production)\n");
-    } catch (err) {
-      console.error("XMTP init failed:", err.message);
-      await pool.end();
-      process.exit(1);
-    }
+  try {
+    xmtpClient = await createXmtpClient();
+    console.log(`XMTP V3 client ready (production)`);
+    console.log(`Sender address: ${xmtpClient.accountAddress || "unknown"}\n`);
+  } catch (err) {
+    console.error("XMTP V3 init failed:", err.message);
+    await pool.end();
+    process.exit(1);
   }
 
-  // Process each wallet
-  let sent = 0, notCapable = 0, errors = 0;
+  // Check XMTP capability for all wallets
+  let sent = 0, notCapable = 0, errors = 0, checked = 0;
+
+  for (const w of uniqueWallets) {
+    if (sent >= MAX_SEND) {
+      console.log(`  [LIMIT] MAX_SEND=${MAX_SEND} reached, stopping.`);
+      break;
+    }
 
-  for (const w of wallets) {
     const addr = w.wallet;
+    checked++;
     try {
-      if (DRY_RUN) {
-        // In dry run, just check XMTP capability
-        try {
-          const tempClient = await Client.create(wallet, { env: "production" });
-          const canMsg = await tempClient.canMessage(addr);
-          console.log(`  [DRY] ${addr}: XMTP=${canMsg ? "YES" : "NO"}  tx=${w.tx_count}`);
-          if (!canMsg) notCapable++;
-          await tempClient.close();
-        } catch {
-          console.log(`  [DRY] ${addr}: XMTP=UNKNOWN (client error)  tx=${w.tx_count}`);
-        }
-        continue;
-      }
+      // V3: canMessage accepts an array of Identifier objects
+      const identifier = { identifier: addr.toLowerCase(), identifierKind: 0 };
+      const canMsgResult = await xmtpClient.canMessage([identifier]);
+      const canMsg = canMsgResult && (canMsgResult.get ? canMsgResult.values().next().value : Object.values(canMsgResult)[0]);
 
-      // Check if wallet can receive XMTP
-      const canMsg = await xmtpClient.canMessage(addr);
       if (!canMsg) {
         console.log(`  [SKIP] ${addr}: not XMTP-capable`);
-        await recordOutreach(addr, false, null);
+        if (!DRY_RUN) await recordOutreach(addr, false, null);
         notCapable++;
         continue;
       }
 
-      // Send message
+      if (DRY_RUN) {
+        console.log(`  [DRY] ${addr}: XMTP=YES  tx=${w.tx_count}  src=${w.source}`);
+        continue;
+      }
+
+      // Send message via V3 DM conversation
       const msg = buildMessage(addr, w.tx_count, parseFloat(w.total_usdc), w.source || "payment");
-      const conversation = await xmtpClient.conversations.newConversation(addr);
-      const sentMsg = await conversation.send(msg);
+      const conversation = await xmtpClient.conversations.newDm(identifier);
+      await conversation.send(msg);
 
-      await recordOutreach(addr, true, sentMsg.id || "sent");
+      await recordOutreach(addr, true, conversation.id || "sent");
       sent++;
-      console.log(`  [SENT] ${addr}  tx=${w.tx_count}  msgId=${sentMsg.id || "ok"}`);
+      console.log(`  [SENT] ${addr}  tx=${w.tx_count}  src=${w.source}`);
 
       // Rate limit: 2 second delay between messages
       await new Promise(r => setTimeout(r, 2000));
@@ -201,12 +264,14 @@ async function main() {
 
   console.log(`\n=== Report ===`);
   console.log(`Eligible:      ${wallets.length}`);
+  console.log(`Unique:        ${uniqueWallets.length}`);
+  console.log(`Checked:       ${checked}`);
+  console.log(`Max send:      ${MAX_SEND}`);
   console.log(`Sent:          ${sent}`);
   console.log(`Not XMTP:      ${notCapable}`);
   console.log(`Errors:        ${errors}`);
   console.log(`Mode:          ${DRY_RUN ? "DRY RUN" : "LIVE"}`);
 
-  if (xmtpClient) await xmtpClient.close();
   await pool.end();
 }
 
```

---

## 3. Sprint migration files (verbatim)

### 3a. `migrations/2026-05-11_auto_probe.sql`

```sql
-- Auto-Probe-Token: zero-friction onboarding tables.
-- Per spec: docs/auto-probe-token-spec.md §4.1, §9, §13.
--
-- Three new tables, no changes to existing tables in this migration.
-- Companion migration (2026-05-11_agents_probe_parent.sql) adds parent_probe_did
-- to agents and is run after this one.

BEGIN;

-- probe_agents: ephemeral DIDs auto-minted on keyless MCP connections.
-- Kept separate from `agents` so they cannot leak into trust graph queries.
CREATE TABLE IF NOT EXISTS probe_agents (
    did                    text PRIMARY KEY,
    probe_key_hash         text NOT NULL UNIQUE,
    created_at             timestamptz NOT NULL DEFAULT now(),
    expires_at             timestamptz NOT NULL,
    call_count             int NOT NULL DEFAULT 0,
    call_cap               int NOT NULL DEFAULT 50,
    ttl_extensions         int NOT NULL DEFAULT 0,
    first_seen_ip          inet,
    first_seen_ua          text,
    smithery_session_hash  text,
    claimed_at             timestamptz,
    claimed_did            text,
    claimed_email_hash     text,
    CONSTRAINT probe_did_format CHECK (did ~ '^did:moltrust:probe:[0-9a-f]{8}$'),
    CONSTRAINT probe_call_cap_positive CHECK (call_cap > 0),
    CONSTRAINT probe_ttl_extensions_bounded CHECK (ttl_extensions BETWEEN 0 AND 2)
);

CREATE INDEX IF NOT EXISTS idx_probe_active
    ON probe_agents (expires_at)
    WHERE claimed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_probe_ip_recent
    ON probe_agents (first_seen_ip, created_at);

CREATE INDEX IF NOT EXISTS idx_probe_smithery_session
    ON probe_agents (smithery_session_hash)
    WHERE smithery_session_hash IS NOT NULL;

-- probe_activity: per-probe tool call log. Args are redacted of PII before write.
-- Auto-GC drops this alongside the parent probe row.
CREATE TABLE IF NOT EXISTS probe_activity (
    id              bigserial PRIMARY KEY,
    probe_did       text NOT NULL REFERENCES probe_agents(did) ON DELETE CASCADE,
    tool_name       text NOT NULL,
    args_redacted   jsonb,
    result_summary  text,
    at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_probe_act_did ON probe_activity (probe_did, at DESC);
CREATE INDEX IF NOT EXISTS idx_probe_act_tool ON probe_activity (tool_name, at DESC);

-- conversion_funnel: analytics row per probe, lifecycle state + cross-vertical breadth.
-- Survives claim (claim_state flips), GC'd with parent probe row.
CREATE TABLE IF NOT EXISTS conversion_funnel (
    probe_did          text PRIMARY KEY REFERENCES probe_agents(did) ON DELETE CASCADE,
    source             text,
    first_tool         text,
    tool_count         int NOT NULL DEFAULT 0,
    unique_tools       int NOT NULL DEFAULT 0,
    verticals_touched  int NOT NULL DEFAULT 0,
    claim_state        text NOT NULL DEFAULT 'unclaimed',
    claimed_at         timestamptz,
    CONSTRAINT funnel_claim_state_valid CHECK (
        claim_state IN ('unclaimed', 'claimed', 'anonymous-claimed', 'expired')
    )
);

CREATE INDEX IF NOT EXISTS idx_funnel_source     ON conversion_funnel (source);
CREATE INDEX IF NOT EXISTS idx_funnel_state      ON conversion_funnel (claim_state);
CREATE INDEX IF NOT EXISTS idx_funnel_claimed_at ON conversion_funnel (claimed_at) WHERE claimed_at IS NOT NULL;

COMMIT;
```

### 3b. `migrations/2026-05-11_agents_probe_parent.sql`

```sql
-- agents.parent_probe_did: link sub-agents back to their parent probe.
-- Per spec §6.2 (moltrust_register from a probe creates a probe-scoped child).
-- On claim, rows referencing the parent probe are rewritten as legitimate
-- agents bound to the claimed parent DID.

BEGIN;

ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS parent_probe_did text REFERENCES probe_agents(did) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_agents_parent_probe
    ON agents (parent_probe_did)
    WHERE parent_probe_did IS NOT NULL;

-- api_keys.tier already exists; extend the implicit value-set with
-- 'anonymous_claimed' for probe-claims that did not provide an email.
-- No DDL needed (tier is plain text), this comment is the audit trail.

COMMIT;
```

---

## 4. `services/mcp_http.py` (legacy MCP standalone)

### 4a. Diff vs `origin/main`

`git diff --name-status origin/main..feature/auto-probe-token -- services/mcp_http.py`

```
M	services/mcp_http.py
```

### 4b. Full file content (52 lines)

```python
#!/usr/bin/env python3
"""MolTrust MCP Server — HTTP Streamable Transport.

DEPRECATED standalone process. The same MCP server is now mounted as an
ASGI sub-app under the main FastAPI app at app/main.py. The mount puts
identity resolution and the dispatch-level auth gate on the same code
path as the REST API, removing the prior auth bypass where /mcp ran
outside the FastAPI middleware stack.

Removal plan: at Phase 8 deploy, nginx /mcp proxy_pass switches from
127.0.0.1:8002 to :8000, and moltrust-mcp-http.service is stopped and
disabled. This file is kept until that cutover so the existing systemd
unit keeps working during transition.
"""

import os
import sys

# Use local REST API to avoid round-tripping through nginx
os.environ.setdefault("MOLTRUST_API_URL", "http://127.0.0.1:8000")

from moltrust_mcp_server.server import mcp  # noqa: E402
from mcp.server.transport_security import TransportSecuritySettings  # noqa: E402

# Register MoltGuard tools and Auto-Probe identity tool
sys.path.insert(0, os.path.dirname(__file__))
from moltguard_mcp_tools import register_moltguard_tools  # noqa: E402
from probe_mcp_tools import register_probe_tools  # noqa: E402
register_moltguard_tools(mcp)
register_probe_tools(mcp)

# Override settings for HTTP deployment behind nginx
mcp.settings.host = "127.0.0.1"
mcp.settings.port = 8002
mcp.settings.streamable_http_path = "/mcp"

# Allow nginx-proxied requests (default DNS rebinding protection
# only allows localhost origins, but nginx sends Host: api.moltrust.ch)
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=["127.0.0.1:*", "localhost:*", "api.moltrust.ch"],
    allowed_origins=[
        "http://127.0.0.1:*",
        "http://localhost:*",
        "https://api.moltrust.ch",
        "https://smithery.ai",
        "https://server.smithery.ai",
    ],
)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### 4c. `grep -n "IdentityMiddleware|McpAuthMiddleware|resolve_identity" services/mcp_http.py`

```
(no matches)
```

---

## 5. `app/main.py` — middleware registration context

### 5a. Sprint-specific imports of `app.identity` + `app.mcp_auth_middleware`

```
559:from app.identity import (
582:from app.mcp_auth_middleware import McpAuthMiddleware  # noqa: E402
680:from app.identity import build_claim_value_pitch as _build_claim_pitch
681:from app.identity import get_probe_summary as _get_probe_summary
728:from app.identity import claim_probe as _claim_probe, ClaimError as _ClaimError
```

### 5b. Lines 555-605 (middleware registration block, widened by 5 each side for full context)

```python
 555: # moltrust_identity MCP tool — never as a response header. Header surfacing
 556: # was removed per H11 of the AI security review because Nginx, Sentry, and
 557: # any monitoring stack that captures response headers would have logged the
 558: # key in plaintext. Per docs/auto-probe-token-spec.md §4.2 / §4.4 / §10.2.
 559: from app.identity import (
 560:     resolve_identity as _resolve_identity,
 561:     increment_probe_call_count as _inc_probe_calls,
 562:     maybe_extend_probe_ttl as _maybe_extend_ttl,
 563:     AuthError as _IdentityAuthError,
 564:     Identity,
 565:     require_claimed,
 566:     require_probe,
 567:     detect_source as _detect_source,
 568:     record_probe_spawn as _record_probe_spawn,
 569:     record_probe_activity as _record_probe_activity,
 570: )
 571: 
 572: _IDENTITY_SKIP_PATHS = {"/", "/health", "/openapi.json", "/favicon.ico"}
 573: _IDENTITY_SKIP_PREFIXES = ("/docs", "/static/", "/auth/claim")
 574: 
 575: 
 576: # --- MCP dispatch-level auth gate ---
 577: # FastAPI's add_middleware inserts at user_middleware[0], so the LAST
 578: # middleware added is OUTERMOST (fires first on request). Wiring this
 579: # BEFORE the identity_middleware decorator below puts McpAuthMiddleware
 580: # DEEPER in the stack at build time — identity_middleware runs first,
 581: # sets request.state.identity, then this gate inspects /mcp tools/call.
 582: from app.mcp_auth_middleware import McpAuthMiddleware  # noqa: E402
 583: app.add_middleware(McpAuthMiddleware)
 584: 
 585: 
 586: @app.middleware("http")
 587: async def identity_middleware(request: Request, call_next):
 588:     path = request.url.path
 589:     if (
 590:         request.method == "OPTIONS"
 591:         or path in _IDENTITY_SKIP_PATHS
 592:         or any(path.startswith(p) for p in _IDENTITY_SKIP_PREFIXES)
 593:     ):
 594:         return await call_next(request)
 595:     if not db_pool:
 596:         return await call_next(request)
 597:     try:
 598:         async with db_pool.acquire() as conn:
 599:             identity = await _resolve_identity(request, conn)
 600:             # Record the spawn-attribution row before the request runs so a
 601:             # crashed handler still leaves an analytics trail of where this
 602:             # probe came in.
 603:             if identity.kind == "probe-new":
 604:                 source = _detect_source(
 605:                     request.headers.get("user-agent"),
```

---

## Notes

- All commands run as user `moltstack` on host `ubuntu-4gb-nbg1-1` (`api.moltrust.ch`).
- No `git checkout`, no `git reset`, no service restart, no nginx reload, no DB write executed during data gathering.
- `git fetch --all` was the only network/ref-updating command; it does not touch the working tree.
- Bundle file path on server: `audits/2026-05-12_gpt5-verification-bundle.md` (chmod 644).
- Companion file: `audits/2026-05-12_static-analysis.md` (the original inventory GPT-5 reviewed).

*End of verification bundle.*
