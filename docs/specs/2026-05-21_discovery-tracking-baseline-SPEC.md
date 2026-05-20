# Spec — Discovery-Tracking-Baseline (P1, WORKFLOW §3.3)

**Status:** ENTWURF — Lars-Freigabe vor Code.
**§2.3-Cross-Review:** **Skip empfohlen** — read-only Tracking, kein Auth-/Credential-/Token-Pfad, kein neuer Daten-Egress. Re-evaluate falls Implementation in P3 unerwartet einen API-Key gegen externe Dienste mountet (GSC-OAuth, GitHub-PAT — siehe §9.2).
**Datum:** 2026-05-21 · **Repo:** moltrust-api · **Branch:** docs/discovery-tracking-baseline-spec
**Vorausgegangener Sprint:** moltguard-Remote-Migration (PR #52 SPEC merged 2026-05-20, #53 BACKLOG-Sync merged 2026-05-20). Discovery-Trio (P2-P4) live seit 2026-05-20.

## 1. Goal

Tägliches Discovery-Tracking-Dashboard für Lars, das zeigt **ob die Discovery-Investments der letzten Sprints wirken**: indexierte URLs in GSC, Bot-Hits pro Crawler/Agent, GitHub-Engagement, Live-Probe-Pass-Rate. Optimiert auf **„Lars schaut täglich kurz drauf"**, nicht Investor-Pitch.

Antwort auf konkrete Fragen wie:
- Findet GPTBot/ClaudeBot/PerplexityBot die neuen MoltGuard-OpenAPI-Surfaces?
- Wächst GSC-Impressions auf den Blog-Posts/Whitepapers?
- Gibt es Stars/Clones auf `MoltyCel/moltguard` seit Public-Toggle?
- Sind die Discovery-Surfaces (sitemap.xml, llms.txt, /guard/openapi.json, /extendedAgentCard) heute noch live, oder still gefallen?

## 2. Non-Goals

- **Kein** Realtime-Monitoring (täglicher Snapshot reicht, Alerts nur bei Hard-Down → Healthcheck-Subscope).
- **Kein** SEO-Detail-Analysis (Keyword-Position-Trends, Query-Optimization, Backlink-Audit). Hier nur Aggregate.
- **Kein** User-PII-Tracking. Bot-Hits sind aggregierte User-Agent-Counts, keine individuellen Sessions.
- **Kein** Investor-Pitch-Dashboard (Visualisierung optimiert auf Lars' tägliche 30-Sek-Sichtung, nicht externe Show).
- **Kein** Reverse-Engineering der Konsumenten-Identität hinter Bot-Hits (Bot-IP-Source-Lookup für statistische Zwecke ist OK; per-Caller-Profiling nicht).

## 3. Architecture-Layer-Scope *(Pflichtfeld)*

### 3.1 Metriken — Source-of-Truth pro Metrik

| Metrik | Quelle | Frequenz | Aufwand V1 | Privacy |
|---|---|---|---|---|
| **GSC: indexierte URLs, Impressions, Klicks, Crawl-Frequenz** | Google Search Console API (Webmasters API v3) | täglich snapshot last 7 days | M — OAuth-Setup mit Service-Account ODER manual paste-in als V0 | aggregat, kein PII |
| **nginx-Bot-Hits per User-Agent + Endpoint-Klasse** (api.moltrust.ch FastAPI) | DB-Tabelle `request_log` (existiert, DSGVO-anonym, columns: ts, endpoint, method, status_code, user_agent, ip(anonym)) | daily aggregation cron, group by UA+endpoint-class | S — query auf existing table | DSGVO-konform (existing) |
| **nginx-Bot-Hits per User-Agent + Endpoint-Klasse** (moltrust.ch static + /guard proxy) | nginx access log `/var/log/nginx/access.log` | daily parse + grep + group | M — neues parsing-script + DSGVO-Anonymisierung auf last-octet ODER nur User-Agent-Counts (keine IPs persistieren) | requires explicit anonymization step in parser |
| **GitHub Stars/Forks/Watchers** | `gh api /repos/MoltyCel/<repo>` für moltrust-api, moltrust-web, moltguard, moltrust-mcp-server, moltrust-x402, moltrust-openclaw | täglich snapshot | S — single REST call pro repo | public-Daten |
| **GitHub Clones + Views (last 14 days)** | `gh api /repos/MoltyCel/<repo>/traffic/clones` und `/views` | täglich snapshot | S — REST-Call mit auth-token (PAT) | public-Daten (nur owner-sichtbar via API) |
| **Self-Probes (Discovery-Surface Health)** | curl mit erwarteten Inhalts-Checks: `sitemap.xml` lautet 93 URLs, `llms.txt` enthält MoltGuard-Block, `/guard/openapi.json` returns 200 mit 67 paths, `/extendedAgentCard` mit DID-Auth zeigt 2 MoltGuard-Extensions | täglich + Alert-bei-Regression | S — bash-Script analog zu Deploy-Verify-Pattern | aggregat-pass/fail, kein PII |
| **Optional: Google Alerts auf „MolTrust"/„moltguard"/„MoltyCel"** | Google Alerts (Lars-Setup), email-delivered | nicht-API, manuelles Tracking | n/a — out-of-scope für Dashboard | n/a |

### 3.2 Endpoint-Klassen für die nginx-Bot-Aggregation

Pro Bot-User-Agent wollen wir Hits pro **Endpoint-Klasse** sehen, nicht pro Pfad einzeln. Vorgeschlagene Klassen:

| Class | Pattern | Beispiele |
|---|---|---|
| `web/blog` | `^/blog/` | /blog/aws-agent-…, /blog/moltid-… |
| `web/publications` | `^/publications/`, `\.pdf$` (root-level) | /publications/, /MolTrust_KYA_Whitepaper.pdf |
| `web/static-page` | `\.html$` ohne /blog/ | /developers.html, /hackathon.html, /skills.html |
| `web/root` | `^/$` | / |
| `web/discovery-surface` | `sitemap.xml`, `llms.txt`, `robots.txt`, `/.well-known/` | sitemap.xml, llms.txt, /.well-known/agent-card.json |
| `api/guard` | `^/guard/` | /guard/openapi.json, /guard/api/info, /guard/health |
| `api/identity` | `^/identity/`, `^/skill/`, `^/swarm/` | … (FastAPI-routes) |
| `api/discovery-surface` | `api.moltrust.ch/openapi.json`, `/llms.txt`, `/extendedAgentCard`, `/.well-known/` | … |
| `api/other` | catch-all für non-classified API paths | |

### 3.3 Bot-User-Agents — Explicit Allowlist für Aggregation

Catalog (V1):

```
GPTBot, ChatGPT-User, ClaudeBot, anthropic-ai, PerplexityBot, Perplexity-User,
Google-Extended (Google-AI), Bytespider (TikTok/ByteDance), Applebot-Extended,
GoogleBot, GoogleBot-Image, GoogleBot-Mobile,
Bingbot, BingPreview,
DuckDuckBot, YandexBot, BaiduSpider, FacebookExternalHit,
Twitterbot, LinkedInBot, Slackbot, TelegramBot,
Other-Crawlers (catch-all per regex "bot|spider|crawler" — non-allowlisted)
```

UAs außerhalb der Allowlist + nicht-bot-pattern werden NICHT als „Bot-Hit" gezählt — die landen in einer separaten Bucket „human/agent" (für sich, V2-Subscope).

### 3.4 WO TRACKEN — Recommendation

**Empfehlung: (a) Neuer Block auf existierendem `moltrust.ch/admin`-Dashboard.**

Begründung:
- Admin-Dashboard existiert: 14 `/admin/dashboard/*`-Endpoints live (`overview`, `agents`, `activity`, `security`, `x402`, `journal`, `callers`, `traffic`, …), Auth via `app/admin_auth.py` + RBAC via `app/admin_rbac.py`.
- Bestehende Frontend-Struktur (HTML/JSON-API-Pattern) → niedriger Implementation-Aufwand für P3.
- Lars hat bestehende Routine, Admin-Dashboard zu sichten. Discovery-Block dort = höchste Wahrscheinlichkeit täglicher Konsumtion.
- Eigenes Tool (Option c) wäre Doppelarbeit. Eigene Page `/admin/discovery` (Option b) hätte ähnlichen Aufwand wie integrierter Block ohne Vorteil.

Konkret: ein neuer Tab/Block **`Discovery`** unter `/admin/dashboard/discovery` (analog zu `/admin/dashboard/x402`), mit Sub-Sections:
- Self-Probe-Status (live HEAD)
- GSC-Snapshot (last 7 days)
- Bot-Hits (last 7 days, grouped by UA × endpoint-class)
- GitHub-Engagement (last 14 days delta für Clones/Views)

### 3.5 Aggregations-Frequenz + Storage

**Frequenz:** **täglicher Snapshot um 00:30 UTC** (nach täglichem Backup-Window 03:00 UTC vermeiden → 00:30 reicht und vermeidet Cron-Konflikt).

**Storage:** **PostgreSQL `moltstack` DB**, neue Tabelle `discovery_snapshots`:

```sql
CREATE TABLE discovery_snapshots (
  id          BIGSERIAL PRIMARY KEY,
  snapshot_at DATE NOT NULL UNIQUE,            -- one row per day
  generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  payload     JSONB NOT NULL,                  -- full snapshot content (flexible schema)
  source_run_status TEXT NOT NULL DEFAULT 'ok' -- 'ok' | 'partial' | 'failed'
);

CREATE INDEX idx_discovery_snapshots_at ON discovery_snapshots(snapshot_at DESC);
```

`payload` JSONB-Shape (Vorschlag):

```json
{
  "self_probes": {
    "sitemap.xml": {"status": 200, "url_count": 93, "byte_count": 17088},
    "llms.txt": {"status": 200, "has_moltguard_block": true, "byte_count": 10297},
    "guard_openapi": {"status": 200, "path_count": 67, "byte_count": 53018},
    "extendedAgentCard": {"status": 200, "moltguard_extensions_present": ["moltguard/v1","x402-pricing/v1"]}
  },
  "gsc": {
    "fetch_status": "ok|manual|failed",
    "last_7d": {"impressions": 0, "clicks": 0, "indexed_urls": 0, "ctr": 0.0, "avg_position": 0.0}
  },
  "bot_hits": {
    "GPTBot": {"web/blog": 0, "api/guard": 0, ...},
    "ClaudeBot": {...},
    ...
  },
  "github": {
    "MoltyCel/moltguard": {"stars": 0, "forks": 0, "clones_last_14d": 0, "views_last_14d": 0},
    "MoltyCel/moltrust-api": {...},
    "MoltyCel/moltrust-web": {...}
  },
  "errors": []  // collected non-fatal errors from each source
}
```

Schema-flexibilität via JSONB: V1-Felder können sich erweitern ohne ALTER TABLE.

### 3.6 BASELINE-SNAPSHOT-Phase (P2 — heute Abend)

**Pflicht** vor Dashboard-Implementation: einmal heute (2026-05-21) abends manuell alle Metriken einsammeln + als Zeile-0 in `discovery_snapshots` einfügen. Ohne diesen Baseline-Punkt ist „Delta morgen vs heute" nicht messbar.

Konkrete Sub-Steps für P2:
1. **Self-Probes** ausführen — bash-Script `scripts/discovery_probe.sh` (Phase-2-Implementation-Subset)
2. **GSC manuell** — Lars logged sich in GSC ein, Snapshot „last 7 days" als JSON-Block (V0: paste-in via SQL INSERT; V2: API)
3. **Bot-Hits last 7 days** aus `request_log` querieren + nginx-Logs parsen (für moltrust.ch static)
4. **GitHub** via `gh api` für 6 Repos
5. INSERT in `discovery_snapshots` als snapshot_at='2026-05-21'

Erwartet Aufwand P2: ~1h.

### 3.7 PRIVACY — Disziplin-Check

**§DSGVO-Compliance-Verifikation für jede neue Source:**

| Source | DSGVO-Status | Maßnahme |
|---|---|---|
| `request_log` (FastAPI) | ✓ schon DSGVO-konform | last octet zeroed (verified in `app/middleware/request_logger`-Pattern) |
| `requestLogger` (moltguard Hono) | ✓ DSGVO-konform | last octet zeroed (verified in `~/moltguard/src/middleware/requestLogger.ts` — Commit `9592b22`) |
| nginx `/var/log/nginx/access.log` | ⚠️ **roh-IPs** | Parser muss **bei Lese-Zeit anonymisieren** (last octet zeroed), keine roh-IPs ins `payload`-JSONB persistieren |
| GSC, GitHub API | aggregate, keine User-PII | n/a |

**Verstärkung:** Discovery-Metriken aggregieren ausschließlich auf `(user_agent, endpoint_class, date)`-Granularität. Keine IPs (auch nicht anonyme) in `discovery_snapshots.payload` persistieren. Falls jemals per-IP-Granularität nötig → eigener SPEC + Cross-Review.

Memory-Cross-Check (§21 user-instruction): `moltrust.ch/admin` hat schon DSGVO-Anonymisierung — wir docken an dieser etablierten Schicht an, ohne sie zu unterlaufen.

### 3.8 EXISTING TOOLING — was schon da ist, was nicht

| Asset | Status | Reuse für Discovery? |
|---|---|---|
| `/admin/dashboard/*` 14 Endpoints | live | ✓ neuer `/admin/dashboard/discovery`-Endpoint dort einhängen |
| `app/admin_auth.py` + `app/admin_rbac.py` | live | ✓ Discovery-Endpoint nutzt selbe Auth-Dependency |
| DB-Tabelle `request_log` (DSGVO-anonym) | live, populated | ✓ Source für api.moltrust.ch-Bot-Hits |
| DB-Tabelle `caller_labels`, `known_callers` | live | optional — V2-Erweiterung „bekannte Bot-IPs labellen" |
| `/admin/dashboard/traffic` (existing) | live | Komplement, nicht ersetzt — Discovery ist eigener Block |
| nginx access.log parser | **fehlt** | NEU in P2/P3 |
| GSC-OAuth-Setup | **fehlt** | V0 manual paste, V2 API-Integration (§9.2) |
| GitHub-PAT für Traffic-API | wahrscheinlich da (gh-CLI auf Server fehlt — siehe moltguard-Migration P6, deploy-key existiert für moltguard) | benötigt evtl. neuen PAT für read-only Traffic-API auf MoltyCel-org |

**Zentrale Erkenntnis:** sehr viel Infrastruktur existiert. Die Discovery-Lücke ist:
1. Keine zusammenfassende „Discovery"-Sicht (alle Quellen aggregiert)
2. Kein nginx-Log-Parsing (moltrust.ch static + /guard-proxy)
3. Kein automated GSC-Snapshot
4. Kein automated GitHub-Traffic-Snapshot
5. Keine `discovery_snapshots`-Tabelle für Zeitreihen

## 4. Data-Model-Changes

Eine neue Tabelle, kein bestehendes Schema berührt:

```sql
CREATE TABLE discovery_snapshots (
  id          BIGSERIAL PRIMARY KEY,
  snapshot_at DATE NOT NULL UNIQUE,
  generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  payload     JSONB NOT NULL,
  source_run_status TEXT NOT NULL DEFAULT 'ok'
    CHECK (source_run_status IN ('ok','partial','failed'))
);

CREATE INDEX idx_discovery_snapshots_at ON discovery_snapshots(snapshot_at DESC);
```

Migration via `migrations/`-Pfad (existing pattern). One-time-INSERT für 2026-05-21-Baseline in P2.

## 5. API-Contract-Changes

Ein neuer Admin-Endpoint, eine neue Cron-Job:

### 5.1 `GET /admin/dashboard/discovery`

Auth: admin-RBAC (selbe Pattern wie andere `/admin/dashboard/*`).
Response: latest `discovery_snapshots`-Row plus delta-vs-vorgestrigem (für „heute vs gestern"-Lesart).

```json
{
  "latest": { ... full payload ... },
  "snapshot_at": "2026-05-21",
  "delta_vs_previous": {
    "github.MoltyCel/moltguard.stars": 0,
    "bot_hits.GPTBot.api/guard": 5,
    ...
  }
}
```

Optional `?range=7d` query-param für 7-day-Reihe (V2).

### 5.2 Cron `0 30 * * *` — `scripts/discovery_snapshot.py`

Läuft 00:30 UTC täglich. Sammelt alle 5 Quellen ein, INSERTet eine Zeile in `discovery_snapshots`. Bei partial-failure: `source_run_status='partial'` + `errors[]` im payload. Bei total-failure: `'failed'` + Telegram-Alert via existing `~/.moltrust_secrets` `TELEGRAM_BOT_TOKEN`.

## 6. Migration-Path (Phasen)

| Phase | Inhalt | Aufwand |
|---|---|---|
| **P1 (diese SPEC)** | Architektur-Briefing, keine DB-/Code-Changes | — |
| **P2 (heute Abend)** | (a) Migration `migrations/2026-05-21_create_discovery_snapshots.sql` erstellen + apply · (b) Baseline-Snapshot 2026-05-21 manuell einsammeln (self-probes + GSC manual + bot-hits-query + GitHub) · (c) INSERT als snapshot_at='2026-05-21' | ~1h |
| **P3** | Implementation: `scripts/discovery_snapshot.py` (cron-script) · `app/admin_discovery.py` (router) · `/admin/dashboard/discovery`-Endpoint · cron-eintrag · Frontend-Block | ~3h |
| **P4 (optional, separat)** | GSC-API-Integration (OAuth + automated daily fetch) — replaces V0 manual GSC paste | ~2h |

**P2 ist Pflicht heute** (sonst „Delta morgen vs heute" nicht messbar — siehe §3.6). P3 + P4 können nachgelagert.

## 7. Rollback-Plan

| Phase | Rollback |
|---|---|
| P2 DB-Migration | `DROP TABLE discovery_snapshots` — trivial, keine Konsumenten ausserhalb P3 |
| P2 Baseline-Snapshot | DELETE row WHERE snapshot_at='2026-05-21' — trivial |
| P3 Script + Endpoint | Remove cron entry + delete `scripts/discovery_snapshot.py` + remove `/admin/dashboard/discovery`-route. Daten in `discovery_snapshots` bleiben für nachträgliche Inspektion erhalten. |

## 8. Success-Criteria

1. **`discovery_snapshots`-Tabelle existiert** mit Baseline-Row für 2026-05-21 (P2 done).
2. **Cron-Job läuft 00:30 UTC täglich** und INSERTet eine Zeile mit `source_run_status='ok'` (P3 done).
3. **`/admin/dashboard/discovery`** liefert latest + delta-vs-previous in <500ms (P3 done).
4. **Lars schaut mind. 4 von 7 Tagen pro Woche kurz drauf** (Verhaltens-Akzeptanz; selbst-reported).
5. **Bei Discovery-Surface-Regression** (z.B. `/guard/openapi.json` returned 5xx) loggt der nächste daily-Snapshot `source_run_status='partial'` + Telegram-Alert.

## 9. Open Decisions (für Lars vor P2-Start zu klären)

- **9.1 GSC-Integration V1 — manual paste oder API?**
  - V0 (manual): Lars paste'd weekly aus GSC-UI in ein JSON-Block, einfaches `INSERT … ON CONFLICT DO UPDATE`. Niedrigster Aufwand.
  - V1 (API): Google OAuth + Service-Account + Webmasters-API v3. Setup-Aufwand ~2h, einmalig.
  - Empfehlung: **V0 in P2, V1 in P4** (separater Sprint nach Discovery-Dashboard läuft). Aufwand-zu-Nutzen-Verhältnis: API-Setup nur sinnvoll wenn Lars das Discovery-Dashboard tatsächlich täglich konsumiert (Success-Criterion #4 muss erfüllt sein bevor V1).

- **9.2 GitHub-API: gh-CLI installieren oder PAT?**
  - gh-CLI auf Server installieren + auth: erstmals nötig (Server hat heute kein gh). ~30 min Setup.
  - PAT in `~/.moltrust_secrets`: raw HTTPS-Calls. Auth via header `Authorization: Bearer …`. Minimal-Setup.
  - Empfehlung: **PAT in `~/.moltrust_secrets`** für read-only Repo+Traffic-API. Niedrigste neue Surface.
  - Scope-Frage: PAT muss `public_repo` + `repo:read` haben. Aus Privatsphären-Sicht ist PAT-Scope-Auswahl wichtig — kein org-write-access.

- **9.3 nginx-Log-Parsing: live tail vs daily batch?**
  - Daily batch (cron): einfach, fault-tolerant, nur 24h Daten pro Run.
  - Live tail: schwerer, könnte für Realtime-Bot-Alerts erweitert werden.
  - Empfehlung: **daily batch in V1**, live tail aus Scope.

- **9.4 Endpoint-Klassen-Definition stabil oder iterativ?**
  - V1 hat 9 Klassen aus §3.2. Falls Bot-Verhalten andere Granularität verlangt: einfach erweitern (JSONB-Schema-flexibel, kein ALTER TABLE).
  - Empfehlung: V1-Klassen festschreiben, in P3 anpassbar via Script-Change ohne DB-Migration.

- **9.5 Cross-repo BACKLOG-Sync nach P3:** Discovery-Tracking-Dashboard ist heute kein BACKLOG-Item. Nach P3-Merge ergänzen oder als Sub-Item zu „Discovery is the new SEO"-Theme?
  - Empfehlung: kein separates BACKLOG-Item. P3-Merge schließt den Sprint ab; künftige Verbesserungen werden über reguläre PR-Streams getrieben (z.B. V1-GSC-Integration als eigener kleiner PR).

- **9.6 §2.3-Cross-Review-Timing für die spätere P3-Implementation:**
  - Diese SPEC: skip (rein deklarativ).
  - P2 Baseline-Insert: skip (one-off Datenpunkt).
  - P3 Code: **Empfehlung Skip** falls nginx-Parser nur User-Agent-Counts persistiert (Privacy schon in §3.7 hart festgelegt). **Empfehlung Required** falls P3 die GSC-OAuth oder GitHub-PAT-Integration mitbringt (neue Auth-Surface → security-relevant).

## Appendix A — Heutige verifizierte Tooling-Inventar (read-only 2026-05-21)

```
moltrust-api app/main.py admin-endpoints (14):
   /admin/me
   /admin/dashboard/overview
   /admin/dashboard/agents
   /admin/dashboard/activity
   /admin/dashboard/security
   /admin/dashboard/x402
   /admin/dashboard/journal (+ /list, /search, /{date})
   /admin/journal/append (POST)
   /admin/dashboard/callers (+ /{ip})
   /admin/dashboard/traffic
   /admin/traffic/caller/{ip} (+ /label POST)

moltrust-api app/ modules:
   admin_auth.py
   admin_rbac.py

DB tables relevant:
   request_log (ts, endpoint, method, status_code, ip [anonym],
                user_agent, response_ms, source, agent_did,
                ip_org, ip_country, ip_spoof_detected)
   caller_labels (IP → label mapping)
   known_callers (recognized callers)

DSGVO-Compliance:
   moltrust-api request-logger: last octet zeroed (verified Memory #21)
   moltguard requestLogger: last octet zeroed (commit 9592b22)
   nginx access.log: roh-IPs — parser MUSS anonymisieren

Server-side gh CLI: NOT installed (verified moltguard-Migration P6 2026-05-20)
Server-side PostgreSQL `moltstack` DB: live, single DB für API + moltguard
Server cron: läuft mehrere jobs (Backup 03:00 UTC, Herald 4×, Moltbook 2×, Ambassador 1×, TrustGuard 6×, Watchdog hourly)
Server filesystem: /var/log/nginx/ requires sudo for read
```

## Appendix B — Open Questions für künftige Sprints

- Bot-Identitäts-Drift: ändern User-Agents über Zeit? (GPTBot → GPTBot/2.0, etc.) → Mapping-Layer in P3-Script falls nötig.
- Robots.txt-Compliance-Check: erkennen Crawler die `robots.txt`-Direktiven der moltrust.ch? V2-Subscope.
- Per-Crawler-Rate-Limits: machen wir das? Discovery-Tracking könnte das beantworten.
