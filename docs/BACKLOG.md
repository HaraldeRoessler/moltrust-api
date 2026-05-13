# BACKLOG.md — MolTrust Open Items

**Status:** V1.1, lebendiges Dokument
**Letzte Aktualisierung:** 2026-05-13
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

### TrustScout: reanimate oder decommission
- **Status:** Open
- **Aufwand:** M
- **Added:** 2026-05-12
- **Source:** Konversation 12.05.26 (Auto-Probe-Drama-Tag), Memory #25
- **Details:** Drei Scout-Files koexistieren (`scout.py`, `trustscout.py`, `news_scout.py`) — nur scout.py läuft 2x/day per cron, trustscout.py orphaned. DB-Heartbeat 74 Tage alt. Heartbeat-File 41h alt. Watchdog temporär silenced. Decision: reanimate via cron auf trustscout.py umstellen ODER decommission permanent + Code-Cleanup.

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

### TrustScout-Silencing als separater Commit
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** WORKFLOW.md Sektion 4.2 Working-Tree-Hygiene
- **Details:** TEMP DISABLED watchdog.py-Änderung lebt aktuell als uncommitted Working-Tree-Modifikation. Sollte auf `chore/trustscout-silence-2026-05-12` Branch committed werden — bis Reanimate/Decommission-Decision getroffen ist.

### Memory #25 TrustScout-Crontab-Lüge korrigieren
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-12
- **Source:** Diagnostic 12.05.26
- **Details:** Memory sagt "TrustScout (crontab 4x/day)" — Realität: scout.py läuft 2x/day, trustscout.py wird gar nicht getriggert. Memory-Realitäts-Sync (WORKFLOW Sektion 4.3) muss greifen.

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

### experiments/xmtp/ Sandbox-Architektur-Entscheidung
- **Status:** Deferred (Decision needed)
- **Aufwand:** M
- **Added:** 2026-05-12
- **Source:** Commit 4b skip-Entscheidung 12.05.26
- **Details:** `scripts/outreach_xmtp.js` V3-Migration-Code aktuell als Working-Tree-Modifikation (M), nicht im Stash. Script kann deps in `experiments/xmtp/node_modules/` nicht erreichen. Entscheidung: (α) viem zu experiments/xmtp/package.json + npm install, (β) Script relocaten nach experiments/xmtp/, (γ) eigenes node_modules für scripts/.

### agents/traffic_monitor.py File-vs-DB Architektur
- **Status:** Deferred (Decision needed)
- **Aufwand:** M
- **Added:** 2026-05-12
- **Source:** Commit 6 skip-Entscheidung 12.05.26 (Working-Tree-Rescue)
- **Details:** Working-Tree-Modifikation (M, nicht im Stash) enthält zwei v2-Versionen parallel: file-based (`known_ips.txt`) vs DB-based (`known_callers` table mit asyncpg). Mutually exclusive. Production-Impact = 0 (Script nicht im cron). Decision: welche v2 ist canonical.

### Stash@{0} Post-Triage Review
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-13
- **Source:** BACKLOG-Audit 13.05.26
- **Details:** Audit 13.05.26 zeigte: outreach_xmtp.js + traffic_monitor.py + watchdog.py existieren als Working-Tree-Modifikationen (M), aber Stash `pre-auto-probe-deploy-2026-05-12-WIP-incl-prediction-accuracy` existiert weiterhin. Vermutung: Working-Tree-Rescue gestern hat Files via `git checkout stash@{0} -- <file>` extrahiert, aber Stash dabei nicht reduziert — Files sind dupliziert in beiden Locations. Review: was ist tatsächlich noch im Stash drin, was redundant. Stash sauber droppen sobald nichts uniques mehr drin ist.

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
- **Details:** ADRs für (1) Auto-Probe V2-Architektur mounted-sub-app, (2) Pattern B credential-helper (Token-Rotation), (3) MCP-Tool-Convention beibehalten, (4) Sequential A/B-Test bei Smithery, (5) Memory-Reality-Sync-Pflicht.

### Multi-Repo-Inventory-File
- **Status:** Open
- **Aufwand:** S
- **Added:** 2026-05-13
- **Source:** WORKFLOW.md Sektion 7.1
- **Details:** `docs/repos.md` mit Liste aller MolTrust-Repos, Branch-Naming-Status, Cross-Dependencies, Verantwortung.

---

## Changelog

- **2026-05-13 — V1.1**: BACKLOG-Audit gegen Server-State durchgeführt (4 von 30 Items stale: stash-Claims falsch, herald_v3.py uuid-pattern nicht im File, settlement.py isinstance-Pattern anders als vermutet, KNOWN_FAILURES-Tests nicht im File). CAEP v2 umformuliert per Lars-Korrektur (nicht blocked auf Harald, sondern neuer Sprint mit Cross-LLM-Review). Telegram-Token-Item präzisiert (Rotation done by Lars server-side, verbleibendes Issue ist httpx-Log-Leak). Stash@{0} Post-Triage Review als neues Medium-Item hinzu.
- **2026-05-13 — V1**: Initial. Konsolidiert offene Items aus 12.05.26 (Auto-Probe-Drama) + 13.05.26 (WORKFLOW.md V1-Merge).
