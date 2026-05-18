# Spec — V1.4-5a: Single-Source-of-Truth für den internen Build-Versions-String (9 Sektionen)

**Status:** ENTWURF — Lars-Freigabe vor Code.
**§2.3-Cross-Review:** bewusster, begründeter **Skip** — interne Build-Konstante/Refactor, kein Auth-/Credential-/Token-Pfad, keine Verhaltensänderung nach außen. State-Check ergab nichts Security-Relevantes.
**Datum:** 2026-05-18 · **Repo:** moltrust-api · **Branch:** docs/v145a-version-ssot-spec
**BACKLOG-Mapping (verifiziert):** echte `docs/BACKLOG.md` hat **ein** kombiniertes Item `### API-Versionierung — Single-Source + v1-Contract klären (Phase-1-Analyse §8 Punkt 5)` (## Medium). „5a" ist ein **Teilaspekt** dieses einen Items, kein eigenes BACKLOG-Item. Abweichung im Schluss-Report.
**Quelle der Fakten:** Versionierungs-Audit `~/moltstack/audits/2026-05-15_api-versioning.md` (V-10, V-13).

## 1. Goal
Den internen Build-Versions-String aus **einer** Quelle (SSOT) speisen, statt ihn an mehreren Stellen hartzucodieren. Verifiziert (V-10): `version="2.4"` als FastAPI-Konstruktor-Argument plus zwei weitere `"version": "2.4"`-Literale in Handler-Bodies; **kein** zentraler Versions-Konstanten-Ort (`pyproject.toml`/`setup.cfg`/`app/__init__.py` ohne API-Versions-String — verifiziert). V-13: in der History rückwärts von „2.6" auf „2.4" dekrementiert (Beleg für fehlende Disziplin durch fehlenden SSOT).

## 2. Non-Goals
- **Keine** öffentliche v1-Contract-Entscheidung (= V1.4-5b).
- **Kein** Breaking-Change-Pfad / Deprecation-Mechanik (= 5c/5d, Produktentscheidungen, NICHT hier).
- **Keine** Änderung der ausgelieferten Versionsnummer in diesem Schritt — reiner Quellen-Refactor (Wert bleibt zunächst gleich; was der Wert künftig ist, entscheidet 5b).

## 3. Architecture-Layer-Scope *(Pflichtfeld)*
- **Code:** eine Versions-Konstante (z. B. `app.version.API_BUILD_VERSION`) als alleinige Quelle; alle Verwender lesen sie.
- **WICHTIG — Zeilennummern-Drift:** die drei Fundstellen sind **zweimal gedriftet** (Audit `:50/:1519/:5855` → später `:50/:1647/:6093` → State-Check 2026-05-18 erneut `:50/:1647/:6093`). **Diese Spec referenziert Funktion/Verhalten** („FastAPI-Konstruktor-`version=`" + „zwei Handler-Body-`version`-Literale, u. a. `/health`"); **konkrete Zeilen erst bei Implementierung frisch verifizieren** (`grep`), nie aus der Spec übernehmen.
- **NICHT betroffen:** Auth, Credentials, DB, externes Verhalten (Wert unverändert).

## 4. Data-Model-Changes
Keine. Reiner Code-Konstanten-Refactor.

## 5. API-Contract-Changes
Keine sichtbare Änderung: `openapi.json` `info.version` bleibt zunächst `2.4` (Wert unverändert, nur Quelle zentralisiert). Eine spätere Wert-/Contract-Änderung ist 5b.

## 6. Migration-Path
1. SSOT-Konstante einführen.
2. Alle (per frischem `grep` zu verifizierenden) Fundstellen darauf umstellen — FastAPI-Konstruktor + alle Handler-Body-Literale.
3. Verifikation: `grep` findet **keine** verbleibenden hartcodierten `"2.x"`-API-Versions-Literale; `openapi.json`/`/health` melden unverändert denselben Wert.

## 7. Rollback-Plan
Konstante wieder durch Literale ersetzen bzw. Commit revert; rein interner Refactor, keine Daten/State, kein externes Verhalten betroffen → risikoarm reversibel.

## 8. Success-Criteria
1. Genau **eine** Quelle für den API-Build-Versions-String; 0 verbleibende Hardcode-Literale (frischer grep-Nachweis bei Implementierung).
2. `openapi.json` `info.version` + `/health` unverändert (kein externes Delta).
3. Ein künftiger Versions-Bump erfordert genau **eine** Änderung (SSOT-Nachweis).

## 9. Open Decisions
- **9.1** Ort/Name der Konstante (`app/__init__.py` vs. `app/version.py` vs. `pyproject`-gelesen) — Implementierungsdetail, beim Bau festlegen, nicht raten.
- **9.2** Gekoppelt an V1.4-5b: welcher **Wert** künftig SSOT-seitig steht (intern `2.x` vs. öffentlich `v1`) ist **nicht** 5a — 5a zentralisiert nur die Quelle, 5b entscheidet den Wert/Contract. Querverweis, kein Blocker für den Refactor.
