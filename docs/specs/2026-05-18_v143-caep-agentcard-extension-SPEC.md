# Spec — V1.4-3: CAEP als Extension in agent-card.json (9 Sektionen, WORKFLOW §1.3)

**Status:** ENTWURF — Lars-Freigabe vor Code.
**§2.3-Cross-Review:** bewusster, begründeter **Skip** — kein Auth-/Credential-/Token-Pfad; rein deklarative Metadaten-Ergänzung in `agent-card.json` einer bereits live laufenden CAEP-v1-Fläche. State-Check ergab nichts Security-Relevantes. (Bei Implementierung der Doku-Drift-Korrektur erneut prüfen.)
**Datum:** 2026-05-18 · **Repo:** moltrust-api · **Branch:** docs/v143-caep-agentcard-spec
**BACKLOG-Mapping (verifiziert):** echte `docs/BACKLOG.md` nutzt **kein** „V1.4-3", sondern „### CAEP als Extension in agent-card.json deklarieren (Phase-1-Analyse §8 Punkt 3)" (## Medium). Abweichung in Schluss-Report.

## 1. Goal
CAEP-Profil v1 (live: `agent-firewall` PROFILE.md, 4 Endpoints) als **6. Extension** in `agent-card.json` deklarieren, damit A2A-Konsumenten CAEP per Discovery finden statt aus PROFILE.md hardzucoden. Zusätzlich Doku-Drift mitfixen: PROFILE.md nennt CAEP-Default-Limit 100, **Server `app/caep.py` `limit: int = Query(default=50,…)` — Server-Wert (50) gilt** (verifiziert).

## 2. Non-Goals
- **Kein** CAEP-v2/Push (separates BACKLOG-Item „CAEP Profile v2" — nicht verwechseln).
- Keine CAEP-Endpoint-Logik-Änderung; rein Discovery-Deklaration + PROFILE.md-Drift-Korrektur.

## 3. Architecture-Layer-Scope *(Pflichtfeld)*
- **Discovery/Metadaten:** `agent-card.json` Generierung — `capabilities.extensions` (heute 5: trust-score/v1, aae/v1, erc8004/v1, x402-payment/v1, discovery-surfaces/v1 — verifiziert live) um `caep/v1` erweitern.
- **Doku:** `agent-firewall` PROFILE.md Limit 100 → 50 angleichen (Server ist Wahrheit).
- **NICHT betroffen:** CAEP-Endpoints selbst, Auth, Credentials, Rate-Limiter-Logik.

## 4. Data-Model-Changes
Keine DB-Änderung. Nur die `agent-card.json`-Generierungsquelle (Extension-Liste) + PROFILE.md-Textkorrektur.

## 5. API-Contract-Changes
- `agent-card.json` `capabilities.extensions[]` +1 Eintrag `https://moltrust.ch/extensions/caep/v1` (URI-Schema konsistent zu den 5 bestehenden). Exakte Extension-Felder (uri, ggf. endpoints/Beschreibung) am bestehenden 5-Extension-Format ausrichten — Format bei Implementierung 1:1 spiegeln, nicht erfinden.
- Additiv, kein Breaking Change (Konsumenten, die Extensions ignorieren, unberührt).

## 6. Migration-Path
1. Extension-Liste der Generierungsquelle ergänzen → `agent-card.json` neu generieren → kanonisch (api.moltrust.ch) ausliefern. (Mirror-Konsistenz moltrust.ch hängt an V1.4-4 — Querverweis.)
2. PROFILE.md 100→50 im selben PR-Change (Doku-Drift).
3. Verifikation: `agent-card.json` zeigt 6 Extensions inkl. caep/v1; PROFILE.md = 50.

## 7. Rollback-Plan
Extension-Eintrag entfernen + agent-card neu generieren (rein additiv, folgenlos). PROFILE.md-Textänderung trivial reversibel. Keine Daten.

## 8. Success-Criteria
1. `GET /.well-known/agent-card.json` listet 6 Extensions inkl. `…/caep/v1`.
2. PROFILE.md nennt Default-Limit 50 (= Server `app/caep.py`).
3. CAEP-Endpoints funktional unverändert (Regressions-frei).
4. Mirror (moltrust.ch) zieht nach — abhängig von V1.4-4 (dokumentierter Querverweis, kein Blocker für die kanonische Quelle).

## 9. Open Decisions
- **9.1** Exakte Extension-Objektform (nur `uri` vs. zusätzliche `endpoints`/`description`-Felder): am bestehenden 5er-Format ausrichten — bei Implementierung verifizieren, nicht raten.
- **9.2** Reihenfolge zu V1.4-4: kanonische Quelle kann sofort; konsistente Mirror-Anzeige erst nach V1.4-4. Kein harter Blocker, nur Sequenz-Hinweis.
