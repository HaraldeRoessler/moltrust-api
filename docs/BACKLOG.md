# BACKLOG.md — MolTrust Open Items

**Status:** V1.4, lebendiges Dokument
**Letzte Aktualisierung:** 2026-05-15
**Geltungsbereich:** Alle MolTrust-Repos (moltstack, moltguard, moltrust-protocol)
**Definiert durch:** WORKFLOW.md Sektion 1.7

---

## Lese-Anleitung

- **Severity:** High / Medium / Low — Priorität in der Bearbeitungs-Reihenfolge
- **Status:** Open / In-Progress / Blocked / Deferred — aktueller Bearbeitungs-Zustand
- **Aufwand:** S (<30 Min) / M (30 Min - 2h) / L (>2h) — Zeitschätzung
- **Added:** Datum der Erstaufnahme
- **Source:** Wo das Item herkommt (Memory-Eintrag, Sprint-Doc, Audit-Output, Konversation)

**Hygiene-Regel (WORKFLOW Sektion 1.7):** Items älter als 30 Tage ohne Bewegung werden hinterfragt — ist es noch relevant, oder gestrichen?

---

## High

### V1.4-1: D3 = kritischer Pfad — keine Produktion ohne formales Delegations-Enforcement-Modell
- **Status:** Open
- **Aufwand:** L
- **Added:** 2026-05-18
- **Source:** AAE-D1-Kanonisierung §2.3-Security-Cross-Review (PR #41, Verdikt GRUNDLEGEND ÜBERDENKEN, Punkt C1)
- **Details:** Das D1-AAE-Schema (PR #41) ist als **strukturelle** Baseline freigegeben (Lars, Option a), aber die `delegation`-**Semantik ist NICHT enforce-bar**. Drei-Reviewer-Konsens (GPT-4o + Gemini + Perplexity, security mode): das Verschieben der Reconciliation zwischen Schema-`Delegation` (`attenuationOnly`/`maxSubAgents`/`maxDepth`) und der Live-`agent_delegation_config` (`constraint_mode ∈ {inherit,restrict,none}`) auf V1.4-1 D3 ist ein **Privilege-Escalation-Risiko** (zwei konkurrierende Delegationsmodelle ohne formales Kompositions-/Attenuationsmodell). **Konsequenz: V1.4-1 darf NICHT in Produktion, bevor D3 ein formales Delegations-Enforcement-Modell (Attenuation/Komposition + Mapping zur Live-`agent_delegation_config`) geliefert hat.** D3 ist damit **kritischer Pfad** für V1.4-1. Quelle/Detail: PR #41 NORMATIV-Block + Appendix B.

### AAE ins Credential einbauen (Phase-1-Analyse §8 Punkt 1)
- **Status:** Open
- **Aufwand:** L
- **Added:** 2026-05-15
- **Source:** moltrust-web Phase-1-Analyse v4 (UNC-07 Lars-Entscheidung), API-Sprint-Übergabe §8
- **Details:** `POST /identity/register` liefert aktuell ein vollständiges signiertes `AgentTrustCredential` **ohne** AAE-Envelope. AAE läuft separat über `POST /delegation/configure` und ist in `agent-card.json` als eigene Extension deklariert. Die Developer-Seite behauptet aber "Every MolTrust credential embeds an Agent Authorization Envelope" — im Ist-Zustand eine Falschaussage. Lars-Entscheidung: API erweitern, damit das Credential die AAE tatsächlich trägt. Voller WORKFLOW-Pfad (Spec mit 9 Sections, Cross-Review, Tests, PR). **Sequenzierung mit Credit-Middleware-Idempotency koordinieren** — beide ändern Schema, beide berühren `/identity/register`-Pfad, sollten nicht parallel laufen. moltrust-web kann die "embedded"-Darstellung erst nach Merge auf "embedded" heben; bis dahin entschärft PR1 die Falschaussage zu "separater delegation/configure-Schritt".

### Credit-Middleware Idempotency-Mechanismus
- **Status:** Open
- **Aufwand:** L
- **Added:** 2026-05-15
- **Source:** GPT-5 Cross-Review der Credit-Middleware-Spec V2 (CRITICAL F), bewusst Out-of-Scope des heutigen Schema-Alignment-Sprints
- **Details:** Retries und Duplicate-Deliveries können einen Agent doppelt charged werden, weil `reference = resolve_endpoint_key(method, path)` nicht pro Request eindeutig ist. Vollständige Lösung: Idempotency-Key pro Request (`X-Idempotency-Key`-Header oder serverseitig generierte UUID), Unique-Index auf `credit_transactions.idempotency_key`, INSERT mit `ON CONFLICT DO NOTHING`, bei Konflikt das vorherige Ergebnis replayen. Schema-Change. Eigener Spec mit voller 9-Section-Disziplin, eigener Cross-Review.

### cron.service OOM-kill investigieren
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-15
- **Source:** Session-Start Health-Check 2026-05-14 06:36 UTC
- **Details:** cron.service wurde am 14.05. 02:01 UTC vom OOM-Killer beendet. Memory-Pressure auf dem 4GB-Server. Mindestens ein 02:00-cron-Tick ist verloren gegangen. Investigation: welche Prozesse zogen zu dem Zeitpunkt Memory? Ist das ein einmaliger Vorfall oder ein Muster? Mögliche Mitigationen: systemd-Memory-Limits, Swap erhöhen, Memory-fressende Background-Jobs zeitlich entzerren.

### Telegram-Bot httpx-Logging-Leak fix
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** Claude Code diagnostic output 12.05.26 abends
- **Details:** Token-Rotation am 12.05. erledigt (Lars, server-side direkt). Verbleibendes Issue: httpx schreibt aktuellen Bot-Token weiterhin in plain text in `logs/watchdog.log` bei jedem Telegram-API-Call (175 Treffer im Log). Fix: httpx-Logger auf WARNING-Level setzen ODER Token via HTTP-Header statt URL-Pfad (httpx redacts Header by default). Plus: alte logs mit dem alten Token-Wert auditen und ggf rotieren/löschen.

### moltguard-Repo Working-Tree-Triage
- **Status:** Open
- **Aufwand:** L
- **Added:** 2026-05-12
- **Source:** Konversation 12.05.26 (während CONFORMANCE-Drift-Fix)
- **Details:** 9 modified + 14 untracked Files inkl. mehrerer .bak-Files und neuer Routen (events.ts, wallet.ts, aeoess-verify.ts). Separate Triage-Session analog zu moltstack PR #18. master-branch (nicht main).

### WORKFLOW.md Bootstrap-Items (Scripts)
- **Status:** Open
- **Aufwand:** L (gesamt, sequenziell)
- **Added:** 2026-05-13
- **Source:** WORKFLOW.md Sektion 10
- **Details:** Vier Scripts schreiben:
  - `scripts/generate_status.py` (für daily STATUS.md auto-refresh)
  - `scripts/weekly_health_check.sh` (Multi-Repo-Health + Token-Audit + Stash-Aging)
  - `scripts/pre_sprint_check.sh` (manueller pre-sprint state check)
  - cron-jobs für 5.1, 5.2, 5.3 in WORKFLOW.md installieren
  Plus: `docs/STATUS.md` erste manuelle Version, dann auto-refresh aktivieren.

---

## Medium

### AAE `tool_allowlist`-Inhaltsmodell (C2, Follow-up — KEIN D1-Blocker)
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-18
- **Source:** AAE-D1-Kanonisierung §2.3-Cross-Review (PR #41, Punkt C2)
- **Details:** Das D1-Schema führt `tool_allowlist` als `Obligation`-Flag, aber **ohne Inhaltsmodell** (welche Tools konkret erlaubt sind). In v1 daher **deklarativ/inert** — DARF nicht für Enforcement herangezogen werden, bis ein Tool-Constraint-Inhaltsmodell entschieden ist. Reviewer-Optionen (nicht entschieden, **nicht erfunden**): `ToolConstraint[]` direkt im Schema vs. externer Referenz-Hash. **Ausdrücklich KEIN D1-Blocker** (Lars-Entscheidung) — eigenes Follow-up. Relevant erst, sobald `obligations` tatsächlich enforced werden.

### §9.2 global: Debit-vor-call_next für alle 12 paid Routes (sauberer Endzustand)
- **Status:** Open
- **Aufwand:** L
- **Added:** 2026-05-18
- **Source:** Idempotency-Spec D1 (PR #34) — Lars: Option A (keyed-only vor call_next) bestätigt
- **Details:** D1-Option-A ist eine **bewusste, dokumentierte Risiko-Akzeptanz**: Aufrufer **ohne** `Idempotency-Key` behalten das alte Verhalten (Legacy-Pfad unverändert, Debit **nach** `call_next` → Doppel-Belastung bei Retry weiterhin möglich). Nur der Opt-in-keyed-Pfad bekommt Debit-vor-`call_next`. Sauberer Endzustand: §9.2 **global** — Debit-vor-`call_next` für **alle 12 paid `ENDPOINT_COSTS`-Routes**. Eigener Sprint: eigene 9-Sektionen-Spec, eigener §2.3-Cross-Review, **gestuft ausrollen — NICHT Big-Bang über alle 12 Routes** (Auto-Probe-Lesson: prozessweite Middleware-Änderung ist dieselbe Architektur-Klasse wie die Auto-Probe-Regression; schema-alignment §9.2 hat die Process-wide-Middleware-Frage bereits markiert). **Unabhängig von / nach** der Idempotency-Foundation (PR #34) und V1.4-1.

### ai_review.py — Synthese-400 war Billing (Credits falsche Org); Silent-Success-Defekt
- **Status:** Primärursache RESOLVED (2026-05-18); sekundärer Code-Defekt Open → eigener Fix
- **Aufwand:** S
- **Added:** 2026-05-18
- **Source:** `/review`-Lauf 2026-05-18 (credit-idempotency-brief); Root-Cause-Verifikation 2026-05-18 (read-only API-Diagnose)
- **Details:** **Korrektur der ursprünglichen Fehldiagnose.** Primärursache war **nicht** der Code: die Anthropic-API-Credits waren erschöpft bzw. in der **falschen Organisation** aufgeladen — `POST /v1/messages` lieferte für **jeden** Model-String identisch `invalid_request_error: "Your credit balance is too low"`. ~4 Tage Totalausfall aller Anthropic-Consumer (erste Beobachtung `moltbook.log 2026-05-14T09:00`, behoben `2026-05-18T10:38Z` nach Top-up in der korrekten Org `5f4b3dfb-…`). **Model-ID-Verdacht widerlegt:** `claude-sonnet-4-20250514` ist gültig und gelistet (`GET /v1/models` → HTTP 200), war nie das Problem; ein Modellwechsel hätte nichts behoben. **Sekundärer, echter Code-Defekt:** `ai_review.py` meldet `Synthesis : ✅` / `✅ Review abgeschlossen` und exitet 0 **auch wenn** der Synthese-Schritt einen Error-String zurückgibt — dieser Silent-Success hat die Fehldiagnose (Model-ID statt Billing) erst ermöglicht. Fix dieses Defekts: separater Code-PR (`fix/ai-review-silent-success`), nicht hier. **Unabhängig von V1.4** — eigenes Fix-Item.
### API-Versionierung — Single-Source + v1-Contract klären (Phase-1-Analyse §8 Punkt 5)
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-15
- **Source:** moltrust-web Phase-1-Analyse v4 OD-8, plus Versionierungs-Audit 2026-05-15 (`~/moltstack/audits/2026-05-15_api-versioning.md`)
- **Details:** Der Audit hat drei zusammenhängende Probleme aufgedeckt: (a) **Drei-Stellen-Duplikation ohne Single-Source** — `FastAPI(version="2.4")` in `app/main.py:50`, zusätzlich "2.4" als Literal in `:1519` (`/health`-Body) und `:5855` (zweiter Handler-Body). Kein zentraler Versions-String in `pyproject.toml`/`setup.cfg`/`app/__init__.py`. Ein Bump heute muss drei Stellen einzeln anfassen. (b) **Rückwärts-Dekrement 2.6 → 2.4** in der Repo-Historie — Initial-Commit `6c6a892` (2026-03-10) setzte `version="2.6"`, HEAD ist "2.4". Diagnostisches Signal: irgendwann hat jemand den Wert manuell editiert ohne sauberen Sprint-Pfad. (c) **Null versionierte Pfade** — 0 von 136 OpenAPI-paths haben `/v1/`, `/v2/`, `/api/v*`. Konvention ist domänen-präfixiert (`/identity/`, `/credits/`), nicht versions-präfixiert. Die OAS-`info.version` ist damit die einzige öffentliche Versions-Aussage des Systems — und sie ist unzuverlässig. Fix: Single-Source-of-Truth für die Versionsangabe (eine Konstante, z.B. `app.version.API_VERSION`, drei Stellen lesen sie), v1-Contract-Deklaration ("MolTrust API v2.4" im OAS vs. öffentliche v1-Aussage synchronisieren), Versionierungs-Schema (Breaking Changes über `/v2` oder Version-Header), Deprecation-Policy (6-Monats-Fenster, RFC 8594 `Deprecation`/`Sunset`-Header).

### Trust-Score-Reads Rate-Limiting (Phase-1-Analyse §8 Punkt 2)
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-15
- **Source:** moltrust-web Phase-1-Analyse v4 (OD-7 / V-9 partial), API-Sprint-Übergabe §8
- **Details:** Handler `/skill/trust-score/{did:path}` ist un-rate-limited und konstruktiv mit slowapi nicht nachrüstbar — der Handler hat keinen `request: Request`-Parameter. Signatur-Refactor nötig: `request: Request` als Parameter aufnehmen, slowapi-Decorator anwenden (Vorschlag: `60/minute/IP` analog zu anderen Read-Endpoints). Strukturarbeit, kein Config-Fix.

### CAEP als Extension in agent-card.json deklarieren (Phase-1-Analyse §8 Punkt 3)
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** moltrust-web Phase-1-Analyse v4 (UNC-11 / V-7), API-Sprint-Übergabe §8
- **Details:** CAEP-Profil ist live (`@moltrust/agent-firewall@1.0.0`, PROFILE.md sauber, 4 Endpoints live), aber **nicht** als sechste Extension in `agent-card.json` deklariert. Aktuell dort nur fünf: trust-score, aae, erc8004, x402-payment, discovery-surfaces. CAEP-Extension-Eintrag ergänzen mit korrektem Schema-URI und Endpoint-Liste. Reine Doku-Auslieferungs-Asymmetrie, kein Funktions-Bug. Beim Gelegenheits-Cleanup auch den Doku-Drift in `agent-firewall` PROFILE.md angleichen: nennt CAEP-Default-Limit 100, Server-Code nutzt 50 — Server-Wert übernehmen, PROFILE.md korrigieren.

### .well-known-Mirror-Generierung + Deprecation-Header (Phase-1-Analyse §8 Punkt 4)
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-15
- **Source:** moltrust-web Phase-1-Analyse v4 (OD-8 / INC-08), API-Sprint-Übergabe §8
- **Details:** `agent-card.json` ist aktuell identisch unter `api.moltrust.ch/.well-known/` und `moltrust.ch/.well-known/` ausgeliefert, ohne kanonische Quelle. Entscheidung (OD-8): `api.moltrust.ch/.well-known/...` = kanonisch, `moltrust.ch/.well-known/...` = generierter Mirror. Mirror-Generierungs-Pipeline aufsetzen (cron, post-merge-hook, oder build-time). Plus RFC 8594 `Deprecation`/`Sunset`-Header für deprecated Endpoints implementieren. Hängt nicht von "API-Versionierung Single-Source" ab, aber thematisch verwandt — sinnvoll im selben Sprint oder direkt danach.

### Credit-Middleware process-wide-Scope + Inversion debit-vor-call_next
- **Status:** Open
- **Aufwand:** L
- **Added:** 2026-05-15
- **Source:** GPT-5 Cross-Review der Credit-Middleware-Spec V2 (CRITICAL A "Preferred"-Variante), bewusst Out-of-Scope des heutigen Sprints (Spec V2.1 Section 9.2)
- **Details:** `credit_middleware` läuft via `@app.middleware("http")` auf jedem Request — dieselbe Architektur-Klasse wie die Auto-Probe-Regression. Zwei verbundene offene Fragen: (a) soll Credit-Deduction wirklich für jeden Request laufen, oder nur für explizit als "paid" markierte Routen? (b) soll der Debit **vor** `call_next` passieren statt danach, damit der Handler im Race-Fall gar nicht erst aufgerufen wird? Aktueller Zustand (Spec V2.1) nutzt die Minimal-Variante: Debit nach `call_next`, bei UPDATE=0 → HTTP-402-Mutation. Funktioniert, aber im Race-Fenster lief der Handler bereits. Eigener Spec mit voller 9-Section-Disziplin, eigener Cross-Review.

### WORKFLOW.md V1.2 — heutige Lessons einarbeiten
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** Credit-Middleware-Sprint + Working-Tree-Cleanup 2026-05-14/15
- **Details:** Drei Lessons aus den letzten zwei Tagen gehören in WORKFLOW.md:
  - **SQL-Validation niemals gegen Live-DB:** "Dry-Run gegen Live-DB" ist ein Widerspruch — `psql --single-transaction -f` committed bei `-f`-Ende. SQL-Validierung gehört offline (`pg_format --check`, `sqlparse`) oder gegen Wegwerf-DB. Aufgedeckt durch den unbeabsichtigten Live-DB-Touch im Step B des Credit-Sprints (drei Indizes wurden ungewollt auf Production angelegt; netto harmlos, aber Prozessfehler).
  - **Vor Branch-Creation `git fetch && git log origin/main`:** stale-local-main verhindern. Aufgedeckt durch die Working-Tree-Cleanup-PR-Erstellung am 14.05. die zunächst gegen stale-local-main lief.
  - **Reviewbedürftige Outputs immer in `/tmp/`-Datei, nicht inline:** Transport-Verlust beim Kopieren aus der Console — lange Diffs und Schema-Dumps kommen unvollständig beim Reviewer an. Standardmuster ab jetzt: Claude Code schreibt Diff/Schema/Log in `/tmp/<file>`, Lars lädt hoch.

### tx_type CHECK-Constraint + FK credit_transactions → credit_balances
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** Credit-Middleware-Spec V2.1 (Open Decisions, beide bewusst Out-of-Scope des heutigen Sprints)
- **Details:** Zwei kleine Schema-Migrationen die zusammen passen: (a) `credit_transactions.tx_type` bekommt einen CHECK-Constraint auf die Convention-Werte `('grant', 'api_call', 'transfer')` statt Convention-only durch `credits.py` enforced. (b) Foreign-Key von `credit_transactions.from_did` und `credit_transactions.to_did` auf `credit_balances.did`, `DEFERRABLE INITIALLY DEFERRED` damit Transaktions-Reihenfolgen nicht brechen. Sinnvoll als Eine-Migration-Item, low-risk.

### FastAPI on_event → lifespan Migration
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-15
- **Source:** Credit-Middleware-Sprint Test-Output — 4 DeprecationWarnings im pytest run
- **Details:** `@app.on_event("startup")` und `@app.on_event("shutdown")` in `app/main.py` (mehrere Stellen) sind seit FastAPI 0.110+ deprecated. Migration auf `@asynccontextmanager` mit `lifespan=`-Parameter beim FastAPI-Konstruktor. Mehrere Handler zusammenführen. Test-conftest's manueller Startup-Trigger muss entsprechend angepasst werden (`async with LifespanManager(app):` aus asgi-lifespan statt manueller Handler-Loop).

### traffic_monitor.py in Watchdog AGENTS-Liste aufnehmen
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** Working-Tree-Cleanup 2026-05-14 — der 3-Tage-Bug war unsichtbar genau weil traffic_monitor nicht in der AGENTS-Liste war
- **Details:** `agents/traffic_monitor.py` läuft stündlich via cron, ist aber nicht in `agents/watchdog.py`'s AGENTS-Liste. Folge: SyntaxError-Crash über 3+ Tage (11.05.–14.05.) blieb unbemerkt, ~72 fehlgeschlagene cron-Runs. AGENTS-Liste ergänzen, damit broken-state künftig im Watchdog-Alert auftaucht.

### migrations/add_outcome_tracker.sql Altlast klären
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** Working-Tree-Realität 2026-05-14 (Datei existiert in `migrations/`, ist aber nie committet — wurde von altem `*.sql` in `.gitignore` geblockt, jetzt durch `.gitignore`-Negation sichtbar)
- **Details:** `migrations/add_outcome_tracker.sql` liegt seit 2.04. im Ordner, ist untracked. Prüfen: ist die Migration noch relevant (welche Tabelle/Spalte würde sie anlegen, existiert sie schon)? Wenn relevant + nicht applied: committen + applien. Wenn relevant + bereits applied: committen als historisches Artefakt mit Kommentar. Wenn irrelevant: löschen.

### Auto-Probe-Migrations Repo-Status verifizieren
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** `.gitignore`-Realität-Check 2026-05-14 — `*.sql` blockte alle Migrations bis zur heutigen Negation
- **Details:** Es gibt mehrere `.sql`-Files in `migrations/` und `app/migrations/`. Vier sind getrackt (siehe `git ls-files | grep .sql$`). Verifizieren: welche Auto-Probe-relevanten Migrations existieren im Working-Tree der Server-Installation, und sind sie alle im Repo? Falls eine Migration nur auf dem Server liegt und nirgends versioniert ist, ist sie de facto ein loses File — committen oder dokumentieren.

### Stash-Hygiene Post-Credit-Sprint
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** Working-Tree-Cleanup 2026-05-14
- **Details:** Aktuell sind mindestens zwei Stashes im moltstack-Repo: `pre-auto-probe-deploy-2026-05-12-WIP-incl-prediction-accuracy` (alt, 12.05.) und `pre-2026-05-14-WIP-xmtp-v3-migration` (heute angelegt). Review: was ist tatsächlich im alten Stash noch unique vs. inzwischen anderswo gemerged? Alten Stash sauber droppen sobald nichts uniques mehr drin ist. Konsolidiert das frühere V1.2-Item "Stash@{0} Post-Triage Review", inkl. heutiger neuer Stash-Information.

### flag_records.anomaly_score integer → numeric(10,4) migration
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** Commit 2 Pre-Commit-Verifikation 12.05.26
- **Details:** `anomaly_score integer` vs Code übergibt potenziell float aus MoltGuard API. Silent-rounding-Risiko bei Outcome-Tracking. Migration ist backward-compatible (existing integers parsen als numeric).

### CAEP Profile v2 — neuer Sprint mit Cross-LLM-Review
- **Status:** Open
- **Aufwand:** L
- **Added:** 2026-05-12
- **Source:** Konversation 13.05.26 (Harald Rückfrage)
- **Details:** CAEP v2 envelope-sync war ursprünglich als "wait for Harald slot" markiert. Korrektur per Lars 13.05.: Harald hat aktuell keine Items offen, V2 muss als kompletter neuer Sprint aufgesetzt werden — mit Cross-LLM-Architecture-Review im Sinne von WORKFLOW Sektion 2.3 + Memory #28 Lesson. Spec mit allen 9 Sections schreiben, Layer-Scope explizit, vor Implementation Cross-Review durch GPT-5/DeepSeek/Kimi.

### Re-Deploy V2 Auto-Probe sprint
- **Status:** In-Progress (Workflow-Doc fertig, Code noch nicht)
- **Aufwand:** L
- **Added:** 2026-05-12
- **Source:** Memory #25, audits/2026-05-12_gpt5-verification-bundle.md, docs/sprints/2026-05-12_smithery-v2-workflow.md
- **Details:** GPT-5 D3 Architektur (mounted sub-app statt globale Middleware) + composite client-instance token + decorator pattern. Sprint-Code preserved auf feature/auto-probe-token. Spec mit allen 9 Sections schreiben bevor Implementation startet.

### moltstack/CONFORMANCE.md Namespace-Konflikt
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** CONFORMANCE-Drift-Diagnose 12.05.26
- **Details:** `moltstack/CONFORMANCE.md` ist "AIP Conformance Report", `moltrust-protocol/CONFORMANCE.md` ist "Skill Audit Conformance" — zwei verschiedene Docs mit identischem Filename. Rename ersteres zu `moltstack/AIP_CONFORMANCE.md` + Referenzen im Code updaten.

### XMTP v3 Migration testen + committen, dann Sandbox-Architektur entscheiden
- **Status:** Deferred (Reactivation-Bedingung: dedizierter Test-Sprint)
- **Aufwand:** M
- **Added:** 2026-05-12 (Sandbox-Architektur), 2026-05-15 update (Migration-Code seit heute als named-stash)
- **Source:** Commit 4b skip-Entscheidung 12.05.26 + heutiger Working-Tree-Cleanup (Stash `pre-2026-05-14-WIP-xmtp-v3-migration`)
- **Details:** Zwei verbundene Threads, in dieser Reihenfolge zu lösen: (1) Den seit 2026-05-14 named-stashten XMTP-v3-Migrations-Code (`scripts/outreach_xmtp.js`, ~80 Zeilen, Library-Swap `@xmtp/xmtp-js` → `@xmtp/node-sdk`, neue Signer-API mit `IdentifierKind.Ethereum`, encryption-key via sha256(privateKey)) zuerst gegen v3-API testen — unklar ob die Migration tatsächlich funktioniert, ist 35+ Tage alte uncommittete Arbeit. Sobald getestet: regulär committen. (2) Sandbox-Architektur entscheiden: aktuell kann das Script `node_modules` in `experiments/xmtp/` nicht erreichen. Drei Optionen: (α) viem zu `experiments/xmtp/package.json` + npm install, (β) Script relocaten nach `experiments/xmtp/`, (γ) eigenes `node_modules` für `scripts/`. Reihenfolge wichtig — ohne Test ist die Architektur-Entscheidung vorzeitig.

### Multi-Repo Branch-Naming Vereinheitlichung
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** Working-Tree-Triage 12.05.26
- **Details:** moltguard nutzt `master`, moltstack nutzt `main`. WORKFLOW Sektion 7.2 listet inkonsistente Namen als Backlog-Item. Migration moltguard `master` → `main` über GitHub-Settings.

### Auto-update-Hook für /var/www/html/CONFORMANCE.md
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** CONFORMANCE-Drift-Resolution 12.05.26
- **Details:** Aktuell muss man nach jedem `gen_conformance.py`-Run manuell `sudo cp` zum Web-Path. Anti-Pattern. Fix: post-merge-hook in moltrust-protocol/.git/hooks/ ODER systemd-path-watcher auf docs/CONFORMANCE.md.

### gh CLI installieren auf moltstack-server
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** PR-Creation-Friction 12.05.26
- **Details:** `gh` fehlt auf api.moltrust.ch-Server, PR-Creation läuft manuell via Browser. `sudo apt install gh && gh auth login` löst es. Plus: Bot-Account-Authentication damit gh-Calls als MoltyCel funktionieren.

### SSH-Migration für MoltyCel-Bot
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-12
- **Source:** PAT-Rotation 12.05.26
- **Details:** Aktuell Pattern B (credential-helper aus env) für moltrust-protocol. Langfristig sauberer: SSH-Key für MoltyCel-Bot auf GitHub registriert, kein Token-in-env mehr nötig. Setup: neuer ed25519 für MoltyCel-personal, GitHub key + ssh config alias, dann Pattern A für alle bot-getriebenen Repos.

---

## Low

### Separate Test-DB für Credit-Tests
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-15
- **Source:** Credit-Middleware-Sprint Test-Architektur-Entscheidung (Spec V2.1 Section 9.3)
- **Details:** Die heutige Test-Architektur testet `credit_middleware` gegen die Live-DB mit klar markierten Test-DIDs (`did:moltrust:<16hex>`, `display_name='tc-...'`, `platform='test'`). `credit_balances`/`agents`/`api_keys` werden aufgeräumt; `credit_transactions`-Einträge bleiben wegen append-only Trigger als markierte Audit-Spur in der Live-DB. Über Zeit sammelt sich Test-Müll an (filterbar, aber unschön). Saubere Lösung: separate Test-DB `moltstack_test` mit eigenem Schema-Sync, in Test-Env-Vars verdrahtet, Tests laufen dagegen. Eigene Infrastruktur-Arbeit (DB-Setup, env-Handling, Schema-Sync), deshalb low-priority.

### known_callers Tabelle DROP oder Migration
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** Working-Tree-Cleanup 2026-05-14 — bei der traffic_monitor.py-Restore aufgedeckt
- **Details:** Postgres-Tabelle `known_callers` (45 rows, oldest Jan 2026, last write 2026-04-18 — 4 Wochen stale). Wurde von der nie-committeten DB-based v2 von `traffic_monitor.py` befüllt; die heutige Entscheidung war file-based v2 zu restoren, damit wird `known_callers` dauerhaft nicht mehr beschrieben. Nur von `traffic_monitor.py` referenziert (verifiziert via grep). Entscheidung: `DROP TABLE` oder Migration des State-Files zur Tabelle (falls man später doch DB-based will). Pragmatisch: DROP, da file-based jetzt der bewusste Stand ist.

### logrotate permissions fix (moltguard.log)
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** Session-Start Health-Check 2026-05-14 06:36 UTC
- **Details:** logrotate hat heute morgen `moltguard.log` (19.8 MB) abgelehnt — Permission-Fehler. Log wächst ungebremst weiter. Fix: logrotate-Config für moltguard prüfen, User/Group anpassen, manuell einmal rotieren.

### app/settlement.py defensive coding cleanup
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** Commit 3 Pre-Commit-Diff-Review 12.05.26
- **Details:** Defensive `isinstance`-Pattern in settlement.py prüft Type für asyncpg-Return-Values. Audit zeigt: aktueller Code hat `isinstance(prediction, str)` (line 221), nicht der vermutete `isinstance(row, dict)`. Code-Review nötig ob das aktuelle Pattern semantisch korrekt ist.

### Audit-Endpoints konsolidieren (404er)
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** CONFORMANCE-Drift-Diagnose 12.05.26
- **Details:** `/guard/audit/version` funktioniert, aber `/audit/version` 404, `/guard/audit` 404. Inkonsistente Convention. Fix: alle Audit-Endpoints unter `/guard/audit/*` konsolidieren ODER 301-redirects einrichten.

### gen_conformance.py als täglicher Cron
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** CONFORMANCE-Drift-Resolution 12.05.26
- **Details:** Script läuft aktuell nur manuell. Bei jedem MoltGuard-Update sollte CONFORMANCE.md automatisch nachgezogen werden. Cron 1x täglich, idempotent.

### Pre-commit-hook conflict-marker-check auf alle Repos
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** Commit 5 Conflict-Resolution 12.05.26 (Gemini-Migration)
- **Details:** `git diff --check` als pre-commit-hook in moltstack + moltguard + moltrust-protocol. Findet `<<<<<<<`/`=======`/`>>>>>>>` Marker bevor sie committed werden.

### `./mcp_server.py` Legacy stdio cleanup
- **Status:** Open
- **Aufwand:** S
- **Added:** Pre-2026-05-12
- **Source:** Memory (legacy MCP transition)
- **Details:** stdio-File obsolet seit MCP-HTTP-Migration. Audit bestätigt: existiert weiter als 2495 B (Mar 29). Löschen.

### PR7 Post-Quantum ML-DSA Diskussion mit Harald
- **Status:** Blocked (waiting for Harald)
- **Aufwand:** M
- **Added:** Pre-2026-05-12
- **Source:** Memory (laufende Diskussion)
- **Details:** Dual-Signature-Approach für VC-Issuance. Harald hat PR auf moltrust-protocol mit Implementation-Vorschlag.

### PR14 CI workflow (alt 30.04)
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-04-30
- **Source:** Memory
- **Details:** GitHub Actions workflow für agent-firewall provenance + tests. Vor V1-Publish gestern noch nicht aktiv — jetzt Backlog für v1.0.1.

### sys.path.insert services/ → proper Python-Package
- **Status:** Open
- **Aufwand:** M
- **Added:** Pre-2026-05-12
- **Source:** Memory (technical-debt)
- **Details:** services/ wird via `sys.path.insert` importiert. Sauber wäre __init__.py + proper package-structure.

### withheld-200 documentation (Harald-Finding)
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** Harald-Mail
- **Details:** `/skill/trust-score` returns 200 mit signed `withheld:true` für bogus DIDs — kann als "registration proof" missverstanden werden. Doku-Klarstellung + Empfehlung `/identity/verify/{did}` als registration-gate.

### Harald's PROFILE.md als authoritative wire-format
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-12
- **Source:** Harald-Mail
- **Details:** Harald hat eigene PROFILE.md die das tatsächliche CAEP-Wire-Format dokumentiert (consistency_level, evaluation_context, registry_signature Fields nicht in offizieller PR16-Description). Übernehmen als authoritative docs für CAEP v1.x.

### trustscout.py + 2 systemd-Service-Files Investigation
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-13
- **Source:** TrustScout-Diagnose 13.05.26 (PR #22)
- **Details:** Diagnose ergab: `agents/trustscout.py` (514 Zeilen) hat 2 systemd-Service-Files (`moltrust-trustscout.service` heartbeat, `moltrust-trustscout-daily.service` daily). Nicht orphaned wie initial vermutet. Schreibt parallel mit `agents/moltguard.py` post-edu/post-deep das `data/trustscout_state.json`. Multi-Writer-Pattern für `last_post_time` Field. Funktional läuft alles (Posts kommen auf Moltbook an, verifiziert via Telegram-Stats), aber Architektur ist unklar: warum 2 Code-Pfade parallel? Soll konsolidiert werden? Reines Investigation-Item, kein akuter Fix nötig.

### 5 stale lokale Branches Cleanup
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-13
- **Source:** Side-Beobachtung 13.05.26 (PR #22 prep)
- **Details:** Nach git branch -vv mit gone upstream: chore/smithery-v2-workflow-doc (PR#19), chore/workflow-doc (PR#20), chore/working-tree-rescue-2026-05-12 (PR#18), chore/backlog-init (PR#21), feature/caep-registry-endpoints (orphaned probe-sprint base). Cleanup via `git branch -d <name>` für jeweils. Vermutlich nach heutigem Sprint zusätzliche Branches dazu (fix/credit-middleware-schema-alignment wurde von GitHub automatisch gelöscht, aber lokal noch zu prüfen).

---

## Deferred (Decision Required Before Activation)

### B2C Prediction-Market Edge-Tool (Polymarket+Kalshi)
- **Status:** Deferred (separater Geschäftsmodell-Discovery-Chat)
- **Aufwand:** L
- **Added:** 2026-05-10
- **Source:** Memory #26
- **Details:** Anomaly-Spotting für Counter-Bet-Opportunities + Investigative-Stories. SEC/Peirce-Validation 08.05. Klärungen pending: Naming, Single/Multi-Platform, Free/Paid, Channel-Account, Brand-Verhältnis zu MolTrust.

### Bernd Plugin-Idee (A2A-Card für Drittsites)
- **Status:** Deferred (Reactivation-Bedingung definiert)
- **Aufwand:** L
- **Added:** 2026-05-11
- **Source:** Memory #27
- **Details:** WP/Shopify-Plugin als MolTrust-Distribution. Nicht bauen ohne Pilot-Pipeline. Reactivation-Bedingung: 5 konkrete Sites die installieren würden. Implementer wäre Lars/Harald, nicht Bernd. Fallback Mini-Tool moltrust.ch/card-generator (8-16h).

---

## Bootstrap (WORKFLOW.md V1 fordert, keine Spec nötig)

### docs/STATUS.md erste Version
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-13
- **Source:** WORKFLOW.md Sektion 1.2 + 10
- **Details:** Manuell erste Version mit aktuellem System-State. Danach via `scripts/generate_status.py` auto-refreshed.

### docs/decisions/ initialisieren mit 3-5 ADRs
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-13
- **Source:** WORKFLOW.md Sektion 1.4 + 10
- **Details:** ADRs für (1) Auto-Probe V2-Architektur mounted-sub-app, (2) Pattern B credential-helper (Token-Rotation), (3) MCP-Tool-Convention beibehalten, (4) Sequential A/B-Test bei Smithery, (5) Memory-Reality-Sync-Pflicht. Plus neu: (6) Credit-Middleware Minimal-Variante (statt Inversion) für 402-Mutation — bewusste Scope-Entscheidung des 15.05.-Sprints.

### Multi-Repo-Inventory-File
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-13
- **Source:** WORKFLOW.md Sektion 7.1
- **Details:** `docs/repos.md` mit Liste aller MolTrust-Repos, Branch-Naming-Status, Cross-Dependencies, Verantwortung.

### docs/incidents/ Folder als Konzept einführen
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-15
- **Source:** Working-Tree-Cleanup-Lesson 14.05.: Incident-Post-Mortems sind anderes Format als ADRs (in `docs/decisions/`) — Auto-Probe-Drama + Credit-Middleware-Sprint-Validate-Touch wären beides Kandidaten
- **Details:** ADRs dokumentieren *Entscheidungen* mit Kontext, Optionen, Begründung. Incidents dokumentieren *Vorfälle* mit Hergang, Root-Cause, Lessons-Learned, Mitigationen. Separater Folder `docs/incidents/` mit eigenem Template. Initial: 2-3 retrospektive Incidents als Beispiele (Auto-Probe 12.05., SQL-Validate-Live-DB-Touch 14.05., MoltyCel-PAT-Cascade-Failure 12.05.).

---

## Changelog

- **2026-05-15 — V1.4**: API-Sprint-Übergabe aus moltrust-web Phase-1-Analyse §8 als verfolgbare Items aufgenommen, ausgelöst durch den Versionierungs-Audit am 2026-05-15 (~/moltstack/audits/2026-05-15_api-versioning.md) und die Conversion-Chat-Nachfrage zur §8-Kommunikation.
  - **Neu High (1):** AAE ins Credential einbauen (Phase-1 UNC-07 + Lars-Entscheidung) — koordinieren mit Credit-Middleware-Idempotency-Sprint (beide Schema-Change auf /identity/register, nicht parallel).
  - **Neu Medium (4):** API-Versionierung Single-Source + v1-Contract klären (Audit-Befunde: 3 Stellen ohne zentrale Quelle, Rückwärts-Dekrement 2.6→2.4, 0/136 Pfade versioniert), Trust-Score-Reads Rate-Limiting (Handler-Signatur-Refactor), CAEP als Extension in agent-card.json deklarieren, .well-known-Mirror-Generierung + Deprecation-Header.
  - **Sequenzierungs-Hinweis:** AAE-Sprint und Credit-Idempotency-Sprint berühren beide /identity/register — Reihenfolge ist Lars-Entscheidung, aber nicht parallel laufen lassen.
  - moltrust-web kann die "embedded AAE"-Darstellung erst nach Merge des AAE-Sprints zeigen; bis dahin entschärft PR1 die Falschaussage zu "separater delegation/configure-Schritt".
- **2026-05-15 — V1.3**: Credit-Middleware-Sprint 14./15.05. abgeschlossen (PR #27 merged), Out-of-Scope-Items + Health-Check-Findings nachgezogen.
  - **Resolved (raus):** `agents/traffic_monitor.py File-vs-DB Architektur` — heutige Entscheidung file-based v2 wiederhergestellt + cron wieder funktional, Item geschlossen.
  - **Neu High (2):** Credit-Middleware Idempotency-Mechanismus (GPT-5 Cross-Review CRITICAL F, eigenes Feature mit Schema-Change), cron.service OOM-kill investigieren (Health-Check 14.05. 02:01 UTC).
  - **Neu Medium (7):** Credit-Middleware process-wide-Scope + Inversion debit-vor-call_next (Spec V2.1 Section 9.2), WORKFLOW.md V1.2 — heutige Lessons einarbeiten (SQL-Validation, fetch-vor-Branch, /tmp-Dateien), tx_type CHECK + FK credit_transactions→credit_balances, FastAPI on_event → lifespan Migration (4 DeprecationWarnings im Test-Output), traffic_monitor.py in Watchdog AGENTS-Liste, migrations/add_outcome_tracker.sql Altlast klären, Auto-Probe-Migrations Repo-Status verifizieren, Stash-Hygiene Post-Credit-Sprint (konsolidiert mit altem "Stash@{0} Post-Triage Review").
  - **Neu Low (3):** Separate Test-DB für Credit-Tests, known_callers Tabelle DROP/Migration (45 rows, seit 18.04. stale), logrotate permissions fix (moltguard.log 19.8 MB).
  - **Neu Bootstrap (1):** docs/incidents/ Folder als Konzept einführen.
  - **Umformuliert:** `experiments/xmtp/ Sandbox-Architektur-Entscheidung` → zusammengezogen mit dem neuen XMTP-v3-Stash zu einem Item "XMTP v3 Migration testen + committen, dann Sandbox-Architektur entscheiden" mit Reihenfolge-Hinweis.
  - **ADR-Liste in `docs/decisions/`-Item ergänzt** um ADR (6) Credit-Middleware Minimal-Variante als bewusste Scope-Entscheidung des 15.05.-Sprints.
- **2026-05-13 — V1.2**: Drei resolved-by-action Items entfernt: TrustScout reanimate/decommission (resolved durch Diagnose 13.05. → PR #22 permanently removed Watchdog-Eintrag), TrustScout-Silencing-Commit (resolved durch PR #21 + #22), Memory #25 TrustScout-crontab-Lüge (resolved durch Memory-Replace 12.05.). Zwei neue Low-Items hinzu: trustscout.py + 2 systemd-Service-Files Investigation (offene Architektur-Frage, kein akuter Fix nötig), 5 stale lokale Branches Cleanup.
- **2026-05-13 — V1.1**: BACKLOG-Audit gegen Server-State durchgeführt (4 von 30 Items stale: stash-Claims falsch, herald_v3.py uuid-pattern nicht im File, settlement.py isinstance-Pattern anders als vermutet, KNOWN_FAILURES-Tests nicht im File). CAEP v2 umformuliert per Lars-Korrektur (nicht blocked auf Harald, sondern neuer Sprint mit Cross-LLM-Review). Telegram-Token-Item präzisiert (Rotation done by Lars server-side, verbleibendes Issue ist httpx-Log-Leak). Stash@{0} Post-Triage Review als neues Medium-Item hinzu.
- **2026-05-13 — V1**: Initial. Konsolidiert offene Items aus 12.05.26 (Auto-Probe-Drama) + 13.05.26 (WORKFLOW.md V1-Merge).
