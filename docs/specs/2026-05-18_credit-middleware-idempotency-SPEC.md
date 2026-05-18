# Spec — Credit-Middleware Idempotency (9 Sektionen, WORKFLOW §1.3)

**Status:** ENTWURF — wartet auf Cross-Review (§2.3, Pflicht: Schema-Change auf Bezahl-Pfad) + Lars-Freigabe. KEIN Code vor Freigabe.
**Datum:** 2026-05-18 · **Repo:** moltrust-api · **Branch:** docs/credit-idempotency-spec
**Vorgänger:** Architektur-Brief `2026-05-18_credit-middleware-idempotency-ARCHITEKTUR-BRIEF.md` (PR #30, gemerged). Q1–Q6 dort von Lars beantwortet — verbindlicher Input, hier 1:1 umgesetzt.
**Sequenz:** Diese Spec → Cross-Review → Freigabe → erst danach V1.4-1-Spec (AAE-ins-Credential, beide berühren `/identity/register`-Schema; Idempotency zuerst).

---

## 1. Goal
`credit_middleware` so erweitern, dass ein **client-gelieferter `Idempotency-Key`** Retries / Duplicate-Deliveries auf den kostenpflichtigen Routen **genau einmal** verrechnet und bei einem Duplikat die **ursprüngliche Antwort 1:1 wiedergibt** (voller Response-Replay, Q2), ohne Handler-Re-Run und ohne Doppel-Charge. Heutiger Defekt (verifiziert, `app/main.py` ~`:506-610`): Debit + `INSERT INTO credit_transactions` laufen **nach** `call_next` bei `status_code < 400`; der Ledger-`reference = resolve_endpoint_key(method,path)` (`app/credits.py:83`) ist **pro Endpoint, nicht pro Request** eindeutig → jeder Retry charged erneut. Ursprung als GPT-5-CRITICAL-F aus dem Schema-Alignment-Sprint bewusst ausgelagert.

## 2. Non-Goals
- **Kein** Free-Tier (cost 0) — bucht nicht, kein Ledger, out of scope (Q3).
- **Kein** Pflicht-Header / Breaking Change — Header optional; ohne Header exakt heutiges Verhalten (Q6).
- **Kein** Backfill bestehender Ledger-Zeilen; **kein** `tx_type`-CHECK/FK (eigene Backlog-Items, schema-alignment §9.4/9.5 — unberührt).
- **Kein** Model-/Pipeline-/anderer-Endpoint-Umbau. Nur der Verbuchungs-/Idempotenz-Pfad der Middleware.
- **Kein** V1.4-1-Inhalt (AAE) — separate Folge-Spec.

## 3. Architecture-Layer-Scope  *(WORKFLOW-Pflichtfeld, explizit)*
- **DB (neu):** **eigene, mutable Tabelle `idempotency_keys`** (NICHT Spalte auf `credit_transactions`). **Begründung — verifizierter Constraint:** `credit_transactions` trägt den Append-only-Trigger `trg_no_update_credit_tx` (`BEFORE DELETE OR UPDATE → RAISE EXCEPTION credit_transactions is append-only`). Voller Response-Replay (Q2) braucht **veränderlichen** Zustand (`in_progress`→`completed`, gespeicherte Response). Mutable State auf einer Append-only-Tabelle ist unmöglich. **→ Dies ist eine bewusste, begründete Verfeinerung der Brief-„MUSS-abdecken #2"-Formulierung** („Spalte + Partial-Index auf credit_transactions"): durch den verifizierten Trigger technisch unzulässig für Q2. Intent von MUSS#2 (sichere Online-Migration) bleibt erfüllt — sogar sicherer (CREATE TABLE statt ALTER auf heißer Ledger-Tabelle). **Prominent für Cross-Review/Lars markiert.**
- **API/Middleware:** `credit_middleware` — neuer keyed Pfad (Header vorhanden) zusätzlich zum unveränderten Legacy-Pfad (Header fehlt).
- **Contract:** optionaler Request-Header `Idempotency-Key` (RFC 6648, ohne `X-`); neue Response-Status bei Duplikat (siehe §5).
- **Cleanup:** ein Cron-Job (24h-Retention, Q4).
- **NICHT betroffen:** Auth-/Credential-Pfad, `/identity/register`-Logik selbst, moltrust-web, Free-Tier-Routen, der Append-only-Ledger-Schreibpfad (bleibt 1× immutabel).

## 4. Data-Model-Changes
Neue Tabelle (mutable, eigene Retention — **nicht** dem Append-only-Trigger unterworfen):
```
CREATE TABLE idempotency_keys (
  agent_did      text   NOT NULL,
  endpoint_key   text   NOT NULL,          -- = resolve_endpoint_key(method,path)
  idem_key       text   NOT NULL,          -- client Idempotency-Key (validiert: len<=255)
  status         text   NOT NULL,          -- in_progress | completed
  cost           bigint NOT NULL CHECK (cost > 0),
  response_status int,
  response_body   bytea,                   -- gespeicherte Original-Antwort (Q2 voller Replay)
  attempts       int    NOT NULL DEFAULT 1,
  created_at     timestamptz NOT NULL DEFAULT now(),
  last_attempt_at timestamptz NOT NULL DEFAULT now(),
  completed_at   timestamptz,
  PRIMARY KEY (agent_did, endpoint_key, idem_key)   -- MUSS#3: Key-Subject-Scope, nicht global
);
CREATE INDEX idempotency_keys_cleanup ON idempotency_keys (created_at);
```
- `credit_transactions`: **keine Schema-Änderung** (Append-only, unangetastet). Optional-additiv (eigenes, späteres Item, NICHT in dieser Spec): plain `idem_key`-Spalte rein für Audit — bewusst ausgelassen, hält Scope.
- `credit_balances`: unverändert (bestehendes atomares `UPDATE … WHERE did=$ AND balance>=cost RETURNING balance`).

## 5. API-Contract-Changes
- Request: optionaler Header **`Idempotency-Key`** (RFC 6648). Fehlt er → **Legacy-Pfad, Verhalten unverändert** (Q6, kein Breaking Change). Vorhanden → keyed Pfad. Validierung: 1–255 Zeichen, sonst `400` (kein Charge, kein Handler).
- Duplikat, vorheriger Lauf `completed` → **Replay**: ursprünglicher `response_status` + `response_body` 1:1, zusätzlich Header `Idempotency-Replayed: true`. Kein Charge, kein Handler.
- Duplikat, vorheriger Lauf `in_progress` **innerhalb** `IN_PROGRESS_TTL` (Default 60 s) → **`409 Conflict`** `{"error":"idempotency_in_progress"}`. Kein Charge, kein Handler.
- Duplikat, `in_progress` **älter** als `IN_PROGRESS_TTL` (Erstversuch nach Charge abgestürzt, 5xx-nach-Debit) → Handler **erneut** ausführen **ohne erneuten Charge**, `attempts++`; bei Erfolg Response speichern → ab dann Replay (MUSS#4 / Q2-Begründung).
- Unzureichendes Guthaben → `402` wie heute (Transaktion rollt zurück, kein `idempotency_keys`-Eintrag persistiert).

## 6. Migration-Path
1. `CREATE TABLE idempotency_keys …` — neue Tabelle, **kein** Lock/ALTER auf der heißen Append-only-`credit_transactions` (online-sicher, erfüllt MUSS#2 risikoärmer als die Brief-Skizze).
2. Code-Deploy: Middleware-Keyed-Pfad hinter Header-Präsenz (kein Header ⇒ exakt Alt-Verhalten ⇒ Null-Risiko für bestehende Clients, Q6).
3. Cleanup-Cron: `DELETE FROM idempotency_keys WHERE created_at < now() - interval 24 hours` (Q4-Retention; reguläre Tabelle, löschbar — anders als der Ledger).
4. Reihenfolge gegenüber V1.4-1: **diese Spec zuerst** umsetzen/mergen, dann V1.4-1 (beide berühren `/identity/register`-Pfad, nicht parallel).

## 7. Rollback-Plan
- Code-Rollback: vorheriger Middleware-Stand (keyed Pfad entfällt; Legacy-Pfad war nie verändert) → sofort sicher, da additiv.
- `idempotency_keys` kann stehen bleiben (unbenutzt) oder per `DROP TABLE` entfernt werden — keine FK, keine Ledger-Kopplung, daher folgenlos.
- Kein Daten-Rollback nötig: der Ledger (`credit_transactions`) wurde semantisch nie anders geschrieben (weiterhin 1× immutabler `api_call`-INSERT pro effektivem Charge).

## 8. Success-Criteria
1. Gleicher `Idempotency-Key` + (agent,endpoint) zweimal → **genau ein** Ledger-`api_call`-INSERT, **ein** Debit; zweite Antwort = Byte-Replay der ersten + `Idempotency-Replayed: true`.
2. Kein Header → Ledger/__balance identisch zum heutigen Verhalten (Regressions-Frei-Nachweis).
3. Nebenläufige Doppel-Requests gleicher Key: genau einer charged+führt Handler aus, der andere `409`; **kein** Doppel-Charge (MUSS#1 Atomicity-Test mit zwei echten Connections, analog schema-alignment §9.3 Gruppe B).
4. 5xx-nach-Debit: Charge genau einmal; späterer Retry gleichen Keys produziert/speichert Antwort, danach Replay (MUSS#4).
5. Unterschiedlicher Endpoint/Agent, gleicher Key → **kein** Cross-Talk (MUSS#3).
6. Cleanup-Cron entfernt >24 h-Einträge; `idempotency_keys` wächst nicht unbegrenzt.

## 9. Open Decisions

**9.1 — §9.2 Debit-Position (HIER entschieden, Q5 — nicht entkoppelt).** Ausgangspunkt GPT-5 „Preferred: vor `call_next`". **Entscheidung dieser Spec:** Für den **keyed Pfad** wird in **einer** DB-Transaktion: (a) `INSERT INTO idempotency_keys … ON CONFLICT (agent_did,endpoint_key,idem_key) DO NOTHING`; bei 0 Rows → Duplikat-Behandlung (§5, kein Charge/Handler). (b) Bei Neu-Insert: atomares `UPDATE credit_balances … WHERE balance>=cost` (None→402, Rollback) sonst immutabler Ledger-`INSERT`. **COMMIT — Charge ist durabel BEVOR der Handler läuft** (= GPT-5 „vor `call_next`"). (c) Danach `call_next`, Response erfassen, `UPDATE idempotency_keys SET status=completed,response_*` (mutable Tabelle, erlaubt). Damit erfüllt: MUSS#1 (Check+Debit+Ledger atomar in einer Txn). **Legacy-Pfad (kein Header) bleibt Debit-nach-`call_next` wie heute** — bewusste Scope-/Risiko-Begrenzung; §9.2 ist damit *für den keyed Pfad* entschieden, nicht global umgebaut. *Cross-Review-Frage:* ist „Debit vor `call_next` nur im keyed Pfad, Legacy unverändert" akzeptabel, oder soll §9.2 global gezogen werden (größerer Blast-Radius)?

**9.2 — Q4 Storage-Architektur (ausgearbeitet mit Begründung, nicht geraten).** Optionen: (A) dedizierte Postgres-Tabelle (oben), (B) Redis (Service ist auf der Box **aktiv**, aber vom App-Code **nicht** genutzt), (C) Spalte auf `credit_transactions` — **(C) ausgeschlossen** (Append-only-Trigger, s. §3). **Empfehlung: (A) reines Postgres.** Begründung: MUSS#1 verlangt Idempotenz-Claim **und** Debit **atomar in einer Transaktion**. Liegt der Claim in Redis (separates System), ist Claim+Debit nicht in **einer** Txn → genau die Race, die das Feature verhindern soll, käme zurück (Two-System-Commit-Problem). Redis als optionaler Fast-Pre-Check-Cache wäre denkbar, aber Source-of-Truth muss die transaktionale Postgres-Tabelle sein; für v1 **kein** Redis (keine neue Infra im kritischen Bezahl-Pfad, Reliability: Redis-Ausfall dürfte Paid-Requests nicht kippen). 24h-Retention via Cron-DELETE. *Residual-Entscheidung für Lars:* v1 rein Postgres (Empfehlung) vs. Postgres+Redis-Cache später — **Empfehlung dokumentiert, nicht geraten**.

**9.3 — Response-Storage-Größe.** `response_body bytea` speichert ganze Antworten. Risiko: große Bodies. Vorschlag: Cap (z. B. 256 KB); überschreitet eine Antwort den Cap → `status=completed_no_replay`, Duplikat liefert dann `409`+Hinweis statt Byte-Replay (Charge-Dedup bleibt, voller Replay nur bis Cap). *Cross-Review/Lars:* Cap-Wert + Verhalten-über-Cap bestätigen.

**9.4 — Validierungs-/Format-Politik des Keys.** Vorschlag: opake 1–255-Zeichen-ASCII, serverseitig nicht interpretiert; `agent_did` aus API-Key-Resolution (wie heute), `endpoint_key` aus bestehender `resolve_endpoint_key`. Kein UUID-Zwang (Client-Freiheit). *Cross-Review:* ausreichend?

---
**Cross-Review-Pflicht (WORKFLOW §2.3):** Schema-Change auf Bezahl-Pfad → Cross-Review **vor** Code zwingend. Durchführung: gefixtes `ai_review.py` (meldet seit PR #33 ehrlich). Ergebnis wird als Appendix angehängt; mindestens eine Iteration vor Code.

---

## Appendix A — Cross-Review §2.3 (2026-05-18) + eingearbeitete Iteration

**Durchführung:** `ai_review.py` (GPT-4o + Gemini 2.5 Flash + Perplexity → Claude-Synthese), ehrlich seit PR #33 (EXIT 0 = echter Erfolg). Report: `reviews/20260518_111437_idempotency-spec-xreview_review.md`. **Verdikt: FREIGEBEN nach Einarbeitung** — Kern-Architektur von allen drei als Stärke bestätigt (separate `idempotency_keys`-Tabelle fundiert, PK `(agent,endpoint,key)` verhindert Cross-Talk, Atomicity-Strategie robust, Append-only-Begründung korrekt, Legacy-Backward-Compat). Keine kritische Anmerkung verwirft den Ansatz; alle 🔴 sind Präzisierungen. Diese Iteration arbeitet sie ein (WORKFLOW §2.3: ≥1 Iteration vor Code).

**Normative Einarbeitung (ergänzt/präzisiert die jeweilige Sektion — gilt für die Implementierung):**

- **A1 [KRITISCH→§9.1] Expliziter SELECT nach ON CONFLICT.** Claim ist: `INSERT … ON CONFLICT (agent_did,endpoint_key,idem_key) DO NOTHING RETURNING idem_key`. Bei 0 Rows (Duplikat): `SELECT status,response_status,response_body,last_attempt_at FROM idempotency_keys WHERE (agent_did,endpoint_key,idem_key)=… FOR UPDATE` → dann Verzweigung §5. Der `FOR UPDATE` serialisiert nebenläufige Duplikate.
- **A2 [KRITISCH→§4/§5] Response-Cap konkret.** `RESPONSE_BODY_CAP = 256 KB`. Status-Enum erweitert: `in_progress | completed | completed_no_replay`. Über Cap → `completed_no_replay`; Duplikat darauf → `409 {"error":"idempotency_no_replay"}` (Charge-Dedup bleibt, kein Byte-Replay).
- **A3 [KRITISCH→§5/§9.4] Key-Validierung präzise.** Regex `^[A-Za-z0-9._:-]{1,255}$` (druckbar, keine Steuerzeichen, kein Whitespace, kein Trimming — exakt-match), sonst `400 {"error":"invalid_idempotency_key"}`. Kein Charge/Handler.
- **A4 [HOCH→§9.1] Isolation-Level.** Default `READ COMMITTED` genügt: der atomare Claim erfolgt über das **Unique-PK** (`ON CONFLICT`) — das ist der Serialisierungspunkt, nicht das Isolation-Level; nebenläufige Duplikate werden durch `FOR UPDATE` (A1) serialisiert. SERIALIZABLE erwogen (Synthese-Empfehlung) — **bewusst nicht** nötig, da PK-Constraint die Single-Claim-Garantie gibt; vermeidet Serialization-Failure-Retries auf dem heißen Pfad. Begründet, nicht geraten.
- **A5 [HOCH→§5] `IN_PROGRESS_TTL` konfigurierbar.** Env `IDEMPOTENCY_IN_PROGRESS_TTL_S`, Default 60. Begründung: unterschiedliche Handler-Latenzen.
- **A6 [MITTEL→§5] Parallel-Retry nach TTL atomar.** Das „abgestürzten Slot übernehmen" ist ein bedingtes `UPDATE idempotency_keys SET attempts=attempts+1,last_attempt_at=now() WHERE (…)=… AND status='in_progress' AND last_attempt_at < now()-INTERVAL-TTL RETURNING idem_key` — nur **ein** nebenläufiger Retry gewinnt (RETURNING), die anderen → `409`. Kein Doppel-Handler.
- **A7 [MITTEL→§5] Post-Handler-Persist-Fehler.** Schlägt das `UPDATE … status='completed'` nach erfolgreichem Handler fehl: Response trotzdem an Client (Charge+Handler waren erfolgreich); Eintrag bleibt `in_progress` → späterer Retry läuft über A6 (Handler erneut, kein Re-Charge). Kein Datenverlust am Ledger (der ist committed).

**Offene Entscheidung für Lars (NICHT eingearbeitet — bewusst):**
- **D1 [HOCH] Debit-Timing-Divergenz keyed vs. legacy** — alle drei Reviewer nennen das unterschiedliche Debit-Timing (keyed: vor `call_next`; legacy: nach) als größtes Risiko. **Spec-Empfehlung: keyed-only-vor-`call_next`, Legacy unverändert** — bewusste Risiko-/Blast-Radius-Begrenzung: bestehende Clients (kein Header) sehen exakt Null Verhaltensänderung (Q6, kein Breaking Change), nur der Opt-in-keyed-Pfad bekommt die neue Semantik. Alternative: §9.2 global auf „Debit vor `call_next`" ziehen — sauberer/einheitlich, aber großer Blast-Radius auf allen 12 Paid-Routen. **Entscheidung Lars:** keyed-only (Empfehlung, dokumentierte Risikoakzeptanz) vs. global. Bewusst nicht geraten.

**Perplexity-Fact-Check:** RFC 6648 korrekt, Txn-Pattern wie Stripe/PayPal etabliert, Postgres-`ON CONFLICT`-Syntax korrekt. (Interne MUSS#-Refs extern nicht prüfbar — erwartbar.)
