# Architektur-Brief — Credit-Middleware Idempotency

**Typ:** WORKFLOW §3.3 Architektur-Brief (1-Pager). **KEINE 9-Sektionen-Spec, KEIN Code.**
**Datum:** 2026-05-18 · **Status:** ENTWURF — wartet auf Lars-Freigabe.
**Quelle:** BACKLOG „Credit-Middleware Idempotency-Mechanismus" (High, Open) ·
schema-alignment-Spec §9.1 (GPT-5 Cross-Review CRITICAL F) ·
V1.4-1-Vorbedingung (AAE-ins-Credential ist hierdurch geblockt; „Idempotency zuerst").
**Zweck:** Scope **nicht raten** — Entscheidungsraum aufzeigen, Produktfragen an Lars
eskalieren. Stufe 2 (9-Sektionen-Spec + Cross-Review) erst nach Freigabe dieses Briefs.

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
- **Contract:** ggf. neuer Request-Header `X-Idempotency-Key` (öffentliche API-Fläche).
- **Kein** Auth-/Credential-Pfad, **kein** moltrust-web. (V1.4-1 ist separat.)

## Scope-Grenze
**Drin:** Doppel-Charge-Verhinderung im Verbuchungs-Block der kostenpflichtigen Routen.
**Draußen / NICHT in Stufe 2 ohne separate Entscheidung:** Free-Tier-Routen;
die §9.2-Frage „Debit vor statt nach `call_next` / Middleware nur für paid Routen";
Voll-Response-Replay (Speicherung & Wiedergabe ganzer Antworten) sofern Lars nur
Charge-Dedup will; Backfill (§9.4 abgelehnt).

## Offene Produktfragen an Lars (NICHT geraten — blocken Stufe 2)
1. **Key-Quelle:** Client-`X-Idempotency-Key`-Header (dedupt Client-Retries
   *über* Requests) vs. server-generierte UUID (dedupt nur *innerhalb* eines
   Requests, nicht über Client-Retries) vs. beides? — semantisch sehr verschieden.
2. **Replay-Semantik:** bei Konflikt nur **nicht erneut charchen** (Handler darf
   re-laufen) ODER **vorherige Antwort 1:1 wiedergeben** (braucht Response-Storage =
   deutlich größerer Scope)? BACKLOG sagt „vorheriges Ergebnis replayen" — bestätigen.
3. **Endpoint-Scope:** alle ~13 paid Routen, oder nur mutierende `POST/PATCH`
   (paid `GET` wie `/identity/verify` — re-charge bei Retry akzeptabel?).
4. **Key-Window:** unbegrenzt unique vs. TTL-Fenster (append-only Tabelle → Index
   wächst unbegrenzt; Bestandszeilen haben keinen Key → NULL-/Partial-Index-Politik).
5. **Kopplung §9.2:** Idempotency-Check-Position relativ zu `call_next` hängt an der
   noch offenen „Debit-vor-vs-nach"-Frage — gemeinsam entscheiden oder entkoppeln?
6. **Header-Politik:** `X-Idempotency-Key` optional (Fallback?) oder pflicht für
   paid Routen (Breaking Change für bestehende Clients)?

## Nächster Schritt
**STOP — Freigabe abwarten.** Nach Freigabe + Beantwortung von Q1–Q6: Stufe 2 =
9-Sektionen-Spec (`docs/specs/`) + verpflichtender Cross-Review (§2.3, Schema-Change
auf Bezahl-Pfad), danach V1.4-1-Spec. Kein Code vor Spec-Freigabe.
