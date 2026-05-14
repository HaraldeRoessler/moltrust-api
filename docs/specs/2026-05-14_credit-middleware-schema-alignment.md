# Spec: Credit-Middleware Schema-Alignment Fix

**Datum:** 2026-05-14
**Branch:** `fix/credit-middleware-schema-alignment`
**Autor:** Lars (Decision) + Claude (Spec) + Claude Code (Implementation)
**Status:** Draft — pending Cross-Review
**WORKFLOW-Konformität:** Sektion 1.3 (9-Section-Spec), Sektion 2.3 (Cross-Review-Pflicht, money-handling = security-kritisch)

---

## 1. Goal

Den `credit_middleware`-Code in `app/main.py` (Zeilen ~440-465) so reparieren, dass paid API-Calls korrekt verbucht werden — sowohl im `credit_balances`-Dekrement als auch im `credit_transactions`-Ledger-Eintrag — gegen das tatsächliche Live-DB-Schema.

Sekundär: die durch denselben Root-Cause aufgedeckte Schema-Drift in `init_db.sql` beheben, damit ein Neu-Setup nicht eine andere Tabelle baut als Production hat.

## 2. Non-Goals

- **Kein Backfill** der 4 betroffenen Agents (`did:moltrust:012bfcf64b724400`, `2d843526de08485e`, `f0853f05f64a46ca`, `f34fcbb8b296424c`). Bewusste Write-off-Entscheidung: keine zahlenden Kunden im betroffenen Zeitraum, ~12 Calls fiktiver Gegenwert <$1, manueller Backfill aus request_log wäre mehr Engineering-Risiko als der Betrag wert ist. Dokumentiert als bewusste Entscheidung, nicht als Versäumnis.
- **Kein Redesign** des Credit-Pricing-Modells oder der Tarif-Logik.
- **Kein Refactor** von `app/credits.py` — diese Datei nutzt das Schema bereits korrekt und dient als Pattern-Referenz.
- **Keine UPDATE/DELETE-Operationen** auf `credit_transactions` — die Tabelle hat einen `trg_no_update_credit_tx` append-only Trigger. Append-only bleibt append-only.
- Keine Änderung an der Entscheidung, ob `credit_middleware` überhaupt process-wide läuft — siehe Sektion 9, das ist eine offene Frage für einen Folge-Sprint, nicht für diesen Fix.

## 3. Architecture-Layer-Scope

Explizit betroffene Layer (Pflichtfeld nach Auto-Probe-Lesson):

- **HTTP-Middleware-Layer:** `app/main.py` — der `credit_middleware`-Block. Registriert via `@app.middleware("http")` Zeile 386, läuft process-wide. **Dieser Fix ändert nur die SQL-Statements innerhalb der Middleware, nicht ihre Registrierung oder ihren Scope.** Die process-wide-Frage wird in Sektion 9 als offene Frage festgehalten, aber bewusst NICHT in diesem Sprint angefasst — Scope-Disziplin.
- **Datenbank-Layer:** keine Schema-Änderung an den Live-Tabellen `credit_balances` und `credit_transactions`. Die Live-Tabellen sind korrekt; der Code ist falsch. Eine neue Migration wird hinzugefügt, aber nur als idempotenter No-op-Aligner (siehe Sektion 6).
- **Setup-Layer:** `init_db.sql` wird korrigiert, damit es das Live-Schema widerspiegelt.
- **Test-Layer:** neue Integration-Tests unter `tests/` für den Credit-Deduct-Flow.

Nicht betroffen: `app/credits.py` (bereits korrekt), MCP-Layer, Agent-Layer, Swarm-Layer.

## 4. Data-Model-Changes

**Keine Änderung an Live-DB-Tabellen.** Die Live-Schemas sind die Quelle der Wahrheit:

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
amount        (CHECK > 0 — immer positiv)
tx_type       text NOT NULL
reference     text
description   text
balance_after NOT NULL
created_at    timestamptz
+ Trigger trg_no_update_credit_tx (BEFORE UPDATE OR DELETE → prevent_ledger_mutation)
```

`tx_type`-Werte: kein DB-CHECK-Constraint vorhanden; Convention-enforced durch `app/credits.py`. Verwendete Literale codebase-weit: `'grant'`, `'api_call'`, `'transfer'`. **Entscheidung für diese Spec:** wir fügen KEINEN CHECK-Constraint hinzu (Scope-Disziplin — wäre eine eigene Schema-Migration mit eigenem Risiko), aber dokumentieren die Konvention in `init_db.sql` als Kommentar. CHECK-Constraint wird Backlog-Item.

## 5. API-Contract-Changes

Keine. Endpoints, Request-/Response-Formate, Status-Codes bleiben unverändert. Der Fix ist rein intern: dieselben Calls werden weiterhin akzeptiert und beantwortet, aber jetzt korrekt verbucht.

Ein verhaltensbezogener Unterschied: Calls die bisher **stillschweigend nicht verbucht** wurden (wegen `except Exception` das den SQL-Error schluckte), werden nach dem Fix korrekt dekrementiert. Für einen Agent mit zu wenig Balance bedeutet das: der `WHERE ... AND balance >= $1`-Guard greift jetzt tatsächlich. Das ist beabsichtigtes, korrektes Verhalten — kein Contract-Bruch, aber erwähnenswert.

## 6. Migration-Path

**Schritt 1 — Code-Fix in `app/main.py`:**

UPDATE-Statement (war: `WHERE agent_did = $2`):
```sql
UPDATE credit_balances
SET balance = balance - $1, updated_at = NOW()
WHERE did = $2 AND balance >= $1
RETURNING balance
```
Das `RETURNING balance` liefert den `balance_after`-Wert atomar und race-free — kein separates `SELECT` nötig.

INSERT-Statement (war: falscher Spaltenname, fehlende NOT-NULL-Felder, negativer amount):
```sql
INSERT INTO credit_transactions
  (from_did, to_did, amount, tx_type, reference, description, balance_after, created_at)
VALUES ($1, NULL, $2, 'api_call', $3, $4, $5, NOW())
```
- `from_did` = caller_did (der zahlende Agent)
- `to_did` = NULL (Konvention für Deduct an die Plattform, konsistent mit `app/credits.py`)
- `amount` = cost als **positiver** Wert (nicht `-cost` — verletzt CHECK > 0)
- `tx_type` = `'api_call'` (konsistent mit `app/credits.py`)
- `balance_after` = der Wert aus dem `RETURNING balance` des UPDATE
- Beide Statements in **einer** DB-Transaktion, damit Dekrement und Ledger-Eintrag atomar sind. Wenn der INSERT fehlschlägt, wird auch das UPDATE zurückgerollt — kein Ledger-Drift mehr.

**Wichtig — Guard-Verhalten:** wenn das UPDATE 0 Zeilen zurückgibt (Balance zu niedrig oder DID existiert nicht), darf der INSERT NICHT laufen. Der Code muss das `RETURNING`-Ergebnis prüfen und bei leerem Ergebnis sauber abbrechen (loggen + entsprechende Behandlung, kein stiller `except`).

**Schritt 2 — `init_db.sql` alignen:**

Die `CREATE TABLE credit_balances` in `init_db.sql` an das Live-Schema anpassen: `did` statt `agent_did`, `bigint` statt `INTEGER`, `currency`- und `created_at`-Spalten ergänzen. Falls `credit_transactions` nicht in `init_db.sql` enthalten ist, dort ergänzen (inklusive Trigger-Definition), damit `init_db.sql` wieder vollständige Source-of-Truth ist.

**Schritt 3 — Migration als idempotenter Aligner:**

`migrations/2026-05-14_credit_schema_alignment.sql` — dokumentiert die Schema-Realität für Re-Apply-Sicherheit. Da die Live-DB bereits korrekt ist, ist diese Migration auf Production ein No-op. Sie nutzt `IF NOT EXISTS` / `IF EXISTS`-Guards, sodass sie auf einer frischen DB UND auf der Live-DB sicher läuft. Zweck: Audit-Trail, dass die `agent_did → did`-Realität ein bekannter, dokumentierter Zustand ist — nicht undokumentierte Drift.

**Reihenfolge:** Code-Fix und init_db.sql/Migration sind unabhängig und können in einem Commit-Set zusammen. Kein Live-DB-Eingriff nötig — die DB ist bereits im Zielzustand.

## 7. Rollback-Plan

- **Code-Fix:** `git revert` des Merge-Commits. Der vorherige Zustand ist der bekannte broken-Zustand (stiller Money-Leak), also ist Rollback "zurück zum bekannten Bug" — kein Datenverlust, kein Schaden über den bereits bekannten hinaus.
- **init_db.sql:** reine Datei-Änderung, `git revert` trivial. Betrifft nur Neu-Setups, nicht Production.
- **Migration:** der idempotente Aligner ist ein No-op auf Production. Selbst wenn fälschlich applied, ändert er nichts an der bereits korrekten Live-DB. Kein Rollback nötig; falls gewünscht, einfach die Datei entfernen.
- **Keine** destruktiven Operationen, **keine** Live-Schema-Änderungen → Rollback-Risiko minimal.

## 8. Success-Criteria

1. Ein paid API-Call eines Agents mit ausreichender Balance dekrementiert `credit_balances.balance` um exakt den Cost-Betrag.
2. Derselbe Call erzeugt **genau einen** `credit_transactions`-Eintrag mit korrektem `from_did`, `amount` (positiv), `tx_type='api_call'`, `balance_after` = neuer Balance-Wert.
3. `credit_balances.balance` und die Summe der `credit_transactions` für eine DID sind konsistent (kein Ledger-Drift).
4. Ein paid API-Call eines Agents mit **zu niedriger** Balance: UPDATE betrifft 0 Zeilen, **kein** `credit_transactions`-Eintrag wird erzeugt, der Code behandelt das sauber (kein stiller Crash).
5. Kein `column "agent_did" does not exist` mehr im journal nach Deploy.
6. `init_db.sql` auf einer frischen DB erzeugt exakt das Live-Schema (verifizierbar via Schema-Diff).
7. Integration-Tests (Sektion 9) laufen grün.

## 9. Open Decisions

1. **Process-wide-Middleware-Frage (NICHT in diesem Sprint):** `credit_middleware` läuft via `@app.middleware("http")` auf jedem Request — dieselbe Architektur-Klasse wie die Auto-Probe-Regression. Sollte Credit-Deduction wirklich für jeden Request laufen, oder nur für explizit als "paid" markierte Routen? Das ist eine echte Architektur-Frage, die einen eigenen Spec + Cross-Review verdient. **Für diesen Fix bewusst out-of-scope** — wir reparieren erst den akut falschen SQL-Code, dann denken wir über den Scope nach. Wird Backlog-Item.
2. **tx_type CHECK-Constraint:** soll `credit_transactions.tx_type` einen DB-CHECK-Constraint auf `('grant','api_call','transfer')` bekommen, statt Convention-only? Sinnvoll, aber eigene Schema-Migration mit eigenem Risiko → Backlog-Item, nicht dieser Sprint.
3. **Test-Infrastruktur:** `tests/` hat aktuell nur `test_caep.py`. Dieser Sprint fügt `tests/test_credit_middleware.py` hinzu. Offene Frage: braucht der Test eine eigene Test-DB / Fixture-Setup, oder reicht eine transaktionale Rollback-Fixture gegen die lokale DB? Vorschlag: transaktionale Fixture (Test öffnet Transaktion, macht Assertions, rollt zurück) — kein Datenmüll, kein separates DB-Setup. Cross-Review soll das bewerten.
4. **Backfill endgültig abgelehnt?** Sektion 2 sagt Write-off. Falls Lars später doch backfillen will, ist das ein separates, eigenständiges Item gegen `request_log` — ändert nichts an diesem Fix.

---

## Test-Plan (Detail zu Success-Criteria 7)

`tests/test_credit_middleware.py` — Integration-Tests gegen lokale DB mit transaktionaler Rollback-Fixture:

1. **test_deduct_sufficient_balance:** Agent mit Balance 1000, Call kostet 10 → Balance danach 990, genau 1 transaction-Eintrag, `balance_after=990`, `amount=10`, `tx_type='api_call'`.
2. **test_deduct_insufficient_balance:** Agent mit Balance 5, Call kostet 10 → Balance unverändert 5, kein transaction-Eintrag.
3. **test_deduct_unknown_did:** DID nicht in `credit_balances` → kein Crash, kein transaction-Eintrag, sauberes Logging.
4. **test_ledger_consistency:** nach N Calls ist `balance` = initial_balance − Σ(transaction amounts).
5. **test_atomicity:** simulierter INSERT-Fehler → UPDATE wird zurückgerollt (kein Ledger-Drift).

Tests müssen grün sein, bevor der PR gemerged wird (WORKFLOW Sektion 2.3).

## Cross-Review-Auftrag

Diese Spec geht vor Implementation an ein zweites LLM (GPT-5 / DeepSeek / Kimi) mit dem expliziten Auftrag: "Money-handling code, security-kritisch. Finde: (a) Race-Conditions im UPDATE...RETURNING + INSERT-Flow, (b) Transaktions-Isolation-Probleme, (c) Edge-Cases im Guard-Verhalten bei balance < cost, (d) ob die transaktionale Test-Fixture race-conditions maskieren könnte, (e) übersehene Schema-Constraints." Mindestens eine Review-Iteration vor dem ersten Code.
