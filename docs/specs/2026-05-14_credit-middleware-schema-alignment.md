# Spec: Credit-Middleware Schema-Alignment Fix — V2.1

**Datum:** 2026-05-14
**Branch:** `fix/credit-middleware-schema-alignment`
**Autor:** Lars (Decision) + Claude (Spec) + Claude Code (Implementation)
**Status:** V2.1 — Pre-Check-Format-Harmonisierung nach Test-Befund ergänzt
**WORKFLOW-Konformität:** Sektion 1.3 (9-Section-Spec), Sektion 2.3 (Cross-Review durchlaufen)

**Changelog V2 → V2.1:**
- Section 5: Pre-Check-402-Format explizit aufgenommen. Die Gruppe-A-Tests (`test_deduct_insufficient_balance`, `test_error_body_no_balance_disclosure`) deckten auf, dass der Pre-Check (app/main.py ~428) ein abweichendes 402-Format zurückgab (`"Insufficient credits"` mit Balance-Disclosure) statt des in Section 5 definierten `{error, detail}`-Schemas. V2 sagte "Pre-Check bleibt" — gemeint war die Funktion, nicht das Format. V2.1 stellt klar: beide 402-Pfade nutzen dasselbe Schema. Code-Fix: Commit `fdab618`.

**Changelog V1 → V2:**
- Free-Ride-Race adressiert: HTTP-Status-Mutation bei UPDATE=0 (GPT-5 CRITICAL A)
- Error-Path-HTTP-Semantik normativ gemacht (GPT-5 HIGH C)
- asyncpg-Korrektur: `fetchval`/`fetchrow` statt `execute` für RETURNING (GPT-5 MEDIUM A)
- Concurrency-Test mit zwei echten Connections ergänzt (GPT-5 HIGH D)
- Wording: "4 Constraint-Violations" → 3 echte Constraints + 2 Schema-Mismatches (GPT-5 E)
- `amount NOT NULL` verifiziert (Live-DB hat es bereits — kein Schema-Change nötig, GPT-5 HIGH E entkräftet)
- Idempotency als bewusstes Out-of-Scope mit Begründung dokumentiert (GPT-5 CRITICAL F)

---

## 1. Goal

Den `credit_middleware`-Code in `app/main.py` (Zeilen 446-465) so reparieren, dass paid API-Calls korrekt verbucht werden — `credit_balances`-Dekrement und `credit_transactions`-Ledger-Eintrag — gegen das verifizierte Live-DB-Schema. Verbuchungsfehler dürfen nicht mehr still geschluckt werden, sondern müssen sich im HTTP-Status widerspiegeln.

Sekundär: die durch denselben Root-Cause aufgedeckte Schema-Drift in `init_db.sql` beheben.

## 2. Non-Goals

- **Kein Backfill** der 4 betroffenen Agents (`did:moltrust:012bfcf64b724400`, `2d843526de08485e`, `f0853f05f64a46ca`, `f34fcbb8b296424c`). Bewusste Write-off-Entscheidung: keine zahlenden Kunden im betroffenen Zeitraum, ~12 Calls fiktiver Gegenwert <$1. Append-only Trigger bestätigt: Backfill ginge ohnehin nur via neuem INSERT, nie via Korrektur bestehender Rows.
- **Kein Idempotency-Mechanismus** in diesem Sprint. GPT-5 hat zu Recht aufgezeigt, dass Retries/Duplicate-Deliveries doppelt charged werden können, weil `reference` nicht pro Request eindeutig ist. Ein vollständiger Idempotency-Key (Header oder generierte UUID, Unique-Index, `ON CONFLICT DO NOTHING`) ist jedoch ein eigenes Feature mit Schema-Change — das gehört nicht in einen Schema-*Alignment*-Fix. Wird High-Severity-Backlog-Item. Siehe Section 9.1.
- **Keine Middleware-Inversion** (debit vor `call_next`). Das ist GPT-5s "Preferred"-Lösung für die Free-Ride-Race und architektonisch sauberer — aber sie ändert das process-wide-Middleware-Verhalten substantiell und berührt genau die Architektur-Frage, die out-of-scope ist. Diese Spec nutzt die **Minimal-reversible-Variante** (Section 6). Inversion → Folge-Sprint.
- **Kein** `credits.py`-Refactor — nutzt das Schema bereits korrekt, dient als Pattern-Referenz.
- **Keine UPDATE/DELETE** auf `credit_transactions` — append-only Trigger `trg_no_update_credit_tx` würde es ohnehin ablehnen (`RAISE EXCEPTION 'credit_transactions is append-only'`).
- **Kein tx_type CHECK-Constraint**, **keine FK** von `credit_transactions` zu `credit_balances` — beide sinnvoll, beide eigene Schema-Migrationen mit eigenem Risiko → Backlog.

## 3. Architecture-Layer-Scope

- **HTTP-Middleware-Layer:** `app/main.py` Zeilen 446-465 — der Verbuchungs-Block innerhalb `credit_middleware`. Registriert via `@app.middleware("http")` Zeile 386, läuft process-wide. **Dieser Fix ändert die SQL-Statements UND fügt eine HTTP-Status-Mutation bei fehlgeschlagener Verbuchung hinzu — aber NICHT die Registrierung, den Scope oder die Position der Middleware.** Die process-wide-Frage bleibt Section 9.2.
- **Datenbank-Layer:** keine Schema-Änderung an Live-Tabellen. `credit_balances` und `credit_transactions` sind verifiziert korrekt; der Code ist falsch. Neue Migration ist reiner idempotenter No-op-Aligner.
- **Setup-Layer:** `init_db.sql` wird korrigiert (aktuell drei Drift-Layer plus fehlende `credit_transactions`-Tabelle komplett).
- **Test-Layer:** neue Integration-Tests `tests/test_credit_middleware.py`, inklusive eines Concurrency-Tests mit zwei echten DB-Connections.

Nicht betroffen: `app/credits.py`, MCP-Layer, Agent-Layer, Swarm-Layer.

## 4. Data-Model-Changes

**Keine Änderung an Live-DB-Tabellen.** Verifizierte Live-Schemas (Stand 2026-05-14):

`credit_balances`:
```
did        text NOT NULL PRIMARY KEY
balance    bigint NOT NULL DEFAULT 0
currency   text NOT NULL DEFAULT 'CREDITS'
created_at timestamptz NOT NULL DEFAULT now()
updated_at timestamptz NOT NULL DEFAULT now()
```

`credit_transactions`:
```
id            (PK)
from_did      text
to_did        text
amount        bigint NOT NULL CHECK (amount > 0)    ← verifiziert: NOT NULL UND CHECK, 0 NULL-Werte im Live-Ledger
tx_type       text NOT NULL
reference     text
description   text
balance_after NOT NULL
created_at    timestamptz NOT NULL DEFAULT now()    ← verifiziert: DEFAULT vorhanden
+ Trigger trg_no_update_credit_tx: BEFORE DELETE OR UPDATE → prevent_ledger_mutation() → RAISE EXCEPTION 'credit_transactions is append-only'
```

**Korrektur des V1-Wordings:** Die 4 Bug-Dimensionen im aktuellen INSERT sind nicht 4 Constraint-Violations, sondern **3 echte Constraint-Violations** (`tx_type` NOT NULL fehlt, `balance_after` NOT NULL fehlt, `amount = -cost` verletzt `CHECK > 0`) plus **2 Schema-Mismatches** (`agent_did` im UPDATE und im INSERT — Spalte existiert nicht, Laufzeitfehler `column does not exist`). Wegen `amount NOT NULL` würde ein `NULL`-amount zusätzlich blockiert — aber der aktuelle Code liefert `-cost`, nicht NULL, daher ist das CHECK-Constraint der greifende Block.

`tx_type`-Werte: kein DB-CHECK-Constraint, Convention-enforced durch `credits.py`. Codebase-Literale: `'grant'` (Inflow), `'api_call'` (Outflow), `'transfer'`. Diese Spec nutzt `'api_call'`. CHECK-Constraint bleibt Backlog.

## 5. API-Contract-Changes

Eine bewusste, normative Änderung am Verhalten — kein Bruch des Request-/Response-Formats, aber eine Korrektur der HTTP-Semantik:

**Bisher:** Verbuchungsfehler (Schema-Error, Race, DB-Fehler) werden in `except Exception` geloggt, der Client erhält trotzdem `2xx`. Stiller Money-Leak.

**Neu (normativ):**
- Verbuchung erfolgreich → Status unverändert (der Status den der Handler gesetzt hat).
- `UPDATE` betrifft 0 Zeilen (Balance zu niedrig, DID unbekannt, oder Race-Fenster) → Response wird auf **HTTP 402 Payment Required** mutiert, mit strukturiertem JSON-Body. **Kein** `credit_transactions`-Eintrag.
- Unerwarteter DB-Fehler im Verbuchungs-Block → Response wird auf **HTTP 500** mutiert, strukturierter JSON-Body. **Niemals** stiller `2xx`-Erfolg bei Verbuchungsfehler.

JSON-Error-Body-Schema (konsistent für 402 und 500):
```json
{"error": "<kurzer code>", "detail": "<menschenlesbar>"}
```
Für 402: `error: "insufficient_credits"`. Der Body nennt **nicht** den exakten Balance-Stand (GPT-5 LOW C — bewusste Entscheidung: keine Balance-Disclosure im Error-Body, der Caller kann seinen Stand über den dedizierten Balance-Endpoint abfragen).

**Pre-Check-402-Format (V2.1):** Es gibt zwei Stellen die ein 402 zurückgeben können — den advisory Pre-Check (vor `call_next`, filtert offensichtlich zahlungsunfähige Requests früh) und den Deduct-Block (nach `call_next`, bei `UPDATE=0`). **Beide MÜSSEN dasselbe Schema liefern:** `{"error": "insufficient_credits", "detail": "..."}`, ohne Balance-Disclosure. Der Pre-Check gab ursprünglich ein abweichendes Format zurück (`"Insufficient credits"` mit `balance`/`required`/`pricing_url`) — das wurde harmonisiert (Commit `fdab618`). Ein Client darf nicht je nach Code-Pfad ein anderes 402-Format bekommen.

**Hinweis zur Free-Ride-Race:** Mit der 402-Mutation bei `UPDATE=0` ist das Race-Fenster für den *Ledger* vollständig geschlossen (atomares `UPDATE ... WHERE balance >= cost RETURNING balance`) und für den *HTTP-Status* ebenfalls — der zweite konkurrierende Request erhält 402 statt 200. Was nicht verhindert wird: der Handler des zweiten Requests **lief bereits**, bevor die Mutation greift. Da die durch `credit_middleware` geschützten Endpoints lesende/berechnende Calls sind (Trust-Score etc.), ist ein einzelner gelaufener-aber-mit-402-quittierter Handler-Durchlauf im exakten Race-Fenster kein Schaden — der Client bekommt 402, hat also kein verwertbares Ergebnis. Die vollständige Vermeidung (Handler gar nicht erst aufrufen) ist die Inversion aus Section 2 / Section 9.2.

## 6. Migration-Path

**Schritt 1 — Code-Fix in `app/main.py`, Ersatz für Zeilen 446-465:**

```python
if response.status_code < 400:
    deduct_failed = False
    try:
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                from app.credits import resolve_endpoint_key
                ref = resolve_endpoint_key(method, path)
                # Atomarer Deduct: WHERE balance >= cost schliesst Race + Insufficient
                # in einem Statement. RETURNING liefert balance_after race-free.
                new_balance = await conn.fetchval(
                    "UPDATE credit_balances "
                    "SET balance = balance - $1, updated_at = NOW() "
                    "WHERE did = $2 AND balance >= $1 "
                    "RETURNING balance",
                    cost, caller_did,
                )
                if new_balance is None:
                    # 0 Zeilen: Balance zu niedrig, DID unbekannt, oder Race-Fenster.
                    # Kein Ledger-Eintrag. Transaktion ist effektiv leer -> sauberer Abschluss.
                    deduct_failed = True
                    logger.warning(
                        "Credit deduct: insufficient/race for %s (cost=%s)",
                        caller_did, cost,
                    )
                else:
                    await conn.execute(
                        "INSERT INTO credit_transactions "
                        "(from_did, to_did, amount, tx_type, reference, "
                        "description, balance_after) "
                        "VALUES ($1, NULL, $2, 'api_call', $3, $4, $5)",
                        caller_did, cost, ref, f"API call: {ref}", new_balance,
                    )
    except Exception as e:
        # Unerwarteter DB-Fehler: NIEMALS stiller 2xx-Erfolg.
        logger.error("Credit deduction DB error for %s: %s", caller_did, e)
        return JSONResponse(
            status_code=500,
            content={"error": "credit_processing_error",
                     "detail": "Credit deduction failed unexpectedly."},
        )
    if deduct_failed:
        return JSONResponse(
            status_code=402,
            content={"error": "insufficient_credits",
                     "detail": "Not enough credits for this call."},
        )
```

**Asyncpg-Korrektur (GPT-5 MEDIUM A):** `conn.fetchval(...)` liefert den ersten Spaltenwert der ersten Zeile bzw. `None` bei 0 Zeilen — das ist exakt das gewünschte Verhalten für `RETURNING balance`. `conn.execute(...)` hätte nur den Status-String (`"UPDATE n"`) geliefert und die `RETURNING`-Spalte verworfen.

**Bindings explizit (GPT-5 MEDIUM F):**
- UPDATE: `$1 = cost`, `$2 = caller_did`
- INSERT: `$1 = caller_did` (from_did), `$2 = cost` (amount, positiv), `$3 = ref` (reference), `$4 = "API call: {ref}"` (description), `$5 = new_balance` (balance_after). `to_did = NULL` fix, `tx_type = 'api_call'` fix, `created_at` über DEFAULT.

**Transaktions-Isolation (GPT-5 B):** Die Transaktion umschließt **nur** UPDATE + INSERT, läuft **nicht** über `call_next` — `call_next` ist zu diesem Zeitpunkt längst zurück. Keine langlebigen Locks, kein Contention mit `transfer`/`grant`-`SELECT ... FOR UPDATE`. Der Pre-Check via `get_balance` (Zeile 433, vor `call_next`) bleibt — er ist explizit **advisory**: er filtert offensichtlich zahlungsunfähige Requests früh, aber die **finale Autorisierung kommt ausschließlich aus dem `UPDATE`-Ergebnis**. Ein zwischen Pre-Check und Deduct entstandenes Race wird durch das atomare `WHERE balance >= cost` korrekt aufgelöst.

**Schritt 2 — `init_db.sql` alignen:** `CREATE TABLE credit_balances` an Live-Schema anpassen (`did` statt `agent_did`, `bigint` statt `INTEGER`, `currency` + `created_at` ergänzen). `credit_transactions` komplett ergänzen — Tabelle, `amount bigint NOT NULL CHECK (amount > 0)`, `created_at timestamptz NOT NULL DEFAULT now()`, Funktion `prevent_ledger_mutation()`, Trigger `trg_no_update_credit_tx`. `tx_type`-Konvention als SQL-Kommentar dokumentieren.

**Schritt 3 — Migration als idempotenter Aligner:** `migrations/2026-05-14_credit_schema_alignment.sql` mit `IF NOT EXISTS` / `IF EXISTS`-Guards. Auf Production No-op (DB bereits im Zielzustand), auf frischer DB voll funktional. Zweck: Audit-Trail, dass die `did`-Realität dokumentiert und kein undokumentierter Drift ist.

**Reihenfolge:** Code-Fix, init_db.sql und Migration sind unabhängig, können in einem Commit-Set zusammen. Kein Live-DB-Eingriff.

## 7. Rollback-Plan

- **Code-Fix:** `git revert` des Merge-Commits. Vorheriger Zustand = bekannter broken-Zustand (stiller Leak). Rollback = "zurück zum bekannten Bug", kein zusätzlicher Schaden, kein Datenverlust.
- **init_db.sql / Migration:** reine Datei-Änderungen, `git revert` trivial. Migration ist No-op auf Production — selbst fälschlich applied ändert sie nichts.
- **Verhaltensänderung im Rollback-Fall:** Nach Revert kämen wieder stille `2xx` bei Verbuchungsfehler statt 402/500. Das ist akzeptabel als temporärer Rückfallzustand, da keine zahlenden Kunden betroffen.
- **Keine** destruktiven Operationen, **keine** Live-Schema-Änderungen → Rollback-Risiko minimal.

## 8. Success-Criteria

1. Paid API-Call, ausreichende Balance → `credit_balances.balance` exakt um `cost` dekrementiert, Status unverändert.
2. Derselbe Call → **genau ein** `credit_transactions`-Eintrag: `from_did = caller`, `to_did = NULL`, `amount = cost` (positiv), `tx_type = 'api_call'`, `balance_after = new_balance`.
3. `credit_balances.balance` = `initial_balance − Σ(api_call amounts)` für eine DID — kein Ledger-Drift.
4. Paid API-Call, **zu niedrige** Balance → `UPDATE` betrifft 0 Zeilen, **kein** `credit_transactions`-Eintrag, Client erhält **HTTP 402** mit `error: "insufficient_credits"`.
5. Paid API-Call, **unbekannte DID** → `UPDATE` betrifft 0 Zeilen, kein Eintrag, **HTTP 402** (gleicher Pfad wie 4).
6. Unerwarteter DB-Fehler im Verbuchungs-Block → Client erhält **HTTP 500** mit `error: "credit_processing_error"`, niemals stiller `2xx`.
7. Zwei **gleichzeitige** Requests, gleiche DID, `balance == cost` → genau einer erhält 200, einer erhält 402; **genau ein** `credit_transactions`-Eintrag; `balance` danach exakt 0.
8. Kein `column "agent_did" does not exist` mehr im journal nach Deploy.
9. `init_db.sql` auf frischer DB erzeugt exakt das Live-Schema (Schema-Diff verifizierbar).
10. Alle Integration-Tests (Section 9.3 / Test-Plan) grün.

## 9. Open Decisions

**9.1 — Idempotency (bewusst Out-of-Scope, High-Backlog-Item).** Retries und Duplicate-Deliveries können doppelt charged werden, weil `reference = resolve_endpoint_key(method, path)` nicht pro Request eindeutig ist. Vollständige Lösung: Idempotency-Key pro Request (`X-Idempotency-Key`-Header oder serverseitig generierte UUID), Unique-Index, `INSERT ... ON CONFLICT DO NOTHING`, bei Konflikt das vorherige Ergebnis replayen. Das ist ein Schema-Change + neues Feature → eigener Spec, eigener Sprint. **Backlog-Item, High-Severity.** Begründung für Out-of-Scope: ein Schema-*Alignment*-Fix soll den Code an das existierende Schema angleichen, nicht neue Schema-Features einführen — sonst Scope-Creep in genau dem Sprint, der Disziplin demonstrieren soll.

**9.2 — Process-wide-Middleware-Frage (Out-of-Scope, eigener Sprint).** `credit_middleware` läuft via `@app.middleware("http")` auf jedem Request — dieselbe Architektur-Klasse wie die Auto-Probe-Regression. Offen: soll Credit-Deduction wirklich für jeden Request laufen, oder nur für explizit als "paid" markierte Routen? Und: soll der Debit **vor** `call_next` passieren (GPT-5s "Preferred", verhindert dass der Handler im Race-Fall überhaupt läuft)? Beides verdient einen eigenen Spec + Cross-Review. Backlog-Item.

**9.3 — Test-Infrastruktur.** `tests/` hat aktuell nur `test_caep.py`. Dieser Sprint fügt `tests/test_credit_middleware.py` hinzu. **Entscheidung nach GPT-5 HIGH D:** die Tests für Criteria 1-6 nutzen eine transaktionale Rollback-Fixture (Test öffnet Transaktion, Assertions, Rollback — kein Datenmüll). **Aber Criterion 7 (Concurrency) MUSS zwei separate, non-transaktionale DB-Connections nutzen** — eine transaktionale Single-Connection-Fixture würde die Requests serialisieren und genau die Free-Ride-Race maskieren, die der Test nachweisen soll. Der Concurrency-Test räumt seine Test-DID am Ende explizit auf (DELETE auf `credit_balances` für die Test-DID; `credit_transactions` kann wegen append-only Trigger nicht gelöscht werden — daher eine eindeutige Test-DID pro Lauf verwenden, z.B. mit UUID-Suffix, damit kein Cross-Run-Interferenz entsteht).

**9.4 — Backfill endgültig abgelehnt.** Section 2 sagt Write-off. Falls Lars später doch backfillen will: separates Item, neuer INSERT mit `tx_type='api_call'` + `description="backfill: missed deduct 2026-05-12..."` (kein UPDATE wegen append-only Trigger). Ändert nichts an diesem Fix.

---

## Test-Plan (Detail zu Success-Criterion 10)

`tests/test_credit_middleware.py`:

**Gruppe A — transaktionale Rollback-Fixture (Criteria 1-6):**
1. `test_deduct_sufficient_balance` — Balance 1000, cost 10 → Balance 990, genau 1 Eintrag, `balance_after=990`, `amount=10`, `tx_type='api_call'`, `from_did=caller`, `to_did=NULL`.
2. `test_deduct_insufficient_balance` — Balance 5, cost 10 → Balance unverändert 5, kein Eintrag, HTTP 402.
3. `test_deduct_unknown_did` — DID nicht in `credit_balances` → kein Eintrag, HTTP 402.
4. `test_ledger_consistency` — nach N Calls: `balance == initial − Σ(amounts)`.
5. `test_db_error_returns_500` — simulierter DB-Fehler im Verbuchungs-Block (z.B. gepatchte `fetchval`-Exception) → HTTP 500, `error: "credit_processing_error"`.
6. `test_error_body_no_balance_disclosure` — 402-Body enthält **nicht** den exakten Balance-Wert.

**Gruppe B — non-transaktionale Concurrency-Fixture, zwei echte Connections (Criterion 7):**
7. `test_concurrent_deduct_same_did` — Test-DID mit UUID-Suffix, Balance == cost. `asyncio.gather` mit 2 parallelen Requests. Assert: genau einer 200, einer 402; genau ein `credit_transactions`-Eintrag; `balance` danach exakt 0. Cleanup: DELETE der Test-DID aus `credit_balances` (transactions bleiben wegen append-only Trigger, daher eindeutige DID pro Lauf).

Alle Tests grün, bevor PR gemerged wird (WORKFLOW Sektion 2.3).

## Cross-Review-Status

**V1 → GPT-5 Cross-Review durchlaufen.** Findings eingearbeitet: 1 CRITICAL (Free-Ride-Race → Section 5 HTTP-Status-Mutation), 1 CRITICAL als dokumentiertes Out-of-Scope (Idempotency → Section 9.1), 4 HIGH (Error-Path-Semantik, UPDATE=0→402, Test-Fixture-Concurrency, amount-NOT-NULL — letzteres durch Server-Verifikation entkräftet), 2 Wording-Korrekturen (Constraint-Zählung, asyncpg-API). Verbleibende Out-of-Scope-Punkte sind in Section 9 mit Begründung dokumentiert.

**V2 benötigt keinen zweiten vollen Cross-Review-Pass** — die CRITICAL- und HIGH-Findings sind entweder eingearbeitet oder als bewusste, begründete Scope-Entscheidung dokumentiert. Falls Claude Code bei der Implementation auf eine Abweichung von dieser Spec stößt: stop, Spec-Amendment, kein Ad-hoc-Abweichen.
