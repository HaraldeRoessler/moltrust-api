# Incident — Öffentlich exponierter Live-Bootstrap-Key `mt_test_key_2026`

| Feld | Wert |
|---|---|
| **Datum** | 2026-05-22 |
| **Incident-ID** | INC-2026-05-22-test-key-exposure |
| **Severity** | **HIGH** — voll privilegierter Live-Bootstrap-API-Key öffentlich exponiert |
| **Status** | **RESOLVED** (2026-05-22) |
| **Betroffene Systeme** | `moltrust-api` (Auth), `moltrust-mcp-server` (Public-Repo + PyPI) |
| **Verantwortlich** | Lars Kroehl / CryptoKRI GmbH |

---

## 1. Zusammenfassung

Der API-Key `mt_test_key_2026` war im öffentlichen Repo `MoltyCel/moltrust-mcp-server`
(`README.md`, „Setup"-Abschnitt) seit dem Initial-Release als Onboarding-„Test-Key"
annonciert. Der Key war **kein** Sandbox-Key: Er war der **einzige** Eintrag in der
Env-Var `MOLTRUST_API_KEYS` und damit ein **voll privilegierter Produktiv-Bootstrap-Key**.
`verify_api_key` (`app/main.py:628`) prüft nur Set-Mitgliedschaft — **kein Tier-/Scope-Gate**.
Jeder, der den README las, konnte damit gegen alle `verify_api_key`-Write-Endpoints
authentifizieren (`/identity/register`, `/reputation/rate`, `/credentials/issue`,
`/identity/bind`, `/identity/bridge`, `set_agent_class`).

Behoben in vier Phasen am 2026-05-22: Server-Revocation (Replace durch neuen privaten
Bootstrap-Key), Git-History-Scrub des mcp-server-Repos, Working-Tree-Redact in
moltrust-api, Dokumentation (dieser Doc).

---

## 2. Timeline (alle Zeiten UTC)

| Zeitpunkt | Ereignis |
|---|---|
| 2026-03-09 | `moltrust-sdk`-Key-Scrub: `mt_test_key_2026` per `git-filter-repo` aus der SDK-History entfernt + Force-Push (siehe Memory). **Lücke:** der mcp-server-README blieb unangetastet. |
| 2026-05-22 | **Discovery** — Visibility-Sprint-Audit deckt den Live-Key im `moltrust-mcp-server`-README auf (Glama-Listing-Sichtprüfung). |
| 2026-05-22 · P0 | README-Cleanup `moltrust-mcp-server` (Commit `6a8dc07`) — Key-Zeile aus „Setup" entfernt (kosmetisch). |
| 2026-05-22 · P1 | **Server-Revocation** — `mt_test_key_2026` aus `MOLTRUST_API_KEYS` ersetzt durch neuen privaten Bootstrap-Key, DB-Row deaktiviert, `moltstack.service` neugestartet. |
| 2026-05-22 · P2-SPEC | Scrub-SPEC erstellt + abgenommen (PR #60). |
| 2026-05-22 · P2a | `moltrust-mcp-server` Git-History-Scrub (`git-filter-repo`) + §2.3-Cross-Review + Force-Push. |
| 2026-05-22 · P2b | `moltrust-api` `pentest.sh` Working-Tree-Redact (PR #61). |
| 2026-05-22 · P4 | Incident-Dokumentation (dieser Doc). |

---

## 3. Discovery

Der Befund entstand **nicht** durch einen gezielten Security-Scan, sondern als
**Nebenbefund eines Visibility-Sprint-Audits**: Bei der read-only Prüfung, welche
MCP-Registry-/Directory-Listings live sind, lieferte eine Web-Suche das
Glama-Listing `glama.ai/mcp/servers/@MoltyCel/mol-trust`. Dessen aus dem GitHub-README
gespeiste Beschreibung zitierte `mt_test_key_2026` wörtlich als nutzbaren „test key".
Der Befund wurde im Audit-Output als Security-Nebenbefund markiert und anschließend
als eigener Incident-Sprint aufgegriffen.

→ Siehe Lessons §8: „Entdeckbarkeit = Definition of Done" hat hier **defensiv**
funktioniert — derselbe Audit-Schritt, der die Außenwirkung prüft, fand das Leck.

---

## 4. Scope

### 4.1 Charakter des Keys
- **Einziger** Eintrag in `MOLTRUST_API_KEYS` (Env-Var, `~/.moltrust_secrets`) — d.h.
  Entfernen ohne Ersatz hätte `app/main.py:182` `RuntimeError` ausgelöst → Service-Ausfall.
- Zusätzlich als aktive DB-Row in `api_keys` (`tier=standard`, `email='env-hardcoded'`).
- **Kein Tier-/Scope-Gate** — voll privilegiert für alle `Depends(verify_api_key)`-Routen.

### 4.2 Exposure-Flächen
| Ort | Umfang |
|---|---|
| `moltrust-mcp-server` (PUBLIC) | `README.md`, seit Initial-Commit `46122eb` (v0.1.0); 37 Commits (main+Tags) / 40 im `--mirror` (inkl. `refs/pull/*`); 13 Tags `v0.3.0`–`v1.2.0` |
| `moltrust-api` (PUBLIC) | 9 Dateien über die Full-History: `app/main.py`, `app/main.py.bak`, `app/main.py.bak2`, `mcp_server.py`, `operator/agent.py.bak`, `seed_ecosystem.py`, `test_sandbox.py`, `pentest.sh`, `docs/auto-probe-token-spec.md`; 220 Commits / 10 Branches / 2 Tags. Im **Working-Tree** nur `pentest.sh`. |
| PyPI | `moltrust-mcp-server`, 14 Releases `0.1.0`–`1.2.0` — Key im README/`long_description` aller Releases |
| Sekundär | je 1 Fork pro Repo; Such-Index-Caches; Glama-Listing-Cache |

---

## 5. Maßnahmen pro Phase + Verifikation

### P0 — README-Cleanup (kosmetisch)
`moltrust-mcp-server/README.md` Setup-Zeile von Key-Annonce auf Signup-only
geändert (Commit `6a8dc07`). **Wichtig:** rein kosmetisch — der Key blieb live.

### P1 — Server-Revocation (Replace, nicht Delete)
- Backup `~/secret-backups/moltrust_secrets.20260522T112910Z` (`chmod 600`, byte-identisch verifiziert).
- Neuer privater Bootstrap-Key server-seitig generiert (Format `mt_<32hex>`) — **nicht in diesem Doc**, liegt in `~/.moltrust_secrets`.
- `MOLTRUST_API_KEYS` ersetzt; alle übrigen 67 Secret-Zeilen md5-verifiziert unverändert.
- DB: `UPDATE api_keys SET active=false WHERE key='mt_test_key_2026'` + neuer Key als Row (`active`, `tier=standard`, `email='env-bootstrap'`) — nötig, weil der Startup-Hook `load_api_keys()` (`app/main.py:3097`) alle aktiven DB-Keys lädt.
- `moltstack.service` neugestartet.
- **Verifikation:** alter Key → **401** (lokal + public durch nginx); neuer Key → 200; bestehender DB-Key → 200 (Regression); `/health` → 200; DB-active-count 57; Startup-Log `Loaded 57 API keys from DB`, kein `RuntimeError`.

### P2-SPEC — Scrub-Spezifikation
`docs/specs/2026-05-22_test-key-history-scrub-SPEC.md`, abgenommen + gemergt (PR #60).
Entscheidung moltrust-api = **Option C** (kein History-Rewrite — siehe §6 Begründung).

### P2a — `moltrust-mcp-server` Git-History-Scrub
- Dated `--mirror`-Backup `~/scrub-backups/moltrust-mcp-server.mirror.20260522T114702Z`.
- `python3 -m git_filter_repo --replace-text` mit Regel `mt_test_key_2026==>***REMOVED***` auf frischem Mirror.
- **§2.3-Cross-Review** (GPT-4o + Gemini 2.5 Flash + Perplexity → Claude-Synthese; Report `~/moltstack/reviews/20260522_115041_p2a-scrub-filterrepo_review.md`): Verdikt **ÜBERARBEITEN** → Revisionen umgesetzt: `publish.yml` vor dem Tag-Push deaktiviert, Race-Check (origin vs. Backup-Mirror), **explizite Refspecs statt `--mirror`** (der Mirror enthielt `refs/pull/*`, die GitHub beim Push ablehnt).
- Force-Push: `main` `6a8dc07→9f6013c` + alle 13 Tags; `publish.yml` reaktiviert.
- **Verifikation:** `mt_test_key_2026` = **0 Treffer** über `origin/main` + alle 13 Tags (Frischklon); `***REMOVED***` in README-History vorhanden; **0 spurious** `publish.yml`-Runs; `ci.yml`-Run vom main-Push = success.

### P2b — `moltrust-api` Working-Tree-Redact (Option C)
`pentest.sh:5` `KEY="mt_test_key_2026"` → `KEY="***REMOVED***"` — einzige Datei mit
Key im Working-Tree. Regulärer Commit, PR #61, kein History-Rewrite, kein §2.3-Review
(nicht destruktiv).

---

## 6. Residuen — verbleibende Vorkommen + warum tragbar

**Grundlage der Tragbarkeit:** Der Key ist seit P1 **revoked und tot** — jeder
verbleibende String `mt_test_key_2026` erzeugt **kein** Auth-Risiko mehr. Die
folgenden Residuen sind dokumentiert akzeptiert (konsistent mit SPEC §12):

| Residual | Grund / Begründung |
|---|---|
| `refs/pull/1` + `refs/pull/11` (mcp-server, GitHub) | `refs/pull/*` ist GitHub-immutable — nicht überschreib-/löschbar. Tragbar: Key tot. |
| Fork `ElishaKay/moltrust-mcp-server` | Dritt-Fork, kein Schreibzugriff — behält Alt-History. Tragbar: Key tot. |
| `moltrust-api` Full-History (8 History-only-Dateien) | Option C = bewusst **kein** Rewrite (220 Commits / 10 Branches / 4 offene PRs — unverhältnismäßig für toten Key). Tragbar: Key tot. |
| GitHub-Commit-SHA-Caches | Alte SHAs evtl. per Direkt-URL erreichbar bis GitHub-GC — klingt ab. |
| PyPI Releases `0.1.0`–`1.2.0` | Artefakte immutable — Key bleibt im README. Adressiert durch Folge-Item PyPI `1.2.1` (§7). |
| Such-Index- / Glama-Caches | Klingen über Tage/Wochen nach Re-Crawl ab — kein aktiver Eingriff möglich. |

---

## 7. Folge-Items

1. **PyPI `1.2.1`-Release** mit bereinigtem README — separater Folge-Sprint (SPEC §6 Opt a; kein Yank der Alt-Versionen).
2. **Voll-Secret-Scan `moltrust-api` Full-History** — bereits als BACKLOG-Item (Low) erfasst (`docs/BACKLOG.md`, V1.5); Vorbedingung für einen etwaigen späteren moltrust-api-History-Rewrite. Commit `e51c05a` („hardcoded key … CLI private key") deutet auf weitere Alt-Secrets.
3. **Pre-push Token-/Secret-Audit-Hook** — strukturelle Prävention (§9). **Hinweis:** Aktuell existiert hierfür **kein** dediziertes BACKLOG-Item; nächstverwandt sind die `weekly_health_check.sh`-„Token-Audit"-Komponente (anderer Mechanismus, kein Pre-push-Gate) und das „Pre-commit-hook conflict-marker-check"-Item (anderer Zweck). **Empfehlung: eigenes BACKLOG-Item anlegen.**

---

## 8. Lessons Learned

1. **Bootstrap-Keys gehören nie in öffentliche README-Files — auch nicht als „Test-Key".**
   Die „Test-Key"-Benennung suggerierte Harmlosigkeit; tatsächlich war es der einzige,
   voll privilegierte Bootstrap-Key. Ein als public-demo gedachter Key braucht einen
   echten Scope-/Tier-Mechanismus — den gibt es derzeit nicht (`verify_api_key` kennt
   kein Tiering).

2. **Working-Tree-Redact ≠ History-Scrub ≠ Revocation.** Der P0-README-Cleanup war
   rein kosmetisch — der Key blieb live. Ein Cosmetic-Fix darf nicht mit einer echten
   Revocation verwechselt werden. Die Reihenfolge muss immer sein: **erst revoken
   (P1), dann aufräumen (P2)**. Ein „aus dem README entfernt" ohne Revocation ist
   eine gefährliche Scheinsicherheit.

3. **Der Audit-Schritt im Visibility-Sprint hat den Befund gefunden.** Das Prinzip
   „Entdeckbarkeit = Definition of Done" (Discovery-Checklist) ist als Wachstums-Hebel
   gedacht — hier hat es **defensiv** funktioniert: Wer die eigene Außenwirkung
   systematisch prüft, findet dabei auch Lecks. Outbound-Audits haben Security-Wert.

4. **`MOLTRUST_API_KEYS` mit nur einem Key ist fragil.** Die Single-Key-Situation
   machte die naive „Key entfernen"-Annahme der ersten Plan-Iteration unausführbar
   (Service-Crash). Bootstrap-Auth sollte vom Public-Onboarding-Pfad getrennt sein.

---

## 9. Prävention

**Struktureller Schutz: Pre-push Token-/Secret-Audit-Hook.** Ein Git-`pre-push`-Hook
(bzw. CI-Gate) der Diffs/Blobs gegen bekannte Secret-Muster prüft (`mt_<hex>`-Keys,
`sk-…`, `ghp_…`, `github_pat_…` etc.) und den Push bei Treffer blockiert — der einzige
Mechanismus, der das ursprüngliche Leck (Key im Initial-Commit-README) **vor** der
Veröffentlichung gestoppt hätte. Als Folge-Item §7.3 zu führen.

Flankierend: Secret-Hygiene-Grundsätze gemäß **Memory #21 (Secret-Hygiene)** —
keine Secrets in Code/Repos/Logs, Bootstrap-Auth getrennt vom Public-Onboarding,
Leak → sofort rotieren (nicht nur verstecken).

---

## 10. Referenzen

- SPEC: `docs/specs/2026-05-22_test-key-history-scrub-SPEC.md`
- §2.3-Cross-Review: `~/moltstack/reviews/20260522_115041_p2a-scrub-filterrepo_review.md`
- PRs: `MoltyCel/moltrust-api#60` (SPEC), `#61` (P2b); `MoltyCel/moltrust-mcp-server` Commit `6a8dc07` (P0)
- BACKLOG: `docs/BACKLOG.md` — „Voll-Secret-Scan moltrust-api Full-History" (V1.5)
- Backups: `~/secret-backups/moltrust_secrets.20260522T112910Z` (P1), `~/scrub-backups/moltrust-mcp-server.mirror.20260522T114702Z` (P2a)
