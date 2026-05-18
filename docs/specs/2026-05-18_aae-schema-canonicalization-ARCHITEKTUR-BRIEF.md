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

---

## KANONISCHES D1-SCHEMA — FREIGEGEBEN 2026-05-18 (Lars)

Alle [LARS]-Punkte entschieden. Basis @moltrust/aae 1.1.0 + Console-Empfehlungen + folgende Vokabular-/Scope-Entscheidungen. **camelCase, flacher Wrapper `{mandate,constraints,validity}`.** Dies ist (nach dem Pflicht-§2.3-Cross-Review, Appendix unten) **das D1-Schema für V1.4-1**.

```ts
type Purpose  = commerce | data_read | data_write | communication | compute | delegation;            // v1, erweiterbar
type Obligation = log_all_actions | tool_allowlist | notify_on_step_up | human_in_loop;                 // v1, erweiterbar
type Currency = USDC | EUR | CHF | USD;
type SigningAlgorithm = Ed25519 | ML-DSA-65;

interface Delegation {            // A-Variante (mit attenuationOnly)
  allowed: boolean;
  maxSubAgents: number;
  maxDepth: number;
  attenuationOnly: boolean;       // Sub-Agent darf nur einschränken, nie erweitern
}
interface Mandate {
  purpose: Purpose[];             // Enum-Array (nicht Freitext)
  allowedActions: string[];
  deniedActions?: string[];
  resources?: string[];
  delegation?: Delegation;
}
interface TimeWindow {            // absolutes Fenster; KEINE wiederkehrenden Fenster in v1
  notBefore: string;             // ISO 8601
  notAfter: string;              // ISO 8601
}
interface Limits {               // typisierte Zahlen + separates Currency-Enum; nur Pro-Transaktion in v1
  autonomousThreshold: number;
  stepUpThreshold: number;
  approvalThreshold: number;     // = Human-Approval-Schwelle (HIER, dedupliziert)
  maxTransactionsPerHour?: number;
  currency: Currency;
}
interface Scope {
  jurisdictions?: string[];
  counterpartyMinScore?: number;
}
interface Constraints {
  timeWindow: TimeWindow;
  limits: Limits;
  scope?: Scope;
  obligations?: Obligation[];     // Flag-Set; human_in_loop nur als Flag, Schwelle steht in limits.approvalThreshold
}
interface OnChainAnchor { chain: string; block: number; txHash: string; }
interface Validity {              // = A (einzige in sich konsistente Variante)
  issuer: string;
  holderBinding: string;
  issuedAt: string;
  expiresAt: string;
  revocationEndpoint: string;
  signingAlgorithm?: SigningAlgorithm;
  onChainAnchor?: OnChainAnchor;
}
interface AAE { mandate: Mandate; constraints: Constraints; validity: Validity; }
```

**Bewusst getroffene Entscheidungen (Nachweis 1:1 zum Auftrag):**
- `purpose`-Enum v1 (erweiterbar): commerce, data_read, data_write, communication, compute, delegation. *(Weicht bewusst von npm 1.1.0 ab: `administration`/`general` raus, `compute` rein.)*
- `obligations`-Enum v1 (erweiterbar): log_all_actions, tool_allowlist, notify_on_step_up, human_in_loop. Human-Approval-**Schwelle** dedupliziert → `limits.approvalThreshold`; obligations trägt nur das `human_in_loop`-**Flag**.
- `timeWindow` = einfaches absolutes Fenster (notBefore/notAfter), **keine** wiederkehrenden Fenster v1.
- `limits` = nur Pro-Transaktion-Schwellen; **kein** daily-cumulative cap v1 (additiv nachrüstbar).
- `delegation` = A-Feldstruktur inkl. `attenuationOnly`. **Reconciliation mit der Live-`agent_delegation_config` (`constraint_mode ∈ {inherit,restrict,none}`) wird NICHT hier gelöst** → explizit **V1.4-1 D3**. (Pointer, bewusst nicht zu Ende geführt.)
- `Validity` = A; `SigningAlgorithm` aus npm 1.1.0 übernommen.

**Offene Rest-Schemafrage (nicht geraten, Kandidat fürs Cross-Review/Folge):** `tool_allowlist` ist als Obligation-Flag modelliert; *wo* der konkrete Allowlist-Inhalt (welche Tools) getragen wird, ist in v1 **nicht** modelliert — bewusst nicht erfunden.

**Versions-Label (zu korrigieren, NICHT hier):** npm-Paket-`description` „MolTrust Protocol v0.5" ist falsch (Paket ist 1.1.0). Korrektur gehört in den **npm-Paket-Strang**, nicht in diese Kanonisierung / nicht in V1.4-1.

**WP v0.8 §4.6** bleibt als kaputt markiert (doppelter `issuer`-Key) — Korrektur = Whitepaper-Strang, nicht hier.

---

## Appendix B — §2.3 Cross-Review (2026-05-18, security mode) + Iteration

**Durchführung:** `ai_review.py` (GPT-4o + Gemini 2.5 + Perplexity → Claude-Synthese), **ehrlich** (PR #33; EXIT 0 = echter Erfolg, 0 Fehler-Marker, echter 3-Reviewer-Konsens — **keine** manuelle Synthese, wie gefordert für das Autorisierungs-Primitiv). Report: `reviews/20260518_130814_aae-d1-schema-xreview_review.md`.

**Verdikt: `GRUNDLEGEND ÜBERDENKEN`** (stärkste Negativ-Kategorie). Architektur als Stärke bestätigt (ausführbare-Wahrheit-Basislinie, Enum-Typisierung, 3-Schichten, Human-Approval-Dedup — alle drei loben). Aber **drei kritische Konsens-Lücken** machen das Schema **nicht enforcement-/produktionsreif**. **Ehrlich berichtet, nicht beschönigt.**

**Eingearbeitet — eindeutige Robustheits-Härtung (keine Produktentscheidung, normativ für die Implementierung):**
- **B1 [KRITISCH] Finanz-Präzision:** `autonomousThreshold`/`stepUpThreshold`/`approvalThreshold` sind **Integer in kleinster Währungseinheit** (z. B. USDC-µ, Cent), **keine** Floats; pro `Currency` ein definierter `decimals`-Scale; Overflow → **reject**. (Perplexity, in der Divergenz als „kritisch" adjudiziert — Float-Geld ist Antipattern, konsistent mit der String-Ablehnung weiter oben.)
- **B2 [HOCH] Zeit:** `notBefore`/`notAfter` MÜSSEN UTC ISO-8601 mit `Z` sein; Evaluierung MUSS eine Clock-Drift-Toleranz berücksichtigen (Toleranz-**Wert** = Folge-Entscheidung, nicht erfunden — die *Anforderung* ist normativ).
- **B3 [HOCH] Canonicalization:** Die Signatur-Serialisierung des AAE MUSS **RFC 8785 (JCS)** sein — konsistent mit dem bestehenden Registry-JCS+Ed25519 und V1.4-1 D8.

**NICHT eingearbeitet — security-kritisch, Lars-/D3-Entscheidung (bewusst nicht eigenmächtig „gefixt"):**
- **C1 [KRITISCH] Delegation-Enforcement-Gap (alle 3):** Das ist **genau** die von Lars bewusst nach **V1.4-1 D3** verschobene Reconciliation (Schema-`Delegation` ↔ live `agent_delegation_config`). Cross-Review stuft die Verschiebung als Privilege-Escalation-Risiko ein (zwei konkurrierende Delegationsmodelle ohne formales Kompositions-/Attenuation-Modell). **Konsequenz, normativ festgehalten:** die `delegation`-**Feldstruktur** ist kanonisch (A, Lars-entschieden), aber die **Delegations-Semantik ist NICHT enforce-bar**, bis V1.4-1 D3 ein formales Attenuation-/Kompositions- + Mapping-Modell liefert. Dokumentierte akzeptierte Risiko-Verschiebung — kein eigenmächtiges Auslösen.
- **C2 [KRITISCH] `tool_allowlist`-Inhaltsmodell (Gemini+Perplexity):** Bestätigt die offene Rest-Schemafrage oben. `tool_allowlist` ist in v1 **rein deklarativ / inert** — DARF nicht für Enforcement herangezogen werden, bis ein Tool-Constraint-Inhaltsmodell entschieden ist (Lars/Folge; Reviewer-Vorschläge `ToolConstraint[]` vs. externer Referenz-Hash = Designentscheidung, **nicht erfunden**).
- **C3 [HOCH] Versions-Label:** Cross-Review bestätigt das Verwirrungsrisiko; bleibt — wie von Lars entschieden — **npm-Paket-Strang**, nicht hier.

**Folgeliste (nicht erfunden, weitergereicht):** Action/Resource-URI-Syntax + Wildcard-Regeln; Revocation HTTPS/TLS-Pinning + Cache-TTL/Offline; Currency Fiat/Token-Trennung (USDC-Contract-Adresse); Threat-Modeling der künftigen Erweiterungspunkte. WP-v0.8-§4.6-Fix bleibt Whitepaper-Strang.

**Status / ehrliche Konsequenz:** Das Schema ist **strukturell die kanonische D1-Basislinie**, aber der Pflicht-Security-Review sagt `GRUNDLEGEND ÜBERDENKEN` wegen C1–C2. Ich **deklariere PR #41 NICHT eigenmächtig als „mergebar/sicheres finales D1-Schema"** gegen ein GRUNDLEGEND-ÜBERDENKEN-Verdikt eines Autorisierungs-Primitivs. **Lars-Entscheidung nötig:** (a) PR #41 als *strukturelle* D1-Basislinie mergen **mit** den dokumentierten Nicht-Enforcement-Caveats (C1→V1.4-1 D3, C2→Folge-Entscheidung, B1–B3 normativ eingearbeitet) — Enforcement bleibt bis D3/C2 gesperrt; ODER (b) Schema **jetzt** überarbeiten (Delegations-Reconciliation + Tool-Allowlist-Inhaltsmodell vorziehen). **STOP vor Code.**
