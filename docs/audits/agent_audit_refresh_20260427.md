# Agent Audit Refresh — 2026-04-27

Differenz zum Audit vom 2026-04-24. Reine Diagnose, keine Code-Änderungen.

**Auditor:** Claude (Opus 4.7)  
**Methodik:** SSH-Probes auf `api.moltrust.ch`, API-Calls auf `https://api.moltrust.ch`, Code-Greps gegen Stand 24.04.  
**Vorgänger:** `agent_audit_20260424.md` (754 Zeilen, 18 Agents) + `vcone_audit_20260424.md` (24492 Bytes).

---

## A) IST-Stand pro Agent (18 + neue)

| # | Agent | Status (27.04.) | Modell | Output letzte 48h | Drift seit 24.04. |
|---|-------|------------------|--------|-------------------|-------------------|
| 1 | MoltyCel (Telegram HITL) | active, effektiv containment | claude-sonnet-4-20250514 | 0 posts (62/62 watch_list observe_only); 1 draft pending 66h | code unverändert |
| 1a | MoltyCel Monitor | DISABLED (Incident 23.04.) | n/a | 0 | unverändert |
| 2 | Ambassador Daemon (`moltrust-agent.service`) | active | non-AI Backend | nur DB-Ops + Milestone | unverändert; flags `low_confidence,ghost_agent` auf trust-score |
| 3 | Ambassador Moltbook (cron */30min + 14:00) | active | claude-haiku-4-5 (Annahme) | replies + daily post | code unverändert |
| 4 | TrustScout / TrustGuard (`moltguard_v1`) | active, trust_score=85.0 grade=A | claude-haiku-4-5 (Annahme) | scan 4×/d + 2 posts | trust_score 85 (alter Audit nahm "karma 96" an — diff!) |
| 5 | Herald v3 | active, healthy | claude-haiku-4-5 | mind. 4 Tweets/Threads geposted (zuletzt 27.04. 07:00 ID `2048658418...`) | unverändert |
| 6 | Moltbook Poster (MolTrust brand) | active | claude-haiku-4-5 (Annahme) | 27.04. 09:00 post #88 ("Your Agents Best Skill...) | code 24.03. unverändert |
| 7 | Moltbook Heartbeat (systemd 60s) | active | non-AI | 5.0 MB log, kontinuierlich | unverändert |
| 8 | MoltGuard Agent (Polymarket) | active | claude-haiku-4-5 | nicht direkt verifiziert | unverändert |
| 9 | PR Monitor (cron 09+18 UTC) | active | non-AI | 0 visible alerts | unverändert |
| 10 | News Scout (cron 17 UTC) | active | non-AI | scout_20260425/26/27_*.md vorhanden | unverändert |
| 11 | Scout (legacy) | active | non-AI | OK | unverändert |
| 12 | Operator (cron */5min) | active | non-AI | OK | unverändert |
| 13 | Watchdog (cron hourly) | active | non-AI | 670 KB log, keine ERROR-Hits in tail | Meta acquisition-comment in Z. 42 unverändert |
| 14 | Outcome Tracker (*/6h) | active | non-AI | OK | unverändert |
| 15 | Traffic Monitor (*/30min) | active | non-AI | log frisch (27.04. 09:30) | unverändert |
| 16 | Retention Cleanup (daily 03:30) | active | non-AI | OK | unverändert |
| 17 | Endpoint Probe (*/5min) | active | non-AI | OK | unverändert |
| 18 | Auditor (Mo 10:00) | active | non-AI | scheduled (today 10:00 fällig) | unverändert |

**NEU seit 24.04. (nicht in alter 18er-Tabelle):**

| # | Agent | Status | Notes |
|---|-------|--------|-------|
| N1 | **ThreadWatch** (cron 2×/d) | active aber Telegram-Send BROKEN | crawl 8 repos, classified 22 threads 27.04. 08:03; Telegram 400 can\t find end tag <i>" — Reports kommen NIE bei Lars an |
| N2 | **moltrust-uresolver** (systemd) | active seit 17.04. | Node.js DID-Driver Port 8168, im alten Audit nur als Beilage erwähnt |

**Externe Referenzen:**
- VCOne-AI: GitHub 404 (still suspended). NEU: als 4. Swarm-Seed `did:moltrust:vcone` mit base_score 75.0 registriert.

---

## B) Status der acht Hardening-Items

| # | Item | Status | Begründung |
|---|------|--------|------------|
| 1 | MoltyCel Halluzinations-Hardening (Modell-Upgrade, "MUST end with endpoint", fact-corpus statt memory_ctx) | **still-open** | Modell weiterhin `claude-sonnet-4-20250514` (Sonnet 4.0, älter). System-Prompt hat "Never invent endpoints"-Rule + "MUST end with closing action"-Struktur — beides bereits 24.04. drin. memory_ctx noch unverändert. Keine Halluzinations-Indikatoren in Logs gefunden, aber containment hält Volume bei 0. |
| 2 | Persona-Inkohärenz auf moltrust-agent (3 Prozesse, 3 Prompts, 1 Account) | **still-open** | 3 Prozesse laufen weiter: Ambassador Daemon (`moltrust-agent.service`), Ambassador Moltbook cron, Moltbook Heartbeat systemd. Alle posten via gleichem Account. Kein Refactoring. |
| 3 | TrustScout Containment-Release (karma 96 > threshold 50) | **changed** | Live trust_score=85.0 (nicht 96 wie alter Audit annahm). Containment-Logik nicht im Code von trustscout.py auffindbar — vermutlich nur cron-basiert (max 2 posts/day via crontab). Bei score 85 ist threshold (50) deutlich überschritten — Release wäre fällig, aber Release-Action ist undefiniert ohne dass Containment im Code gegated ist. |
| 4 | ERC-8004 ID-Drift fix (21023 → 33553 in moltbook_poster.py) | **still-open** | `moltbook_poster.py:62` hat weiterhin `agentId 21023 on Base` im System-Prompt. Korrekt wäre `33553` (siehe MEMORY.md). Fix NICHT durchgeführt. |
| 5 | Moltbook-Agents Content-Update (SOUL.md veraltet seit 17.03.) | **still-open** | `workspace/trustscout/SOUL.md` (4542 B) + `workspace/ambassador/SOUL.md` (3710 B) beide last-modified `2026-03-17 22:37`. 41 Tage alt. |
| 6 | Watchdog max_hours:72 reset | **still-open** | `agents/watchdog.py:42` hat weiterhin `"max_hours": 72,  # Moltbook API 500 errors since 2026-03-27 (Meta acquisition)`. Threshold + Begründungs-Comment beide unverändert. Moltbook Poster postet aber täglich erfolgreich (88 posts cum.) — 72h-Threshold ist obsolet. |
| 7 | Math-Challenge-Parser hardening (Lobster-Garbling) | **still-open / structural** | Parser-Code unverändert seit 17.03.-Fix (heartbeat.py 10.03., moltbook_poster.py 24.03., trustscout.py 16.03.). KEINE Lobster-Garbling-Vorfälle in Logs seit 24.04.; aktueller Posts-Output normal. Strukturelles Problem: Solver-Code in 5 Files dupliziert (heartbeat, moltbook_poster, ambassador, trustscout, moltguard) — Hardening würde Konsolidierung in 1 shared module erfordern. |
| 8 | Memory updates (moltguard karma 96 not 11, Moltbook-Meta claim removed) | **partial-done** | MEMORY.md (lokal) wurde gepflegt — laut Brief "heute Vormittag". ABER `watchdog.py:42` Code-Comment "(Meta acquisition)" bleibt drin. Memory-Edit erledigt, Code-Comment-Edit nicht. **moltguard_v1 (`did:moltrust:70eb425c`)** trust_score ist heute `null`/withheld=true, endorser_count=0 — neuer State, weder 11 noch 96; Memory-Eintrag mit "11 karma" ist nicht falsch sondern altes-Reddit-karma vs. neue Phase-2-Logik (zwei Metriken, eine Memory-Zeile mischt sie). |

---

## C) Neue Items seit 24.04. (Diff-Findings)

- **[P0] ThreadWatch Telegram-Report-Send broken**  
  Bei jedem 2×/täglichen Run schlägt der Telegram-Send mit HTTP 400 fehl: "can't parse entities: Can't find end tag corresponding to start tag i". Gestern (26.04.) deployed, aber Lars sieht NIE einen Report. Ursache: Report-Formatter emit unbalanced `<i>...` Tag in HTML-Mode. ~5-Min-Fix.

- **[P1] moltrust v0.2.0 + MolTrustResolver NICHT auf Server installiert**  
  Server-venv (`/home/moltstack/moltstack/venv`) hat `moltrust-mcp-server 0.4.0`. Kein Paket `moltrust` (heute publiziert) und keine `moltresolver`. Falls die `app/main.py`-Änderung von 26.04. den Bridge-Resolution-Bugfix enthält, könnte sie auf einer Version laufen die nicht mehr auf PyPI ist. Verifizieren: hängt Bridge-Fix vom v0.2.0-Package ab oder ist er API-app-internal?

- **[P1] ThreadWatch repo-config-Bug**  
  `w3c-cg/did-resolution` returns GH 404 bei jedem Crawl (repo umbenannt/gelöscht). config-yaml `repos`-Liste nicht gepflegt. 1 Zeile rauslöschen.

- **[P1] ThreadWatch Duplicate-Logging**  
  Jeder Log-Eintrag erscheint 2× — Logger-Setup hat 2 Handler an gleichem Logger registriert. Cosmetic, aber 2× Log-Volume und 2× Telegram-Sends (sobald Send funktioniert) wäre Spam. 1-Zeilen-Fix in `setup_logger()`.

- **[P1] moltguard_v1 trust_score withheld**  
  `did:moltrust:70eb425c` hat aktuell `trust_score=null, withheld=true, endorser_count=0`. Phase-2-Score-Logik withholdet Agents ohne Endorsements. Alter Audit (24.04.) erwartete moltguard_v1 als active duo-partner zu TrustScout — aktuell ist seine eigene Trust-Position fragil. Untersuchen: hat moltguard_v1 Endorsements verloren oder nie welche gehabt?

- **[P2] VCOne neuer Swarm-Seed-Status**  
  `did:moltrust:vcone` als 4. Seed mit base_score 75.0 registriert (`POST /swarm/seed` ist admin-gated, also bewusste Aktion). GitHub-Account dagegen 404 (suspended seit 24.04. unverändert). Frage: Identitätsmodell — Seed im Swarm ohne aktive externe Präsenz?

- **[P2] Ambassador "ghost_agent" flag**  
  `did:moltrust:ambassador0001` hat trust-score-flags `["low_confidence","ghost_agent"]`. Als Seed (base_score 80.0) greift der Floor, der Live-Score ist also 80, aber die Flag bleibt informativ. "Ghost" bedeutet vermutlich: registriert, kein-bis-wenig sichtbarer Output. Konsistent mit Ambassador Daemon = Backend-only.

- **[P2] MoltyCel HITL-Queue stale**  
  ThreadWatch-Probe meldet "1 pending, oldest 66h". Ein Telegram-Draft wartet seit 2.75 Tagen auf Lars' Approval/Reject. Containment + ThreadWatch-Telegram-broken zusammen ergeben: Lars sieht weder den Draft noch den ThreadWatch-Hinweis darauf.

- **[P3] Moltbook 500-Probleme scheinen resolved**  
  Watchdog max_hours:72 wurde 27.03. wegen Moltbook-API-500ern hochgesetzt. Daten zeigen: Moltbook Poster postet seitdem täglich erfolgreich (88 cum. posts, zuletzt 27.04. 09:00). Threshold ist obsolet. Passt zu Item 6.

- **[P3] @moltrust/openclaw v2.0-alpha Side-Effects**  
  Server-Pfad `~/moltstack/moltstack/moltrust-openclaw/.git/` hat fresh commits. Keine sichtbaren Auswirkungen auf bestehende Agents (Plugin ist Plugin, läuft auf User-Maschinen, nicht auf Server).

---

## Empfehlung — Reihenfolge nach Risiko/Impact

1. **[P0] ThreadWatch Telegram-Send-Fix** — ohne Fix ist die ganze ThreadWatch-Investition wirkungslos. ~5 Min.
2. **[P1] moltrust v0.2.0 server-side verify + ggf. install** — Klarheit ob Bridge-Fix abhängig ist. ~10 Min.
3. **[P1] Item 4: ERC-8004 ID 21023 → 33553 in moltbook_poster.py:62** — System-Prompt korrigieren, kein Restart nötig (Cron-Job lädt jeden Run). ~5 Min.
4. **[P1] Item 6 + Item 8 zusammen: watchdog.py:42 reset** — `max_hours` von 72 auf 15-26 reduzieren, "(Meta acquisition)"-Comment entfernen. ~3 Min.
5. **[P1] ThreadWatch repo-config + duplicate-logging fix** — 2 kleine Patches in einem Edit. ~10 Min.
6. **[P2] moltguard_v1 trust_score-Withhold investigieren** — vor Containment-Release nötig, sonst Annahme nicht haltbar.
7. **[P2] Item 1: MoltyCel-Modell-Migration** — Sonnet 4 → Haiku 4.5 (Cost ~70% reduziert) ODER Opus 4.7 (Quality up). Containment macht den Unterschied klein, aber Migration unabhängig sinnvoll.
8. **[P2] Item 3: TrustScout Containment-Release entscheiden** — entweder cron auf 4 posts/day hochsetzen (aktive Release) oder Containment-Definition aktualisieren.
9. **[P3] Item 2: Persona-Inkohärenz** — strukturell, kein Bug. Nur wenn Tone-Konflikt sichtbar wird.
10. **[P3] Item 5 + Item 7: SOUL.md update + Lobster-Parser-Konsolidierung** — beides editorial / DRY-Verbesserung. Niedrigste Dringlichkeit.

---

## Wichtige Caveats

- "TrustScout containment threshold" konnte nicht im Code-Pfad eindeutig lokalisiert werden — Annahme: nur cron-basiert (2 posts/day), nicht code-gated. Validierung empfohlen.
- "MoltyCel queue 1 pending 66h" stammt aus ThreadWatch-Probe — Inhalt des pending Drafts nicht inspiziert (Datenschutz / kein expliziter Auftrag).
- Modell-Werte für Ambassador-Moltbook / Moltbook Poster / MoltGuard / TrustScout sind als "claude-haiku-4-5 (Annahme)" markiert weil ich die `ANTHROPIC_API_KEY`-Aufrufe nicht direkt re-greppt habe; alter Audit sagt Herald = haiku-4-5, andere wahrscheinlich gleich.
- Ambassador-Output 48h nicht direkt aus dedicated log verifiziert (kein `ambassador.log` in `logs/`-Listing) — Status "active" basiert auf systemd-running-State.

_Audit Ende. 27.04.2026 ~10:30 UTC_
