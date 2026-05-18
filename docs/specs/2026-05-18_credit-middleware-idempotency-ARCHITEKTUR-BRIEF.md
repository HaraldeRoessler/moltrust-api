# Architektur-Brief — Credit-Middleware Idempotency

**Typ:** WORKFLOW §3.3 Architektur-Brief (1-Pager). **KEINE 9-Sektionen-Spec, KEIN Code.**
**Datum:** 2026-05-18 · **Status:** FREIGEGEBEN (Option a). Multi-AI-`/review` 2026-05-18 → FREIGEBEN; Q1–Q6 von Lars beantwortet 2026-05-18; 2 Review-Tweaks eingefaltet. **Stufe 2 startet erst nach Merge dieses Briefs (PR #30).**
**Quelle:** BACKLOG „Credit-Middleware Idempotency-Mechanismus" (High, Open) ·
schema-alignment-Spec §9.1 (GPT-5 Cross-Review CRITICAL F) ·
V1.4-1-Vorbedingung (AAE-ins-Credential ist hierdurch geblockt; „Idempotency zuerst").
**Zweck:** Scope **nicht raten** — Entscheidungsraum aufzeigen, Produktfragen an Lars
eskalieren (beantwortet, siehe unten). Stufe 2 (9-Sektionen-Spec + Cross-Review) erst nach Merge dieses Briefs.

## Problem (verifiziert, read-only)
`credit_middleware` (`app/main.py:506-610`, global `@app.middleware("http")`) bucht
**nach** `call_next` bei `response.status_code < 400`: atomarer
`UPDATE credit_balances … WHERE balance >= cost RETURNING balance` + `INSERT INTO
credit_transactions (…, reference, …)`. Der Ledger-`reference` =
`resolve_endpoint_key(method, path)` (`app/credits.py:83`) ist **pro Endpoint, nicht
pro Request eindeutig** (z. B. konstant `"POST /identity/register"`). Folge: Retries
und Duplicate-Deliveries (Client-Retry, LB-Replay, Doppel-Submit) **charged denselben
Agent mehrfach**. `credit_transactions` hat **keine** `idempotency_key`-Spalte
(verifiziert: existiert nirgends in Code/SQL) und ist append-only (kein DELETE,
Trigger) → Korrektur ist ein **Schema-Change**, kein Code-Fix.

## Was idempotent werden soll
- **Trigger:** genau der Verbuchungs-Block in `credit_middleware` (Deduct + Ledger-INSERT).
- **Endpoints:** die in `ENDPOINT_COSTS` als kostenpflichtig (cost ≥ 1) markierten
  ~13 Routen (u. a. `POST /identity/register`, `GET /identity/verify/{did}`,
  `POST /credentials/issue|verify`, `POST /reputation/rate`,
  `GET /a2a/agent-card/{did}`, `POST /sports/*commit`, `POST /sports/signals/register`).
  Free-Tier (cost 0) bucht nicht → **außerhalb** des Scopes.

## Warum (Impact)
Doppel-Charge auf einem Bezahl-Pfad ist direkter Geld-/Vertrauensschaden und war ein
GPT-5-**CRITICAL**-Finding, das aus dem Schema-Alignment-Sprint **bewusst** als
eigenes High-Backlog-Item ausgelagert wurde (kein Scope-Creep). Blockiert zusätzlich
V1.4-1 (AAE-ins-Credential), das laut BACKLOG/Reihenfolge erst **nach** Idempotency läuft.

## Betroffene Layer (Architecture-Layer-Scope — WORKFLOW-Pflichtfeld)
- **DB:** neue Spalte `credit_transactions.idempotency_key` + Unique-Constraint/Index
  (Partial/NULL-tolerant wegen append-only Bestandsdaten ohne Key). Migration auf
  live, populierter, append-only Tabelle.
- **API/Middleware:** `credit_middleware` (Insert-Pfad), evtl. Key-Ableitung/-Annahme.
- **Contract:** neuer **optionaler** Request-Header `Idempotency-Key` (ohne `X-`-Präfix,
  RFC 6648; öffentliche API-Fläche; kein Breaking Change — Q1/Q6).
- **Kein** Auth-/Credential-Pfad, **kein** moltrust-web. (V1.4-1 ist separat.)

## Scope-Grenze
**Drin:** Doppel-Charge-Verhinderung im Verbuchungs-Block der kostenpflichtigen Routen;
**voller Response-Replay** inkl. Response-Storage (Q2 — wegen 5xx-nach-Debit); die
**§9.2-„Debit vor vs. nach `call_next`"-Entscheidung** wird in Stufe 2 mitgetroffen
(Q5 — nicht entkoppelt).
**Draußen:** Free-Tier-Routen (cost 0); Backfill (§9.4 abgelehnt).

## Produktfragen an Lars — beantwortet 2026-05-18 (Lars)
Verbindlicher Input für die Stufe-2-9-Sektionen-Spec. Frage verbatim, Entscheidung darunter.

1. **Key-Quelle:** Client-`Idempotency-Key`-Header (dedupt Client-Retries
   *über* Requests) vs. server-generierte UUID (dedupt nur *innerhalb* eines
   Requests, nicht über Client-Retries) vs. beides? — semantisch sehr verschieden.
   → **Entscheidung:** Client-Header; Name `Idempotency-Key` (ohne `X-`, RFC 6648).
2. **Replay-Semantik:** bei Konflikt nur **nicht erneut charchen** (Handler darf
   re-laufen) ODER **vorherige Antwort 1:1 wiedergeben** (braucht Response-Storage =
   deutlich größerer Scope)? BACKLOG sagt „vorheriges Ergebnis replayen" — bestätigen.
   → **Entscheidung:** Voller Replay (BACKLOG bestätigt). Begründung: der
   5xx-nach-Debit-Fall (Cross-Review) macht reines Charge-Dedup unzureichend.
   Stufe-2-Spec muss Response-Storage abdecken.
3. **Endpoint-Scope:** alle ~13 paid Routen, oder nur mutierende `POST/PATCH`
   (paid `GET` wie `/identity/verify` — re-charge bei Retry akzeptabel?).
   → **Entscheidung:** ~13 paid `ENDPOINT_COSTS`-Routen; Free-Tier raus.
4. **Key-Window:** unbegrenzt unique vs. TTL-Fenster (append-only Tabelle → Index
   wächst unbegrenzt; Bestandszeilen haben keinen Key → NULL-/Partial-Index-Politik).
   → **Entscheidung:** 24h-Retention als Default. Die Storage-Architektur
   (Redis/slim-table vs. in `credit_transactions`) ist Teil dieser Frage — in der
   Stufe-2-Spec als Sub-Entscheidung mit Begründung ausarbeiten, **nicht raten**.
5. **Kopplung §9.2:** Idempotency-Check-Position relativ zu `call_next` hängt an der
   noch offenen „Debit-vor-vs-nach"-Frage — gemeinsam entscheiden oder entkoppeln?
   → **Entscheidung:** **NICHT entkoppeln.** Die §9.2-„Debit vor vs. nach
   `call_next`"-Frage wird Teil des Idempotency-Sprints — architektonisch untrennbar
   von der Idempotency-Check-Position. GPT-5s „Preferred: vor `call_next`" ist der
   Ausgangspunkt. Stufe 2 entscheidet das in der 9-Sektionen-Spec mit, mit Cross-Review.
6. **Header-Politik:** `Idempotency-Key` optional (Fallback?) oder pflicht für
   paid Routen (Breaking Change für bestehende Clients)?
   → **Entscheidung:** Header **optional**, NICHT required (kein Breaking Change).
   Wer ihn schickt, bekommt Idempotenz; wer nicht, altes Verhalten.

## Nächster Schritt
**FREIGEGEBEN (Option a).** Stufe 2 (9-Sektionen-Spec in `docs/specs/` + verpflichtender
Cross-Review §2.3, Schema-Change auf Bezahl-Pfad) **darf erst nach Merge dieses Briefs
(PR #30) starten**; danach die V1.4-1-Spec. Kein Code vor Spec-Freigabe.

### Stufe-2-9-Sektionen-Spec MUSS abdecken (Cross-Review-Konsens 2026-05-18 + Q-Antworten)
1. **Transaction-Atomicity:** Idempotency-Check + Debit (`UPDATE credit_balances`) +
   Ledger-`INSERT` in **einer** DB-Transaktion (sonst Race trotz Unique-Index).
2. **Online-Migration:** live, populierte, append-only Tabelle — Spalte nullable
   hinzufügen → Backfill → `CREATE UNIQUE INDEX CONCURRENTLY … WHERE idempotency_key
   IS NOT NULL` (partial, NULL-tolerant für Bestandszeilen).
3. **Key-Subject-Scope:** Eindeutigkeit pro `(agent, endpoint, idempotency_key)`,
   nicht global (Cross-Tenant-Kollision vermeiden).
4. **Conflict-/HTTP-Semantik:** Status/Body bei Duplikat plus 4xx/5xx-Verhalten —
   insbesondere **5xx-nach-Debit → Response-Replay** (begründet Q2 = voller Replay).
5. **§9.2-Debit-Position mitentscheiden:** „Debit vor vs. nach `call_next`"
   (Q5, nicht entkoppelt); GPT-5s „Preferred: vor `call_next`" ist Ausgangspunkt.
6. **Q4-Storage-Sub-Entscheidung:** 24h-Retention-Default; Redis/slim-table vs.
   in `credit_transactions` mit Begründung ausarbeiten (nicht raten).
