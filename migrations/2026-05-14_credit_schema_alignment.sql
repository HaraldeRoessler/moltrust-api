-- Migration: Credit-Schema-Alignment
-- Datum: 2026-05-14
-- Spec: docs/specs/2026-05-14_credit-middleware-schema-alignment.md (V2)
--
-- Zweck: idempotenter Aligner. Auf der Live-DB ist das Schema bereits im
-- Zielzustand — diese Migration ist dort ein No-op. Auf einer frischen DB
-- (oder einer DB die das alte init_db.sql-Schema hat) bringt sie credit_balances
-- und credit_transactions auf den verifizierten Live-Stand.
--
-- Alle Statements sind IF NOT EXISTS / OR REPLACE / DROP-then-CREATE — die
-- Migration ist gefahrlos mehrfach ausfuehrbar.
--
-- HINWEIS zu den drei Indizes idx_credit_tx_from/to/type: diese wurden auf der
-- Live-DB am 2026-05-14 angelegt — urspruenglich unbeabsichtigt waehrend eines
-- SQL-Validate-Laufs, danach als sinnvoll bewertet (Ledger-Tabelle wird nach
-- from_did/to_did/tx_type abgefragt) und hier nachtraeglich legitimiert.
-- IF NOT EXISTS macht das auf Live zum No-op.

BEGIN;

-- credit_balances: auf frischer DB ist die Tabelle ggf. im alten Schema
-- (agent_did/INTEGER). Diese Migration setzt NICHT destruktiv um — sie legt
-- die Tabelle nur an falls sie fehlt. Eine bestehende Tabelle im alten Schema
-- muss manuell migriert werden (out of scope, siehe Spec Section 6 — auf Live
-- bereits korrekt, daher kein ALTER noetig).
CREATE TABLE IF NOT EXISTS credit_balances (
    did text NOT NULL PRIMARY KEY REFERENCES agents(did),
    balance bigint NOT NULL DEFAULT 0 CHECK (balance >= 0),
    currency text NOT NULL DEFAULT 'CREDITS',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS credit_transactions (
    id bigserial PRIMARY KEY,
    from_did text,
    to_did text,
    amount bigint NOT NULL CHECK (amount > 0),
    tx_type text NOT NULL,
    reference text,
    description text,
    balance_after bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_credit_tx_from ON credit_transactions (from_did, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_tx_to   ON credit_transactions (to_did, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_tx_type ON credit_transactions (tx_type);

-- Append-only enforcement. CREATE OR REPLACE ist idempotent; der DROP TRIGGER
-- davor faengt den Fall ab dass ein Trigger mit gleichem Namen aber anderer
-- Definition existiert.
CREATE OR REPLACE FUNCTION prevent_ledger_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'credit_transactions is append-only';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_no_update_credit_tx ON credit_transactions;
CREATE TRIGGER trg_no_update_credit_tx
    BEFORE DELETE OR UPDATE ON credit_transactions
    FOR EACH ROW
    EXECUTE FUNCTION prevent_ledger_mutation();

COMMIT;
