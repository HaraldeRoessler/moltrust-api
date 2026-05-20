# Spec — moltguard-Repo nach GitHub bringen (MoltyCel/moltguard, §11.1)

**Status:** ENTWURF — Lars-Freigabe vor Code.
**§2.3-Cross-Review:** **Required für den Push-Commit selbst** — der Push exposes die gesamte Code-Historie, einschließlich Auth-/Credential-/Payment-Pfade, in einem öffentlichen Repo. Sekundärer Trigger: SPEC §9 BACKLOG-Item, das die Migration als „§11.1-Konformitätsblocker" deklariert.
**Datum:** 2026-05-20 · **Repo:** moltrust-api (für die SPEC-Datei) · **Branch:** docs/moltguard-remote-migration-spec
**BACKLOG-Mapping (verifiziert):** `docs/BACKLOG.md` Zeile 67-71 — „moltguard-Repo nach GitHub bringen (`MoltyCel/moltguard`, §11.1-Konformität)", Severity High, Aufwand L, Source: „MoltGuard-Discovery-Phase-1 SPEC §9.5 Drift-Forensik (PR #48)".

## 1. Goal

Den server-local-only moltguard-Repo (`~/moltguard/.git`, 32 Commits, 85 tracked Files) nach `MoltyCel/moltguard` migrieren, sodass:

- §11.1 `post-sha == repo-sha` mit einer externen Wahrheitsquelle prüfbar wird (statt nur server-on-disk).
- PR-Review-Workflow möglich wird (entscheidende Konsequenz aus den zwei Drift-Fällen aus Discovery-SPEC §9.5 — ein PR-Review hätte beide früher gefangen).
- Discovery-P2 Folge-Sprints (MoltGuard Validation Hardening, `/api/market/feed`-Doppelpfad) auf normalen PR-Pfaden laufen können.
- moltrust-api `extendedAgentCard` build-time-fetch (P3, live) ggf. langfristig durch Repo-Import statt HTTP-Fetch ersetzt werden kann (SPEC §9.4 Variante B).

## 2. Non-Goals

- **Keine** Codeänderungen an MoltGuard-Endpoints, Middleware oder Logik. Reine Repo-Operation.
- **Kein** Re-Deploy von MoltGuard — Service läuft unverändert weiter.
- **Keine** Adoption von Zod-Validierung oder zod-openapi-Codegen — das ist BACKLOG-Item „MoltGuard Validation Hardening" (Medium, separater Sprint).
- **Keine** Code-Reviews von Bestandscode — nur Sichtbarmachung. Inhaltliche Audits folgen via reguläre PR-Reviews bei künftigen Changes.
- **Kein** Push, bevor §3.1 Working-Tree-Triage abgeschlossen + §3.4 Secret-Audit final freigegeben.

## 3. Architecture-Layer-Scope *(Pflichtfeld)*

### 3.1 Working-Tree-Triage (8 modified + 14 untracked)

Live-State (verifiziert 2026-05-20):

**Modified (8) — Inhalts-Triage erforderlich, dann audit-sync committen:**

| File | Status | Empfehlung |
|---|---|---|
| `src/middleware/rateLimit.ts` | M | audit-sync commit — Live-Code, läuft schon (dist compiled), §11.2-Sync |
| `src/middleware/requestLogger.ts` | M | audit-sync commit — gleicher Pattern |
| `src/routes/flags.ts` | M | audit-sync — Live-Route per Discovery-SPEC Cluster `agent-flags` referenced |
| `src/routes/governance.ts` | M | audit-sync — Live-Route `/governance/validate-capabilities` per Discovery-SPEC referenced |
| `src/routes/hackathon.ts` | M | audit-sync — Live-Route `/hackathon/{register,stats}` |
| `src/routes/skill.ts` | M | audit-sync — Live, **siehe §3.4** (enthält Secret-Scanner-Regex-Patterns) |
| `src/routes/webhooks.ts` | M | audit-sync — Live `/api/webhooks/aeoess` (internal) |
| `src/services/market.ts` | M | audit-sync — Live-Service |

Vor jedem audit-sync-Commit: 5-Minuten-Diff-Review (was hat sich vs HEAD geändert?). Falls eine der modifications **nicht** live-relevant ist (z.B. abgebrochene WIP), discard via `git checkout <file>`. Default-Annahme: alles M ist live (das dist/ wurde gebaut + läuft).

**Untracked Live-Files (3) — audit-sync commit (analog zur events.ts-Operation aus Discovery-P2.2):**

| File | Status | Empfehlung |
|---|---|---|
| `src/routes/wallet.ts` | ?? | audit-sync commit — Live-Route `/api/wallet/attest`, im Discovery-Spec referenced |
| `src/services/aeoess-verify.ts` | ?? | audit-sync commit — Live-Service (gehört zu `webhooks.ts` aeoess-Webhook-Handler) |
| `scripts/gen_conformance.py` | ?? | audit-sync commit — Build-Script (verwiesen von `feat(scripts): add CONFORMANCE.md drift check`-Commit) |

**Untracked .bak-Files (11) — rotation, nicht committen:**

| File | Empfehlung |
|---|---|
| `scripts/gen_conformance.py.bak-20260418-104132` | move to `~/moltguard/.attic/` (server-only) |
| `src/index.ts.bak.pre-events` | move |
| `src/middleware/rateLimit.ts.bak-20260427-194129` | move |
| `src/middleware/requestLogger.ts.bak-20260427-194129` | move |
| `src/routes/hackathon.ts.bak-20260427-194129` | move |
| `src/routes/skill.ts.bak-20260427-194129` | move |
| `src/routes/skill.ts.bak-phase3-20260418-102703` | move |
| `src/services/market.ts.bak.pre-coverage` | move |
| `src/services/skill.ts.bak-phase1-20260418-093444` | move |
| `src/services/skill.ts.bak-phase1-20260418-094203` | move |
| `src/services/skill.ts.bak-phase2-20260418-095248` | move |

`.attic/` ist server-only, nicht-trackable (siehe §3.3 .gitignore-Erweiterung). Falls in 6 Monaten unused: hard-delete. Kein Push auf GitHub.

**Spezialfall `events.ts`**: bereits committed in `bd75d99` während Discovery-P2.2 (audit-sync), kein Re-Touch.

### 3.2 master → main Branch-Rename

**Empfehlung: rename als Teil dieses Sprints.**

Begründung:
- `CLAUDE.md` §11.4 referenziert durchgängig `origin/main`. Beim Cleanup nach diesem Sprint die §11.4-Mechanik 1:1 anwendbar.
- moltrust-api und moltrust-web sind beide auf `main`. Konsistenz reduziert Console-/Worktree-Reibung.
- Atomar mit Push: `git branch -m master main` lokal vor `git push -u origin main`. Server-side `git symbolic-ref HEAD refs/heads/main` falls je vom Server-Repo gefetcht wird (aktuell n/a).
- GitHub setzt `main` als default branch automatisch beim erstmaligen Push einer Branch namens `main` in einen leeren Repo.

Kein Workflow-Bruch: aller bestehende Server-Workflow (`git push`/`git pull` gegen das ALTE name) existiert nicht, weil heute kein Remote.

### 3.3 GitHub-Repo-Setup

| Konfiguration | Empfehlung | Begründung |
|---|---|---|
| Owner | `MoltyCel` | Konsistent mit moltrust-api, moltrust-web, moltrust-openclaw, status.moltrust.ch |
| Visibility | **`private` initial, `public` als separate Lars-Entscheidung** nach erstem CI-Run | License ist MIT (public-kompatibel), aber private gibt Zeit für CI-Stabilisierung + optionales README-Polish bevor öffentlich. **Open Decision §9.1** |
| LICENSE-File | Apache-2.0 hinzufügen (matches CLAUDE.md global rule für API-/Reference-Implementations) ODER MIT (matches existing `package.json.license`) | **Open Decision §9.2** — `package.json` sagt MIT, CLAUDE.md global sagt Apache-2.0 für „API / reference implementations". MoltGuard ist eher Letzteres (sub-API). Konflikt zu klären. |
| `.gitignore`-Erweiterung | + `*.bak`, `*.bak-*`, `.attic/`, `*.log`, `coverage/`, `.vitest-cache/` | Heute deckt nur `node_modules/`, `dist/`, `.env`, `*.log`. `.bak`-Hygiene fehlt vollständig (siehe §3.1). |
| README-Stand | Vor Push 5-Minuten-Polish — `## Build & Run`-Section ergänzen (`npm i`, `npm run build`, `npm start`, env-vars), `## Tests` (`npm test` → vitest), Repo-URL-Link, Apache/MIT-Marker | Heute README hat nur Endpoint-Tabelle, keine Dev-Setup-Hinweise. |
| Branch-Protection | bei `main`: require PR, require status-check `ci/build` (sobald CI da), 0 required reviewers (Single-Maintainer, siehe §3.6) | Niedrige Friktion, aber blockiert direct-pushs auf main |
| Default branch | `main` | siehe §3.2 |

### 3.4 Secret-Audit (verifiziert 2026-05-20)

**Scan-Ergebnis vor Push:**

| Pattern | Hits | Status |
|---|---|---|
| `ghp_[a-zA-Z0-9]{36}` | 0 | ✓ clean |
| `github_pat_[a-zA-Z0-9_]{80,}` | 0 | ✓ clean |
| `sk_live_[a-zA-Z0-9]{20,}` | 0 | ✓ clean |
| `whsec_[a-zA-Z0-9]{20,}` | 0 | ✓ clean |
| `sk-ant-[a-zA-Z0-9_-]{20,}` | 0 | ✓ clean |
| `AKIA[A-Z0-9]{16}` | 0 | ✓ clean |
| `xoxb-...` (Slack) | 0 | ✓ clean |
| `-----BEGIN ... PRIVATE KEY-----` | **3 hits, alle false-positive** | ✓ clean — siehe Begründung |

**Begründung der 3 PRIVATE-KEY-Hits:**

Alle 3 stehen in `src/services/skill.ts` (Skill-Audit-Funktion) als **Regex-Pattern-Strings**, nicht als Schlüssel-Inhalte:
```typescript
{ name: 'private_key', regex: /-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP |)PRIVATE KEY-----/ },
// und
.replace(/-----BEGIN [A-Z ]*PRIVATE KEY-----/, '-----BEGIN ***[REDACTED] PRIVATE KEY-----')
```

Diese Regex-Patterns sind das **Tool**, mit dem MoltGuard fremde Skill-Code-Audits nach Private-Keys absucht — keine eigenen Keys. Sicher für Public-Push.

**Empfohlene Pre-Push-Verifikation (Lars-Sichtprüfung, Audit-trail):**
```bash
ssh moltstack@api.moltrust.ch 'cd ~/moltguard && \
  git log --all -p 2>/dev/null | \
  grep -inE "ghp_[a-zA-Z0-9]{36}|sk_live_[a-zA-Z0-9]{20,}|whsec_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|sk-ant-[a-zA-Z0-9_-]{20,}|AKIA[A-Z0-9]{16}|xox[abpr]-[a-zA-Z0-9-]{20,}|BEGIN [A-Z ]*PRIVATE KEY"'
```

Erwartetes Ergebnis: nur die 3 false-positive-Hits aus `src/services/skill.ts`. Bei jedem unerwarteten Hit: **STOP**, BFG/`git filter-repo`-Bereinigung BEVOR push.

**Tracked-Files-Hygiene-Spot-Check (nicht-historisch, aktueller Stand):**
- `git ls-files | grep -iE "\.env|\.pem$|\.key$"` → nur `.env.example` (sicher, ist Template ohne Werte)
- `package.json` enthält weder Tokens noch URLs mit Credentials
- `.env` (echter) ist gitignored

### 3.5 CI-Minimum

Minimal-CI als `.github/workflows/ci.yml`:

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22', cache: 'npm' }
      - run: npm ci
      - run: npm run build      # tsc — type-check + emit
      - run: npm test            # vitest — heute 1 test (risk-tiers.test.ts), aber Pflicht etablieren
```

Begründung:
- `tsc` als Build-Step fängt Type-Errors früh (z.B. die `nullable: true` und `x-extension`-Probleme aus Discovery-P2 wären hier gefangen worden).
- `vitest` runs the existing risk-tiers test; etabliert Test-Pflicht für künftige PRs.
- Kein Linting in V1 — biome/eslint adds friction without existing config. Open Decision §9.4.

Optional (Phase 2, nicht in diesem Sprint):
- Post-deploy validation gate: `curl /guard/openapi.json` und `openapi-spec-validator` against the response. Closes the loop wenn moltguard-Deploy-Pipeline existiert (heute manuelle Pipeline).

### 3.6 Workflow-Change nach Push

**Vor Push (heute):** Lars (oder Console-Agent) committet direkt auf `master`, kein Review. Deploy = manueller `npm run build` + `systemctl restart moltguard`.

**Nach Push:** PR-Workflow analog moltrust-api/moltrust-web.

| Trigger | Workflow |
|---|---|
| Routine-Change (route-Verbesserung, neue Endpoint, Doku) | Single-Maintainer-PR: Lars eröffnet, mergt selbst. CI must pass. Recommendation: 24h wait-and-think bei substanziellen Changes (>200 LOC). |
| Security-relevant Change (auth, validation, payment middleware, x402-prices) | **§2.3 Cross-Review** (ai_review.py security mode) PR-Comment vor Merge. Same standard wie moltrust-api Discovery-P3. |
| Bug-fix-Hotfix (Live-Regression, Production down) | Direct push to main allowed mit `[HOTFIX]` commit prefix, post-hoc-PR + retroactive review-comment binnen 24h. CLAUDE.md-Workflow-Item für die Konvention. |

**Single-Maintainer-Praxis OK** für MoltGuard, weil:
- Lars ist sole code-owner today
- Cross-Review pipeline (ai_review.py) substituiert peer-review für die security-kritische Subset
- Branch-Protection erzwingt PR + CI für alle non-hotfix Changes

**Open Decision §9.5:** Soll der ai_review.py-Trigger automatisiert werden (CI run security-mode auf jeden PR), oder bleibt es manueller Lars-Trigger wie heute?

### 3.7 Push-Strategie: Full-history vs Squash-Init

**Empfehlung: Full-history-Push (32 Commits behalten).**

Begründung:
- **Audit-Trail wertvoll.** 32 Commits zeigen Evolution von v1.5.0-init (`aab5184`, 2026-03-10) bis Discovery-P2-Abschluss (`8438a28`, 2026-05-20). Wichtig für künftige Forensik (z.B. „wann wurde x402-Middleware eingeführt?").
- **Co-Authored-By preserved.** Mehrere historische Commits haben `Co-Authored-By: Claude Opus`-Annotationen. Squash würde diese verlieren.
- **Bisect-fähigkeit.** Falls in Zukunft ein Regression-Bug die Historie absucht, full-history erlaubt `git bisect`.
- **Kein Squash-Anreiz da kein Secret-Cleanup nötig.** §3.4 zeigt 0 echte Secrets in history — Squash hätte den Zweck „rewrite-to-redact" nicht.

**Nachteil:** Die 32-Commit-Historie zeigt **alle bisherigen §11.2-Verletzungen** (uncommitted-iteration-Phasen, .bak-Files etc.) öffentlich. Falls Visibility=`private` für ersten Monat: kein realer Concern. Falls sofort public: nicht-Idealität sichtbar aber kein Security-Risiko.

**Verworfen: Squash-Init.**
- Würde 32 Commits zu 1 „initial commit" verflachen.
- Nutzbar nur falls Secret-Cleanup zwingend (hier nicht).
- Optional: hybrid — push full history, dann auf GitHub squash-style merges für künftige PRs (orthogonal zur Init-Strategie).

## 4. Data-Model-Changes

Keine. Reine Repo-Operation.

## 5. API-Contract-Changes

Keine. MoltGuard-Service läuft unverändert weiter — die Migration ändert nur, wo die Source-of-Truth lebt (server-local → GitHub).

## 6. Migration-Path (Phasen)

| Phase | Inhalt | Risiko | Restart? |
|---|---|---|---|
| **P1 (diese SPEC)** | Architektur-Briefing, kein Code | — | Nein |
| **P2** Working-Tree-Triage | 8 audit-sync-Commits (modified) + 3 audit-sync (untracked live) + 11 .bak-Files in `.attic/`. Pre/post `git status` = clean working tree. | Niedrig — analog zu Discovery-P2.2 `events.ts`-Operation, bewährter Pfad. | Nein |
| **P3** Repo-Setup-Files | LICENSE-File (Apache-2.0 oder MIT, §9.2), erweiterter `.gitignore`, README-Polish. Commit als „chore: prep repo for github-migration". | Niedrig | Nein |
| **P4** Branch-Rename | `git branch -m master main`. Lokal nur. | Trivial | Nein |
| **P5** Final Secret-Audit | Re-run §3.4-Scan auf den FINALEN Stand (nach P2+P3). Bei jedem unerwarteten Hit: STOP. | Mittel — wenn unentdeckter Secret durchrutscht und auf GitHub landet, force-cleanup teuer (BFG, GitHub-Cache-Invalidierung, Force-Push, Konsumenten-Re-Clone). | — |
| **P6** GitHub-Repo erstellen | `gh repo create MoltyCel/moltguard --private --license=apache-2.0 --description="..."`. Branch-Protection: require PR, require ci/build. | Niedrig | Nein |
| **P7** First Push | `git remote add origin git@github-moltstack:MoltyCel/moltguard.git && git push -u origin main`. | Mittel — ab jetzt öffentlich (oder zumindest GitHub-Cloud-gehostet falls private). | Nein |
| **P8** CI hinzufügen | `.github/workflows/ci.yml` per PR (#1 im neuen Repo). CI muss durchlaufen. | Niedrig | Nein |
| **P9** Visibility-Toggle (optional) | Falls §9.1 = „public": `gh repo edit --visibility=public --accept-visibility-change-consequences`. | Niedrig — license ist MIT (oder Apache, §9.2), public-kompatibel. | Nein |

**Reihenfolge zwingend:** P2 → P3 → P4 → P5 → P6 → P7. P8 und P9 sind nach P7. Kein Schritt vorgreifen (z.B. nicht Repo erstellen bevor P5 grün).

## 7. Rollback-Plan

| Phase | Rollback |
|---|---|
| P2 Triage-Commits | `git reset --hard 8438a28` (vor P2). Reverts alle audit-sync-Commits. .attic/-Moves manuell zurückkopieren falls relevant. |
| P3 Repo-Setup-Files | `git reset --hard <P3^>`. LICENSE/gitignore/README-changes weg. |
| P4 Branch-Rename | `git branch -m main master` lokal. Trivial. |
| P7 Push to GitHub | `gh repo delete MoltyCel/moltguard --yes` UND `git remote remove origin` lokal. **Vor public-toggle in P9 jederzeit möglich.** Nach P9 (öffentlich) ist Delete reversibel aber URL-Permalinks brechen. |

**Nicht-trivialer Rollback-Fall:** Wenn nach P7-Push ein Secret aufgetaucht ist, das im Pre-Audit übersehen wurde:
1. `gh repo delete MoltyCel/moltguard` (sofort, bevor cloning passiert)
2. Server-side `git-filter-repo` zur Bereinigung
3. Re-Audit
4. Re-Push (mit force-with-lease nicht nötig, weil delete + neuer push)

GitHub's repo-deletion **purgiert auch den public cache** für private repos sofort. Für public repos: 24h Cache-Window (CDN), aber Inhalte nicht öffentlich (wenn schnell genug).

## 8. Success-Criteria

1. `ssh moltstack@api.moltrust.ch 'cd ~/moltguard && git status --short' | wc -l` == **0** (clean working tree) nach P2.
2. `ssh moltstack@api.moltrust.ch 'cd ~/moltguard && ls -la LICENSE README.md .gitignore'` listet alle drei mit erwartetem Inhalt (LICENSE = Apache-2.0 oder MIT, .gitignore enthält `*.bak`, README erweitert).
3. `git -C ~/moltguard rev-parse --abbrev-ref HEAD` == `main` nach P4.
4. `gh repo view MoltyCel/moltguard --json visibility,defaultBranchRef,licenseInfo` zeigt: defaultBranchRef.name=`main`, licenseInfo.spdxId in (`Apache-2.0`,`MIT`), visibility per §9.1.
5. `git -C ~/moltguard log --oneline origin/main..HEAD` ist leer nach P7 (server == remote).
6. P5 Secret-Audit-Output: 0 unexpected hits (nur die 3 dokumentierten false-positives).
7. P8 CI-Run grün auf erstem PR.
8. moltrust-api `docs/BACKLOG.md` HIGH-Item „moltguard-Repo nach GitHub bringen" status: Open → **Done** (eigener kleiner Doku-PR im moltrust-api Repo).

## 9. Open Decisions (für Lars vor P2-Start zu klären)

- **9.1 Visibility:** `private` initial (Vorschlag) vs `public` sofort. Trade-off:
  - `private`: Zeit für CI-Stabilisierung + erstes Polish, kein Reputations-Risiko bei kleinen Issues, weniger Drive-by-Issues.
  - `public`: passt zur Open-Source-Positionierung von MolTrust (moltrust-api ist public), maximale Discoverability, externe Beiträge möglich.
  - Empfehlung: `private` initial, public-Toggle nach P8 (CI grün) + 1-Woche-Cooldown.

- **9.2 License-Konflikt: `package.json.license: MIT` vs CLAUDE.md global rule „Apache-2.0 für API/Reference-Implementations":**
  - MoltGuard ist sub-API (Reference-Implementation-Charakter): **CLAUDE.md sagt Apache-2.0**.
  - `package.json` sagt MIT seit v1.0.0 (vermutlich initial-default ohne Reflexion).
  - Empfehlung: Apache-2.0 für moltguard (CLAUDE.md folgen), `package.json.license` updaten auf `Apache-2.0`. Falls Konsumenten existieren die MIT erwarten: dokumentieren (sollte hier nicht der Fall sein).
  - Alternative: bei MIT bleiben, CLAUDE.md-global-rule durch Audit-Eintrag ausnahmen. Inkohärenter, aber kein technischer Blocker.

- **9.3 README-Polish-Tiefe:** Minimal (Build + Run-Sektion ergänzen) oder Full (Architecture-Diagram, Cluster-Übersicht, Cross-Repo-Links zu moltrust-api/-web)?
  - Empfehlung: Minimal in diesem Sprint, Full-README als separate `chore(readme)`-PR nach Migration. Niedrige Friktion.

- **9.4 Linting in CI:** Add biome/eslint in P8 oder defer?
  - Empfehlung: defer. Bestehender Code hat keine Lint-Config — Adding würde 100+ findings auf Bestand erzeugen ohne sofortigen Nutzen. BACKLOG-Item nach Migration.

- **9.5 ai_review.py Auto-Trigger in CI:** automatisierter Security-Review auf jedem PR vs heutiger manueller Lars-Trigger?
  - Empfehlung: weiter manueller Trigger. Auto-Run würde token-Budget unkontrolliert hochtreiben (mehrere $/PR via Synthese-Claude); jeder PR braucht das nicht. Lars-getriggert für security-relevant PRs reicht. CLAUDE.md-Regel präzisieren.

- **9.6 Working-Tree-Triage Edge-Case: was wenn ein modified-file (z.B. `src/services/market.ts`) bei Diff-Review Verdacht erweckt (z.B. debug-prints, hartcodierte test-Values)?**
  - Empfehlung: pro File einzeln entscheiden im P2-Schritt. Default `audit-sync`; bei Auffälligkeit eskalieren zu Lars (kein eigenmächtiges Discard, weil das Live-Verhalten am dist/ hängt).

- **9.7 §2.3 Cross-Review-Timing für diese Migration:** auf welcher Phase?
  - Diese SPEC selbst hat keinen Code-Pfad — Skip für SPEC.
  - P2 (Triage-Commits) ändert keinen Live-Code, nur git-state — Skip empfohlen.
  - P3 (Setup-Files) berührt keinen Code — Skip.
  - **P7 Push:** macht alle bisherigen Auth-/Credential-/Payment-Pfade öffentlich (oder GitHub-cloud-private). Trotz vorigem Secret-Audit: ein letzter Security-Pass auf den Push-Diff (`gh repo view` post-push erlaubt full-tree-review) wäre die maximale Vorsicht.
  - Empfehlung: §2.3 Cross-Review **auf den ersten echten PR im neuen Repo (P8 CI-Add)** statt auf Push selbst — der Push ist ja nur Datentransfer, die inhaltliche Sicherheit liegt im bestehenden Code, der bereits live ist.

## Appendix A — Heutige moltguard-Repo-State (verifiziert 2026-05-20)

```
branch:        master
HEAD:          8438a28 (P2 Discovery-cluster-14 commit)
total commits: 32
tracked files: 85
remote:        none

working tree:
   M  src/middleware/rateLimit.ts
   M  src/middleware/requestLogger.ts
   M  src/routes/flags.ts
   M  src/routes/governance.ts
   M  src/routes/hackathon.ts
   M  src/routes/skill.ts
   M  src/routes/webhooks.ts
   M  src/services/market.ts
   ?? scripts/gen_conformance.py
   ?? src/routes/wallet.ts
   ?? src/services/aeoess-verify.ts
   ?? + 11 .bak-files (siehe §3.1)

package.json:
   license: MIT (siehe §9.2 Konflikt)
   version: 1.3.0  (Hinweis: ~/moltguard/dist behauptet v1.5.0 in api-info — version-Drift, separater Polish)
   scripts: dev/build/start; KEIN test-script trotz vitest devDep — TODO in P3

LICENSE-File:   MISSING (nur package.json.license sagt MIT)
.gitignore:     node_modules/, dist/, .env, *.log (kein .bak-pattern)
README.md:      vorhanden, 1.8 KB, basic endpoint-table, KEIN Build/Run/Test-Section
CI:             keine (kein .github/workflows/)
Tests:          1 vitest-test (src/lib/risk-tiers.test.ts), vitest in devDeps

Secret-Audit (full history):
   ghp_/sk_live_/whsec_/github_pat_/sk-ant-/AKIA/xoxb-: 0 hits
   BEGIN PRIVATE KEY: 3 hits — alle in src/services/skill.ts als Regex-Pattern-Strings (Tool, nicht Schlüssel)
   .env/.pem/.key tracked: 0 (nur .env.example, das ist Template-File)
```

## Appendix B — BACKLOG-Sync nach Sprint-Abschluss

Nach P8 (CI grün) + P9 (visibility-toggle) erfolgt:
- Update `docs/BACKLOG.md` Zeile 67-71: Status Open → Done
- Update item „MoltGuard Validation Hardening" (Medium): Sequenzierungs-Note „NACH moltguard-Remote-Migration" wird obsolet → Sequenzierung entfernen, Item kann starten
- Update item „`x402-prices.ts /api/market/feed`-Doppelpfad konsolidieren" (Medium): Sequenzierungs-Note ebenfalls obsolet
