# Spec — V1.4-5b: Öffentliche v1-Contract-Deklaration (9 Sektionen, WORKFLOW §1.3)

**Status:** ENTWURF — Lars-Freigabe vor Code. Teilweise produktentscheidungs-abhängig (siehe §9 + 5c/5d-Flag).
**§2.3-Cross-Review:** bewusster, begründeter **Skip** — Außenkommunikations-/Doku-Deklaration, kein Auth-/Credential-/Token-Pfad. State-Check ergab nichts Security-Relevantes. (Falls 5c „/v2-Pfade" gewählt würde, entstünde ein Contract-strukturierender Eingriff → dann separater Review; **5c ist hier explizit NICHT entschieden**.)
**Datum:** 2026-05-18 · **Repo:** moltrust-api · **Branch:** docs/v145b-public-v1-contract-spec
**BACKLOG-Mapping (verifiziert):** Teilaspekt des **einen** kombinierten Items `### API-Versionierung — Single-Source + v1-Contract klären (Phase-1-Analyse §8 Punkt 5)` (## Medium). „5b" ist kein eigenes BACKLOG-Item. Abweichung im Schluss-Report.
**Quelle:** Versionierungs-Audit `~/moltstack/audits/2026-05-15_api-versioning.md` (V-11: kein öffentliches „v1" existiert).

## 1. Goal
Eine **öffentliche `MolTrust API v1`-Contract-Deklaration** etablieren: wo und wie wird die nach-außen-stabile Vertragsversion kommuniziert. Verifiziert (V-11/State-Check): heute meldet `openapi.json` `info.version: "2.4"` (interne Build-Zahl), ein öffentliches „v1" existiert **nirgends**. Ziel: klare, dokumentierte v1-Aussage entkoppelt von der internen Build-Version (5a).

## 2. Non-Goals
- **Kein** SSOT-Refactor (= V1.4-5a).
- **Kein** Breaking-Change-Transport-Pfad (= 5c — Produktentscheidung, NICHT hier).
- **Keine** Deprecation-Mechanik-Details (= 5d — Produktentscheidung, NICHT hier).
- Keine API-Logik-Änderung; rein Deklaration/Kommunikation.

## 3. Architecture-Layer-Scope *(Pflichtfeld)*
- **Contract/Doku/Discovery:** wo „v1" deklariert wird — Kandidaten: `openapi.json` `info.version` Semantik (intern vs. extern), `/docs`/`/redoc`, agent-card, llms.txt, Außendoku. Genaue Trägerorte = §9.
- **Abgrenzung:** intern bleibt Build-Version (5a-SSOT); extern wird **v1** als stabiler Vertrag deklariert. Die Auflösung „info.version=2.4 vs. öffentlich v1" ist der Kern.
- **NICHT betroffen:** Auth, Credentials, DB, Request-Routing (Letzteres nur falls 5c „/v2-Pfade" — explizit ausgeklammert).

## 4. Data-Model-Changes
Keine DB-Änderung.

## 5. API-Contract-Changes
- Deklarativ: öffentliche Aussage „MolTrust API v1" an noch zu bestimmenden Trägerorten (§9). Ob `info.version` selbst auf `1.x` umgestellt wird oder ein separates `x-api-contract: v1`/Doku-Statement tritt: **abhängig von 5c-Strategie** → hier nur als Optionen, nicht entschieden.
- Kein Request-Breaking-Change in diesem Item (Breaking-Change-Pfad ist 5c).

## 6. Migration-Path
Abhängig von 5c-Entscheidung — daher hier nur Sequenz: (1) 5a-SSOT vorhanden, (2) Lars entscheidet 5c (Transport) + 5d (Deprecation), (3) dann v1-Deklaration an den in §9 bestätigten Trägerorten umsetzen + Außenkommunikation synchronisieren. Ohne 5c/5d-Entscheid ist 5b nicht implementierungsreif (dokumentiert, nicht geraten).

## 7. Rollback-Plan
Deklaration ist additiv/textuell → Entfernen der v1-Aussage / Doku-Revert, folgenlos (keine Daten/State, kein Routing, solange 5c nicht „/v2-Pfade").

## 8. Success-Criteria
1. Eindeutige, dokumentierte öffentliche Aussage „MolTrust API v1" an den bestätigten Trägerorten.
2. Interne Build-Version (5a) und öffentlicher v1-Contract sind klar getrennt und konsistent kommuniziert (kein „2.4 vs v1"-Widerspruch nach außen).
3. Keine Regression bestehender Konsumenten (kein Breaking Change in 5b selbst).

## 9. Open Decisions
- **9.1** Trägerorte der v1-Deklaration (info.version-Semantik vs. separates Feld vs. nur Doku/agent-card/llms.txt) — zu bestätigen, nicht raten.
- **9.2 [PRODUKTENTSCHEIDUNG — NICHT gespeced, Flag für Lars] V1.4-5c Breaking-Change-Pfad:** `/v2`-Pfad-Präfix vs. Version-Header. Strukturbestimmend für 5b, aber bewusst **nicht** hier entschieden — eigene Produktentscheidung Lars (Audit lieferte dazu nichts; nicht ableitbar).
- **9.3 [PRODUKTENTSCHEIDUNG — NICHT gespeced, Flag für Lars] V1.4-5d Deprecation-Mechanik-Details:** Fenster-Länge, RFC-8594-`Deprecation`/`Sunset`-Ausgestaltung, Changelog-Ort. Eigene Produktentscheidung Lars.
- **9.4** 5b ist erst implementierungsreif, **nachdem** 5c/5d entschieden sind — explizit dokumentiert (kein Code vorher).
