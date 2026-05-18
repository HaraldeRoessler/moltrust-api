# Architektur-Brief — Kanonisierung des AAE-Envelope-Schemas (D1)

**Typ:** WORKFLOW §3.3 Architektur-Brief. **KEIN Code, kein 9-Sektionen-Spec.**
**Status:** ENTWURF — wartet auf Lars-Freigabe → danach Cross-Review → **dann ist das Ergebnis das D1-Schema für V1.4-1**.
**Datum:** 2026-05-18 · **Repo:** moltrust-api · **Branch:** docs/aae-schema-canon-brief
**Einordnung:** **Vorgelagerter eigener Schritt. NICHT Teil der V1.4-1-Implementierung.** V1.4-1 (PR #36) bleibt blockiert (D1–D3/D6/D7), bis dieses Schema kanonisiert ist.
**Quellenlage (verifiziert, read-only, D1-Befund):** Nur **@moltrust/aae 1.1.0** trägt ein echtes maschinenlesbares Schema (TS-Interfaces + zod + `evaluate()`). WP v0.8 §4.6 = illustratives JSON-Beispiel (kein Typsystem). `moltrust-v08-patch-notes` = **keine** Feldschicht (nur Layer-Label) → als Schema-Quelle ausgeschlossen.

## Ausgangspunkt
**@moltrust/aae 1.1.0 ist die Basislinie** (einzige ausführbare Wahrheit). Pro divergierendem Feld unten: Variante A (npm 1.1.0) vs. Variante B (WP v0.8 §4.6), Empfehlung **mit Begründung** wo es eine Robustheitsfrage ist; **[LARS]** wo es eine echte Protokoll-Entscheidung ist (nicht geraten).

## Versions-Inkonsistenz (zu dokumentieren, Teil der Kanonisierung)
npm-`description` sagt „MolTrust Protocol **v0.5**", die Paket-**Version ist 1.1.0** (kein 0.5.x existiert). Prosa-Docs (WP, Patch-Notes) sind **v0.8**. Die einzige Maschinen-Quelle beansprucht damit ein **älteres** Protokoll-Level als die Prosa. **[LARS]**: Welcher Protokoll-Version gehört das kanonische AAE an, und der npm-`description`-String ist anzugleichen. (Reine Doku-/Label-Entscheidung, kein Schema-Inhalt.)

## Divergente Felder — Gegenüberstellung + Empfehlung

**1. MANDATE.purpose**
- A (npm): `purpose: Purpose[]` — geschlossenes Enum-Array (commerce|data_read|data_write|communication|delegation|administration|general).
- B (WP): Freitext-String („Execute procurement transactions").
- **Empfehlung: A (Enum-Array).** Begründung: AAE wird laut WP §4.6 selbst „at every action" maschinell enforced; Freitext ist nicht deterministisch evaluierbar (Ambiguität/Injection). **[LARS]**: das konkrete *Vokabular* (welche purpose-Werte; A hat 7) ist Protokoll-Entscheidung — Form (Enum-Array) empfohlen, Wertemenge zu bestätigen/erweitern.

**2. CONSTRAINTS — Zeit-Modell**
- A (npm): `duration{ttl, maxSessionDuration?, allowedDays?, allowedHours?, timezone?}` — relative TTL + wiederkehrende Fenster.
- B (WP): `time_bound{not_before, not_after}` — absolutes ISO-Fenster.
- **Empfehlung: absolutes Fenster als Basis (B-Modell).** Begründung: AAE-Grenzen sind laut WP „immutably anchored at issuance"; absolute Timestamps sind selbst-enthaltend und konsistent mit VALIDITY (`issuedAt`/`expiresAt` bereits absolut). Relative `ttl` braucht externen Referenzpunkt → fehleranfällig bei anker-immutablen Credentials. **[LARS]**: ob zusätzlich wiederkehrende Fenster (A: allowedDays/allowedHours/timezone) im v1-Scope sind = Feature-/Protokoll-Entscheidung.

**3. CONSTRAINTS — Finanz-Modell**
- A (npm): `limits{autonomousThreshold, stepUpThreshold, approvalThreshold, maxTransactionsPerHour?, currency: <enum>}` — typisierte Zahlen + separates Currency-Enum.
- B (WP): `financial{max_single_transaction:"10000.00 USD", max_cumulative_daily, approval_threshold}` — Betrag-als-String mit Inline-Währung; Einzel- + Tageskumulativ-Cap.
- **Empfehlung: A-Repräsentation (typisierte Zahl + separates Currency-Enum).** Begründung: Geldwert-als-String („10000.00 USD") ist Parsing-/Locale-/Präzisions-Antipattern auf einem Enforcement-Pfad. A-Stufen (autonomous/stepUp/approval) mappen zudem 1:1 auf das bereits implementierte `evaluate()` (`requiresStepUp`/`requiresHumanApproval`) und auf den CONSTRAINTS-Block der Developer-Seite. **[LARS]**: ob *zusätzlich* ein Tageskumulativ-Cap (B: max_cumulative_daily) ins v1 gehört = Kontroll-Semantik-Entscheidung (A hat das nicht).

**4. MANDATE.delegation**
- A (npm): `{allowed, maxSubAgents, maxDepth, attenuationOnly}`.
- B (WP): `{permitted, max_depth, delegate_constraints:"inherit"}`.
- **Empfehlung: A-Struktur.** Begründung: `attenuationOnly:bool` erzwingt das Kern-Sicherheitsprinzip Capability-Attenuation (Sub-Agent darf nur einschränken, nie erweitern); `maxSubAgents` begrenzt Fan-out. B faltet das lose in einen String `delegate_constraints`. **[LARS]**: Reconciliation mit der **live** `agent_delegation_config` (`constraint_mode ∈ {inherit,restrict,none}`, verifiziert in `/delegation/configure`) — drei-Wege-Spannung A↔B↔Server; hängt direkt an V1.4-1-D3. Echte Architektur-/Protokoll-Entscheidung, nicht hier raten.

**5. CONSTRAINTS.obligations**
- A (npm): `{requireHumanApprovalAbove?, toolAllowlist?}`.
- B (WP): `{log_all_transactions: bool, human_approval_above}`.
- Befund: weitgehend **verschiedene Obligations**, nicht dasselbe Feld umbenannt → primär Protokoll-/Produktfrage, keine reine Robustheit.
- **Teil-Empfehlung (robustness):** Human-Approval-Schwelle **nicht doppelt** führen — sie ist bereits in `limits.approvalThreshold` (A); `human_approval_above` (B) ist Redundanz, die zu Inkonsistenz führt → genau **einmal** modellieren (in limits). **[LARS]**: das Obligations-*Set* selbst (toolAllowlist? log_all_transactions? weitere?) = Produkt-/Protokoll-Entscheidung.

## Querschnitt (Robustheits-Empfehlungen, keine Protokollfrage)
- **Naming:** auf **camelCase (A)** kanonisieren — einzige Quelle mit funktionierendem Validator/`evaluate()`; minimiert Implementierungsrisiko. (Kleiner [LARS]-Hinweis: falls VC/JSON-LD-Konvention etwas anderes erzwingt, dort entscheiden.)
- **Wrapper:** A = flaches `{mandate,constraints,validity}`; B = `authorization:{…}`. Empfehlung flach (A); wo es in der VC-`credentialSubject` sitzt = V1.4-1-Strukturfrage (Querverweis, nicht hier).
- **VALIDITY:** kanonisch = **A** (issuer, holderBinding, issuedAt, expiresAt, revocationEndpoint, signingAlgorithm?, onChainAnchor?) — die einzige in sich konsistente Variante.

## WP v0.8 §4.6-Beispiel: KAPUTT — nicht hier korrigieren
Das WP-Beispiel ist intern fehlerhaft: **doppelter `issuer`-Key** (zwei verschiedene DIDs) plus zugleich `holder` UND `holderBinding`. Als kaputt markiert. **Korrektur gehört in den Whitepaper-Strang, NICHT in diesen Brief / nicht in V1.4-1.** Für die Kanonisierung ist die VALIDITY-Wahrheit ausschließlich A.

## Ergebnis / nächster Schritt
Vorschlag = **@moltrust/aae 1.1.0 als kanonische Basis**, mit den obigen Empfehlungen (Enum-purpose, absolutes Zeitfenster-Basis, typisierte Finanz+Currency-Enum, A-delegation-Struktur, deduplizierte Human-Approval, camelCase, A-VALIDITY) und den **[LARS]-Punkten** als offene Protokoll-Entscheidungen (purpose-Vokabular, recurring-Windows-Scope, Tageskumulativ-Cap, delegation↔`agent_delegation_config`-Reconciliation, Obligations-Set, Protokoll-Versions-Label). **STOP — Lars-Freigabe → Cross-Review → dann ist dies das D1-Schema für V1.4-1.** Kein Code.
