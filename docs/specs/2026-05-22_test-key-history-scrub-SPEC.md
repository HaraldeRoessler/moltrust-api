# SPEC — Git-History-Scrub: Test-Key `mt_test_key_2026`

- **Datum:** 2026-05-22
- **Autor:** Lars Kroehl (CryptoKRI GmbH)
- **Status:** FINAL — Decisions (§10.3) eingearbeitet, Abnahme 2026-05-22. PR offen → wartet auf finale Abnahme + Merge. **Kein `git-filter-repo`-Run erfolgt.**
- **Sprint-Kontext:** Test-Key-Incident, Phase 2 (Phase 1 = Revocation, abgeschlossen).
- **Klasse:** Security-Incident, destruktiv-irreversibler History-Rewrite.

---

## 0. Kontext & Risiko-Einordnung (WICHTIG)

Phase 1 (Revocation) ist am **2026-05-22 abgeschlossen und verifiziert**:
`mt_test_key_2026` wurde aus `MOLTRUST_API_KEYS` entfernt, die DB-Row
`active=false` gesetzt, `moltstack.service` neugestartet — Live-Probe:
alter Key → **401**, neuer Bootstrap-Key → 200, 56 echte Consumer → 200.

→ **Der Key ist tot.** Dieser Phase-2-Scrub ist **Hygiene / Defense-in-Depth**,
**keine** Mitigation eines aktiven Risikos. Ein in History/PyPI/Forks
verbleibender String `mt_test_key_2026` erzeugt **kein** Auth-Risiko mehr.

Konsequenz für die Abnahme: Aufwand und Disruption (siehe §4, §10) müssen
gegen ein **bereits geschlossenes** Risiko abgewogen werden.

---

## 1. Scrub-Target — Bestandsaufnahme (read-only verifiziert 2026-05-22)

| Repo | Sichtbarkeit | Vorkommen `mt_test_key_2026` | History-Umfang | Offene PRs | Forks |
|---|---|---|---|---|---|
| `moltrust-sdk` | — | **bereits gescrubbt 2026-03-09** (git-filter-repo, force-push) | — | — | — |
| `moltrust-mcp-server` | PUBLIC | **1 Datei:** `README.md` | 37 Commits, 1 Branch, **13 Tags** (v0.3.0–v1.2.0) | 0 | 1 (`ElishaKay/moltrust-mcp-server`) |
| `moltrust-api` | PUBLIC | **9 Dateien** (s.u.) | 220 Commits, 10 Branches, 2 Tags | **4+ (#3,#4,#7,#10)** | 1 |

**moltrust-mcp-server** — `mt_test_key_2026` eingeführt in `46122eb`
(Initial release v0.1.0), entfernt in `6a8dc07` (Phase-0-Cleanup, 2026-05-22).
Alle 13 Tags zeigen auf Commits **vor** `6a8dc07` → **alle Tags enthalten den Key**.
Pattern-Scan der Full History (`ghp_`, `github_pat_`, `sk-ant-`, `sk_live_`,
`AKIA…`, `mt_<32hex>`): **keine weiteren Secrets**.

**moltrust-api** — Key in 9 Dateien über die History:
`app/main.py`, `app/main.py.bak`, `app/main.py.bak2`, `mcp_server.py`,
`operator/agent.py.bak`, `seed_ecosystem.py`, `test_sandbox.py`,
`pentest.sh`, `docs/auto-probe-token-spec.md`.
Betroffene Commits u.a.: `6c6a892` (Initial commit), `e51c05a`
(`fix(security): CRITICAL-1,2,5 — hardcoded key, …`).

> ⚠️ **Scope-Abweichung vom Auftrag.** Auftragspunkt 6 nahm „nur `pentest.sh`"
> an. Tatsächlich ist der Key in **9 Dateien** inkl. `app/main.py` und mehreren
> `.bak`-Files. Der Commit-Titel `e51c05a` („hardcoded key … CLI private key")
> deutet zudem auf **weitere historische Secrets** in moltrust-api hin — ein
> moltrust-api-Rewrite erfordert daher einen vorgeschalteten Voll-Secret-Scan
> (gitleaks/trufflehog), nicht nur das `mt_test_key_2026`-Pattern.
>
> **Abnahme 2026-05-22:** als BACKLOG-Item in moltrust-api `docs/BACKLOG.md`
> ausgelagert — Vorbedingung für einen etwaigen späteren moltrust-api-Rewrite.

---

## 2. Methode

- **Werkzeug:** `git-filter-repo`, aufgerufen als `python3 -m git_filter_repo`
  (Modul installiert: `~/Library/Python/3.9/lib/python/site-packages/git_filter_repo.py`;
  das `git filter-repo`-Subkommando ist **nicht** im PATH).
  BFG ausgeschlossen — bekannte Bugs mit neueren git-Versionen.
- **Pre-Flight:** `python3 -m git_filter_repo --version` prüfen; auf einer
  **frischen `--mirror`-Clone** arbeiten (nicht im Arbeits-Checkout).
- **Ersetzung:** `--replace-text` mit Replacements-Datei. filter-repo ersetzt
  den Literal-String in **allen Blobs über alle Refs** (Branches **und** Tags),
  Commit-Struktur bleibt erhalten, alle SHAs ändern sich.
- **Replacements-Datei** (`/tmp/scrub-replacements.txt`):
  ```
  mt_test_key_2026==>***REMOVED***
  ```
  (`==>`-Syntax = explizites Ziel; ohne `==>` ersetzt filter-repo per Default
  ebenfalls mit `***REMOVED***`.)

### 2.1 Exakte Befehle — moltrust-mcp-server (Primär-Ziel)

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)

# (A) Mirror-Backup VOR dem Run — Rollback-Quelle, unangetastet lassen
mkdir -p ~/scrub-backups && chmod 700 ~/scrub-backups
git clone --mirror https://github.com/MoltyCel/moltrust-mcp-server.git \
  ~/scrub-backups/moltrust-mcp-server.mirror.$TS

# (B) Separater frischer Mirror für den Rewrite
git clone --mirror https://github.com/MoltyCel/moltrust-mcp-server.git \
  /tmp/scrub-mcp.git
cd /tmp/scrub-mcp.git

# (C) Replacements-Datei
printf 'mt_test_key_2026==>***REMOVED***\n' > /tmp/scrub-replacements.txt

# (D) Rewrite — alle Branches + alle Tags
python3 -m git_filter_repo --replace-text /tmp/scrub-replacements.txt --force

# (E) Verifikation VOR Push (siehe §8 Cross-Review-Gate)
git log --all -S'mt_test_key_2026' --oneline      # erwartet: leer
git grep -l 'mt_test_key_2026' $(git rev-list --all) 2>/dev/null  # erwartet: leer

# (F) Force-Push — erst NACH bestandenem Cross-Review + Lars-Bestätigung
git remote add origin https://github.com/MoltyCel/moltrust-mcp-server.git
git push --force origin 'refs/heads/*'
git push --force origin 'refs/tags/*'
```

> filter-repo entfernt nach dem Run das `origin`-Remote (Sicherheitsfeature) —
> daher Schritt (F) `git remote add` vor dem Push.

### 2.2 moltrust-api — siehe §10 (Entscheidungspunkt, Befehle erst nach Scope-Abnahme)

---

## 3. Backup / Mirror

- **Vor JEDEM filter-repo-Run** ein dated `--mirror`-Backup nach
  `~/scrub-backups/<repo>.mirror.<TS>` (`chmod 700` Verzeichnis).
- `--mirror` sichert **alle** Refs (Branches, Tags, Notes) 1:1.
- Das Backup-Mirror bleibt **unangetastet** = einzige Rollback-Quelle.
- Aufbewahrung mind. bis Sprint-Abschluss + Lars-Sichtkontrolle.

---

## 4. Force-Push-Strategie

- Nach dem Rewrite: `git push --force origin 'refs/heads/*' 'refs/tags/*'`.
- **moltrust-mcp-server:** `main` + 13 Tags. 0 offene PRs → **keine PR-Breakage**.
  Geringe Disruption, einziges Risiko = lokale Klone Dritter (Re-Clone nötig).
- **moltrust-api:** `main` + 10 Branches + 2 Tags. **4+ offene PRs (#3, #4, #7,
  #10) werden durch den Force-Push un-mergebar** — ihre Basis-History ändert
  sich vollständig. → Harte Vorbedingung: PRs vorher mergen/schließen, oder
  nach dem Rewrite neu erstellen (Branch-Rebase auf neue History).
- **Tags:** filter-repo schreibt Tag-Objekte um; Force-Push mit `--force`.
  Wer einen Tag gepinnt hat, bekommt nach Re-Fetch einen anderen Commit.
  PyPI-Release-Artefakte sind davon **unberührt** (immutable, siehe §6).

---

## 5. Forks

- `moltrust-mcp-server` → Fork `ElishaKay/moltrust-mcp-server`.
- `moltrust-api` → 1 Fork.
- **Forks behalten die alte History.** Der Key kann in einem Fremd-Fork
  **nicht** entfernt werden (kein Schreibzugriff).
- **Akzeptiertes Residual:** Forks tragen den String `mt_test_key_2026`
  dauerhaft weiter. Tragbar, weil der Key revoked ist (Phase 1) — der String
  in einem Fork ist wertlos. Wird in §9 / Incident-Doc als akzeptiertes
  Restrisiko dokumentiert. Keine Maßnahme.

---

## 6. NPM / PyPI

- **npm:** `moltrust-mcp-server` → HTTP 404, **nicht auf npm**. Keine Maßnahme.
- **PyPI:** `moltrust-mcp-server`, 14 Releases `0.1.0`–`1.2.0`. Der Key steht
  im README/`long_description` — für `1.2.0` bestätigt (`True`), für alle
  früheren Releases analog (Key war von v0.1.0 bis `6a8dc07` durchgehend im
  README).
- **PyPI-Artefakte sind immutable** — ein git-History-Scrub berührt sie **nicht**.
  Eine bereits hochgeladene Version kann nicht überschrieben werden.
- **Optionen:**
  - **(a) Neues Release `1.2.1`** mit dem bereinigten README (`6a8dc07`).
    Projekt-Seite + neue Installs zeigen dann clean. Alt-Versionen bleiben per
    exaktem Pin (`==1.2.0`) installierbar. — **Empfohlen.**
  - **(b) Yank** der 14 Alt-Versionen: „yanked" = aus der Auflösung versteckt,
    aber per `==`-Pin weiter installierbar; **löscht nichts**. 14 Versionen zu
    yanken bestraft bestehende (gepinnte) Consumer mit Install-Warnungen für
    **null** Security-Gewinn (Key ist tot). — **Nicht empfohlen.**
- **Empfehlung:** nur **(a)** — `1.2.1` mit cleanem README publishen, **kein**
  Yank. Incident-Doc vermerkt: historische Releases tragen einen nun toten
  Key-String.
- **Entscheidung (Abnahme 2026-05-22):** Opt (a). Das `1.2.1`-Release ist ein
  **separater Folge-Sprint nach dem mcp-server-Scrub (P2a)** — nicht Teil von
  P2a/P2b. Kein Yank.

---

## 7. Glama / MCP-Registry Cache

- **Glama:** indexiert das GitHub-README. `6a8dc07` (Phase 0) hat den Working-
  Tree bereits bereinigt; Glama übernimmt das beim nächsten Crawl. Manueller
  Re-Index: über die Server-Seite/Claim-Flow auf glama.ai — **best effort**,
  nach Force-Push + `1.2.1`-Release antriggern.
- **Offizielle MCP-Registry:** die `server.json`-`description` enthielt den Key
  **nie** (nur der README-Body). Ein `1.2.1`-Release + Registry-Update
  spiegelt den cleanen Stand.

---

## 8. §2.3 Cross-Review (Gate vor Ausführung)

- **Geltung:** nur **P2a** (filter-repo + Force-Push = destruktiv-irreversibel).
  **P2b** (moltrust-api Working-Tree-Redact) ist ein regulärer Commit → **kein**
  §2.3-Review nötig (Abnahme 2026-05-22).
- **Vor dem Force-Push** ein fokussierter 3-Modell-Cross-Review
  (`ai_review.py`, GPT-4o + Gemini + Claude-Synthese — **kein** voller
  Security-Mode).
- **Review-Scope:** (a) exakter `filter-repo`-Befehl + Replacements-Datei,
  (b) Force-Push-Kommandos, (c) Rollback-Sequenz (§9).
- **Gate:** Der Review muss **ohne Blocker** abschließen, bevor irgendein Push
  erfolgt. Output → `~/moltstack/reviews/`.
- Verifikation aus §2.1 Schritt (E) (`-S`-Log + `git grep` leer) ist
  Bestandteil des Review-Inputs.

---

## 9. Rollback-Plan

- **Quelle:** das unangetastete dated `--mirror`-Backup aus §3.
- **Restore-Sequenz** (pro Repo):
  ```bash
  cd ~/scrub-backups/<repo>.mirror.<TS>
  git remote set-url origin https://github.com/MoltyCel/<repo>.git   # falls nötig
  git push --mirror --force origin
  ```
  `push --mirror` stellt **alle** Refs exakt auf den Pre-Scrub-Stand zurück.
- **Lokale Klone:** nach Rewrite **und** nach Rollback ungültig — jeder
  Mitarbeiter muss neu klonen oder `git reset --hard origin/<branch>` +
  `git fetch --prune` (alle SHAs haben sich geändert).
- **Worktrees:** alle bestehenden Worktrees der betroffenen Repos vor dem
  Rewrite entfernen/prunen, danach neu anlegen.

---

## 10. Empfehlung & Entscheidungspunkte für die Abnahme

### 10.1 moltrust-mcp-server — **AUSFÜHREN** (Empfehlung)
Günstig und sauber: 1 Datei, 0 offene PRs, 1 Branch, Public, primäre
Glama-sichtbare Exposure. Befehle §2.1. Disruption minimal.

### 10.2 moltrust-api — **ENTSCHIEDEN (Abnahme 2026-05-22): Option C**
Ein Full-History-Rewrite eines **220-Commit / 10-Branch Public-Repos mit 4+
offenen PRs** — für einen **toten** Key — wäre hoch-disruptiv bei geringem
Gewinn. Bewertete Optionen:

| Opt | Vorgehen | Disruption | Wahl |
|---|---|---|---|
| A | Full Scrub aller Refs — PRs #3/#4/#7/#10 vorher mergen/schließen; 10 Branches + 2 Tags rewrite | Hoch | — |
| B | Nur `main` scrubben — Key bleibt in Stale-Branch-History | Mittel | — |
| **C** | **Kein Rewrite** — Working-Tree-Redact, Key → `***REMOVED***`, regulärer Commit | Minimal | **✅ GEWÄHLT** |
| D | Full Scrub aufschieben bis offene PRs gelandet | (verschoben) | optional |

**Entscheidung: Option C** — kein History-Rewrite von moltrust-api. Da der Key
revoked ist, ist ein Public-Repo-Rewrite, der 4 PRs bricht, unverhältnismäßig.

**Working-Tree-Stand verifiziert (2026-05-22, origin/main):** Von den 9
History-Dateien enthält **nur `pentest.sh:5`** den Key aktuell im Working-Tree.
`app/main.py`, `mcp_server.py`, `seed_ecosystem.py`, `test_sandbox.py` existieren,
tragen den Key aber **nicht mehr** (durch frühere Commits entfernt); die drei
`.bak`-Dateien + `docs/auto-probe-token-spec.md` existieren gar nicht mehr.

→ **P2b redactet faktisch nur `pentest.sh`** (Key → `***REMOVED***`, regulärer
Commit, kein filter-repo). Die 8 History-only-Vorkommen bleiben unter Option C
in der History — akzeptiertes Residual (§12), Key ist tot. Ein etwaiger
späterer Full-Scrub (Opt D) braucht zwingend den vorgeschalteten Voll-Secret-
Scan (BACKLOG, §1 / §10.3 Pkt 5).

### 10.3 Entscheidungen (Abnahme 2026-05-22)
1. **moltrust-api Scope: Option C** — kein Rewrite, Working-Tree-Redact (= P2b).
2. **PyPI `1.2.1`:** separater Folge-Sprint **nach** dem mcp-server-Scrub (P2a).
3. **Replacement-String:** `***REMOVED***`.
4. **Reihenfolge:** **P2a** (moltrust-mcp-server filter-repo + Force-Push) zuerst,
   dann **P2b** (moltrust-api Working-Tree-Redact).
5. **Voll-Secret-Scan moltrust-api Full-History:** als separates BACKLOG-Item
   (moltrust-api `docs/BACKLOG.md`) — Vorbedingung für einen etwaigen späteren
   Full-Scrub (Opt D).

---

## 11. Ausführungs-Reihenfolge (NACH finaler Spec-Abnahme + Merge)

**P2a — moltrust-mcp-server History-Scrub (§2.3-Review-pflichtig):**
1. Pre-Flight: `filter-repo`-Version prüfen, Working-Trees prunen.
2. Dated `--mirror`-Backup (§3).
3. `filter-repo`-Run auf frischem Mirror (§2.1 A–D).
4. Lokale Verifikation (§2.1 E) — `-S`-Log + `git grep` müssen leer sein.
5. §2.3 Cross-Review-Gate (§8) — Output abwarten, Blocker = STOP.
6. Force-Push `main` + 13 Tags (Lars-Bestätigung).
7. Glama / MCP-Registry Re-Index antriggern (§7).

**P2b — moltrust-api Working-Tree-Redact (regulärer Commit, KEIN §2.3-Review):**
8. `pentest.sh` — Key durch `***REMOVED***` ersetzen (einzige Working-Tree-Datei).
9. Pre-Commit-Diff, regulärer Commit, PR, Merge.

**Folge-Sprints (separat, nicht Teil von P2a/P2b):**
10. PyPI `1.2.1`-Release mit cleanem README (§6 Opt a).
11. Incident-Doc (`docs/incidents/`) — Sprint-Phase 4.
12. BACKLOG: Voll-Secret-Scan moltrust-api Full-History (Vorbedingung Opt D).

---

## 12. Akzeptierte Restrisiken

- Fremd-Forks behalten `mt_test_key_2026` in History (§5) — tragbar, Key tot.
- PyPI-Alt-Releases `0.1.0`–`1.2.0` behalten den String im README (§6) —
  tragbar, Key tot; `1.2.1` stellt cleanen Default her.
- **moltrust-api History** behält `mt_test_key_2026` in 8 History-only-Dateien
  (Option C, kein Rewrite) — tragbar, Key tot; der Working-Tree wird via P2b
  bereinigt.
- Such-Index-/Cache-Restbestände (Google, Glama-Cache) klingen über Tage/Wochen
  nach dem Force-Push + Re-Index ab — kein aktiver Eingriff möglich.
